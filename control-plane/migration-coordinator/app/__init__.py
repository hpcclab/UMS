from flask import Flask
from kubernetes.client import ApiException

from app.api.create import create_api_blueprint
from app.api.delete import delete_api_blueprint
from app.api.error import error_api_blueprint
from app.api.migrate import migrate_api_blueprint
from app.api.ping import ping_api_blueprint
from app.api.restore import restore_api_blueprint


def handle_exception(e):
    print(e, flush=True)
    return e.body, e.status


def create_app(config):
    app = Flask(__name__)

    for k, v in config.items():
        app.config[k] = v

    app.register_blueprint(error_api_blueprint)
    app.register_blueprint(ping_api_blueprint)
    app.register_blueprint(create_api_blueprint)
    app.register_blueprint(migrate_api_blueprint)
    app.register_blueprint(restore_api_blueprint)
    app.register_blueprint(delete_api_blueprint)

    from . import db
    db.init_app(app)

    app.errorhandler(ApiException)(handle_exception)

    return app
