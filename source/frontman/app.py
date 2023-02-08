from flask import Flask, redirect, Response
from dotenv import dotenv_values

app = Flask(__name__)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    config = dotenv_values('/etc/podinfo/annotations')
    if config.get('redirect') is not None:
        return redirect(config['redirect'], 301)
    return Response(status=425) # todo 503 + Retry-After 0 header


if __name__ == '__main__':
    app.run()
