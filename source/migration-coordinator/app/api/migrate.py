import asyncio
import json
from datetime import datetime
from os import path
from uuid import uuid4

import requests
import yaml
from dateutil.tz import tzlocal
from flask import Blueprint, request, abort
from requests import Timeout

from app.const import MIGRATABLE_ANNOTATION, MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_ACTIVE, \
    START_MODE_PASSIVE, INTERFACE_ANNOTATION, INTERFACE_DIND, VOLUME_LIST_ANNOTATION, \
    SYNC_HOST_ANNOTATION, SYNC_PORT_ANNOTATION, LAST_APPLIED_CONFIG, ORCHESTRATOR_TYPE_MESOS, INTERFACE_PIND, \
    INTERFACE_FF, START_MODE_NULL, BYPASS_ANNOTATION, INTERFACE_SSU
from app.env import env, FRONTMAN_IMAGE, ORCHESTRATOR_TYPE, SSU_INTERFACE_SERVICE, SSU_INTERFACE_ENABLE
import app.interface.dind as dind
import app.interface.pind as pind
import app.interface.ff as ff
import app.interface.ssu as ssu
from app.kubernetes_client import create_pod, update_pod_label, wait_pod_ready, delete_ssu_custom_resource
from app.lib import get_information, gather, get_pod, lock_pod, release_pod, update_pod_restart, update_pod_redirect,\
    delete_pod, exec_pod, check_error_event

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
    # selected_interface = body.get('interface')
    # todo

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
        interface = select_interface(src_pod, des_info)
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
        'checkpoint_and_transfer': (checkpointed_time - created_time).total_seconds(),
        'restoration': (restored_time - checkpointed_time).total_seconds()
    }


# def abort_if_error_exists(migration_id, name, namespace, last_checked_time):
#     cur = get_db().execute("SELECT * FROM message WHERE migration_id = ?", (migration_id,))
#     rv = cur.fetchall()
#     if rv:
#         abort(rv[0]['message'])
#     return check_error_event(name, namespace, last_checked_time)
# todo check if pod restart: checkpoint step and restore step


def ping_destination(destination_url):
    response = requests.get(f"http://{destination_url}")
    response.raise_for_status()
    response = response.json()
    if response['os'] != get_information():
        abort(409, 'Cannot migrate to incompatible destination')
    return response


def select_interface(src_pod, des_info):
    if 'ssu_port' in des_info and SSU_INTERFACE_ENABLE is not None:
        return ssu
    if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) == INTERFACE_DIND:
        return dind
    if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) == INTERFACE_PIND:
        return pind
    if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) == INTERFACE_FF:
        return ff
    abort(409, 'Cannot migrate to incompatible destination')


