import asyncio
import json

import kopf
from kubernetes import client
from kubernetes.client import ApiException

from share.const import MIGRATABLE_ANNOTATION, SYNC_PORT_ANNOTATION, SYNC_HOST_ANNOTATION, \
    VOLUME_LIST_ANNOTATION, INTERFACE_ANNOTATION, INTERFACE_DIND, INTERFACE_FF, INTERFACE_PIND, \
    MIGRATABLE_TRUE, MIGRATABLE_POSSIBLE, MIGRATABLE_FALSE, BYPASS_ANNOTATION
from share.lib import send_event, send_error_event, inject_service, gather
from share.env import HOST_NAME


def check_pod_ready(event, **_):
    return event['type'] == 'MODIFIED' and event['object']['status']['phase'] == 'Running' and \
           'deletionTimestamp' not in event['object']['metadata'] and \
           all([condition['status'] == str(True) for condition in event['object']['status']['conditions']])


@kopf.on.event('v1', 'pods', annotations={BYPASS_ANNOTATION: kopf.ABSENT, MIGRATABLE_ANNOTATION: MIGRATABLE_FALSE}, when=check_pod_ready)
def report_ready(name, annotations, body, patch, **_):
    if annotations.get(INTERFACE_ANNOTATION) is None:
        patch.metadata['annotations'] = {MIGRATABLE_ANNOTATION: MIGRATABLE_POSSIBLE}
    else:
        patch.metadata['annotations'] = {MIGRATABLE_ANNOTATION: MIGRATABLE_TRUE}
    if SYNC_PORT_ANNOTATION in annotations:
        send_event(body, 'ready', {'pod': name, 'annotations': {
            VOLUME_LIST_ANNOTATION: annotations[VOLUME_LIST_ANNOTATION],
            SYNC_HOST_ANNOTATION: annotations[SYNC_HOST_ANNOTATION],
            SYNC_PORT_ANNOTATION: annotations[SYNC_PORT_ANNOTATION],
        }, 'ip': body['status']['podIP']})


def check_pod_not_ready(event, **_):
    return not(check_pod_ready(event))


@kopf.on.event('v1', 'pods', annotations={BYPASS_ANNOTATION: kopf.ABSENT, MIGRATABLE_ANNOTATION: MIGRATABLE_TRUE}, when=check_pod_not_ready)
@kopf.on.event('v1', 'pods', annotations={BYPASS_ANNOTATION: kopf.ABSENT, MIGRATABLE_ANNOTATION: MIGRATABLE_POSSIBLE}, when=check_pod_not_ready)
def report_failure(name, body, patch, **_):
    send_error_event(body, name, 'pod becomes not ready')
    patch.metadata['annotations'] = {MIGRATABLE_ANNOTATION: MIGRATABLE_FALSE}


@kopf.on.create('v1', 'pods', annotations={BYPASS_ANNOTATION: kopf.ABSENT, INTERFACE_ANNOTATION: INTERFACE_DIND})
@kopf.on.create('v1', 'pods', annotations={BYPASS_ANNOTATION: kopf.ABSENT, INTERFACE_ANNOTATION: INTERFACE_PIND})
def expose_service(logger, name, meta, namespace, spec, body, patch, **_):
    try:
        service_template = inject_service('../template/service.yml', name, meta['labels'])
        service = client.CoreV1Api().create_namespaced_service(namespace, service_template)
        logger.info(f"creating Service: {service.metadata.name}")

        node = HOST_NAME if HOST_NAME else client.CoreV1Api().read_node(spec['nodeName']).status.addresses[0].address

        patch.metadata['annotations'] = {
            SYNC_HOST_ANNOTATION: f'{node}.nip.io',
            SYNC_PORT_ANNOTATION: str(service.spec.ports[0].node_port)
        }
    except ApiException as e:
        logger.error(f"[{e.status}]: {e.body}")
        send_error_event(body, name, e.body)
        return


async def expose_one_service_ff(logger, name, meta, namespace, container_name):
    service_template = inject_service('../template/service-ff.yml', name, meta['labels'])
    container_names = container_name.split('__')
    if len(container_names) > 1:
        service_template['spec']['ports'][0]['targetPort'] = int(container_names[-1])
    thread = client.CoreV1Api().create_namespaced_service(namespace, service_template, async_req=True)
    service = thread.get()
    logger.info(f"creating Service: {service.metadata.name}")
    return container_name, str(service.spec.ports[0].node_port)


@kopf.on.create('v1', 'pods', annotations={BYPASS_ANNOTATION: kopf.ABSENT, INTERFACE_ANNOTATION: INTERFACE_FF})
def expose_service_ff(logger, name, meta, namespace, spec, body, patch, **_):
    try:
        results = asyncio.run(gather([expose_one_service_ff(
            logger, name, meta, namespace, container['name']
        ) for container in spec['containers']]))

        node = HOST_NAME if HOST_NAME else client.CoreV1Api().read_node(spec['nodeName']).status.addresses[0].address

        patch.metadata['annotations'] = {
            SYNC_HOST_ANNOTATION: f'{node}.nip.io',
            SYNC_PORT_ANNOTATION: json.dumps({result[0]: result[1] for result in results})
        }
    except ApiException as e:
        logger.error(f"[{e.status}]: {e.body}")
        send_error_event(body, name, e.body)
        return


@kopf.on.update('v1', 'pods', annotations={BYPASS_ANNOTATION: kopf.ABSENT}, field=f'metadata.annotations.{SYNC_PORT_ANNOTATION}', old=kopf.ABSENT, new=kopf.PRESENT)
def report_expose(name, annotations, body, **_):
    if 'podIP' in body['status']:
        send_event(body, 'ready', {'pod': name, 'annotations': {
                VOLUME_LIST_ANNOTATION: annotations[VOLUME_LIST_ANNOTATION],
                SYNC_HOST_ANNOTATION: annotations[SYNC_HOST_ANNOTATION],
                SYNC_PORT_ANNOTATION: annotations[SYNC_PORT_ANNOTATION],
            }, 'ip': body['status']['podIP']})
    else:
        send_event(body, 'expose', {'pod': name, 'annotations': {
            VOLUME_LIST_ANNOTATION: annotations[VOLUME_LIST_ANNOTATION],
            SYNC_HOST_ANNOTATION: annotations[SYNC_HOST_ANNOTATION],
            SYNC_PORT_ANNOTATION: annotations[SYNC_PORT_ANNOTATION],
        }})
