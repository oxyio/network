from datetime import datetime, timedelta

from flask import request, jsonify
from elasticquery import Query, Aggregate

from ...mappings import MAPPINGS

# Reverse mapping's doc_type -> mapping class
TYPE_TO_MAPPING = {
    stat.__doc_type__: stat
    for stat in MAPPINGS
}


def api_get_device_stats(device):
    stat_key = 'device_stat_{}'.format(request.args.get('stat_type'))
    if stat_key not in TYPE_TO_MAPPING:
        return jsonify(error='Invalid stat type')

    keys = request.args.get('keys', 'true') == 'true'
    sum_keys = request.args.get('sum_keys', 'true') == 'true'

    mapping = TYPE_TO_MAPPING[stat_key]
    mapping_keys = mapping.attributes()['stats']['properties'].keys()

    # Query by our device_id
    q = mapping.query().must(
        Query.term(device_id=device.id)
    )
    # Aggregate data only please!
    q.set('size', 0)

    # Set daterange
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    datetime_from = request.args.get('datetime_from', hour_ago)
    datetime_to = request.args.get('datetime_to', now)
    q.must(Query.range(
        'datetime',
        gte=datetime_from,
        lte=datetime_to
    ))

    # Build sum aggregates for each of the stats
    stat_aggs = [
        mapping.__aggregate__(name, name)
        for name in mapping_keys
        if name != 'key'
    ]
    # Nest the sum aggregates inside stats
    nested_aggregate = Aggregate.nested('stats', 'stats')
    if sum_keys:
        nested_aggregate.sub(*stat_aggs)
    # & nest again inside key terms to get key counts
    if keys:
        nested_aggregate.sub(Aggregate.terms('keys', 'key').sub(*stat_aggs))

    # Stick the nested aggregate inside a date histogram
    aggregate = Aggregate.date_histogram(
        'stats_dateogram',
        'datetime',
        interval=request.args.get('interval', 'minute')
    )
    aggregate.sub(nested_aggregate)

    # Finally, add to the query & get results
    q.aggregate(aggregate)
    results = q.get()

    # Build stat output by making a list of days containing aggregate info under sum or keys
    stats = []
    dateogram_buckets = results['aggregations']['stats_dateogram']['buckets']
    for bucket in dateogram_buckets:
        stat = {
            'date': bucket['key_as_string']
        }

        if sum_keys:
            stat['sum'] = {
                name: bucket['stats'][name]['value']
                for name in mapping_keys
                if name != 'key'
            }

        if keys:
            stat['keys'] = {
                b['key']: {
                    name: b[name]['value']
                    for name in mapping_keys
                    if name != 'key'
                }
                for b in bucket['stats']['keys']['buckets']
            }

        stats.append(stat)

    stats.reverse()
    return jsonify(stats=stats)
