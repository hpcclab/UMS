import json
from datetime import datetime

from dateutil.tz import tzlocal
from flask import abort
from kubernetes import client
from kubernetes.stream import stream
from kubernetes.watch import watch

from app.const import MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION


class FakeKubeResponse:
    def __init__(self, obj):
        self.data = json.dumps(obj)


def pod_to_dict(pod):
    return client.ApiClient().sanitize_for_serialization(pod)


def dict_to_pod(dict_object):
    return client.ApiClient().deserialize(FakeKubeResponse(dict_object), 'V1Pod')


def list_pod():
    return client.CoreV1Api().list_pod_for_all_namespaces()


def get_pod(name, namespace):
    return pod_to_dict(client.CoreV1Api().read_namespaced_pod(name, namespace))


def create_pod(namespace, body):
    return pod_to_dict(client.CoreV1Api().create_namespaced_pod(namespace, dict_to_pod(body)))


def delete_pod(name, namespace):
    client.CoreV1Api().delete_namespaced_pod(name, namespace)


def update_pod_label(name, namespace, body):
    return pod_to_dict(client.CoreV1Api().patch_namespaced_pod(name, namespace, body))


def lock_pod(name, namespace, migration_id):
    return pod_to_dict(client.CoreV1Api().patch_namespaced_pod(name, namespace, {'metadata': {'annotations': {
        MIGRATION_ID_ANNOTATION: migration_id}}}))


def release_pod(name, namespace):
    return pod_to_dict(client.CoreV1Api().patch_namespaced_pod(name, namespace, {'metadata': {'annotations': {
        MIGRATION_ID_ANNOTATION: None}}}))


def update_pod_restart(name, namespace, start_mode):
    return pod_to_dict(client.CoreV1Api().patch_namespaced_pod(name, namespace, {'metadata': {'annotations': {
        START_MODE_ANNOTATION: start_mode}}}))


def update_pod_redirect(name, namespace, redirect_uri):
    return pod_to_dict(client.CoreV1Api().patch_namespaced_pod(name, namespace, {'metadata': {'annotations': {
        'redirect': redirect_uri}}}))


async def exec_pod(pod_name, namespace, command, container_name):
    return stream(client.CoreV1Api().connect_get_namespaced_pod_exec, pod_name, namespace,
                  command=['/bin/sh', '-c', command], container=container_name,
                  stderr=True, stdin=True, stdout=True, tty=False, )


def log_pod(pod_name, namespace, container_name):
    return client.CoreV1Api().read_namespaced_pod_log(pod_name, namespace, container=container_name)


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
                    return msg
                if event['object'].reason == 'error':
                    w.stop()
                    abort(500, msg['error'])
    abort(504, 'Timeout while waiting pod to be ready')


def check_error_event(name, namespace, last_checked_time):
    events = client.CoreV1Api().list_namespaced_event(namespace)
    for event in events.items:
        if event.event_time is not None and event.type == 'migration' and event.event_time > last_checked_time:
            msg = json.loads(event.message)
            if msg['pod'] == name and event.reason == 'error':
                abort(500, msg['error'])
    return datetime.now(tz=tzlocal())
