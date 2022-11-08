from flask import Blueprint, jsonify

from app.const import MIGRATABLE_ANNOTATION, START_MODE_ANNOTATION, START_MODE_ACTIVE, MIGRATION_ID_ANNOTATION
from app.kubernetes_client import list_pod

list_api_blueprint = Blueprint('list_api', __name__)


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
                     'migratable': pod.metadata.annotations.get(MIGRATABLE_ANNOTATION, str(False)),
                     'status': determine_status(pod)} for pod in pods])


def determine_status(pod):
    if pod.metadata.annotations.get(START_MODE_ANNOTATION, START_MODE_ACTIVE) == START_MODE_ACTIVE \
            and pod.metadata.annotations.get(MIGRATION_ID_ANNOTATION) is None:
        return pod.status.phase
    return 'Migrating'
