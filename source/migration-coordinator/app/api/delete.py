from flask import Blueprint, request, abort

from app.lib import delete_pod

delete_api_blueprint = Blueprint('delete_api', __name__)


@delete_api_blueprint.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    # Other headers can be added here if needed
    return response


@delete_api_blueprint.route("/delete", methods=['POST'])
def delete_api():
    body = request.get_json()
    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    namespace = body.get('namespace', 'default')

    delete_pod(name, namespace)
    return 'deleted!'
