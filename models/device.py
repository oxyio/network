# oxy.io Network
# File: models/device.py
# Desc: the device & device_group models

from socket import error as socket_error, gaierror

from flask import request
from paramiko import (
    SSHClient, RSAKey, MissingHostKeyPolicy, SSHException, AuthenticationException
)

from oxyio import settings
from oxyio.app import db
from oxyio.models.base import Object, Item
from oxyio.util.log import logger
from oxyio.util.tasks import start_update_task, start_task, stop_task
from oxyio.web.util.flashes import flash_request
from oxyio.web.util.websockets import make_websocket_request

from ..mappings import MAPPINGS
from ..web.views.device import api_get_device_stats
from ..helpers import (
    parse_cpu_stats, parse_memory_stats, parse_disk_stats,
    parse_disk_io_stats, parse_network_io_stats
)


# Many-many linking table (device <-> device group)
device__group = db.Table('network_device__network_group',
    db.Column(
        'device_id', db.Integer, db.ForeignKey('network_device.id'),
        primary_key=True
    ),
    db.Column(
        'device_group_id', db.Integer, db.ForeignKey('network_group.id'),
        primary_key=True
    )
)


class DeviceGroup(Object, db.Model):
    NAME = 'network/group'
    TITLE = 'Group'

    LIST_MRELATIONS = (
        ('devices', 'network/device', {}),
        ('ipblocks', 'network/ipblock', {'title': 'IP Blocks'})
    )

    devices = db.relationship('Device', secondary=device__group)


class DeviceFact(Item, db.Model):
    NAME = 'network/device/fact'
    TITLE = 'Fact'

    device_id = db.Column(db.Integer,
        db.ForeignKey('network_device.id', ondelete='CASCADE'),
        nullable=False
    )
    device = db.relationship('Device', backref=db.backref('facts'))


