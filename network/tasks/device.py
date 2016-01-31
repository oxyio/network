# oxy.io Network
# File: network/tasks/device_check.py
# Desc: run arbitrary checks on devices and report status back

import gevent
from pytask.helpers import run_loop

from oxyio import settings
from oxyio.tasks.base import Task
from oxyio.log import logger

from ..models.device import Device
from ..helpers import (
    parse_cpu_stats, parse_memory_stats, parse_disk_stats,
    parse_disk_io_stats, parse_network_io_stats
)


class Connect(Task):
    '''
    Connects to a server to verify first connect/ssh details change. Upon success,
    updates the device in db and starts a network/device_monitor task for it.
    '''

    NAME = 'network/device_connect'

    def __init__(self, device_id, password=None):
        self.device_id = device_id
        self.password = password

    def start(self):
        # Get the device
        device = Device.query.get(self.device_id)

        # Try connecting, or fail/end w/error
        try:
            device.connect(password=self.password)

        except device.ConnectionError as e:
            device.ssh_connected = False
            device.save()

            raise self.Error('Could not connect: {0}'.format(e))

        public_key = open(settings.SSH_KEY_PUBLIC).read()

        try:
            # Attempt to write SSH key
            device.execute_multi(
                # Setup .ssh and authorized_keys
                'mkdir -p ~/.ssh',
                'touch ~/.ssh/authorized_keys',
                # Write the pubkey if not present
                'cat ~/.ssh/authorized_keys | grep "{0}" || echo "{0}" >> ~/.ssh/authorized_key'.format(public_key),
                # Ensure permissions
                'chmod 700 ~/.ssh',
                'chmod 600 ~/.ssh/authorized_keys',
            )

        except device.CommandError as e:
            device.ssh_connected = False
            device.save()

            raise self.Error('Error adding key: {0}'.format(e))

        # Set ssh_connected
        device.ssh_connected = True
        device.save()

        # Start the device's tasks
        device.start_monitor()


class Monitor(Task):
    '''
    Monitors a devices CPU/memory/disk/IO stats & writes/published to
    Elasticsearch/Redis.
    '''

    NAME = 'network/device_monitor'

    FIXED_STATS = (
        ('cpu', 'cat /proc/stat; sleep 1; cat /proc/stat', parse_cpu_stats),
        ('memory', 'cat /proc/meminfo', parse_memory_stats),
        ('disk', 'df -PB 1000', parse_disk_stats)
    )

    TOTAL_STATS = (
        ('disk_io', 'cat /proc/diskstats', parse_disk_io_stats),
        ('network_io', 'cat /proc/net/dev', parse_network_io_stats)
    )

    def __init__(self, device_id):
        # Get our device based on the task data
        self.device = Device.query.get(device_id)

        self._previous_stats = {}

    def start(self):
        # Connect
        try:
            self.device.connect()

        except self.device.ConnectionError:
            raise self.Error('Could not connect to device')

        # Start the loop in a greenlet
        logger.debug('Starting device monitor loop on: {0}'.format(self.device))
        self.loop = gevent.spawn(run_loop, self.get_stats, self.device.stat_interval)

        self.loop.get()

    def stop(self):
        if self.loop:
            self.loop.kill()

    def get_stats(self):
        '''
        Fetches the stats defined above in parallel, processes them and queue to be
        indexed in ES.
        '''

        # Fetch the stats in parallel
        stat_requests = {
            type_: gevent.spawn(self.device.execute, command)
            for type_, command, _ in list(self.FIXED_STATS) + list(self.TOTAL_STATS)
        }

        index_stats = []

        # Fixed stats are simple, for each one just populate the values
        for type_, _, parser in self.FIXED_STATS:
            stats = parser(stat_requests[type_].get())
            new_stats = []

            for key, values in stats.iteritems():
                for detail, value in values.iteritems():
                    new_stats.append({
                        'type': type_,
                        'key': key,
                        'detail': detail,
                        'value': value
                    })

            # Emit to Redis, push to index buffer
            self.emit(type_, new_stats)
            index_stats.extend(new_stats)

        # Total stats, however, require the previous values
        for type_, _, parser in self.TOTAL_STATS:
            stats = parser(stat_requests[type_].get())

            if type_ in self._previous_stats:
                new_stats = []

                for key, values in stats.iteritems():
                    if key not in self._previous_stats[type_]:
                        continue

                    for detail, value in values.iteritems():
                        diff = value - self._previous_stats[type_][key][detail]

                        new_stats.append({
                            'type': type_,
                            'key': key,
                            'detail': detail,
                            'value': diff
                        })

                # Emit to Redis, push to index buffer
                self.emit(type_, new_stats)
                index_stats.extend(new_stats)

            self._previous_stats[type_] = stats

        # Index the stats in ES
        self.device.index_stats(index_stats)
