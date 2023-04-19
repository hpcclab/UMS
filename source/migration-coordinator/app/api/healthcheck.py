from flask import Blueprint, Response

healthcheck_api_blueprint = Blueprint('healthcheck_api', __name__)


@healthcheck_api_blueprint.route("/healthcheck", methods=["GET"])
def healthcheck_api():
    return Response(status = 200)
