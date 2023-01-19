from flask import Blueprint, request, abort

from app.lib import select_interface

create_api_blueprint = Blueprint('create_api', __name__)


@create_api_blueprint.route("/create", methods=['POST'])
def create_api():
    body = request.get_json()

    selected_interface = body.get('interface')
    if selected_interface is None:
        abort(400, 'interface is null')

    template = body.get('template')
    if template is None:
        abort(400, 'template is null')

    interface = select_interface(selected_interface)

    return interface.create_new_pod(template)