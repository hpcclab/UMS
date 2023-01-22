import json
from datetime import datetime
from os import path
from uuid import uuid4

import requests
import yaml
from dateutil.tz import tzlocal
from flask import Blueprint, request, abort
from requests import HTTPError
from werkzeug.exceptions import HTTPException

import app.interface.dind as dind
import app.interface.ff as ff
import app.interface.pind as pind
import app.interface.ssu as ssu
from app.const import MIGRATABLE_ANNOTATION, MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_ACTIVE, \
    INTERFACE_ANNOTATION, LAST_APPLIED_CONFIG, BYPASS_ANNOTATION
from app.env import env, FRONTMAN_IMAGE
from app.kubernetes_client import create_pod, update_pod_label, wait_pod_ready_frontman
from app.lib import get_information, get_pod, lock_pod, release_pod, update_pod_redirect, \
    delete_pod, select_interface

migrate_api_blueprint = Blueprint('migrate_api', __name__)


# todo bypass interceptor, migration position, migration phase/status


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
    migration_state = {
        'src_pod_exist': True,
        'des_pod_exist': False,
        'frontmant_exist': False
    }
    interface = None

    try:
        des_info = ping_destination(destination_url)
        interface = select_migration_interface(src_pod, des_info, selected_interface)

        des_pod_template = interface.generate_des_pod_template(src_pod)
        des_pod_info = interface.create_des_pod(des_pod_template, des_info, migration_state)
        create_or_update_frontman(src_pod, migration_state, create_keeper=body.get('keep'))
        created_time = datetime.now(tz=tzlocal())

        checkpoint_id = uuid4().hex[:8]
        src_pod = interface.checkpoint_and_transfer(src_pod, des_pod_info, checkpoint_id, migration_state)
        # todo actual checkpoint time (interface)
        checkpointed_time = datetime.now(tz=tzlocal())

        restore_and_release_des_pod(src_pod, destination_url, migration_id, checkpoint_id, interface, des_pod_template, migration_state)
    except Exception as e:
        if interface:
            interface.recover(src_pod, destination_url, migration_state, delete_frontman, delete_des_pod, release_pod)
        raise e

    create_or_update_frontman(src_pod, migration_state, redirect_uri=body.get('redirect'))
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


def select_migration_interface(src_pod, des_info, selected_interface):
    if selected_interface is not None:
        return select_interface(selected_interface)
    if ssu.is_compatible(src_pod, des_info):
        return ssu
    try:
        interface = select_interface(src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION))
        if interface.is_compatible(src_pod, des_info):
            return interface
    except HTTPException:
        pass
    if ff.is_compatible(src_pod, des_info):
        return ff
    if pind.is_compatible(src_pod, des_info):
        return pind
    if dind.is_compatible(src_pod, des_info):
        return dind
    abort(409, 'Cannot migrate to incompatible destination')


def delete_des_pod(src_pod, destination_url, des_pod_created):
    if not des_pod_created:
        return
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    response = requests.post(f'http://{destination_url}/delete', json={'name': name, 'namespace': namespace})
    response.raise_for_status()


def restore_and_release_des_pod(src_pod, destination_url, migration_id, checkpoint_id, interface, des_pod_template, migration_state):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    try:
        response = requests.post(f"http://{destination_url}/restore", json={
            'migrationId': migration_id,
            'checkpointId': checkpoint_id,
            'name': name,
            'namespace': namespace,
            'interface': interface.get_name(),
            'template': des_pod_template
        })
        response.raise_for_status()
        migration_state['des_pod_exist'] = True
    except HTTPError as e:
        if e.response.status_code == 504:
            migration_state['des_pod_exist'] = True
        raise e


def create_or_update_frontman(src_pod, migration_state, create_keeper=None, redirect_uri=None):
    if redirect_uri and migration_state['frontmant_exist']:
        update_frontman(src_pod, redirect_uri)
    if create_keeper or redirect_uri:
        create_frontman(src_pod, migration_state, redirect_uri=redirect_uri)


def create_frontman(src_pod, migration_state, redirect_uri=None):
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

    frontman_pod = create_pod(src['metadata']['namespace'], frontman_template)
    migration_state['frontmant_exist'] = True
    wait_pod_ready_frontman(frontman_pod, migration_state)

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
