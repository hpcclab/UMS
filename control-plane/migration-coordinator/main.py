from kubernetes import config
from app import create_app

config.load_incluster_config()

app_config = {
    'DATABASE': '/sqlite3/database.db'
}

app = create_app(app_config)


if __name__ == '__main__':
    app.run()
