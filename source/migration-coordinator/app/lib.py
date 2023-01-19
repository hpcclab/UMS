import asyncio

from flask import abort

import app.interface.dind as dind
import app.interface.ff as ff
import app.interface.pind as pind
import app.interface.ssu as ssu
from app.const import ORCHESTRATOR_TYPE_KUBERNETES, \
    ORCHESTRATOR_TYPE_MINISHIFT, INTERFACE_DIND, INTERFACE_PIND, INTERFACE_FF, INTERFACE_SSU
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


def select_interface(selected_interface):
    if selected_interface == INTERFACE_DIND:
        return dind
    if selected_interface == INTERFACE_PIND:
        return pind
    if selected_interface == INTERFACE_FF:
        return ff
    if selected_interface == INTERFACE_SSU:
        return ssu
    abort(404, f'Interface {selected_interface} not found')