import asyncio
import json
from datetime import datetime
from os import path
from uuid import uuid4

import requests
import yaml
from dateutil.tz import tzlocal
from flask import Blueprint, request, abort, Response, current_app

from app.const import MIGRATABLE_ANNOTATION, MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_ACTIVE, \
    START_MODE_PASSIVE, INTERFACE_ANNOTATION, INTERFACE_DIND, VOLUME_LIST_ANNOTATION, \
    SYNC_HOST_ANNOTATION, SYNC_PORT_ANNOTATION, LAST_APPLIED_CONFIG, ORCHESTRATOR_TYPE_MESOS, INTERFACE_PIND, \
    INTERFACE_FF, START_MODE_NULL
from app.db import get_db
from app.env import env, FRONTMAN_IMAGE, ORCHESTRATOR_TYPE
from app.kubernetes_client import create_pod, update_pod_label
from app.lib import get_information, gather, get_pod, lock_pod, release_pod, update_pod_restart, delete_pod, exec_pod, \
    check_error_event

demo_api_blueprint = Blueprint('demo_api', __name__)


@demo_api_blueprint.route("/demo", methods=['POST'])
def demo_api():
    body = request.get_json()

    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    destination_url = body.get('destinationUrl')
    if destination_url is None:
        abort(400, 'destinationUrl is null')

    connection = get_db()

    migration_id = uuid4().hex[:8]

    try:
        connection.execute("INSERT INTO migration (id) VALUES (?)", (migration_id,))
        connection.commit()
        return Response(migrate(body, migration_id, current_app.app_context()), mimetype="text/event-stream")
    finally:
        connection.execute("DELETE FROM migration WHERE id = ?", (migration_id,))
        connection.execute("DELETE FROM message WHERE migration_id = ?", (migration_id,))
        connection.commit()


def migrate(body, migration_id, context):
    with context:
        name = body['name']
        namespace = body.get('namespace', 'default')
        destination_url = body['destinationUrl']
        keep = False
        last_checked_time = datetime.now(tz=tzlocal())
        src_pod = get_pod(name, namespace)
        if not bool(src_pod['metadata']['annotations'].get(MIGRATABLE_ANNOTATION)):
            abort(400, "pod is not migratable")
        if src_pod['metadata']['annotations'][START_MODE_ANNOTATION] != START_MODE_ACTIVE:
            abort(400, "Pod is not migratable")
        if src_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION):
            abort(409, "Pod is being migrated")
        last_checked_time = abort_if_error_exists(migration_id, name, namespace, last_checked_time)
        src_pod = lock_pod(name, namespace, migration_id)
        try:
            last_checked_time = abort_if_error_exists(migration_id, name, namespace, last_checked_time)
            ping_destination(destination_url)
            last_checked_time = abort_if_error_exists(migration_id, name, namespace, last_checked_time)
            des_pod_annotations = create_des_pod(src_pod, destination_url)
            last_checked_time = abort_if_error_exists(migration_id, name, namespace, last_checked_time)
            yield 'RESERVED\n\n'
            # if body.get('keep'):
            #     keep = create_keeper(src_pod)
            try:
                checkpoint_id = uuid4().hex[:8]
                src_pod = checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id)
                _ = abort_if_error_exists(migration_id, name, namespace, last_checked_time)
            except Exception as e:
                delete_des_pod(src_pod, destination_url)
                raise e
            yield 'CHECKPOINTED\n\n'
            restore_and_release_des_pod(src_pod, destination_url, migration_id, checkpoint_id)
            yield 'RESTORED\n\n'
        finally:
            # if body.get('keep') and keep:
            #     delete_keeper(src_pod)
            if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_PIND]:
                update_pod_restart(name, namespace, START_MODE_ACTIVE)
            release_pod(name, namespace)
        try:
            # if body.get('redirect'):
            #     create_redirector(src_pod, body.get('redirect'))
            delete_pod(name, namespace)
            if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MESOS \
                    and src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_PIND]:
                delete_pod(f"{name}-monitor", namespace)
        except Exception as e:
            abort(500, f"Error occurs at post-migration step: {e}")
        yield 'DONE\n\n'


def abort_if_error_exists(migration_id, name, namespace, last_checked_time):
    cur = get_db().execute("SELECT * FROM message WHERE migration_id = ?", (migration_id,))
    rv = cur.fetchall()
    if rv:
        abort(rv[0]['message'])
    return check_error_event(name, namespace, last_checked_time)


def ping_destination(destination_url):
    response = requests.get(f"http://{destination_url}")
    response.raise_for_status()
    if response.text != get_information():  # todo check native support
        abort(409, 'Cannot migrate to incompatible destination')


