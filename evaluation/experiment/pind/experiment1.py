import json
import os
import subprocess
from time import sleep

import requests as requests
import yaml

MEMHOG_CONFIG = './memhog.yml'
SRC_CONFIG = '/example/path'
DES_CONFIG = '/example/path'
SRC = 'example.url'
DES = 'example.url'
NAME = 'memhog'
NAMESPACE = 'default'


def get_pod(config_file, name, namespace):
    return subprocess.run(f'kubectl --kubeconfig="{config_file}" -n {namespace} get pod {name}',
                          capture_output=True).stderr


def test(n, memory_footprint):
    with open('./pind.json') as f:
        results = json.load(f)
    i = 0
    results[memory_footprint] = []
    while True:
        if i >= n:
            with open('./pind.json', 'w') as f:
                json.dump(results, f)
            return
        print(f'round {i + 1}', end=' ')
        while True:
            if get_pod(SRC_CONFIG, NAME, NAMESPACE) != b'':
                break
            sleep(1)
        subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" apply -f {MEMHOG_CONFIG}',
                       capture_output=True)
        subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" wait --for=condition=ready pod -l app={NAME} ',
                       capture_output=True)
        sleep(3 + memory_footprint / 64)
        response = requests.post(f'http://{SRC}/migrate', json={
            'name': NAME,
            'namespace': NAMESPACE,
            'destinationUrl': DES
        })
        if response.status_code == 200:
            result = response.json()
            del result['des_pod']
            print(result['message'], result['overhead']['total'])
            results[memory_footprint].append(result)
            subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" -n {NAMESPACE} delete pod {result["des_pod"]["metadata"]["name"]}',
                           capture_output=True)
            while True:
                if get_pod(DES_CONFIG, result['des_pod']['metadata']['name'], NAMESPACE) != b'':
                    break
                sleep(1)
            i += 1
        else:
            print(f'error: [{response.status_code}] {response.text}')
            raise Exception(f'error: [{response.status_code}] {response.text}')


if __name__ == '__main__':
    if not os.path.exists('./pind.json'):
        with open('./pind.json', 'w') as f:
            json.dump({}, f)
    for memory_footprint in [0, 64, 128, 256, 512, 1024]:
        with open(MEMHOG_CONFIG) as f:
            memhog_spec = yaml.safe_load(f)
        memhog_spec['spec']['containers'][0]['env'][0]['value'] = str(memory_footprint)
        with open(MEMHOG_CONFIG, 'w') as f:
            yaml.dump(memhog_spec, f)
        test(3, memory_footprint)
