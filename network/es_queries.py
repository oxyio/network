{
    # Filter the device/stat_type
    'query': {
        'bool': {
            'must': [
                {
                    'match': {
                        'device_id': 1
                    }
                },
                {
                    'match': {
                        'stat_type': 'network_io'
                    }
                }
            ]
        }
    },
    'aggregations': {
        # Break down resulting documents per minute
        'minutes': {
            'date_histogram': {
                'field': 'datetime',
                'interval': 'minute'
            },
            'aggregations': {
                'stats': {
                    'nested': {
                        'path': 'stats'
                    },
                    'aggregations': {
                        'eth1_filter': {
                            'filter': {
                                'term': {
                                    'stats.stat_key': 'eth0'
                                }
                            },
                            'aggregations': {
                                'total_transmit_bytes': {
                                    'sum': {
                                        'field': 'stats.transmit_bytes'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    'size': 1
}
