import json
import os
import subprocess
from time import sleep

import requests as requests
import yaml

OUTPUT = './experiment2.json'
MEMHOG_CONFIG = './memhog.yml'
SRC_CONFIG = '/example/path'
DES_CONFIG = '/example/path'
SRC = 'example.url'
DES = 'example.url'
NAME = 'memhogff'
NAMESPACE = 'default'


def get_pod(config_file, name, namespace):
    return subprocess.run(f'kubectl --kubeconfig="{config_file}" -n {namespace} get pod {name}',
                          capture_output=True, shell=True).stderr


def test(n, memory_footprint, memory_increment):
    with open(OUTPUT) as f:
        results = json.load(f)
    i = len(results.get(str(memory_footprint), []))
    if i == 0:
        results[str(memory_footprint)] = []
    while True:
        if i >= n:
            break
        print(f'round {i + 1}', end=' ')
        while True:
            if get_pod(SRC_CONFIG, NAME, NAMESPACE) != b'':
                break
            sleep(1)
        subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" apply -f {MEMHOG_CONFIG}',
                       capture_output=True, shell=True)
        subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" wait --for=condition=ready pod -l app={NAME} ',
                       capture_output=True, shell=True)
        sleep(3 + memory_footprint / memory_increment)
        response = requests.post(f'http://{SRC}/migrate', json={
            'name': NAME,
            'namespace': NAMESPACE,
            'destinationUrl': DES
        })
        if response.status_code == 200:
            result = response.json()
            print(result['message'], result['overhead']['total'])
            subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" -n {NAMESPACE} delete pod {result["des_pod"]["metadata"]["name"]}',
                           capture_output=True, shell=True)
            while True:
                if get_pod(DES_CONFIG, result['des_pod']['metadata']['name'], NAMESPACE) != b'':
                    break
                sleep(1)
            i += 1
            del result['des_pod']
            results[str(memory_footprint)].append(result)
        else:
            subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" -n {NAMESPACE} delete pod {NAME}',
                           capture_output=True, shell=True)
            while True:
                if get_pod(SRC_CONFIG, NAME, NAMESPACE) != b'':
                    break
                sleep(1)
    with open(OUTPUT, 'w') as f:
        json.dump(results, f)


if __name__ == '__main__':
    if not os.path.exists(OUTPUT):
        with open(OUTPUT, 'w') as f:
            json.dump({}, f)
    for num_process in range(1, 9):
        with open(MEMHOG_CONFIG) as f:
            memhog_spec = yaml.safe_load(f)
        memhog_spec['spec']['containers'][0]['env'][0]['value'] = str(0)
        memhog_spec['spec']['containers'][0]['env'][1]['value'] = str(64)
        memhog_spec['spec']['containers'][0]['env'][2]['value'] = str(num_process)
        with open(MEMHOG_CONFIG, 'w') as f:
            yaml.dump(memhog_spec, f)
        test(30, 0, 64)
