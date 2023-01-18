import json
from datetime import datetime
from os import path
from uuid import uuid4

import requests
import yaml
from dateutil.tz import tzlocal
from flask import Blueprint, request, abort
from kubernetes.client import ApiException
from requests import Timeout, HTTPError
from werkzeug.exceptions import HTTPException

import app.interface.dind as dind
import app.interface.ff as ff
import app.interface.pind as pind
import app.interface.ssu as ssu
from app.const import MIGRATABLE_ANNOTATION, MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_ACTIVE, \
    INTERFACE_ANNOTATION, INTERFACE_DIND, LAST_APPLIED_CONFIG, INTERFACE_PIND, \
    INTERFACE_FF, BYPASS_ANNOTATION, INTERFACE_SSU
from app.env import env, FRONTMAN_IMAGE, SSU_INTERFACE_ENABLE
from app.kubernetes_client import create_pod, update_pod_label, wait_pod_ready
from app.lib import get_information, get_pod, lock_pod, release_pod, update_pod_restart, update_pod_redirect, \
    delete_pod

migrate_api_blueprint = Blueprint('migrate_api', __name__)


@migrate_api_blueprint.route("/migrate", methods=['POST'])
def migrate_api():
    body = request.get_json()

    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    destination_url = body.get('destinationUrl')
    if destination_url is None:
        abort(400, 'destinationUrl is null')

    migration_id = uuid4().hex[:8]

    report = migrate(body, migration_id)

    return {
        'message': "migration complete!",
        'migration_id': migration_id,
        **report
    }


def migrate(body, migration_id):
    start_time = datetime.now(tz=tzlocal())

    name = body['name']
    namespace = body.get('namespace', 'default')
    destination_url = body['destinationUrl']
    selected_interface = body.get('interface')

    src_pod = get_pod(name, namespace)
    if not bool(src_pod['metadata']['annotations'].get(MIGRATABLE_ANNOTATION)):
        abort(400, "pod is not migratable")
    if src_pod['metadata']['annotations'][START_MODE_ANNOTATION] != START_MODE_ACTIVE:
        abort(400, "Pod is not migratable")
    if src_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION):
        abort(409, "Pod is being migrated")

    src_pod = lock_pod(name, namespace, migration_id)
    des_pod_created = False
    frontman_created = False

    try:
        des_info = ping_destination(destination_url)
        interface = select_interface(src_pod, des_info, selected_interface)
        interface.get_name()

        des_pod_template = interface.generate_des_pod_template(src_pod)
        des_pod_created, des_pod_info = interface.create_des_pod(des_pod_template, des_info, delete_des_pod)
        frontman_created = create_or_update_frontman(src_pod, keeper_mode=body.get('keep'))
        created_time = datetime.now(tz=tzlocal())

        checkpoint_id = uuid4().hex[:8]
        src_pod = interface.checkpoint_and_transfer(src_pod, des_pod_info, checkpoint_id)
        # todo actual checkpoint time (interface)
        checkpointed_time = datetime.now(tz=tzlocal())

        restore_and_release_des_pod(src_pod, destination_url, migration_id, checkpoint_id, interface, des_pod_template)
    except Exception as e:
        if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_PIND]:
            update_pod_restart(name, namespace, START_MODE_ACTIVE)
        delete_frontman(src_pod, frontman_created)
        delete_des_pod(src_pod, destination_url, des_pod_created)
        release_pod(name, namespace)
        raise e

    create_or_update_frontman(src_pod, keeper_mode=frontman_created, redirect_uri=body.get('redirect'))
    interface.delete_src_pod(src_pod)
    restored_time = datetime.now(tz=tzlocal())
    return {
        'creation': (created_time - start_time).total_seconds(),
        'checkpoint': 'todo',
        'transfer': 'todo',
        'checkpoint_and_transfer': (checkpointed_time - created_time).total_seconds(),
        'restoration': (restored_time - checkpointed_time).total_seconds(),
        'total': (restored_time - start_time).total_seconds()
    }


def ping_destination(destination_url):
    response = requests.get(f"http://{destination_url}")
    response.raise_for_status()
    response = response.json()
    if response['os'] != get_information():
        abort(409, 'Cannot migrate to incompatible destination')
    return response


