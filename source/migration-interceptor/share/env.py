from os import getenv

from share.const import ORCHESTRATOR_TYPE_KUBERNETES

ORCHESTRATOR_TYPE = getenv('ORCHESTRATOR_TYPE', ORCHESTRATOR_TYPE_KUBERNETES)
HOST_NAME = getenv('HOST_NAME', None)

DIND_IMAGE = getenv('DIND_IMAGE', 'migration-dind')
PIND_IMAGE = getenv('PIND_IMAGE', 'migration-pind')
AMBASSADOR_IMAGE = getenv('AMBASSADOR_IMAGE', 'migration-ambassador')
FRONTMAN_IMAGE = getenv('FRONTMAN_IMAGE', 'frontman')
IMAGE_PULL_POLICY = getenv('IMAGE_PULL_POLICY', 'IfNotPresent')

env = {
    'DIND_IMAGE': DIND_IMAGE,
    'PIND_IMAGE': PIND_IMAGE,
    'AMBASSADOR_IMAGE': AMBASSADOR_IMAGE,
    'FRONTMAN_IMAGE': FRONTMAN_IMAGE,
    'IMAGE_PULL_POLICY': IMAGE_PULL_POLICY
}