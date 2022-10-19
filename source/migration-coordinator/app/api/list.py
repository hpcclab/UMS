from flask import Blueprint, jsonify

from app.kubernetes_client import list_pod

list_api_blueprint = Blueprint('list_api', __name__)


@list_api_blueprint.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    # Other headers can be added here if needed
    return response


@list_api_blueprint.route("/list", methods=['GET'])
def list_api():
    pods = list_pod().items

    # connection = get_db()
    #
    # try:
    #     connection.execute("INSERT INTO migration (id) VALUES (?)", (migration_id,))
    #     connection.commit()
    # finally:
    #     connection.execute("DELETE FROM migration WHERE id = ?", (migration_id,))
    #     connection.execute("DELETE FROM message WHERE migration_id = ?", (migration_id,))
    #     connection.commit()

    return jsonify([{'name': pod.metadata.name, 'namespace': pod.metadata.namespace,
                     'migratable': True, 'status': 'todo'} for pod in pods])
