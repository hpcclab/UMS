import asyncio
import json
import os

import kopf
import yaml

from share.env import env


def inject_service(name, selectors):
    with open(os.path.join(os.path.dirname(__file__), '../injector/template/service.yml'), 'rt') as f:
        service_template = yaml.safe_load(f.read().format(**env))
    kopf.label(service_template)
    kopf.append_owner_reference(service_template)
    kopf.harmonize_naming(service_template, name)
    kopf.adjust_namespace(service_template, forced=True)
    service_template['spec']['selector'] = selectors
    return service_template


def send_event(body, reason, message):
    kopf.event(body, type='migration', reason=reason, message=json.dumps(message))


def send_error_event(body, name, error):
    kopf.event(body, type='migration', reason='error', message=json.dumps({
        'pod': name,
        'error': error
    }))


def code_should_not_reach_here():
    raise kopf.PermanentError('Code should not reach here')


async def gather(fn_list):
    return await asyncio.gather(*fn_list)
