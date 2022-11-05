import asyncio

from app.const import ORCHESTRATOR_TYPE_KUBERNETES, \
    ORCHESTRATOR_TYPE_MINISHIFT
from app.env import ORCHESTRATOR_TYPE
if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
    from app.kubernetes_client import get_pod, delete_pod, lock_pod, release_pod, update_pod_restart, exec_pod, log_pod, check_error_event
else:
    from app.marathon_client import get_pod, delete_pod, lock_pod, release_pod, update_pod_restart, exec_pod, log_pod, check_error_event


def get_information():
    with open('/etc/os-release') as f:
        return f.read()


async def gather(fn_list):
    return await asyncio.gather(*fn_list)


# def get_pod(name, namespace):
#     if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
#         return kubernetes_get_pod(**locals())
#     else:
#         return marathon_get_pod(**locals())
#
#
# def delete_pod(name, namespace):
#     if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
#         kubernetes_delete_pod(**locals())
#     else:
#         marathon_delete_pod(**locals())
#
#
# def lock_pod(name, namespace, migration_id):
#     if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
#         return kubernetes_lock_pod(**locals())
#     else:
#         return marathon_lock_pod(**locals())
#
#
# def release_pod(name, namespace):
#     if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
#         return kubernetes_release_pod(**locals())
#     else:
#         return marathon_release_pod(**locals())
#
#
# def update_pod_restart(name, namespace, start_mode):
#     if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
#         return kubernetes_update_pod_restart(**locals())
#     else:
#         return marathon_update_pod_restart(**locals())
#
#
# async def exec_pod(pod_name, namespace, command, container_name):
#     if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
#         return kubernetes_exec_pod(**locals())
#     else:
#         return marathon_exec_pod(**locals())
