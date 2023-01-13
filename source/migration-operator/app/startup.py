import kopf
import logging

from share.env import HOST_NAME


logging.getLogger('aiohttp.access').setLevel(logging.ERROR)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.peering.priority = 100
    settings.peering.name = "migration-coordinator"
    settings.peering.mandatory = True
    settings.peering.stealth = True
