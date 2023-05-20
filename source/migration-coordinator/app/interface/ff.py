# import asyncio
import json
from concurrent.futures import wait, ThreadPoolExecutor, FIRST_EXCEPTION
from time import sleep

import requests
from flask import abort
from requests import HTTPError

from app.const import MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_PASSIVE, VOLUME_LIST_ANNOTATION, \
    SYNC_HOST_ANNOTATION, SYNC_PORT_ANNOTATION, LAST_APPLIED_CONFIG, INTERFACE_FF, START_MODE_ACTIVE, \
    MIGRATION_POSITION_ANNOTATION, MIGRATION_STEP_ANNOTATION, MIGRATION_POSITION_DES, MIGRATION_STEP_RESERVED, \
    MIGRATION_STEP_DELETING, MIGRATION_STEP_RESTORING
from app.orchestrator import select_orchestrator

client = select_orchestrator()


# async def gather(fn_list):
#     return await asyncio.gather(*fn_list)


def get_name():
    return INTERFACE_FF


def is_compatible(src_pod, des_info):
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(
            client.exec_pod,
            src_pod['metadata']['name'],
            src_pod['metadata'].get('namespace', 'default'),
            f"ps -A -ww | grep -c [^]]fastfreeze",
            container['name'], )
            for container in src_pod['spec']['containers']]
    done, _ = wait(futures, return_when=FIRST_EXCEPTION)
    for task in done:
        err = task.exception()
        if err is not None:
            raise err
    # ff_processes = asyncio.run(gather([client.exec_pod(
    #     src_pod['metadata']['name'],
    #     src_pod['metadata'].get('namespace', 'default'),
    #     f"ps -A -ww | grep -c [^]]fastfreeze",
    #     container['name'],
    # ) for container in src_pod['spec']['containers']]))
    ff_processes = [future.result() for future in futures]
    for process in ff_processes:
        if not process.isdigit() or int(process) < 1:
            return False
    return True


def generate_des_pod_template(src_pod, migrate_image):
    body = json.loads(src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG))
    body['metadata']['annotations'][LAST_APPLIED_CONFIG] = src_pod['metadata']['annotations'].get(LAST_APPLIED_CONFIG)
    body['metadata']['annotations'][START_MODE_ANNOTATION] = START_MODE_PASSIVE
    body['metadata']['annotations'][MIGRATION_ID_ANNOTATION] = src_pod['metadata']['annotations'][
        MIGRATION_ID_ANNOTATION]
    body['metadata']['annotations'][MIGRATION_POSITION_ANNOTATION] = MIGRATION_POSITION_DES
    body['metadata']['annotations'][MIGRATION_STEP_ANNOTATION] = MIGRATION_STEP_RESERVED
    return body


def create_des_pod(des_pod_template, des_info, migration_state):
    try:
        response = requests.post(f"http://{des_info['url']}/create", json={
            'interface': get_name(),
            'template': des_pod_template
        })
        response.raise_for_status()
        migration_state['des_pod_exist'] = True
        return response.json()
    except HTTPError as e:
        if e.response.status_code == 504:
            migration_state['des_pod_exist'] = True
        raise e


def do_create_pod(template):
    namespace = template.get('metadata', {}).get('namespace', 'default')
    new_pod = client.create_pod(namespace, template)
    msg = client.wait_created_pod_ready_ff(new_pod)
    return {
        **msg['annotations'],
        'current-containers': None
    }


