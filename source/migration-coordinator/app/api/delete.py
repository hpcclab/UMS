from flask import Blueprint, request, abort

from app.interface import select_interface
from app.orchestrator import select_orchestrator

client = select_orchestrator()
delete_api_blueprint = Blueprint('delete_api', __name__)


@delete_api_blueprint.route("/delete", methods=['POST'])
def delete_api():
    body = request.get_json()
    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    selected_interface = body.get('interface')
    if selected_interface is None:
        abort(400, 'interface is null')

    interface = select_interface(selected_interface)

    namespace = body.get('namespace', 'default')

    interface.do_delete_pod(name, namespace)
    return 'deleted!'
