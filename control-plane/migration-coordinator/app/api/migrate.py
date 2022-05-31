import asyncio
import json
from os import path
from uuid import uuid4

import requests
import yaml
from flask import Blueprint, request, abort

from app.const import MIGRATABLE_ANNOTATION, MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_ACTIVE, \
    START_MODE_PASSIVE, START_MODE_FAIL, ENGINE_ANNOTATION, ENGINE_FAST_FREEZE, VOLUME_LIST_ANNOTATION, \
    INTERFACE_HOST_ANNOTATION, INTERFACE_PORT_ANNOTATION
from app.db import get_db
from app.env import EVAL_REDIRECTOR
from app.kubernetes_client import get_pod, lock_pod, release_pod, disable_pod_restart, exec_pod, delete_pod, create_pod
from app.lib import get_information, gather

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

    connection = get_db()

    migration_id = uuid4().hex[:8]

    try:
        connection.execute("INSERT INTO migration (id) VALUES (?)", (migration_id,))
        connection.commit()
        migrate(body, migration_id)
    finally:
        connection.execute("DELETE FROM migration WHERE id = ?", (migration_id,))
        connection.execute("DELETE FROM message WHERE migration_id = ?", (migration_id,))
        connection.commit()

    return f"migration complete! id: {migration_id}"


def migrate(body, migration_id):
    name = body['name']
    namespace = body.get('namespace', 'default')
    destination_url = body['destinationUrl']
    src_pod = get_pod(name, namespace)
    if src_pod['metadata']['annotations'].get(MIGRATABLE_ANNOTATION) != 'True':
        abort(400, "pod is not migratable")
    if src_pod['metadata']['annotations'][START_MODE_ANNOTATION] != START_MODE_ACTIVE:
        abort(400, "Pod is not migratable")
    if src_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION):
        abort(409, "Pod is being migrated")
    abort_if_error_exists(migration_id)
    src_pod = lock_pod(name, namespace, migration_id, src_pod)
    try:
        abort_if_error_exists(migration_id)
        ping_destination(destination_url)
        abort_if_error_exists(migration_id)
        des_pod_annotations = create_des_pod(src_pod, destination_url)
        abort_if_error_exists(migration_id)
        if body.get('queue'):
            block_queue(body.get('queue'), namespace, migration_id)
        try:
            checkpoint_id = uuid4().hex[:8]
            src_pod = checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id)
            abort_if_error_exists(migration_id)
        except Exception as e:
            delete_des_pod(src_pod, destination_url)
            raise e
        restore_and_release_des_pod(src_pod, destination_url, migration_id, checkpoint_id)
    finally:
        release_pod(name, namespace, src_pod)
    try:
        if body.get('redirect'):
            create_redirector(src_pod, body.get('redirect'))
        delete_pod(name, namespace)
        if body.get('queue'):
            unblock_queue(body.get('queue'), namespace)
    except Exception as e:
        abort(500, f"Error occurs at post-migration step: {e}")


def abort_if_error_exists(migration_id):
    cur = get_db().execute("SELECT * FROM message WHERE migration_id = ?", (migration_id,))
    rv = cur.fetchall()
    if rv:
        abort(rv[0]['message'])
    # todo listen events


def ping_destination(destination_url):
    response = requests.get(f"http://{destination_url}")
    response.raise_for_status()
    if response.text != get_information():
        abort(409, 'Cannot migrate to incompatible destination')


def create_des_pod(src_pod, destination_url):
    src_pod['metadata'] = {
        'name': src_pod['metadata']['name'],
        'namespace': src_pod['metadata']['namespace'],
        'labels': src_pod['metadata'].get('labels', {}),
        'annotations': src_pod['metadata']['annotations'],
    }
    src_pod['metadata']['annotations'][MIGRATABLE_ANNOTATION] = 'False'
    src_pod['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_PASSIVE
    response = requests.post(f"http://{destination_url}/create", json=src_pod)
    response.raise_for_status()
    return response.json()


def checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    if src_pod['metadata']['annotations'].get(ENGINE_ANNOTATION) == ENGINE_FAST_FREEZE:
        checkpoint_and_transfer_ff(src_pod, checkpoint_id, des_pod_annotations)
    else:
        src_pod = disable_pod_restart(name, namespace, START_MODE_FAIL, src_pod)
        checkpoint_and_transfer_dind(src_pod, checkpoint_id, des_pod_annotations)
    return src_pod


def checkpoint_and_transfer_ff(src_pod, checkpoint_id, des_pod_annotations):
    volume_list = json.loads(src_pod['metadata']['annotations'][VOLUME_LIST_ANNOTATION])
    interface_host = des_pod_annotations[INTERFACE_HOST_ANNOTATION]
    interface_port = des_pod_annotations[INTERFACE_PORT_ANNOTATION]
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    asyncio.run(gather([exec_pod(
        name,
        namespace,
        f'''bash << EOF
        fastfreeze checkpoint --image-url file:/images/{checkpoint_id} {'--preserve-path' + volume_list[container['name']] if container['name'] in volume_list[container['name']] else ''}
        rsync -avz -e 'ssh -i /app/id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {interface_port}' /images/{checkpoint_id} rsync@${interface_host}:/images/default
        EOF''',
        container['name'],
    ) for container in src_pod['spec']['containers']]))


def checkpoint_and_transfer_dind(src_pod, checkpoint_id, des_pod_annotations):
    response = requests.get(f'http://{src_pod.status.pod_ip}:8888/list')
    response.raise_for_status()
    response = requests.post(f'http://{src_pod.status.pod_ip}:8888/migrate', json={
        'checkpointId': checkpoint_id,
        'interfaceHost': des_pod_annotations[INTERFACE_HOST_ANNOTATION],
        'interfacePort': des_pod_annotations[INTERFACE_PORT_ANNOTATION],
        'containers': response.json(),
        'volumes': des_pod_annotations[VOLUME_LIST_ANNOTATION]
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


def block_queue(name, namespace, migration_id):
    lock_pod(name, namespace, get_pod(name, namespace), migration_id)


def unblock_queue(name, namespace):
    release_pod(name, namespace, get_pod(name, namespace))


def create_redirector(src_pod, new_uri):
    with open(path.join(path.dirname(__file__), '../redirector.yml'), 'rt') as f:
        redirector_template = yaml.safe_load(f.read())

    redirector_template['metadata'] = {
        'name': src_pod['metadata']['name'],
        'namespace': src_pod['metadata'].get('namespace', 'default'),
        'labels': src_pod['metadata'].get('labels', {}),
        'annotations': src_pod['metadata']['annotations']
    }

    redirector_template['spec']['containers'] = [{
        'name': f"{container['name']}-{port['containerPort']}",
        'image': EVAL_REDIRECTOR,
        'imagePullPolicy': 'Always',
        'ports': [{'name': 'web', 'protocol': 'TCP', 'containerPort': port['containerPort']}],
        'env': [
            {'name': 'NGINX_PORT', 'value': str(port['containerPort'])},
            {'name': 'NEW_URI', 'value': new_uri}
        ]
    } for container in src_pod['spec']['containers'] for port in container.get('ports', [])]

    create_pod(src_pod['metadata']['namespace'], redirector_template)
