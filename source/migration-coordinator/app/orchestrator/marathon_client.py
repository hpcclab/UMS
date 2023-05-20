from datetime import datetime

from dateutil.tz import tzlocal
from marathon import MarathonClient
from docker import from_env
from docker.errors import DockerException
from app.const import MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, DOMAIN, MIGRATION_POSITION_ANNOTATION, \
    MIGRATION_POSITION_SRC, MIGRATION_STEP_ANNOTATION, MIGRATION_STEP_RESERVED
from app.env import MARATHON_URL

client = MarathonClient(MARATHON_URL)
docker_client = from_env()


def load_incluster_config():
    pass


def list_pod():
    raise NotImplementedError()


def get_docker_id(name, namespace):
    return docker_client.containers.list(filters={'label': f'{DOMAIN}-app={namespace}-{name}'})[0].id


def get_pod(name, namespace):
    marathon_app = client.get_app(f'{namespace}-{name}')
    app_kubernetes_format = {
        'metadata': {
            'name': name,
            'namespace': namespace,
            'annotations': {param['value'].split('=')[0]: param['value'].split('=')[1]
                            for param in marathon_app.container.docker.parameters if param['key'] == 'label'}
        },
        'spec': {
            'containers': [{
                'name': name,
                'image': marathon_app.container.docker.image,
                'env': [{'name': param['value'].split('=')[0], 'value': param['value'].split('=')[1]}
                        for param in marathon_app.container.docker.parameters if param['key'] == 'env'],
                'volumeMounts': [
                    {'name': volume.host_path.replace('/', ''), 'mountPath': volume.container_path}
                    for volume in marathon_app.container.volumes
                ]
            }],
            'volumes': [
                {'name': volume.host_path.replace('/', ''), 'hostPath': volume.host_path}
                for volume in marathon_app.container.volumes
            ]
        },
        'status': {
            'podIP': docker_client.api.inspect_container(
                get_docker_id(name, namespace)
            )['NetworkSettings']['Networks']['bridge']['IPAddress']
        }
    }
    return app_kubernetes_format


def create_pod(namespace, body):
    raise NotImplementedError()


def delete_pod(name, namespace, delete_ambassador=False):
    client.delete_app(f'{namespace}-{name}')
    if delete_ambassador:
        delete_pod(f"{name}-monitor", namespace)


def update_pod_label(name, namespace, body):
    raise NotImplementedError()


def lock_pod(name, namespace, migration_id):
    # This does not really update the app (leave to future work)
    app = get_pod(name, namespace)
    app['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = migration_id
    app['metadata']['annotations'][MIGRATION_POSITION_ANNOTATION] = MIGRATION_POSITION_SRC
    app['metadata']['annotations'][MIGRATION_STEP_ANNOTATION] = MIGRATION_STEP_RESERVED
    return app


def update_migration_step(name, namespace, migration_step):
    raise NotImplementedError()


def release_pod(name, namespace):
    # This does not really update the app (leave to future work)
    return get_pod(name, namespace)


def update_pod_restart(name, namespace, start_mode):
    # This does not really update the app (leave to future work)
    app = get_pod(name, namespace)
    app['metadata']['annotations'][START_MODE_ANNOTATION] = start_mode
    return app


def update_pod_redirect(name, namespace, redirect_uri):
    # This does not really update the app (leave to future work)
    app = get_pod(name, namespace)
    app['metadata']['annotations']['redirect'] = redirect_uri
    return app


# async def exec_pod(pod_name, namespace, command, container_name):
def exec_pod(pod_name, namespace, command, container_name):
    exit_code, output = docker_client.containers.get(
        get_docker_id(pod_name, namespace)
    ).exec_run(cmd=f'/bin/bash -c "{command}"')
    if exit_code != 0:
        raise DockerException(output)
    return output


def log_pod(pod_name, namespace, container_name):
    return docker_client.containers.get(
        get_docker_id(pod_name, namespace)
    ).logs()


def delete_pod_owner_reference(name, namespace, checkpoint_id):
    raise NotImplementedError()


def delete_ssu_custom_resource(name, namespace):
    raise Exception('Code should not reach here')


def wait_restored_pod_ready_ssu(namespace, migration_id):
    raise NotImplementedError()


def wait_created_pod_ready_ff(pod):
    raise NotImplementedError()


def wait_created_pod_ready_frontman(pod, migration_state):
    raise NotImplementedError()
