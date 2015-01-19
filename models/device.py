# Oxypanel Network
# File: models/device.py
# Desc: the device & device_group models

from uuid import uuid4

from flask import request
from paramiko import RSAKey, SSHException
from pssh import (
    SSHClient,
    AuthenticationException, UnknownHostException, ConnectionErrorException
)

import config
from app import db
from models.base import BaseObject, BaseItem
from util.tasks import start_update_task, start_task, stop_task
from util.web.flashes import flash_request
from util.web.websockets import make_websocket_request

from modules.network.config import DEVICES


# Many-many linking table (device <-> device group)
device__group = db.Table('network_device__network_group',
    db.Column('device_id', db.Integer, db.ForeignKey('network_device.id'), primary_key=True),
    db.Column('device_group_id', db.Integer, db.ForeignKey('network_group.id'), primary_key=True)
)


class DeviceGroup(BaseObject, db.Model):
    NAME = 'network/group'
    TITLE = 'Group'

    devices = db.relationship('Device', secondary=device__group)


class DeviceFact(BaseItem, db.Model):
    NAME = 'network/device/fact'
    TITLE = 'Fact'

    device_id = db.Column(db.Integer, db.ForeignKey('network_device.id', ondelete='CASCADE'), nullable=False)
    device = db.relationship('Device', backref=db.backref('facts'))


# Device configs map (slug name -> display name)
DEVICE_CONFIGS = {
    key: config.NAME
    for key, config in DEVICES.iteritems()
}

