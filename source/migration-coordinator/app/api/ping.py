from urllib.parse import urlparse

from flask import Blueprint, request

from app.env import SSU_INTERFACE_ENABLE, SSU_INTERFACE_NODEPORT, SSU_INTERFACE_HOST
from app.lib import get_information

ping_api_blueprint = Blueprint('ping_api', __name__)


@ping_api_blueprint.route("/", methods=["GET"])
def ping_api():
    base_url = urlparse(request.base_url)
    host = base_url.hostname
    response = {
        'url': host,
        'os': get_information()
    }
    if base_url.port is not None:
        response['url'] += f':{base_url.port}'
    if SSU_INTERFACE_ENABLE is not None:
        response['ssu_host'] = SSU_INTERFACE_HOST or host
        response['ssu_port'] = SSU_INTERFACE_NODEPORT
    return response