# def generate_des_pod_template(src_pod):
#     body = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
#     body['metadata']['annotations'][LAST_APPLIED_CONFIG] = src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG)
#     if body['metadata']['annotations'].get(INTERFACE_ANNOTATION) == INTERFACE_PIND:
#         body['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_NULL
#     elif body['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_FF]:
#         body['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_PASSIVE
#     body['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = src_pod['metadata']['annotations'][
#         MIGRATION_ID_ANNOTATION]
#     return body
#
#
# def create_des_pod(des_pod_template, des_info):
#     if des_pod_template['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_PIND, INTERFACE_FF]:
#         try:
#             response = requests.post(f"http://{des_info['url']}/create", json=des_pod_template)
#         except Timeout as e:
#             # todo try deleting des pod if timeout
#             raise e
#         response.raise_for_status()
#         return True, response.json()
#     return False, {SYNC_HOST_ANNOTATION: '10.131.36.34.nip.io', SYNC_PORT_ANNOTATION: '30002'}
#     # return False, {SYNC_HOST_ANNOTATION: des_info['ssu_host'], SYNC_PORT_ANNOTATION: des_info['ssu_port']}
#     #todo fix mockup
#
#
# def checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id):
#     name = src_pod['metadata']['name']
#     namespace = src_pod['metadata'].get('namespace', 'default')
#     if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_PIND]:
#         src_pod = update_pod_restart(name, namespace, START_MODE_NULL)
#         checkpoint_and_transfer_dind(src_pod, checkpoint_id, des_pod_annotations)
#     elif src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) == INTERFACE_FF:
#         checkpoint_and_transfer_ff(src_pod, des_pod_annotations)
#     else:
#         # todo check native support
#         checkpoint_and_transfer_ssu(src_pod, checkpoint_id, des_pod_annotations)
#     return src_pod
#
#
# # todo sort
# def checkpoint_and_transfer_ssu(src_pod, checkpoint_id, des_pod_annotations):
#     response = requests.post(f"http://{SSU_INTERFACE_SERVICE}:8888/migrate", json={
#         'checkpointId': checkpoint_id,
#         'interfaceHost': des_pod_annotations[SYNC_HOST_ANNOTATION],
#         'interfacePort': des_pod_annotations[SYNC_PORT_ANNOTATION],
#         'template': json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
#         # 'volumes': json.loads(des_pod_annotations[VOLUME_LIST_ANNOTATION])
#         #todo check if volume is migrated
#     })
#     response.raise_for_status()    # todo forward body
#     delete_ssu_custom_resource(checkpoint_id, src_pod['metadata'].get('namespace', 'default'))
#
#
# def checkpoint_and_transfer_ff(src_pod, des_pod_annotations):
#     volume_list = json.loads(src_pod['metadata']['annotations'][VOLUME_LIST_ANNOTATION])
#     interface_host = des_pod_annotations[SYNC_HOST_ANNOTATION]
#     interface_port = json.loads(des_pod_annotations[SYNC_PORT_ANNOTATION])
#     name = src_pod['metadata']['name']
#     namespace = src_pod['metadata'].get('namespace', 'default')
#     asyncio.run(gather([exec_pod(
#         name,
#         namespace,
#         f'''
#         mc alias set migration http://{interface_host}:{interface_port[container['name']]} minioadmin minioadmin &&
#         S3_CMD='/root/s3 migration' fastfreeze checkpoint --leave-running {'--preserve-path' + volume_list[container['name']] if container['name'] in volume_list else ''}
#         ''',
#         container['name'],
#     ) for container in src_pod['spec']['containers']]))
#
#
# def checkpoint_and_transfer_dind(src_pod, checkpoint_id, des_pod_annotations):
#     response = requests.post(f"http://{src_pod['status']['podIP']}:8888/migrate", json={
#         'checkpointId': checkpoint_id,
#         'interfaceHost': des_pod_annotations[SYNC_HOST_ANNOTATION],
#         'interfacePort': des_pod_annotations[SYNC_PORT_ANNOTATION],
#         'containers': des_pod_annotations['current-containers'],
#         'volumes': json.loads(des_pod_annotations[VOLUME_LIST_ANNOTATION])
#     })
#     response.raise_for_status()


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
    response = requests.post(f"http://{destination_url}/restore",
                             json={'migrationId': migration_id,
                                   'checkpointId': checkpoint_id,
                                   'name': name,
                                   'namespace': namespace,
                                   'interface': interface.get_name(),
                                   'template': des_pod_template})
    # todo try deleting des pod if timeout
    response.raise_for_status()


# def delete_src_pod(src_pod):
#     name = src_pod['metadata']['name']
#     namespace = src_pod['metadata'].get('namespace', 'default')
#     if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_PIND, INTERFACE_FF]:
#         delete_pod(name, namespace)
#     if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MESOS \
#             and src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_PIND]:
#         delete_pod(f"{name}-monitor", namespace)


def create_or_update_frontman(src_pod, keeper_mode=None, redirect_uri=None):
    if keeper_mode is None and redirect_uri is None:
        return False
    if keeper_mode and redirect_uri:
        update_frontman(src_pod, redirect_uri)
        return True
    return create_frontman(src_pod, redirect_uri)
    # todo catch timeout


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
