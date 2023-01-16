from app import create_app
from app.const import ORCHESTRATOR_TYPE_MINISHIFT, ORCHESTRATOR_TYPE_KUBERNETES
from app.env import ORCHESTRATOR_TYPE

if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
    from kubernetes import config
    config.load_incluster_config()

app = create_app()


if __name__ == '__main__':
    app.run()