def create_des_pod(src_pod, destination_url):
    # todo dummy create for native
    body = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    body['metadata']['annotations'][LAST_APPLIED_CONFIG] = src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG)
    if body['metadata']['annotations'].get(INTERFACE_ANNOTATION) == INTERFACE_PIND:
        body['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_NULL
    else:
        body['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_PASSIVE
    body['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = src_pod['metadata']['annotations'][
        MIGRATION_ID_ANNOTATION]
    response = requests.post(f"http://{destination_url}/create", json=body)
    response.raise_for_status()
    return response.json()


def checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) in [INTERFACE_DIND, INTERFACE_PIND]:
        src_pod = update_pod_restart(name, namespace, START_MODE_NULL)
        checkpoint_and_transfer_dind(src_pod, checkpoint_id, des_pod_annotations)
    elif src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) == INTERFACE_FF:
        checkpoint_and_transfer_ff(src_pod, des_pod_annotations)
    else:
        pass  # todo
    return src_pod


def checkpoint_and_transfer_ff(src_pod, des_pod_annotations):
    volume_list = json.loads(src_pod['metadata']['annotations'][VOLUME_LIST_ANNOTATION])
    interface_host = des_pod_annotations[SYNC_HOST_ANNOTATION]
    interface_port = json.loads(des_pod_annotations[SYNC_PORT_ANNOTATION])
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    asyncio.run(gather([exec_pod(
        name,
        namespace,
        f'''
        mc alias set migration http://{interface_host}:{interface_port[container['name']]} minioadmin minioadmin &&
        S3_CMD='/root/s3 migration' fastfreeze checkpoint --leave-running {'--preserve-path' + volume_list[container['name']] if container['name'] in volume_list else ''}
        ''',
        container['name'],
    ) for container in src_pod['spec']['containers']]))


def checkpoint_and_transfer_dind(src_pod, checkpoint_id, des_pod_annotations):
    response = requests.post(f"http://{src_pod['status']['podIP']}:8888/migrate", json={
        'checkpointId': checkpoint_id,
        'interfaceHost': des_pod_annotations[SYNC_HOST_ANNOTATION],
        'interfacePort': des_pod_annotations[SYNC_PORT_ANNOTATION],
        'containers': des_pod_annotations['current-containers'],
        'volumes': json.loads(des_pod_annotations[VOLUME_LIST_ANNOTATION])
    })
    response.raise_for_status()


def delete_des_pod(src_pod, destination_url):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    response = requests.post(f'http://{destination_url}/delete',
                             json={'name': name, 'namespace': namespace})
    response.raise_for_status()


def restore_and_release_des_pod(src_pod, destination_url, migration_id, checkpoint_id):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    response = requests.post(f"http://{destination_url}/restore",
                             json={'migrationId': migration_id,
                                   'checkpointId': checkpoint_id,
                                   'name': name,
                                   'namespace': namespace})
    response.raise_for_status()


def create_keeper(src_pod):
    with open(path.join(path.dirname(__file__), '../keeper.yml'), 'rt') as f:
        keeper_template = yaml.safe_load(f.read().format(**env))
    src = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    keeper_template['metadata'] = src['metadata']
    keeper_template['metadata']['name'] += '-keeper'
    keeper_template['metadata']['annotations'].pop(MIGRATABLE_ANNOTATION)

    keeper_template['spec']['containers'] = [{
        'name': f"{container['name']}-{port['containerPort']}",
        'image': FRONTMAN_IMAGE,
        'imagePullPolicy': 'Always',
        'ports': [{'name': 'web', 'protocol': 'TCP', 'containerPort': port['containerPort']}],
        'env': [
            {'name': 'NGINX_PORT', 'value': str(port['containerPort'])}
        ]
    } for container in src['spec']['containers'] for port in container.get('ports', [])]

    if not keeper_template['spec']['containers']:
        return False

    create_pod(src['metadata']['namespace'], keeper_template)
    update_pod_label(src['metadata']['name'], src['metadata']['namespace'],
                     {k: None for k in src['metadata']['labels']})
    return True


def delete_keeper(src_pod):
    src = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    update_pod_label(src['metadata']['name'], src['metadata']['namespace'], src['metadata']['labels'])
    delete_pod(f"{src['metadata']['name']}-keeper", src['metadata']['namespace'])


def create_redirector(src_pod, new_uri):
    with open(path.join(path.dirname(__file__), '../redirector.yml'), 'rt') as f:
        redirector_template = yaml.safe_load(f.read().format(**env))

    src = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))

    redirector_template['metadata'] = src['metadata']
    redirector_template['metadata']['name'] += '-redirector'
    redirector_template['metadata']['annotations'].pop(MIGRATABLE_ANNOTATION)

    redirector_template['spec']['containers'] = [{
        'name': f"{container['name']}-{port['containerPort']}",
        'image': FRONTMAN_IMAGE,
        'imagePullPolicy': 'Always',
        'ports': [{'name': 'web', 'protocol': 'TCP', 'containerPort': port['containerPort']}],
        'env': [
            {'name': 'NGINX_PORT', 'value': str(port['containerPort'])},
            {'name': 'NEW_URI', 'value': new_uri}
        ]
    } for container in src['spec']['containers'] for port in container.get('ports', [])]

    if not redirector_template['spec']['containers']:
        return

    create_pod(src['metadata']['namespace'], redirector_template)
