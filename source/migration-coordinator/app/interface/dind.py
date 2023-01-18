import json
from datetime import datetime, timedelta
from time import sleep

import requests
from dateutil.tz import tzlocal
from flask import abort
from requests import Timeout, HTTPError, RequestException

from app.api.create import probe_all
from app.const import MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_PASSIVE, \
    VOLUME_LIST_ANNOTATION, \
    SYNC_HOST_ANNOTATION, SYNC_PORT_ANNOTATION, LAST_APPLIED_CONFIG, ORCHESTRATOR_TYPE_MESOS, START_MODE_NULL, \
    INTERFACE_DIND, START_MODE_ACTIVE
from app.env import ORCHESTRATOR_TYPE
from app.lib import delete_pod, get_pod, update_pod_restart, release_pod


def get_name():
    return INTERFACE_DIND


def is_compatible(src_pod, des_info):
    try:
        response = requests.get(f"http://{src_pod['status']['podIP']}:2375/_ping")
        response.raise_for_status()
        if 'Docker' in response.headers.get('Server'):
            return True
    except RequestException:
        pass
    return False



def generate_des_pod_template(src_pod):
    body = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    body['metadata']['annotations'][LAST_APPLIED_CONFIG] = src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG)
    body['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_PASSIVE
    body['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = src_pod['metadata']['annotations'][MIGRATION_ID_ANNOTATION]
    return body


def create_des_pod(des_pod_template, des_info, delete_des_pod):
    try:
        response = requests.post(f"http://{des_info['url']}/create", json=des_pod_template)
    except Timeout as e:
        try:
            delete_des_pod(des_pod_template, des_info['url'], True)
        except HTTPError as http_error:
            if http_error.response.status_code != 404:
                raise http_error
        raise e
    response.raise_for_status()
    return True, response.json()


def checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    src_pod = update_pod_restart(name, namespace, START_MODE_NULL)
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
    des_pod = get_pod(name, namespace)
    if des_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION) != migration_id:
        abort(409, "Pod is being migrated")
    response = requests.post(f"http://{des_pod['status']['podIP']}:8888/restore", json={
        'checkpointId': checkpoint_id
    })
    response.raise_for_status()
    wait_pod_ready(des_pod)
    update_pod_restart(name, namespace, START_MODE_ACTIVE)
    release_pod(name, namespace)


def wait_pod_ready(pod):
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
    delete_pod(name, namespace)
    if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MESOS:
        delete_pod(f"{name}-monitor", namespace)
