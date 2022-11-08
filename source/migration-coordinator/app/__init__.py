from flask import Flask
from kubernetes.client import ApiException
from requests.exceptions import RequestException
from werkzeug.exceptions import HTTPException
from docker.errors import DockerException
from app.api.create import create_api_blueprint
from app.api.delete import delete_api_blueprint
from app.api.demo import demo_api_blueprint
from app.api.error import error_api_blueprint
from app.api.list import list_api_blueprint
from app.api.migrate import migrate_api_blueprint
from app.api.ping import ping_api_blueprint
from app.api.restore import restore_api_blueprint


def handle_api_exception(e):
    print(e, flush=True)
    print(1, flush=True)
    return e.body, e.status


def handle_abort_exception(e):
    print(e, flush=True)
    print(2, flush=True)
    return e.description, e.code


def handle_exception(e):
    print(e, flush=True)
    print(3, flush=True)
    return str(e), 500


def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    header['Access-Control-Allow-Headers'] = '*'
    # Other headers can be added here if needed
    return response


def create_app(config):
    app = Flask(__name__)

    for k, v in config.items():
        app.config[k] = v

    app.register_blueprint(error_api_blueprint)
    app.register_blueprint(ping_api_blueprint)
    app.register_blueprint(list_api_blueprint)
    app.register_blueprint(create_api_blueprint)
    app.register_blueprint(migrate_api_blueprint)
    app.register_blueprint(demo_api_blueprint)
    app.register_blueprint(restore_api_blueprint)
    app.register_blueprint(delete_api_blueprint)

    from . import db
    db.init_app(app)

    app.errorhandler(ApiException)(handle_api_exception)
    app.errorhandler(HTTPException)(handle_abort_exception)
    app.errorhandler(RequestException)(handle_exception)
    app.errorhandler(DockerException)(handle_exception)

    app.after_request(after_request)

    return app
