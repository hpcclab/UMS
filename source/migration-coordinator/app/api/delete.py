from flask import Blueprint, request, abort

from app.orchestrator import select_orchestrator

client = select_orchestrator()
delete_api_blueprint = Blueprint('delete_api', __name__)


@delete_api_blueprint.route("/delete", methods=['POST'])
def delete_api():
    body = request.get_json()
    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    namespace = body.get('namespace', 'default')

    client.delete_pod(name, namespace)  # todo delete src pod
    return 'deleted!'
