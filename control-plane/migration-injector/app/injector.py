import json
import os

import kopf
import yaml

from share.const import MIGRATABLE_ANNOTATION, BYPASS_ANNOTATION, ENGINE_ANNOTATION, ENGINE_FAST_FREEZE, \
    START_MODE_ANNOTATION, START_MODE_ACTIVE, VOLUME_LIST_ANNOTATION, CONTAINER_SPEC_ANNOTATION
from share.env import EXEC_MONITOR, IMAGE_PULL_POLICY, env


@kopf.on.mutate('v1', 'pods', operation='CREATE',
                annotations={MIGRATABLE_ANNOTATION: kopf.PRESENT, BYPASS_ANNOTATION: kopf.ABSENT})
def mutate_pod(annotations, spec, patch, **_):
    injected = inject_pod(annotations, spec)
    patch.spec['containers'] = injected['spec']['containers']
    patch.spec['volumes'] = injected['spec']['volumes']
    patch.metadata['annotations'] = injected['metadata']['annotations']


def inject_pod(annotations, spec):
    if annotations.get(ENGINE_ANNOTATION) == ENGINE_FAST_FREEZE:
        template = inject_pod_ff(spec)
    else:
        template = inject_pod_dind(spec)
    template['metadata']['annotations'][MIGRATABLE_ANNOTATION] = str(True)
    template['metadata']['annotations'][START_MODE_ANNOTATION] = annotations.get(START_MODE_ANNOTATION,
                                                                                 START_MODE_ACTIVE)
    template['metadata']['annotations'][BYPASS_ANNOTATION] = str(True)
    return template


def inject_pod_ff(spec):
    with open(os.path.join(os.path.dirname(__file__), '../template/pod-ff.yaml'), 'rt') as f:
        template = yaml.safe_load(f.read().format(**env))
    template['spec']['volumes'] += spec.get('volumes', [])
    for container in template['spec']['containers']:
        container['volumeMounts'] += [{'name': volume['name'], 'mountPath': f"/mount/{volume['name']}"}
                                      for volume in spec.get('volumes', [])]
    template['spec']['containers'] += spec.get('containers', [])
    for container in template['spec']['containers']:
        container['volumeMounts'] = container.get('volumeMounts', []) +\
                                    [{'name': 'image-storage', 'mountPath': '/images'}]
    volume_list = {container['name']: ':'.join(container['volumeMounts'])
                   for container in spec.get('containers', []) if 'volumeMounts' in container}
    template['metadata']['annotations'][VOLUME_LIST_ANNOTATION] = json.dumps(volume_list)
    return template


def inject_pod_dind(spec):
    with open(os.path.join(os.path.dirname(__file__), '../template/pod-dind.yaml'), 'rt') as f:
        template = yaml.safe_load(f.read().format(**env))
    for container in template['spec']['containers']:
        if container['name'] == 'runtime':
            container['ports'] = [port for c in spec.get('containers', []) for port in c.get('ports', [])]
    template['spec']['volumes'] += spec.get('volumes', [])
    for container in template['spec']['containers']:
        container['volumeMounts'] += [{'name': volume['name'], 'mountPath': f"/mount/{volume['name']}"}
                                      for volume in spec.get('volumes', [])]
    template['spec']['containers'] += replace_container(spec, *read_docker_env(template))
    template['metadata']['annotations'][CONTAINER_SPEC_ANNOTATION] = json.dumps(spec.get('containers', []))
    template['metadata']['annotations'][VOLUME_LIST_ANNOTATION] = json.dumps([f"/mount/{volume['name']}"
                                                                              for volume in spec.get('volumes', [])])
    return template


def read_docker_env(template):
    env_api_port = '8888'
    env_docker_host = '127.0.0.1'
    env_docker_port = '2375'
    for container in template['spec']['containers']:
        if container['name'] == 'api-server':
            env_api_port = container['ports'][0]['containerPort']
            for env_var in container['env']:
                if env_var['name'] == 'DOCKER_HOST':
                    env_docker_host = env_var['value']
                if env_var['name'] == 'DOCKER_PORT':
                    env_docker_port = env_var['value']
    return env_docker_host, env_docker_port, env_api_port


def replace_container(spec, env_docker_host, env_docker_port, env_api_port):
    return [{'name': container['name'],
             'image': EXEC_MONITOR,
             'env': [{'name': 'DOCKER_HOST', 'value': f'{env_docker_host}:{env_docker_port}'},
                     {'name': 'CONTAINER_NAME', 'value': container['name']},
                     {'name': 'API_SERVER', 'value': f'127.0.0.1:{env_api_port}'}],
             'imagePullPolicy': IMAGE_PULL_POLICY,
             'startupProbe': {'httpGet': {'port': 8888, 'path': f"/probe/{container['name']}"}, 'periodSeconds': 1}}
            for container in spec.get('containers', [])]
