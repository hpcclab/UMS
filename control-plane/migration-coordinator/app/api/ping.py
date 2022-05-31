from flask import Blueprint

from app.lib import get_information

ping_api_blueprint = Blueprint('ping_api', __name__)


@ping_api_blueprint.route("/", methods=["GET"])
def ping_api():
    return get_information()
