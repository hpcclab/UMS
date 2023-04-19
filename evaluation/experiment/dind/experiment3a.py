import json
import os
import random
import subprocess
from time import sleep

import requests as requests
import yaml

OUTPUT = './experiment3a.json'
YOLO_CONFIG = './yolo.dev.yml'
# SRC_CONFIG = r'C:\Users\User\Projects\tmp\test\service-migration-3.yaml'
# DES_CONFIG = r'C:\Users\User\Projects\tmp\test\service-migration-4.yaml'
SRC_CONFIG = r'C:\Users\User\Projects\tmp\test\service-migration-1.yaml'
DES_CONFIG = r'C:\Users\User\Projects\tmp\test\service-migration-2.yaml'
# SRC = '10.131.36.30.nip.io:30001'
# DES = '10.131.36.31.nip.io:30001'
SRC = '10.131.36.31.nip.io:30001'
DES = '10.131.36.32.nip.io:30001'
NAME = 'yolo'
NAMESPACE = 'default'


def get_log(config_file, name=NAME):
    return subprocess.run(f'kubectl --kubeconfig="{config_file}" -n {NAMESPACE} logs {name} -c {name}',
                          capture_output=True, shell=True).stdout.decode("utf-8")


def get_checkpointed_memory(config_file):
    log = get_log(config_file).split('\n')
    for line, prev_line in zip(log[1:], log):
        split_line = line.split()
        split_prev_line = prev_line.split()
        if len(split_line) == 4 and len(split_prev_line) == 4 \
                and split_line[1] == 'Counter:' and split_prev_line[1] == 'Counter:':
            t = int(split_line[0])
            prev_t = int(split_prev_line[0])
            if t - prev_t > 200000:
                return int(prev_line.split()[3]) / 1000000, prev_t
    else:
        raise Exception('Cannot find counter at checkpointing step')


def get_downtime(config_file, name, prev_t):
    log = get_log(config_file, name).split('\n')
    first_line_incomplete = 0
    for line in log:
        split_line = line.split()
        if len(split_line) == 4 and split_line[1] == 'Counter:':
            if len(line.split()[0]) != 16:
                first_line_incomplete = 1
                continue
            t = int(split_line[0])
            return (t - prev_t - 100000 * (1 + first_line_incomplete)) / 1000000
    else:
        raise Exception('Cannot find counter')


def get_pod(config_file, name, namespace):
    return subprocess.run(f'kubectl --kubeconfig="{config_file}" -n {namespace} get pod {name}',
                          capture_output=True, shell=True).stderr


def test(n, index):
    with open(OUTPUT) as f:
        results = json.load(f)
    i = len(results.get(str(index), []))
    if i == 0:
        results[str(index)] = []
    try:
        while True:
            if i >= n:
                break
            print(f'round {i + 1}', end=' ')
            while True:
                if get_pod(SRC_CONFIG, NAME, NAMESPACE) != b'':
                    break
                sleep(1)
            subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" apply -f {YOLO_CONFIG}',
                           capture_output=True, shell=True)
            subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" wait --for=condition=ready pod -l app={NAME} ',
                           capture_output=True, shell=True)
            sleep(3 + random.random())
            response = requests.post(f'http://{SRC}/migrate', json={
                'name': NAME,
                'namespace': NAMESPACE,
                'destinationUrl': DES
            })
            if response.status_code == 200:
                result = response.json()
                result['memory'], timestamp = get_checkpointed_memory(SRC_CONFIG)
                result['downtime'] = get_downtime(DES_CONFIG, result["des_pod"]["metadata"]["name"], timestamp)
                print(result['message'], result['overhead']['total'], result['downtime'], result['memory'])
                subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" -n {NAMESPACE} delete pod {result["des_pod"]["metadata"]["name"]}',
                               capture_output=True, shell=True)
                while True:
                    if get_pod(DES_CONFIG, result['des_pod']['metadata']['name'], NAMESPACE) != b'':
                        break
                    sleep(1)
                i += 1
                del result['des_pod']
                results[str(index)].append(result)
            else:
                subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" -n {NAMESPACE} delete pod {NAME}',
                               capture_output=True, shell=True)
                subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" apply -f {YOLO_CONFIG}',
                               capture_output=True, shell=True)
                sleep(3)
                subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" -n {NAMESPACE} delete pod {NAME}',
                               capture_output=True, shell=True)
                while True:
                    if get_pod(SRC_CONFIG, NAME, NAMESPACE) != b'':
                        break
                    sleep(1)
                while True:
                    if get_pod(DES_CONFIG, NAME, NAMESPACE) != b'':
                        break
                    sleep(1)
    finally:
        with open(OUTPUT, 'w') as f:
            json.dump(results, f)


if __name__ == '__main__':
    if not os.path.exists(OUTPUT):
        with open(OUTPUT, 'w') as f:
            json.dump({}, f)
    test(40, 0)
