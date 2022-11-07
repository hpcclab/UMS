from flask import Blueprint, abort, request

from app.db import get_db

error_api_blueprint = Blueprint('error_api', __name__)


@error_api_blueprint.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    # Other headers can be added here if needed
    return response


@error_api_blueprint.route("/error", methods=['POST'])
def error_api():
    body = request.get_json()
    if not migration_id_exist(body['migration_id']):
        abort(404)
    insert_message(body['message'], body['migration_id'])


def migration_id_exist(migration_id):
    cur = get_db().execute("SELECT * FROM migration WHERE id = ?", (migration_id,))
    rv = cur.fetchall()
    if not rv:
        return False
    return True


def insert_message(message, migration_id):
    connection = get_db()
    cur = connection.cursor()
    cur.execute("INSERT INTO message (message, migration_id) VALUES (?,?)", (message, migration_id))
    connection.commit()