def checkpoint_and_transfer(src_pod, des_pod_annotations, checkpoint_id, migration_state, migrate_image, destination_url, migration_id, des_pod_template):
    volume_list = json.loads(src_pod['metadata']['annotations'][VOLUME_LIST_ANNOTATION])
    interface_host = des_pod_annotations[SYNC_HOST_ANNOTATION]
    interface_port = json.loads(des_pod_annotations[SYNC_PORT_ANNOTATION])
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(
            client.exec_pod,
            name,
            namespace,
            f'''
            /root/wait-for-it.sh {interface_host}:{interface_port[container['name']]} -t 0 &&
            mc alias set migration http://{interface_host}:{interface_port[container['name']]} minioadmin minioadmin &&
            S3_CMD='/root/s3 migration' CRIU_OPTS='' fastfreeze checkpoint --leave-running -vv {'--preserve-path' + volume_list[container['name']] if container['name'] in volume_list else ''}
            ''',
            container['name'], )
            for container in src_pod['spec']['containers']]
    done, _ = wait(futures, return_when=FIRST_EXCEPTION)
    for task in done:
        err = task.exception()
        if err is not None:
            raise err
    # responses = asyncio.run(gather([client.exec_pod(
    #     name,
    #     namespace,
    #     f'''
    #     /root/wait-for-it.sh {interface_host}:{interface_port[container['name']]} -t 0 &&
    #     mc alias set migration http://{interface_host}:{interface_port[container['name']]} minioadmin minioadmin &&
    #     S3_CMD='/root/s3 migration' CRIU_OPTS='' fastfreeze checkpoint --leave-running -vv {'--preserve-path' + volume_list[container['name']] if container['name'] in volume_list else ''}
    #     ''',
    #     container['name'],
    # ) for container in src_pod['spec']['containers']]))
    responses = [future.result() for future in futures]
    checkpoint_and_transfer_overhead = []
    for response in responses:
        checkpoint_overhead = None
        checkpoint_files_transfer_overhead = None
        for line in response.split('\n'):
            if 'Dumping finished successfully' in line:
                checkpoint_overhead = float(line.split()[1].replace('(', '').replace('s)', ''))
            if 'Checkpoint completed in' in line:
                checkpoint_files_transfer_overhead = float(line.split()[5].replace('(', '').replace('s)', ''))
        if checkpoint_overhead is None or checkpoint_files_transfer_overhead is None:
            abort(500, f"No checkpoint log found in {response}")
        checkpoint_and_transfer_overhead.append({'checkpoint': checkpoint_overhead,
                                                 'checkpoint_files_transfer': checkpoint_files_transfer_overhead,
                                                 'checkpoint_files_delay': 0})
    fields = ['checkpoint', 'pre_checkpoint', 'checkpoint_files_transfer', 'checkpoint_files_delay',
              'file_system_transfer', 'file_system_delay', 'volume_transfer', 'volume_delay',
              'save_image', 'image_layers_transfer', 'image_layers_delay', 'load_image']
    checkpoint_and_transfer_overhead = {
        field: max([overhead.get(field, -1) for overhead in checkpoint_and_transfer_overhead]) for field in fields
    }
    return src_pod, {
        field: checkpoint_and_transfer_overhead[field] if checkpoint_and_transfer_overhead[field] > -1 else None
        for field in fields
    }


def load_image(body):
    pass


def restore(body):
    name = body['name']
    namespace = body.get('namespace', 'default')
    migration_id = body['migrationId']
    des_pod = client.get_pod(name, namespace)
    if des_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION) != migration_id:
        abort(409, "Pod is being migrated")
    client.update_migration_step(name, namespace, MIGRATION_STEP_RESTORING)
    client.update_pod_restart(name, namespace, START_MODE_ACTIVE)
    wait_restored_pod_ready(des_pod)
    return client.release_pod(name, namespace)


def wait_restored_pod_ready(pod):
    name = pod['metadata']['name']
    namespace = pod['metadata'].get('namespace', 'default')
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(
            wait_restored_container_ready,
            name,
            namespace,
            container['name'], )
            for container in pod['spec']['containers']]
    done, _ = wait(futures, return_when=FIRST_EXCEPTION)
    for task in done:
        err = task.exception()
        if err is not None:
            raise err
    # asyncio.run(gather([wait_restored_container_ready(
    #     name,
    #     namespace,
    #     container['name'],
    # ) for container in pod['spec']['containers']]))


# async def wait_restored_container_ready(pod_name, namespace, container_name):
def wait_restored_container_ready(pod_name, namespace, container_name):
    found = False
    while not found:
        log = client.log_pod(pod_name, namespace, container_name).split('\n')
        for line in log:
            if 'Application is ready, restore took' in line:
                found = True
                break
        sleep(0.1)
        # await asyncio.sleep(0.1)


def delete_src_pod(src_pod):
    name = src_pod['metadata']['name']
    namespace = src_pod['metadata'].get('namespace', 'default')
    client.update_migration_step(name, namespace, MIGRATION_STEP_DELETING)
    do_delete_pod(name, namespace)


def do_delete_pod(name, namespace):
    client.delete_pod(name, namespace)


def recover(src_pod, destination_url, migration_state, delete_frontman, delete_des_pod):
    try:
        if migration_state['frontmant_exist']:
            delete_frontman(src_pod)
        if migration_state['des_pod_exist']:
            delete_des_pod(src_pod, destination_url, get_name())
    except Exception:
        pass
