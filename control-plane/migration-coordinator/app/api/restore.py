import asyncio

import requests
from flask import Blueprint, request, abort

from app.const import ENGINE_ANNOTATION, ENGINE_FAST_FREEZE, START_MODE_FAIL
from app.kubernetes_client import wait_pod_ready, get_pod, disable_pod_restart, exec_pod
from app.lib import gather

restore_api_blueprint = Blueprint('restore_api', __name__)


@restore_api_blueprint.route("/restore", methods=['POST'])
def restore_api():
    body = request.get_json()

    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    checkpoint_id = body.get('checkpointId')
    if checkpoint_id is None:
        abort(400, 'checkpointId is null')

    namespace = body.get('namespace', 'default')

    des_pod = get_pod(name, namespace)

    restore(des_pod, checkpoint_id)

    return wait_pod_ready(des_pod)


def restore(des_pod, checkpoint_id):
    name = des_pod['metadata']['name']
    namespace = des_pod['metadata'].get('namespace', 'default')
    if des_pod['metadata']['annotations'].get(ENGINE_ANNOTATION) == ENGINE_FAST_FREEZE:
        restore_ff(des_pod)
    else:
        des_pod = disable_pod_restart(name, namespace, START_MODE_FAIL, des_pod)
        restore_dind(des_pod, checkpoint_id)


def restore_ff(des_pod):
    name = des_pod['metadata']['name']
    namespace = des_pod['metadata'].get('namespace', 'default')
    asyncio.run(gather([exec_pod(
        name,
        namespace,
        '/sbin/killall5',
        container['name'],
    ) for container in des_pod['spec']['containers']]))


def restore_dind(des_pod, checkpoint_id):
    response = requests.post(f'http://{des_pod.status.pod_ip}:8888/restore', json={
        'checkpointId': checkpoint_id
    })
    response.raise_for_status()
