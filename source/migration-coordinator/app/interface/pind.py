import json
import os
from datetime import datetime, timedelta
from time import sleep

import requests
from dateutil.tz import tzlocal
from flask import abort
from requests import HTTPError, RequestException

from app.const import MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, VOLUME_LIST_ANNOTATION, \
    SYNC_HOST_ANNOTATION, SYNC_PORT_ANNOTATION, LAST_APPLIED_CONFIG, ORCHESTRATOR_TYPE_MESOS, START_MODE_NULL, \
    INTERFACE_PIND, START_MODE_ACTIVE, START_MODE_PASSIVE, INTERFACE_ANNOTATION
from app.env import ORCHESTRATOR_TYPE
from app.orchestrator import select_orchestrator

client = select_orchestrator()


def get_name():
    return INTERFACE_PIND


def is_compatible(src_pod, des_info):
    try:
        response = requests.get(f"http://{src_pod['status']['podIP']}:2375/_ping")
        response.raise_for_status()
        if 'Libpod' in response.headers.get('Server'):
            return True
    except RequestException:
        pass
    return False


def generate_des_pod_template(src_pod):
    body = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    body['metadata']['annotations'][LAST_APPLIED_CONFIG] = src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG)
    body['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_NULL
    body['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = src_pod['metadata']['annotations'][
        MIGRATION_ID_ANNOTATION]
    return body


def create_des_pod(des_pod_template, des_info, migration_state):
    try:
        response = requests.post(f"http://{des_info['url']}/create", json={
            'interface': get_name(),
            'template': des_pod_template
        })
        response.raise_for_status()
        migration_state['des_pod_exist'] = True
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 504:
            migration_state['des_pod_exist'] = True
        raise e


def create_new_pod(template):
    namespace = template.get('metadata', {}).get('namespace', 'default')
    new_pod = client.create_pod(namespace, template)
    msg = wait_created_pod_ready(new_pod)
    response = requests.get(f"http://{msg['ip']}:8888/list")
    response.raise_for_status()
    return {
        **msg['annotations'],
        'current-containers': response.json()
    }


def wait_created_pod_ready(pod):
    start_time = datetime.now(tz=tzlocal())
    while True:
        if 'podIP' in pod['status']:
            status_code = probe_all(pod['status']['podIP'])
            annotations = pod['metadata']['annotations']
            if (annotations[START_MODE_ANNOTATION] == START_MODE_ACTIVE and status_code == 200) \
                    or (annotations[START_MODE_ANNOTATION] == START_MODE_PASSIVE and status_code == 204) \
                    or (annotations[START_MODE_ANNOTATION] == START_MODE_NULL and status_code < 400):
                if SYNC_PORT_ANNOTATION in annotations:
                    return {'annotations': {
                        VOLUME_LIST_ANNOTATION: annotations[VOLUME_LIST_ANNOTATION],
                        SYNC_HOST_ANNOTATION: annotations[SYNC_HOST_ANNOTATION],
                        SYNC_PORT_ANNOTATION: annotations[SYNC_PORT_ANNOTATION]
                    }, 'ip': pod['status']['podIP']}
                else:
                    pod = client.get_pod(pod['metadata']['name'], pod['metadata']['namespace'])
        else:
            pod = client.get_pod(pod['metadata']['name'], pod['metadata']['namespace'])

        if datetime.now(tz=tzlocal()) - start_time > timedelta(minutes=1):
            abort(504, 'Timeout while waiting pod to be ready')

        sleep(0.1)


def probe_all(pod_ip):
    exit_code = os.system(f"/app/wait-for-it.sh {pod_ip}:8888 -t 1")
    if exit_code == 0:
        return requests.get(f"http://{pod_ip}:8888/probeAll").status_code
    return 1


def checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id, migration_state):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    src_pod = client.update_pod_restart(name, namespace, START_MODE_NULL)
    response = requests.post(f"http://{src_pod['status']['podIP']}:8888/migrate", json={
        'checkpointId': checkpoint_id,
        'interfaceHost': des_pod_annotations[SYNC_HOST_ANNOTATION],
        'interfacePort': des_pod_annotations[SYNC_PORT_ANNOTATION],
        'containers': des_pod_annotations['current-containers'],
        'volumes': json.loads(des_pod_annotations[VOLUME_LIST_ANNOTATION])
    })
    response.raise_for_status()
    return src_pod


def restore(body):
    name = body['name']
    namespace = body.get('namespace', 'default')
    migration_id = body['migrationId']
    checkpoint_id = body['checkpointId']
    des_pod = client.get_pod(name, namespace)
    if des_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION) != migration_id:
        abort(409, "Pod is being migrated")
    response = requests.post(f"http://{des_pod['status']['podIP']}:8888/restore", json={
        'checkpointId': checkpoint_id
    })
    response.raise_for_status()
    wait_restored_pod_ready(des_pod)
    client.update_pod_restart(name, namespace, START_MODE_ACTIVE)
    client.release_pod(name, namespace)


def wait_restored_pod_ready(pod):
    start_time = datetime.now(tz=tzlocal())
    while True:
        status_code = probe_all(pod['status']['podIP'])
        if status_code == 200:
            return

        if datetime.now(tz=tzlocal()) - start_time > timedelta(minutes=1):
            abort(504, 'Timeout while waiting pod to be ready')

        sleep(0.1)


def delete_src_pod(src_pod):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    client.delete_pod(name, namespace)
    if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MESOS:
        client.delete_pod(f"{name}-monitor", namespace)


def recover(src_pod, destination_url, migration_state, delete_frontman, delete_des_pod):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    if src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION) != START_MODE_ACTIVE:
        client.update_pod_restart(name, namespace, START_MODE_ACTIVE)
    if migration_state['frontmant_exist']:
        delete_frontman(src_pod)
    if migration_state['des_pod_exist']:
        delete_des_pod(src_pod, destination_url)
