import asyncio
import json
import os

import kopf
import yaml

from share.env import env


def inject_service(template_file, name, selectors, node_port):
    with open(os.path.join(os.path.dirname(__file__), template_file), 'rt') as f:
        service_template = yaml.safe_load(f.read().format(**env))
    kopf.label(service_template)
    kopf.append_owner_reference(service_template)
    kopf.harmonize_naming(service_template, name)
    kopf.adjust_namespace(service_template, forced=True)
    service_template['spec']['selector'] = selectors
    if node_port is not None:
        service_template['spec']['ports'][0]['nodePort'] = int(node_port)
    return service_template


def send_event(body, reason, message):
    kopf.event(body, type='migration', reason=reason, message=json.dumps(message))


def send_error_event(body, name, error):
    kopf.event(body, type='migration', reason='error', message=json.dumps({
        'pod': name,
        'error': error
    }))


async def gather(fn_list):
    return await asyncio.gather(*fn_list)
