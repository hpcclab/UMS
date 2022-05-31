import json
from datetime import datetime

from dateutil.tz import tzlocal
from flask import abort
from kubernetes import client
from kubernetes.watch import watch

from app.const import MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION


def get_pod(name, namespace):
    return client.CoreV1Api().read_namespaced_pod(name, namespace).to_dict()


def create_pod(namespace, body):
    return client.CoreV1Api().create_namespaced_pod(namespace, body).to_dict()


def delete_pod(name, namespace):
    client.CoreV1Api().delete_namespaced_pod(name, namespace)


def lock_pod(name, namespace, body, migration_id):
    body['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = migration_id
    return client.CoreV1Api().replace_namespaced_pod(name, namespace, body)


def release_pod(name, namespace, body):
    body['metadata']['annotations'].pop(MIGRATION_ID_ANNOTATION)
    return client.CoreV1Api().replace_namespaced_pod(name, namespace, body)


def disable_pod_restart(name, namespace, body, start_mode):
    body['metadata']['annotations'][START_MODE_ANNOTATION] = start_mode
    return client.CoreV1Api().replace_namespaced_pod(name, namespace, body)


async def exec_pod(pod_name, namespace, command, container_name):
    thread = client.CoreV1Api().connect_get_namespaced_pod_exec(pod_name, namespace, command=command,
                                                                container=container_name, async_req=True)
    return thread.get()


def wait_pod_ready(pod):
    name = pod['metadata']['name']
    current_time = datetime.now(tz=tzlocal())
    w = watch.Watch()
    for event in w.stream(func=client.CoreV1Api().list_event_for_all_namespaces, timeout_seconds=60):
        if event['type'] == 'ADDED' and event['object'].type == 'migration' and \
                event['object'].event_time > current_time:
            msg = json.loads(event['object'].message)
            if msg['pod'] == name:
                if event['object'].reason == 'ready':
                    w.stop()
                    return pod['metadata']['annotations']
                if event['object'].reason == 'error':
                    w.stop()
                    abort(500, msg['error'])
    abort(504, 'timeout while waiting pod to be ready')
