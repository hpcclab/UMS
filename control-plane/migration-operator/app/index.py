import kopf

from share.const import MIGRATABLE_ANNOTATION


@kopf.index('v1', 'pods', annotations={MIGRATABLE_ANNOTATION: kopf.PRESENT})
def index_pod(name, namespace, meta, **_):
    return {(name, namespace): meta.get('deletionTimestamp') is None}


@kopf.index('v1', 'pods', annotations={MIGRATABLE_ANNOTATION: kopf.PRESENT})
def index_pod_ip(namespace, meta, status, **_):
    return {(meta['annotations'][MIGRATABLE_ANNOTATION], namespace): status.get('podIP')}


@kopf.index('v1', 'services', annotations={MIGRATABLE_ANNOTATION: kopf.PRESENT})
def index_service(name, namespace, spec, **_):
    return {(name, namespace): spec}
