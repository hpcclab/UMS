from os import getenv

INTERFACE_HOST = getenv('INTERFACE_HOST', None)

EXEC_RUNTIME = getenv('EXEC_RUNTIME', 'migration-dind')
EXEC_MONITOR = getenv('EXEC_MONITOR', 'migration-monitor')
EVAL_REDIRECTOR = getenv('EVAL_REDIRECTOR', 'migration-redirector')
EVAL_KEEPER = getenv('EVAL_KEEPER', 'migration-keeper')
IMAGE_PULL_POLICY = getenv('IMAGE_PULL_POLICY', 'IfNotPresent')

env = {
    'INTERFACE_HOST': INTERFACE_HOST,
    'EXEC_RUNTIME': EXEC_RUNTIME,
    'EXEC_MONITOR': EXEC_MONITOR,
    'EVAL_REDIRECTOR': EVAL_REDIRECTOR,
    'EVAL_KEEPER': EVAL_KEEPER,
    'IMAGE_PULL_POLICY': IMAGE_PULL_POLICY
}
