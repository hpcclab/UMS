import asyncio

from app.const import ORCHESTRATOR_TYPE_KUBERNETES, \
    ORCHESTRATOR_TYPE_MINISHIFT
from app.env import ORCHESTRATOR_TYPE
if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
    from app.kubernetes_client import get_pod, delete_pod, lock_pod, release_pod, update_pod_restart, update_pod_redirect, exec_pod, log_pod, check_error_event
else:
    from app.marathon_client import get_pod, delete_pod, lock_pod, release_pod, update_pod_restart, update_pod_redirect, exec_pod, log_pod, check_error_event


def get_information():
    with open('/etc/os-release') as f:
        return f.read()


async def gather(fn_list):
    return await asyncio.gather(*fn_list)
