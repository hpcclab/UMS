import json
import os

import kopf
import yaml

from share.const import MIGRATABLE_ANNOTATION, BYPASS_ANNOTATION, INTERFACE_ANNOTATION, INTERFACE_DIND, \
    START_MODE_ANNOTATION, START_MODE_ACTIVE, VOLUME_LIST_ANNOTATION, CONTAINER_SPEC_ANNOTATION, LAST_APPLIED_CONFIG, \
    ORCHESTRATOR_TYPE_MINISHIFT, ORCHESTRATOR_TYPE_KUBERNETES, INTERFACE_PIND, INTERFACE_FF, MIGRATABLE_FALSE
from share.env import AMBASSADOR_IMAGE, IMAGE_PULL_POLICY, env, ORCHESTRATOR_TYPE


@kopf.on.mutate('v1', 'pods', operation='CREATE', annotations={BYPASS_ANNOTATION: kopf.ABSENT})
def mutate_pod(annotations, spec, patch, **_):
    if annotations.get(LAST_APPLIED_CONFIG):
        spec_to_mutate = json.loads(annotations[LAST_APPLIED_CONFIG])['spec']
    else:
        spec_to_mutate = spec
    injected = inject_pod(annotations, spec_to_mutate)
    patch.spec['containers'] = injected['spec']['containers']
    if 'volumes' in injected['spec']:
        patch.spec['volumes'] = injected['spec']['volumes']
    patch.metadata['annotations'] = injected['metadata']['annotations']


def inject_pod(annotations, spec):
    if annotations.get(INTERFACE_ANNOTATION) == INTERFACE_DIND:
        template = inject_pod_dind(spec, '../template/pod-dind.yaml')
    elif annotations.get(INTERFACE_ANNOTATION) == INTERFACE_PIND:
        template = inject_pod_dind(spec, '../template/pod-pind.yaml')
    elif annotations.get(INTERFACE_ANNOTATION) == INTERFACE_FF:
        template = inject_pod_ff(spec)
    else:
        template = inject_native(spec)
    template['metadata']['annotations'][MIGRATABLE_ANNOTATION] = MIGRATABLE_FALSE
    template['metadata']['annotations'][START_MODE_ANNOTATION] = annotations.get(START_MODE_ANNOTATION,
                                                                                 START_MODE_ACTIVE)
    template['metadata']['annotations'][BYPASS_ANNOTATION] = str(True)
    return template


def inject_native(spec):
    with open(os.path.join(os.path.dirname(__file__), '../template/pod.yaml'), 'rt') as f:
        template = yaml.safe_load(f.read().format(**env))
    template['spec'] = spec
    return template


def inject_pod_ff(spec):
    with open(os.path.join(os.path.dirname(__file__), '../template/pod-ff.yaml'), 'rt') as f:
        template = yaml.safe_load(f.read().format(**env))
    volume_list = {container['name']: ':'.join([mount['mountPath'] for mount in container['volumeMounts']])
                   for container in spec['containers'] if len(container.get('volumeMounts', [])) > 0}
    template['metadata']['annotations'][VOLUME_LIST_ANNOTATION] = json.dumps(volume_list)
    template['spec']['volumes'] += spec.get('volumes', [])
    template['spec']['containers'] = spec['containers']
    for container in template['spec']['containers']:
        if 'volumeMounts' not in container:
            container['volumeMounts'] = []
        container['volumeMounts'] += [{'name': 'podinfo', 'mountPath': '/etc/podinfo'}]
        if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
            container['securityContext'] = {'privileged': True}
        elif ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES:
            container['securityContext'] = {'capabilities': {'add': ['SYS_PTRACE']},
                                            'seccompProfile': {'type': 'RuntimeDefault'}}
    return template


def inject_pod_dind(spec, template_path):
    with open(os.path.join(os.path.dirname(__file__), template_path), 'rt') as f:
        template = yaml.safe_load(f.read().format(**env))
    template['spec']['volumes'] += spec.get('volumes', [])
    template['spec']['containers'][0]['ports'] = [port for c in spec.get('containers', []) for port in
                                                  c.get('ports', [])]
    template['spec']['containers'][0]['volumeMounts'] += [
        {'name': volume['name'], 'mountPath': f"/mount/{volume['name']}"}
        for volume in spec.get('volumes', [])]
    template['spec']['containers'] += replace_container(spec, read_docker_env(template))
    template['metadata']['annotations'][CONTAINER_SPEC_ANNOTATION] = json.dumps(spec.get('containers', []))
    template['metadata']['annotations'][VOLUME_LIST_ANNOTATION] = json.dumps([f"/mount/{volume['name']}"
                                                                              for volume in spec.get('volumes', [])])
    return template


def read_docker_env(template):
    env_docker_host = '127.0.0.1:2375'
    for container in template['spec']['containers']:
        if container['name'] == 'runtime':
            for env_var in container['env']:
                if env_var['name'] == 'DOCKER_HOST':
                    env_docker_host = env_var['value']
    return env_docker_host


def replace_container(spec, env_docker_host):
    return [{'name': container['name'],
             'image': AMBASSADOR_IMAGE,
             'env': [{'name': 'DOCKER_HOST', 'value': f'{env_docker_host}'},
                     {'name': 'CONTAINER_NAME', 'value': container['name']},
                     {'name': 'API_SERVER', 'value': f'127.0.0.1:8888'}],
             'imagePullPolicy': IMAGE_PULL_POLICY,
             'startupProbe': {'httpGet': {'port': 8888, 'path': f"/probe/{container['name']}"}, 'periodSeconds': 1}}
            for container in spec.get('containers', [])]
