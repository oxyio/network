# Oxypanel Network
# File: tasks/device_check.py
# Desc: run arbitrary checks on devices and report status back

import config
from models.task import Task

from ..models.device import Device


class Connect(Task):
    '''
    Connects to a server to verify first connect/ssh details change
    upon success, updates the device in db and starts a network/device_monitor task for it (if status == Active)
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

        # Attempt to write SSH key, or fail/end w/error
        ssh_public_key = open(config.SSH_KEY_PUBLIC).read()
        try:
            device.execute_script('''
                mkdir -p ~/.ssh/
                touch ~/.ssh/authorized_keys
                cat ~/.ssh/authorized_keys | grep "{0}" || echo "{0}" > ~/.ssh/authorized_key
            '''.format(ssh_public_key))
        except (device.CommandError, device.ScriptError) as e:
            device.ssh_connected = False
            device.save()
            return False, 'Error adding key: {}'.format(e)

        # Set ssh_connected
        device.ssh_connected = True
        device.save()

        # Start the device's tasks
        device.start_tasks()


class Monitor(Task):
    '''Monitors a devices CPU, memory, network and disk loads & writes to Elasticsearch'''
    NAME = 'network/device_monitor'

    def start(self):
        # Get the device
        device = Device.query.get(self.task_data['device_id'])
        # Connect
        device.connect()

        # Lets monitor!
        return False, 'oh, balls'