from app import create_app
from app.orchestrator import select_orchestrator

client = select_orchestrator()
client.load_incluster_config()

app = create_app()

if __name__ == '__main__':
    app.run()
