import json
import subprocess
from time import sleep

import requests as requests


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


def test(n):
    i = 0
    results = []
    while True:
        if i >= n:
            with open('./dind.json', 'w') as f:
                json.dump(results, f)
            return
        print(f'round {i + 1}', end=' ')
        (src, des, config_file) = (SRC, DES, DES_CONFIG) if i % 2 == 0 else (DES, SRC, SRC_CONFIG)
        while True:
            if get_pod(config_file, NAME, NAMESPACE) != b'':
                break
            sleep(1)
        response = requests.post(f'http://{src}/migrate', json={
            'name': NAME,
            'namespace': NAMESPACE,
            'destinationUrl': des
        })
        if response.status_code == 200:
            result = response.json()
            print(result)
            results.append(result)
            i += 1
        else:
            print(f'error: [{response.status_code}] {response.text}')
            break


if __name__ == '__main__':
    # subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" apply -f {MEMHOG_CONFIG}',
    #                capture_output=True)
    # subprocess.run(f'kubectl --kubeconfig="{SRC_CONFIG}" wait --for=condition=ready pod -l app={NAME} ',
    #                capture_output=True)
    test(5)
    # subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" -n {NAMESPACE} delete pod {NAME}',
    #                capture_output=True)
