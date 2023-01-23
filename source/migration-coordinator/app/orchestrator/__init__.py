from flask import abort

import app.orchestrator.kubernetes_client as kubernetes_client
import app.orchestrator.marathon_client as marathon_client
from app.const import ORCHESTRATOR_TYPE_KUBERNETES, ORCHESTRATOR_TYPE_MINISHIFT, ORCHESTRATOR_TYPE_MESOS
from app.env import ORCHESTRATOR_TYPE


def select_orchestrator():
    if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
        return kubernetes_client
    if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MESOS:
        return marathon_client
    abort(404, f'Orchestrator {ORCHESTRATOR_TYPE} not found')
