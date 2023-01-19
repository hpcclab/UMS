import asyncio
import json

import requests
from flask import abort
from requests import Timeout, HTTPError
from werkzeug.exceptions import HTTPException

from app.const import MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_PASSIVE, VOLUME_LIST_ANNOTATION, \
    SYNC_HOST_ANNOTATION, SYNC_PORT_ANNOTATION, LAST_APPLIED_CONFIG, INTERFACE_FF, START_MODE_ACTIVE
from app.kubernetes_client import create_pod, wait_pod_ready_ff
from app.kubernetes_client import delete_pod, exec_pod, get_pod, update_pod_restart, release_pod, log_pod


async def gather(fn_list):
    return await asyncio.gather(*fn_list)


def get_name():
    return INTERFACE_FF


def is_compatible(src_pod, des_info):
    ff_processes = asyncio.run(gather([exec_pod(
        src_pod['metadata']['name'],
        src_pod['metadata'].get('namespace', 'default'),
        f"ps -A -ww | grep -c [^]]fastfreeze",
        container['name'],
    ) for container in src_pod['spec']['containers']]))
    for process in ff_processes:
        if int(process) < 1:
            return False
    return True


def generate_des_pod_template(src_pod):
    body = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    body['metadata']['annotations'][LAST_APPLIED_CONFIG] = src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG)
    body['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_PASSIVE
    body['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = src_pod['metadata']['annotations'][MIGRATION_ID_ANNOTATION]
    return body


def create_des_pod(des_pod_template, des_info, delete_des_pod):
    try:
        response = requests.post(f"http://{des_info['url']}/create", json={
            'interface': get_name(),
            'template': des_pod_template
        })
    except (Timeout, HTTPException) as e:
        try:
            delete_des_pod(des_pod_template, des_info['url'], True)
        except HTTPError as http_error:
            if http_error.response.status_code != 404:
                raise http_error
        raise e
    response.raise_for_status()
    return True, response.json()


def create_new_pod(template):
    namespace = template.get('metadata', {}).get('namespace', 'default')
    new_pod = create_pod(namespace, template)
    msg = wait_pod_ready_ff(new_pod)
    return {
        **msg['annotations'],
        'current-containers': None
    }


def checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id):
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
    return src_pod


def restore(body):
    name = body['name']
    namespace = body.get('namespace', 'default')
    migration_id = body['migrationId']
    des_pod = get_pod(name, namespace)
    if des_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION) != migration_id:
        abort(409, "Pod is being migrated")
    update_pod_restart(name, namespace, START_MODE_ACTIVE)
    wait_restored_pod_ready(des_pod)
    release_pod(name, namespace)


def wait_restored_pod_ready(pod):
    name = pod['metadata']['name']
    namespace = pod['metadata'].get('namespace', 'default')
    asyncio.run(gather([wait_restored_container_ready(
        name,
        namespace,
        container['name'],
    ) for container in pod['spec']['containers']]))


async def wait_restored_container_ready(pod_name, namespace, container_name):
    found = False
    while not found:
        log = log_pod(pod_name, namespace, container_name).split('\n')
        for line in log:
            if 'Application is ready, restore took' in line:
                found = True
                break
        await asyncio.sleep(0.1)


def delete_src_pod(src_pod):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    delete_pod(name, namespace)
