from flask import abort
from werkzeug.exceptions import HTTPException

import app.interface.dind as dind
import app.interface.ff as ff
import app.interface.pind as pind
import app.interface.ssu as ssu
from app.const import INTERFACE_DIND, INTERFACE_PIND, INTERFACE_FF, INTERFACE_SSU, INTERFACE_ANNOTATION


def select_interface(selected_interface):
    if selected_interface == INTERFACE_DIND:
        return dind
    if selected_interface == INTERFACE_PIND:
        return pind
    if selected_interface == INTERFACE_FF:
        return ff
    if selected_interface == INTERFACE_SSU:
        return ssu
    abort(404, f'Interface {selected_interface} not found')


def select_migration_interface(src_pod, des_info, selected_interface):
    if selected_interface is not None:
        return select_interface(selected_interface)
    if ssu.is_compatible(src_pod, des_info):
        return ssu
    try:
        interface = select_interface(src_pod['metadata']['annotations'].get(INTERFACE_ANNOTATION))
        if interface.is_compatible(src_pod, des_info):
            return interface
    except HTTPException:
        pass
    if ff.is_compatible(src_pod, des_info):
        return ff
    if pind.is_compatible(src_pod, des_info):
        return pind
    if dind.is_compatible(src_pod, des_info):
        return dind
    abort(409, 'Cannot find the compatible interface')
