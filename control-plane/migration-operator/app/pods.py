import kopf
from kubernetes import client
from kubernetes.client import ApiException

from share.const import MIGRATABLE_ANNOTATION, INTERFACE_PORT_ANNOTATION, INTERFACE_HOST_ANNOTATION
from share.lib import send_event, send_error_event, inject_service


def check_pod_ready(event, **_):
    return event['type'] == 'MODIFIED' and event['object']['status']['phase'] == 'Running' and \
           'deletionTimestamp' not in event['object']['metadata'] and \
           all([condition['status'] == 'True' for condition in event['object']['status']['conditions']]) and \
           all([status['lastState'] == {} for status in event['object']['status']['containerStatuses']])


@kopf.on.event('v1', 'pods', annotations={MIGRATABLE_ANNOTATION: 'False'}, when=check_pod_ready)
def created_to_running_or_ready(name, body, patch, **_):
    send_event(body, 'ready', {'pod': name})
    patch.annotations[MIGRATABLE_ANNOTATION] = True


def check_pod_not_ready(event, **_):
    return not(check_pod_ready(event))


@kopf.on.event('v1', 'pods', annotations={MIGRATABLE_ANNOTATION: 'True'}, when=check_pod_not_ready)
def report_failure(event, logger, name, body, patch, **_):
    logger.error(event)
    send_error_event(body, name, 'pod becomes not ready')
    patch.annotations[MIGRATABLE_ANNOTATION] = False


@kopf.on.create('v1', 'pods', annotations={MIGRATABLE_ANNOTATION: kopf.PRESENT})
def expose_service(logger, name, meta, namespace, spec, body, patch, **_):
    try:
        service_template = inject_service(name, meta['labels'])
        service = client.CoreV1Api().create_namespaced_service(namespace, service_template)
        logger.info(f"creating Service: {service.metadata.name}")

        node = client.CoreV1Api().read_node(spec['nodeName']).status.addresses[0].address

        patch.metadata.annotations = {
            INTERFACE_HOST_ANNOTATION: f'{node}.nip.io',
            INTERFACE_PORT_ANNOTATION: service.spec.ports[0].node_port
        }
    except ApiException as e:
        logger.error(f"[{e.status}]: {e.body}")
        send_error_event(body, name, e.body)
        return
