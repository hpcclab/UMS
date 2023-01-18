from flask import Blueprint, request, abort, Response

import app.interface.dind as dind
import app.interface.ff as ff
import app.interface.pind as pind
import app.interface.ssu as ssu
from app.const import INTERFACE_DIND, INTERFACE_PIND, INTERFACE_FF, INTERFACE_SSU

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

    interface.restore(body)
    return Response(status = 200)


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
