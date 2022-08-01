from app import create_app
from app.const import ORCHESTRATOR_TYPE_MINISHIFT, ORCHESTRATOR_TYPE_KUBERNETES
from app.env import ORCHESTRATOR_TYPE

if ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_KUBERNETES or ORCHESTRATOR_TYPE == ORCHESTRATOR_TYPE_MINISHIFT:
    from kubernetes import config
    config.load_incluster_config()

app_config = {
    'DATABASE': '/sqlite3/database.db'
}

app = create_app(app_config)


if __name__ == '__main__':
    app.run()
