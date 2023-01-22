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


def delete_pod_owner_reference(name, namespace, checkpoint_id):
    pod = get_pod(name, namespace)
    if pod['metadata'].get('ownerReferences') is None:
        return pod
    owner_references = []
    for owner_reference in pod['metadata'].get('ownerReferences', []):
        if owner_reference['apiVersion'] == 'podmig.dcn.ssu.ac.kr/v1' and owner_reference['kind'] == 'Podmigration' \
                and owner_reference['name'] == checkpoint_id:
            continue
        owner_references.append(owner_reference)
    owner_references = owner_references or None
    return client.CoreV1Api().patch_namespaced_pod(name, namespace, {'metadata': {'ownerReferences': owner_references}})


def delete_ssu_custom_resource(name, namespace):
    return client.CustomObjectsApi().delete_namespaced_custom_object(
        group='podmig.dcn.ssu.ac.kr',
        version='v1',
        plural='podmigrations',
        name=name,
        namespace=namespace
    )


def wait_pod_ready_ssu(namespace, migration_id):
    name = 'Unknown'
    w = watch.Watch()
    for event in w.stream(func=client.CoreV1Api().list_namespaced_pod,
                          namespace=namespace,
                          timeout_seconds=60):
        # event.type: ADDED, MODIFIED, DELETED
        if event['object'].metadata.annotations.get(MIGRATION_ID_ANNOTATION) == migration_id:
            name = event['object'].metadata.name
            if event["object"].status.phase == "Running":
                w.stop()
                return name
            if event["type"] == "DELETED":
                # Pod was deleted while we were waiting for it to start.
                w.stop()
                abort(500, f'{name} deleted before it started')
    abort(504, f'Timeout while waiting {name} to be ready')


def wait_pod_ready_frontman(pod, migration_state):
    name = pod['metadata']['name']
    namespace = pod['metadata']['namespace']
    w = watch.Watch()
    for event in w.stream(func=client.CoreV1Api().list_namespaced_pod,
                          namespace=namespace,
                          field_selector=f'metadata.name={name}',
                          timeout_seconds=60):
        if event["object"].status.phase == "Running":
            w.stop()
            return
        # event.type: ADDED, MODIFIED, DELETED
        if event["type"] == "DELETED":
            # Pod was deleted while we were waiting for it to start.
            w.stop()
            migration_state['frontmant_exist'] = False
            abort(500, f'{name} deleted before it started')
    abort(504, f'Timeout while waiting {name} to be ready')


def wait_pod_ready_ff(pod):
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
                    abort(500, msg['error'])  # todo type DELETED
    abort(504, 'Timeout while waiting pod to be ready')


def check_error_event(name, namespace, last_checked_time):
    events = client.CoreV1Api().list_namespaced_event(namespace)
    for event in events.items:
        if event.event_time is not None and event.type == 'migration' and event.event_time > last_checked_time:
            msg = json.loads(event.message)
            if msg['pod'] == name and event.reason == 'error':
                abort(500, msg['error'])
    return datetime.now(tz=tzlocal())
