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
    while True:
        if i >= n:
            break
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
            print(response.json())
            i += 1
        else:
            print(f'error: [{response.status_code}] {response.text}')
            break
        # subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" -n {NAMESPACE} delete pod {NAME}',
        #                capture_output=True)


if __name__ == '__main__':
    # subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" apply -f {MEMHOG_CONFIG}',
    #                capture_output=True)
    test(1)
    # subprocess.run(f'kubectl --kubeconfig="{DES_CONFIG}" -n {NAMESPACE} delete pod {NAME}',
    #                capture_output=True)
