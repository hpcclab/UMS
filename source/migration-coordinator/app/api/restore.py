from flask import Blueprint, request, abort, Response

from app.interface import select_interface

restore_api_blueprint = Blueprint('restore_api', __name__)


@restore_api_blueprint.route("/restore", methods=['POST'])
def restore_api():
    body = request.get_json()

    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    migration_id = body.get('migrationId')
    if migration_id is None:
        abort(400, 'migrationId is null')

    checkpoint_id = body.get('checkpointId')
    if checkpoint_id is None:
        abort(400, 'checkpointId is null')

    selected_interface = body.get('interface')
    if selected_interface is None:
        abort(400, 'interface is null')

    interface = select_interface(selected_interface)

    return interface.restore(body)