class Device(Object, db.Model):
    NAME = 'network/device'
    TITLE = 'Device'

    ES_DOCUMENTS = MAPPINGS

    # No listing of status (just filter/edit)
    LIST_FIELDS = (
        ('location', {}),
        ('ips', {'title': 'IPs', 'join': True}),
    )

    EDIT_FIELDS = (
        ('status', {'text': 'enables or disables stat/log collection'}),
        ('location', {'text': 'for display/filtering only'}),
    )

    LIST_MRELATIONS = (
        ('ipblocks', 'network/ipblock', {'title': 'IP Blocks'}),
        ('groups', 'network/group', {})
    )

    EDIT_MRELATIONS = (
        ('groups', 'network/group', {}),
    )

    ROUTES = (
        ('/stats', ['GET'], api_get_device_stats, 'view'),
    )

    MONITOR_TASK_PREFIX = 'monitor-device-'

    # Should we collect stats for this device & any virtual devices
    status = db.Column(
        db.Enum('Active', 'Suspended'),
        default='Active', server_default='Active', nullable=False
    )

    # For display/filters only
    location = db.Column(db.String(64))

    # Stats
    stat_interval = db.Column(db.Integer,
        nullable=False, default=10, server_default='10'
    )

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

    # Base exception
    class DeviceError(Exception):
        pass

    # SSH errors
    class NotConnected(DeviceError):
        pass

    class ConnectionError(DeviceError):
        pass

    class CommandError(DeviceError):
        pass

    class FileError(DeviceError):
        pass

    class FunctionError(DeviceError):
        pass

    def pre_view(self):
        if self.status == 'Active':
            # Create websocket request for client to receive monitor updates
            request_key = make_websocket_request(
                'core/task_subscribe', '{0}{1}'.format(self.MONITOR_TASK_PREFIX, self.id)
            )
            flash_request('device_monitor', request_key)

            # Create websocket request for the processes tab

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
            raise self.ValidationError('Invalid stat interval')

        # Data affecting SSH connection
        try:
            ssh_data = {
                'ssh_host': request.form.get('ssh_host'),
                'ssh_user': request.form.get('ssh_user'),
                'ssh_port': int(request.form.get('ssh_port'))
            }
        except ValueError:
            raise self.ValidationError('Invalid SSH port')

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
        else:
            # Reload tasks to get any changed info
            self.start_update_tasks()

    def _list_tasks(self):
        return [(
            '{0}{1}'.format(self.MONITOR_TASK_PREFIX, self.id),
            'network/device_monitor',
            {'device_id': self.id}
        )]

    def stop_tasks(self):
        for (task_id, _, _) in self._list_tasks():
            stop_task(task_id)

    def start_tasks(self):
        if self.status != 'Active' or not self.ssh_connected:
            return

        for task in self._list_tasks():
            start_task(*task)

    def start_update_tasks(self):
        if self.status != 'Active' or not self.ssh_connected:
            return

        for task in self._list_tasks():
            start_update_task(*task)

    def connect(self, password=None):
        '''Connect this device to it's bound SSH host.'''
        logger.debug('Connecting to device #{}: {}'.format(self.id, self.ssh_host))

        kwargs = {
            'username': self.ssh_user,
            'port': self.ssh_port,
            'timeout': settings.SSH_TIMEOUT
        }

        if password:
            kwargs['password'] = password
        else:
            kwargs['pkey'] = RSAKey.from_private_key_file(
                filename=settings.SSH_KEY_PRIVATE,
                password=settings.SSH_KEY_PASSWORD
            )

        client = SSHClient()
        client.set_missing_host_key_policy(MissingHostKeyPolicy())

        try:
            client.connect(self.ssh_host, **kwargs)
        except (
            SSHException, AuthenticationException, socket_error, gaierror
        ) as e:
            raise self.ConnectionError(str(e))

        self._connection = client
        self._connected = True

    def put(self, data, destination):
        '''Copy data to the remote device's filesystem.'''
        if not self._connected:
            raise self.NotConnected()

        if not self._sftp:
            # Naughty use of private method here, but Paramiko only does filename uploads
            # see: http://stackoverflow.com/questions/5914761
            self._sftp = self._connection._make_sftp()

        file = self._sftp.open(destination, 'wb')
        file.write(data)
        file.close()

    def execute(self, command, sudo=False):
        '''Execute a command on the remote device.'''
        if not self._connected:
            raise self.NotConnected()

        # If sudo, wrap w/sudo & bash
        if sudo:
            command = 'sudo -S bash -c "{}"'.format(command)
        # Else just wrap w/bash
        else:
            command = 'bash -c "{}"'.format(command)

        logger.debug('Executing command on device #{}: {}'.format(self.id, command))

        # Run the command, get stdout, stderr & the channel
        _, stdout, stderr = self._connection.exec_command(command)
        channel = stdout.channel

        # We have to iterate to get an exit_status
        # so we return stdout/stderr as lists of each line of output
        stdout = [line for line in stdout]
        stderr = [line for line in stderr]

        # Return depending on the exit code
        # when the server provides no exit status, paramiko will return -1
        # here we assume this is correct, and return stdout as normal
        if channel.exit_status <= 0:
            return stdout
        else:
            # The number of programs which don't use stderr is quite insane
            raise self.CommandError(channel.exit_status, stderr, stdout)

    def execute_multi(self, *commands):
        '''Multi-command wrapper around _execute above.'''
        return [self.execute(command) for command in commands]

    def get_cpu_stats(self):
        '''Take two readings of CPU stats 1s apart, and calculate usage during.'''
        return parse_cpu_stats(
            self.execute('cat /proc/stat; sleep 1; cat /proc/stat')
        )

    def get_memory_stats(self):
        '''Get current memory usage from /proc/meminfo.'''
        return parse_memory_stats(
            self.execute('cat /proc/meminfo')
        )

    def get_disk_stats(self):
        '''Get current disk usage.'''
        return parse_disk_stats(
            self.execute('df -B 1000')
        )

    def get_disk_io_stats(self):
        '''Take two readings of disk IO stats 1s apart, and calculate usage during.'''
        return parse_disk_io_stats(
            self.execute('cat /proc/diskstats; sleep 1s; cat /proc/diskstats')
        )

    def get_network_io_stats(self):
        '''Take two readings of network IO stats 1s apart and calculate usage during.'''
        return parse_network_io_stats(
            self.execute('cat /proc/net/dev; sleep 1s; cat /proc/net/dev')
        )
