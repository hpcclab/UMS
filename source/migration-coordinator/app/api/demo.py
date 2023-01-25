import asyncio
from uuid import uuid4

from flask import Blueprint, request, abort, Response, current_app

from app.api.migrate import ping_destination, create_or_update_frontman, restore_and_release_des_pod, delete_frontman, \
    delete_des_pod
from app.const import MIGRATABLE_ANNOTATION, MIGRATION_ID_ANNOTATION, START_MODE_ANNOTATION, START_MODE_ACTIVE, \
    MIGRATION_STEP_CHECKPOINTING, MIGRATION_STEP_CONFIRMING
from app.interface import select_migration_interface
from app.orchestrator import select_orchestrator

client = select_orchestrator()
demo_api_blueprint = Blueprint('demo_api', __name__)


async def gather(fn_list):
    return await asyncio.gather(*fn_list)


@demo_api_blueprint.route("/demo", methods=['GET'])
def demo_api():
    body = request.args.to_dict()

    name = body.get('name')
    if name is None:
        abort(400, 'name is null')

    destination_url = body.get('destinationUrl')
    if destination_url is None:
        abort(400, 'destinationUrl is null')

    migration_id = uuid4().hex[:8]

    return Response(migrate(body, migration_id, current_app.app_context()), mimetype="text/event-stream")


def migrate(body, migration_id, context):
    with context:
        name = body['name']
        namespace = body.get('namespace', 'default')
        destination_url = body['destinationUrl']
        selected_interface = body.get('interface')

        src_pod = client.get_pod(name, namespace)
        if not bool(src_pod['metadata']['annotations'].get(MIGRATABLE_ANNOTATION)):
            abort(400, "pod is not migratable")
        if src_pod['metadata']['annotations'][START_MODE_ANNOTATION] != START_MODE_ACTIVE:
            abort(400, "Pod is not migratable")
        if src_pod['metadata']['annotations'].get(MIGRATION_ID_ANNOTATION):
            abort(409, "Pod is being migrated")

        src_pod = client.lock_pod(name, namespace, migration_id)
        migration_state = {
            'src_pod_exist': True,
            'des_pod_exist': False,
            'frontmant_exist': False
        }
        interface = None

        try:
            des_info = ping_destination(destination_url)
            interface = select_migration_interface(src_pod, des_info, selected_interface)

            des_pod_template = interface.generate_des_pod_template(src_pod)
            des_pod_info = interface.create_des_pod(des_pod_template, des_info, migration_state)
            create_or_update_frontman(src_pod, migration_state, create_keeper=body.get('keep'))
            yield 'data: RESERVED\n\n'

            checkpoint_id = uuid4().hex[:8]
            client.update_migration_step(name, namespace, MIGRATION_STEP_CHECKPOINTING)
            src_pod = interface.checkpoint_and_transfer(src_pod, des_pod_info, checkpoint_id, migration_state)
            yield 'data: CHECKPOINTED\n\n'

            client.update_migration_step(name, namespace, MIGRATION_STEP_CONFIRMING)
            restore_and_release_des_pod(src_pod, destination_url, migration_id, checkpoint_id, interface, des_pod_template,
                                        migration_state)
            yield 'data: RESTORED\n\n'
        except Exception as e:
            if interface:
                interface.recover(src_pod, destination_url, migration_state, delete_frontman, delete_des_pod)
            client.release_pod(name, namespace)
            raise e

        create_or_update_frontman(src_pod, migration_state, redirect_uri=body.get('redirect'))
        interface.delete_src_pod(src_pod)
        yield 'data: DONE\n\n'
