from flask import Blueprint, request

from app.kubernetes_client import create_pod, wait_pod_ready

create_api_blueprint = Blueprint('create_api', __name__)


@create_api_blueprint.route("/create", methods=['POST'])
def create_api():
    body = request.get_json()
    new_pod = create_new_pod(body)
    # return wait_pod_ready(new_pod)
    return new_pod['metadata']['annotations']


def create_new_pod(body):
    namespace = body.get('metadata', {}).get('namespace', 'default')
    return create_pod(namespace, body)
