# oxy.io Network
# File: network/web/views/group.py
# Desc: group views

from flask import jsonify
from elasticquery import Query

from oxyio.stats import get_stats
from oxyio.web.request import get_stat_request_kwargs


def api_get_group_stats(group):
    device_ids = [device.id for device in group.devices]

    queries = [
        Query.term('object_module', 'network'),
        Query.term('object_type', 'device'),
        Query.terms('object_id', device_ids)
    ]

    stats = get_stats(
        queries=queries,
        **get_stat_request_kwargs()
    )

    return jsonify(stats=stats)
