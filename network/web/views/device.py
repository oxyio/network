# oxy.io Network
# File: network/web/views/device.py
# Desc: device views

from flask import jsonify, request

from oxyio.stats import get_object_stats, get_object_stat_keys
from oxyio.web.request import get_stat_request_kwargs


def api_get_device_stats(device):
    return jsonify(stats=get_object_stats(
        device,
        **get_stat_request_kwargs()
    ))


def api_get_device_stat_keys(device):
    return jsonify(keys=get_object_stat_keys(
        device,
        type_=request.args.get('type')
    ))
