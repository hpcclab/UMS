import os
from datetime import datetime, timedelta
from time import sleep

import requests
from dateutil.tz import tzlocal
from flask import Blueprint, request, abort

from app.const import VOLUME_LIST_ANNOTATION, INTERFACE_PORT_ANNOTATION, INTERFACE_HOST_ANNOTATION, \
    START_MODE_ANNOTATION, START_MODE_ACTIVE, START_MODE_PASSIVE, ENGINE_ANNOTATION, ENGINE_DIND
from app.kubernetes_client import create_pod, wait_pod_ready as wait_pod_ready_ff
from app.lib import get_pod

create_api_blueprint = Blueprint('create_api', __name__)


@create_api_blueprint.route("/create", methods=['POST'])
def create_api():
    body = request.get_json()
    new_pod = create_new_pod(body)
    if body['metadata']['annotations'].get(ENGINE_ANNOTATION) == ENGINE_DIND:
        msg = wait_pod_ready(new_pod)
        response = requests.get(f"http://{msg['ip']}:8888/list")
        response.raise_for_status()
        current_containers = response.json()
    else:
        msg = wait_pod_ready_ff(new_pod)
        current_containers = None
    return {
        **msg['annotations'],
        'current-containers': current_containers
    }


def create_new_pod(body):
    namespace = body.get('metadata', {}).get('namespace', 'default')
    return create_pod(namespace, body)


def wait_pod_ready(pod):
    start_time = datetime.now(tz=tzlocal())
    while True:
        if 'podIP' in pod['status']:
            status_code = probe_all(pod['status']['podIP'])
            annotations = pod['metadata']['annotations']
            if (annotations[START_MODE_ANNOTATION] == START_MODE_ACTIVE and status_code == 200)\
                    or (annotations[START_MODE_ANNOTATION] == START_MODE_PASSIVE and status_code == 204):
                if INTERFACE_PORT_ANNOTATION in annotations:
                    return {'annotations': {
                        VOLUME_LIST_ANNOTATION: annotations[VOLUME_LIST_ANNOTATION],
                        INTERFACE_HOST_ANNOTATION: annotations[INTERFACE_HOST_ANNOTATION],
                        INTERFACE_PORT_ANNOTATION: annotations[INTERFACE_PORT_ANNOTATION]
                    }, 'ip': pod['status']['podIP']}
                else:
                    pod = get_pod(pod['metadata']['name'], pod['metadata']['namespace'])
        else:
            pod = get_pod(pod['metadata']['name'], pod['metadata']['namespace'])

        if datetime.now(tz=tzlocal()) - start_time > timedelta(minutes=1):
            abort(504, 'Timeout while waiting pod to be ready')

        sleep(0.1)


def probe_all(pod_ip):
    exit_code = os.system(f"/app/wait-for-it.sh {pod_ip}:8888 -t 1")
    if exit_code == 0:
        return requests.get(f"http://{pod_ip}:8888/probeAll").status_code
    return 1
