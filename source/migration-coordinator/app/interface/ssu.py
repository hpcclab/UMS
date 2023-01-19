import json

import requests

from app.const import MIGRATION_ID_ANNOTATION, SYNC_HOST_ANNOTATION, SYNC_PORT_ANNOTATION, LAST_APPLIED_CONFIG, \
    INTERFACE_SSU
from app.env import SSU_INTERFACE_SERVICE, SSU_INTERFACE_ENABLE
from app.kubernetes_client import delete_ssu_custom_resource, delete_pod_owner_reference, wait_pod_ready_ssu, \
    create_pod, release_pod


def get_name():
    return INTERFACE_SSU


def is_compatible(src_pod, des_info):
    if 'ssu_port' in des_info and SSU_INTERFACE_ENABLE is not None:
        return True
    return False


def generate_des_pod_template(src_pod):
    body = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    body['metadata']['annotations'][LAST_APPLIED_CONFIG] = src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG)
    body['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = src_pod['metadata']['annotations'][MIGRATION_ID_ANNOTATION]
    return body


def create_des_pod(des_pod_template, des_info, delete_des_pod):
    return False, {SYNC_HOST_ANNOTATION: des_info['ssu_host'], SYNC_PORT_ANNOTATION: des_info['ssu_port']}


def create_new_pod(template):
    namespace = template.get('metadata', {}).get('namespace', 'default')
    create_pod(namespace, template)
    return {
        'current-containers': None
    }


def checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id):
    response = requests.post(f"http://{SSU_INTERFACE_SERVICE}:8888/migrate", json={
        'checkpointId': checkpoint_id,
        'interfaceHost': des_pod_annotations[SYNC_HOST_ANNOTATION],
        'interfacePort': des_pod_annotations[SYNC_PORT_ANNOTATION],
        'template': json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
        # 'volumes': json.loads(des_pod_annotations[VOLUME_LIST_ANNOTATION])
        #todo check if volume is migrated
    })
    response.raise_for_status()    # todo forward body
    delete_ssu_custom_resource(checkpoint_id, src_pod['metadata'].get('namespace', 'default'))
    return src_pod


def restore(body):
    namespace = body.get('namespace', 'default')
    migration_id = body['migrationId']
    checkpoint_id = body['checkpointId']
    des_pod = body.get('template')
    response = requests.post(f"http://{SSU_INTERFACE_SERVICE}:8888/restore", json={
        'checkpointId': checkpoint_id,
        'template': des_pod
        # 'volumes': json.loads(des_pod_annotations[VOLUME_LIST_ANNOTATION])
        #todo check if volume is migrated
    })
    response.raise_for_status()
    pod_name = wait_pod_ready_ssu(namespace, migration_id)
    delete_pod_owner_reference(pod_name, namespace, checkpoint_id)
    delete_ssu_custom_resource(checkpoint_id, namespace)
    release_pod(pod_name, namespace)


def delete_src_pod(src_pod):
    pass
