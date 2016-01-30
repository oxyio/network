# oxy.io Network
# File: helpers.py
# Desc: general helpers for the network module (parsing of /proc, etc)

from __future__ import division

import re


def parse_cpu_stats(stats):
    '''Parses 2x /proc/stat output to calculate CPU %.'''

    columns = ['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'soft_irq']
    cpus = {}
    cpu_percentages = {}

    for line in stats:
        bits = line.split()
        key, details = bits[0], [int(bit) for bit in bits[1:8]]

        if key.startswith('cpu'):
            if key in cpus:
                # Calculate usage (second cat)
                diffs = [details[i] - cpus[key][i] for i, _ in enumerate(columns)]
                total = sum(diffs)

                percentages = {
                    column: round(diffs[i] / total * 100, 3)
                    for i, column in enumerate(columns)
                    if column != 'idle'
                }
                cpu_percentages[key] = percentages

            else:
                # Set details (first cat)
                cpus[key] = details

    return cpu_percentages


def parse_memory_stats(stats):
    '''Parses /proc/meminfo output.'''

    memory_details = {}
    swap_details = {}

    key_map = {
        'MemTotal:': (memory_details, 'total'),
        'MemFree:': (memory_details, 'free'),
        'Buffers:': (memory_details, 'buffers'),
        'Cached:': (memory_details, 'cached'),
        'SwapTotal:': (swap_details, 'total'),
        'SwapFree:': (swap_details, 'free'),
        'SwapCached:': (swap_details, 'cached')
    }

    for line in stats:
        bits = line.split()
        key, value = bits[:2]

        if key in key_map:
            key = key.strip('')
            type, stat = key_map[key]
            type[stat] = int(value)

    return {
        'memory': memory_details,
        'swap': swap_details
    }


def parse_disk_stats(stats):
    '''Parses df output.'''

    columns = ['blocks', 'used', 'available']
    disks = {}

    for line in stats:
        bits = line.split()
        type, key, details = bits[0], bits[5], bits[1:4]

        if type in ['Filesystem', 'none']:
            continue

        disk = {
            column: int(details[i])
            for i, column in enumerate(columns)
        }

        disks[key] = disk

    return disks


def parse_disk_io_stats(stats):
    '''Parses /proc/diskstats output.'''

    columns = [
        'reads', 'read_merges', 'read_sectors', 'read_time',
        'writes', 'write_merges', 'write_sectors', 'write_time',
        'current_ios', 'io_time'
    ]

    disk_stats = {}

    for line in stats:
        bits = line.split()
        key, details = bits[2], [int(bit) for bit in bits[3:]]

        if key.startswith('loop') or key.startswith('ram'):
            continue

        stats = {
            column: details[i - 1]
            for i, column in enumerate(columns)
        }

        disk_stats[key] = stats

    return disk_stats


def parse_network_io_stats(stats):
    '''Parses /proc/net/dev output.'''

    columns = ['bytes', 'packets', 'errors', 'drop']
    match_device = r'^\s*([a-z0-9A-Z]+):\s+'

    device_stats = {}

    for line in stats:
        matches = re.match(match_device, line)
        if matches:
            key, bits = matches.group(1), line.split()
            details_receive = [int(bit) for bit in bits[1:5]]
            details_transmit = [int(bit) for bit in bits[9:13]]

            stats = {
                'receive_{0}'.format(column): details_receive[i]
                for i, column in enumerate(columns)
            }

            stats.update({
                'transmit_{0}'.format(column): details_transmit[i]
                for i, column in enumerate(columns)
            })

            device_stats[key] = stats

    return device_stats
