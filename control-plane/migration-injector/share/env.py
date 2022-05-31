from os import getenv

EXEC_RUNTIME = getenv('EXEC_RUNTIME', 'migration-dind')
EXEC_ENGINE = getenv('EXEC_ENGINE', 'migration-engine')
EXEC_INTERFACE = getenv('EXEC_INTERFACE', 'migration-interface')
EXEC_MONITOR = getenv('EXEC_MONITOR', 'migration-monitor')
EVAL_REDIRECTOR = getenv('EVAL_REDIRECTOR', 'migration-redirector')
IMAGE_PULL_POLICY = getenv('IMAGE_PULL_POLICY', 'IfNotPresent')

env = {
    'EXEC_RUNTIME': EXEC_RUNTIME,
    'EXEC_ENGINE': EXEC_ENGINE,
    'EXEC_INTERFACE': EXEC_INTERFACE,
    'EXEC_MONITOR': EXEC_MONITOR,
    'EVAL_REDIRECTOR': EVAL_REDIRECTOR,
    'IMAGE_PULL_POLICY': IMAGE_PULL_POLICY
}