class Device(BaseObject, db.Model):
    NAME = 'network/device'
    TITLE = 'Device'

    LIST_FIELDS = EDIT_FIELDS = [
        ('status', {'text': 'enables or disables stat/log collection'}),
        ('config', {'text': 'OS/Distro', 'enums': DEVICE_CONFIGS}),
        ('location', {'text': 'for display/filtering only'})
    ]
    LIST_MRELATIONS = EDIT_MRELATIONS = [
        ('network', 'group', 'groups', {})
    ]

    # Base exception
    class DeviceError(Exception): pass

    # Should we collect stats for this device & any virtual devices
    status = db.Column(db.Enum('Active', 'Suspended'), default='Active', server_default='Active', nullable=False)
    # CentOS/Debian/Ubuntu/etc
    config = db.Column(db.String(16), nullable=False)

    # For display/filters only
    location = db.Column(db.String(64))

    # Stats
    stat_interval = db.Column(db.Integer, nullable=False, default=10, server_default='10')

    # Device groups
    groups = db.relationship('DeviceGroup', secondary=device__group)

    # SSH info
    ssh_host = db.Column(db.String(128), nullable=False)
    ssh_port = db.Column(db.Integer, nullable=False)
    ssh_user = db.Column(db.String(64), nullable=False)
    ssh_sudo = db.Column(db.Boolean, nullable=False)
    # Flag to set whether we've ever connected to the above SSH details
    # the details are set instantly and a background task is run to change this flag
    # NULL = untested
    ssh_connected = db.Column(db.Boolean)

    # SSH internals
    _connected = False
    _connection = None
    _sftp = None

    # SSH errors
    class NotConnected(DeviceError): pass
    class ConnectionError(DeviceError): pass
    class CommandError(DeviceError): pass
    class ScriptError(DeviceError): pass
    class FileError(DeviceError): pass

    def is_valid(self, new=False):
        '''
        Using is_valid to verify extra details not in EDIT_FIELDS: SSH details
        called on EDIT and ADD
        '''
        # Non SSH connection affecting data
        try:
            data = {
                'stat_interval': int(request.form.get('stat_interval')),
                'ssh_sudo': (request.form.get('ssh_sudo') == 'on')
            }
            for field, value in data.iteritems():
                setattr(self, field, value)
        except ValueError:
            return False, 'Invalid stat interval'

        # Data affecting SSH connection
        try:
            ssh_data = {
                'ssh_host': request.form.get('ssh_host'),
                'ssh_user': request.form.get('ssh_user'),
                'ssh_port': int(request.form.get('ssh_port'))
            }
        except ValueError:
            return False, 'Invalid SSH port'

        # New, failed or any different SSH related fields
        if new or self.ssh_connected is not True or any(
            getattr(self, field) != ssh_data[field] for field in ssh_data.keys()
        ):
            # Reset connection status
            self.ssh_connected = None

            # Apply changes
            for field, value in ssh_data.iteritems():
                setattr(self, field, value)

            # Stop existing tasks
            self.stop_tasks()

            # Create check task (which will update connection check & re-start tasks)
            task_id = start_task(None, 'network/device_connect', {
                'device_id': self.id,
                'password': request.form.get('ssh_password')
            })

            # Create websocket request for client to watch progress
            request_key = make_websocket_request('core/task_subscribe', task_id)
            flash_request('device_ssh_connect', request_key)

        return True, None

    def _list_tasks(self):
        '''Tasks which each device should have running all the time, assuming active & ssh_connected'''
        return [
            # Monitor
            ('monitor-device-{0}'.format(self.id), 'network/device_monitor', {
                'device_id': self.id
            })
        ]

    def stop_tasks(self):
        for (task_id, _, _) in self._list_tasks():
            stop_task(task_id)
    def start_tasks(self):
        if self.status != 'Active' or not self.ssh_connected: return
        for task in self._list_tasks():
            start_task(*task)
    def start_update_tasks(self):
        if self.status != 'Active' or not self.ssh_connected: return
        for task in self._list_tasks():
            start_update_task(*task)

    # Tasks: the functions onwards are SSH/remote and used in tasks, so as to avoid long waits over HTTP
    def connect(self, password=None):
        '''Connect this device to it's bound SSH host'''
        kwargs = {
            'user': self.ssh_user,
            'port': self.ssh_port,
            'num_retries': config.SSH_RETRIES,
            'timeout': config.SSH_TIMEOUT
        }

        if password:
            kwargs['password'] = password
        else:
            kwargs['pkey'] = RSAKey.from_private_key_file(
                filename=config.SSH_KEY_PRIVATE,
                password=config.SSH_KEY_PASSWORD
            )

        try:
            self._connection = SSHClient(self.ssh_host, **kwargs)
            self._connected = True
        except (AuthenticationException, UnknownHostException, ConnectionErrorException, SSHException) as e:
            raise self.ConnectionError(str(e))

    def put(self, data, destination):
        '''Copy a file to the remote device'''
        if not self._connected:
            raise self.NotConnected()

        if not self._sftp:
            # Naughty use of private method here, but Paramiko only does filename uploads
            # see: http://stackoverflow.com/questions/5914761
            self._sftp = self._connection._make_sftp()

        file = self._sftp.open(destination, 'wb')
        file.write(data)
        file.close()

    def execute(self, command):
        '''Execute a command on the remote device'''
        if not self._connected:
            raise self.NotConnected()

        # Run the command
        channel, _, stdout, stderr = self._connection.exec_command(command)
        stdout = '\n'.join(line for line in stdout)
        stderr = '\n'.join(line for line in stderr)

        # Return depending on the exit code
        if channel.exit_status == 0:
            return stdout
        else:
            # The number of programs which don't use stderr is quite insane
            raise self.ScriptError(
                stderr if len(stderr) > 0 else stdout
            )

    def execute_script(self, script, executable='sh'):
        '''Execute a script on the remote device'''
        home = self.execute('echo $HOME')

        # Ensure our tmp directory exists
        self.execute('mkdir -p {}/.oxypanel'.format(home))

        # Write script -> tmp remote file
        filename = '{}/.oxypanel/{}'.format(home, str(uuid4()))
        self.put(script, filename)

        # Sh script
        return self.execute('{0} {1}'.format(executable, filename))
