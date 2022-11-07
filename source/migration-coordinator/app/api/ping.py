from flask import Blueprint

from app.lib import get_information

ping_api_blueprint = Blueprint('ping_api', __name__)


@ping_api_blueprint.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    # Other headers can be added here if needed
    return response


@ping_api_blueprint.route("/", methods=["GET"])
def ping_api():
    return get_information()
