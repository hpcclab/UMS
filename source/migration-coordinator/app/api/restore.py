import asyncio
import time
from datetime import datetime, timedelta
from time import sleep

import requests
from dateutil.tz import tzlocal
from flask import Blueprint, request, abort

from app.api.create import probe_all
from app.const import ENGINE_ANNOTATION, ENGINE_DIND, START_MODE_FAIL, MIGRATION_ID_ANNOTATION, \
    START_MODE_ACTIVE
from app.lib import get_pod, update_pod_restart, release_pod, gather, exec_pod, log_pod

restore_api_blueprint = Blueprint('restore_api', __name__)


@restore_api_blueprint.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Headers'] = '*'
    header['Access-Control-Allow-Origin'] = '*'
    # Other headers can be added here if needed
    return response


@restore_api_blueprint.route("/restore", methods=['POST'])
def restore_api():
    body = request.get_json()

    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    migration_id = body.get('migrationId')
    if migration_id is None:
        abort(400, 'migrationId is null')

    checkpoint_id = body.get('checkpointId')
    if checkpoint_id is None:
        abort(400, 'checkpointId is null')

    namespace = body.get('namespace', 'default')

    des_pod = get_pod(name, namespace)

    if des_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION) != migration_id:
        abort(409, "Pod is being migrated")

    return restore(des_pod, checkpoint_id)


def restore(des_pod, checkpoint_id):
    name = des_pod['metadata']['name']
    namespace = des_pod['metadata'].get('namespace', 'default')
    if des_pod['metadata']['annotations'].get(ENGINE_ANNOTATION) == ENGINE_DIND:
        des_pod = update_pod_restart(name, namespace, START_MODE_FAIL)
        restore_dind(des_pod, checkpoint_id)
        wait_pod_ready(des_pod)
        update_pod_restart(name, namespace, START_MODE_ACTIVE)
    else:
        update_pod_restart(name, namespace, START_MODE_ACTIVE)
        wait_pod_ready_ff(des_pod)
    return release_pod(name, namespace)


def restore_dind(des_pod, checkpoint_id):
    response = requests.post(f"http://{des_pod['status']['podIP']}:8888/restore", json={
        'checkpointId': checkpoint_id
    })
    response.raise_for_status()


def wait_pod_ready(pod):
    start_time = datetime.now(tz=tzlocal())
    while True:
        status_code = probe_all(pod['status']['podIP'])
        if status_code == 200:
            return

        if datetime.now(tz=tzlocal()) - start_time > timedelta(minutes=1):
            abort(504, 'Timeout while waiting pod to be ready')

        sleep(0.1)


def wait_pod_ready_ff(pod):
    name = pod['metadata']['name']
    namespace = pod['metadata'].get('namespace', 'default')
    asyncio.run(gather([wait_container_ready_ff(
        name,
        namespace,
        container['name'],
    ) for container in pod['spec']['containers']]))


async def wait_container_ready_ff(pod_name, namespace, container_name):
    found = False
    while not found:
        log = log_pod(pod_name, namespace, container_name).split('\n')
        for line in log:
            if 'Application is ready, restore took' in line:
                found = True
                break
        await asyncio.sleep(0.1)
