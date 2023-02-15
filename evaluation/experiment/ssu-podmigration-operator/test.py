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
            with open('./ssu.json', 'w') as f:
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
        response = requests.post(f'http://{SRC}/migrate', json={
            'name': NAME,
            'namespace': NAMESPACE,
            'destinationUrl': DES
        })
        if response.status_code == 200:
            result = response.json()
            print(result)
            results.append(result)
            subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" -n {NAMESPACE} delete pod {result["des_pod"]["metadata"]["name"]}',
                           capture_output=True)
            while True:
                if get_pod(DES_CONFIG, result['des_pod']['metadata']['name'], NAMESPACE) != b'':
                    break
                sleep(1)
            i += 1
        else:
            print(f'error: [{response.status_code}] {response.text}')
            break


if __name__ == '__main__':
    test(5)