def select_interface(src_pod, des_info, selected_interface):
    interfaces = {
        INTERFACE_DIND: dind,
        INTERFACE_PIND: pind,
        INTERFACE_FF: ff,
        INTERFACE_SSU: ssu
    }
    if selected_interface is not None:
        interface = interfaces.get(selected_interface)
        if interface is not None:
            return interface
        else:
            abort(400, f'Incompatible interface {selected_interface}')
    if 'ssu_port' in des_info and SSU_INTERFACE_ENABLE is not None:
        return ssu
    interface = interfaces.get(src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION))
    if interface is not None:
        return interface
    abort(409, 'Cannot migrate to incompatible destination')


def delete_des_pod(src_pod, destination_url, des_pod_created):
    if not des_pod_created:
        return
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    response = requests.post(f'http://{destination_url}/delete',
                             json={'name': name, 'namespace': namespace})
    response.raise_for_status()


def restore_and_release_des_pod(src_pod, destination_url, migration_id, checkpoint_id, interface, des_pod_template):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    try:
        response = requests.post(f"http://{destination_url}/restore",
                                 json={'migrationId': migration_id,
                                       'checkpointId': checkpoint_id,
                                       'name': name,
                                       'namespace': namespace,
                                       'interface': interface.get_name(),
                                       'template': des_pod_template})
    except Timeout as e:
        try:
            delete_des_pod(des_pod_template, destination_url, True)
        except HTTPError as http_error:
            if http_error.response.status_code != 404:
                raise http_error
        raise e
    response.raise_for_status()


def create_or_update_frontman(src_pod, keeper_mode=None, redirect_uri=None):
    if keeper_mode is None and redirect_uri is None:
        return False
    if keeper_mode and redirect_uri:
        update_frontman(src_pod, redirect_uri)
        return True
    try:
        return create_frontman(src_pod, redirect_uri)
    except HTTPException as e:
        try:
            delete_frontman(src_pod, True)
        except ApiException as kubernetes_error:
            if kubernetes_error.status != 404:
                raise kubernetes_error
        raise e


def create_frontman(src_pod, redirect_uri=None):
    with open(path.join(path.dirname(__file__), '../frontman.yml'), 'rt') as f:
        frontman_template = yaml.safe_load(f.read().format(**env))
    src = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    frontman_template['metadata'] = src['metadata']
    frontman_template['metadata']['name'] += '-frontman'
    frontman_template['metadata']['annotations'].pop(MIGRATABLE_ANNOTATION, None)
    frontman_template['metadata']['annotations'].pop(INTERFACE_ANNOTATION, None)
    frontman_template['metadata']['annotations'][BYPASS_ANNOTATION] = str(True)
    if redirect_uri:
        frontman_template['metadata']['annotations']['redirect'] = redirect_uri

    frontman_template['spec']['containers'] = [{
        'name': f"{container['name']}-{port['containerPort']}",
        'image': FRONTMAN_IMAGE,
        'imagePullPolicy': 'Always',
        'ports': [{'name': 'web', 'protocol': 'TCP', 'containerPort': port['containerPort']}],
        'env': [
            {'name': 'FLASK_RUN_PORT', 'value': str(port['containerPort'])}
        ],
        'volumeMounts': [
            {'mountPath': '/etc/podinfo', 'name': 'podinfo'}
        ]
    } for container in src['spec']['containers'] for port in container.get('ports', [])]

    if not frontman_template['spec']['containers']:
        return False

    wait_pod_ready(create_pod(src['metadata']['namespace'], frontman_template))

    update_pod_label(src['metadata']['name'], src['metadata']['namespace'],
                     {k: None for k in src['metadata']['labels']})
    return True


def update_frontman(src_pod, redirect_uri):
    update_pod_redirect(f"{src_pod['metadata']['name']}-frontman", src_pod['metadata']['namespace'], redirect_uri)


def delete_frontman(src_pod, frontman_created):
    if not frontman_created:
        return
    src = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    update_pod_label(src['metadata']['name'], src['metadata']['namespace'], src['metadata']['labels'])
    delete_pod(f"{src['metadata']['name']}-frontman", src['metadata']['namespace'])
