import kopf

from share.env import HOST_NAME


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.admission.managed = 'auto.kopf.dev'
    settings.admission.server = kopf.WebhookServer(port=30000, host=HOST_NAME)
