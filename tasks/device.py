# Oxypanel Network
# File: tasks/device_check.py
# Desc: run arbitrary checks on devices and report status back

from datetime import datetime

import gevent
from pytask import run_loop

from oxyio import settings
from oxyio.app import es_client
from oxyio.tasks.base import Task
from oxyio.util.log import logger

from ..models.device import Device


class Connect(Task):
    '''
    Connects to a server to verify first connect/ssh details change. Upon success,
    updates the device in db and starts a network/device_monitor task for it.
    '''

    NAME = 'network/device_connect'

    def start(self):
        # Get the device
        device = Device.query.get(self.task_data['device_id'])

        # Try connecting, or fail/end w/error
        try:
            device.connect(password=self.task_data['password'])
        except device.ConnectionError as e:
            device.ssh_connected = False
            device.save()
            return False, 'Could not connect: {}'.format(e)

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
            return False, 'Error adding key: {}'.format(e)

        # Set ssh_connected
        device.ssh_connected = True
        device.save()

        # Start the device's tasks
        device.start_tasks()


class Monitor(Task):
    '''
    Monitors a devices CPU/memory/disk/IO stats & writes/published to
    Elasticsearch/Redis.
    '''

    NAME = 'network/device_monitor'

    device = None

    def start(self):
        # Get the device
        self.device = Device.query.get(self.task_data['device_id'])

        # Connect
        try:
            self.device.connect()
        except self.device.ConnectionError:
            return False, 'Could not connect to device'

        # Start the loop in a greenlet
        logger.debug('Starting device monitor loop on: {}'.format(self.device))
        self.loop = gevent.spawn(run_loop, self.get_stats, self.device.stat_interval)

        self.loop.join()
        return False, 'Unexpected end of get_stats loop'

    def stop(self):
        if self.loop:
            self.loop.kill()

    def get_stats(self):
        # Fetch stats in parallel (most sleep for 1s)
        stat_requests = [
            ('cpu', gevent.spawn(self.device.get_cpu_stats)),
            ('memory', gevent.spawn(self.device.get_memory_stats)),
            ('disk', gevent.spawn(self.device.get_disk_stats)),
            ('disk_io', gevent.spawn(self.device.get_disk_io_stats)),
            ('network_io', gevent.spawn(self.device.get_network_io_stats))
        ]

        # Wait for the results
        [greenlet.join() for (_, greenlet) in stat_requests]

        date = datetime.utcnow()
        for (stat_type, greenlet) in stat_requests:
            stats = greenlet.get()

            # Index in ES
            es_client.create(
                index=settings.ES_DATA_INDEX,
                doc_type='device_stat_{}'.format(stat_type),
                body={
                    'device_id': self.device.id,
                    'datetime': date,
                    'stats': stats
                }
            )

            # Emit to Redis pub/sub (event_type, data)
            self.emit(stat_type, stats)
