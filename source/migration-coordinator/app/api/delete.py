from flask import Blueprint, request, abort

from app.lib import delete_pod

delete_api_blueprint = Blueprint('delete_api', __name__)


@delete_api_blueprint.route("/delete", methods=['POST'])
def delete_api():
    body = request.get_json()
    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    namespace = body.get('namespace', 'default')

    delete_pod(name, namespace)  # todo delete src pod
    return 'deleted!'
