import kopf
import logging

from share.env import HOST_NAME


logging.getLogger('aiohttp.access').setLevel(logging.ERROR)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.admission.managed = 'auto.kopf.dev'
    settings.admission.server = kopf.WebhookServer(port=30000, host=HOST_NAME)
    settings.peering.priority = 0
    settings.peering.name = "migration-coordinator"
    settings.peering.mandatory = True
    settings.peering.stealth = True
