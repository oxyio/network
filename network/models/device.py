# oxy.io Network
# File: network/models/device.py
# Desc: the device & device_group models

from socket import error as socket_error, gaierror

from flask import g
from paramiko import (
    SSHClient, RSAKey, MissingHostKeyPolicy, SSHException, AuthenticationException
)

from oxyio import settings
from oxyio.app import db, task_app
from oxyio.log import logger
from oxyio.models.object import Object
from oxyio.models.item import Item
from oxyio.web.flashes import flash_request, flash_task_subscribe
from oxyio.web.request import get_request_data
from oxyio.web.websockets import make_websocket_request

from ..mappings import MAPPINGS
from ..web.views.device import api_get_device_stats, api_get_device_stat_keys
from ..web.views.group import api_get_group_stats


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

    ROUTES = (
        ('/stats', ['GET'], api_get_group_stats, 'view'),
    )

    devices = db.relationship('Device', secondary=device__group)

    @property
    def stats_api_url(self):
        return '{0}/stats'.format(self.view_url)


class DeviceFact(Item, db.Model):
    NAME = 'network/device/fact'
    TITLE = 'Fact'

    device_id = db.Column(db.Integer,
        db.ForeignKey('network_device.id', ondelete='CASCADE'),
        nullable=False
    )
    device = db.relationship('Device', backref=db.backref('facts'))


class Device(Object, db.Model):
    # Config
    #

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
        ('/stats_keys', ['GET'], api_get_device_stat_keys, 'view')
    )

    MONITOR_TASK_PREFIX = 'monitor-device-'

    # DB Columns
    #

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
    _connecting = False
    _connected = False
    _connection = None
    _sftp = None

    # URL Helper
    #

    @property
    def stats_api_url(self):
        return '{0}/stats'.format(self.view_url)

    # Exceptions
    #

    class DeviceError(Object.ObjectError):
        pass

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

    # oxy.io
    #

    def pre_view(self):
        if self.status == 'Active':
            # Create websocket request for client to receive monitor updates, this will
            # also capture/notify if the monitor task is in ERROR or EXCEPTION state
            request_key = make_websocket_request(
                'core/task_subscribe', '{0}{1}'.format(self.MONITOR_TASK_PREFIX, self.id)
            )
            flash_request('device_monitor', request_key)

            # Create websocket request for the processes tab

    def check_apply_edit(self, request_data):
        # Validate int input
        for field in ('stat_interval', 'ssh_port'):
            if field in request_data:
                try:
                    request_data[field] = int(request_data[field])
                except ValueError:
                    raise self.EditRequestError('Invalid {0}'.format(field))

        # Validate sudo, API expects JSON bool
        if g.api:
            if (
                'ssh_sudo' in request_data
                and not isinstance(request_data['ssh_sudo'], bool)
            ):
                raise self.EditRequestError('Invalid ssh_sudo (not boolean)')

        # HTML is a checkbox, so lack of presence = off
        else:
            request_data['ssh_sudo'] = request_data.get('ssh_sudo') == 'on'

        update = reconnect = False

        # Non SSH connection affecting data
        for field in ('stat_interval', 'ssh_sudo'):
            if field in request_data and request_data[field] != getattr(self, field):
                setattr(self, field, request_data[field])
                update = True

        # SSH connection affecting
        for field in ('ssh_host', 'ssh_user', 'ssh_port'):
            if field in request_data and request_data[field] != getattr(self, field):
                setattr(self, field, request_data[field])
                reconnect = True

        # Connection details changed, prep for connection (post_add_edit)
        if reconnect:
            self.ssh_connected = None

        # Config has changed, restart monitor
        elif update:
            self.reload_monitor()

    def post_add_edit(self):
        # If we're active and already connected, ensure the monitor is running
        if self.status == 'Active' and self.ssh_connected:
            self.ensure_monitor()
            return

        # Stop monitor
        self.stop_monitor()

        # Create check task (which will update connection check & restart monitor)
        task_id = task_app.helpers.start_task(
            'network/device_connect',
            device_id=self.id,
            password=get_request_data().get('password')
        )

        # Websockets not available in API mode
        if not g.api:
            # Create websocket request for client to watch progress
            request_key = make_websocket_request('core/task_subscribe', task_id)
            flash_task_subscribe(request_key)

        # Set connecting for the remainder of the request
        self._connecting = True

    def post_edit(self):
        self.post_add_edit()

    def post_add(self):
        self.post_add_edit()

    # Monitoring
    #

    @property
    def monitor_task_id(self):
        return '{0}{1}'.format(self.MONITOR_TASK_PREFIX, self.id)

    def start_monitor(self):
        task_app.helpers.start_task(
            'network/device_monitor',
            task_id=self.monitor_task_id,
            cleanup=False,
            device_id=self.id
        )

    def stop_monitor(self):
        task_app.helpers.stop_task(self.monitor_task_id)

    def reload_monitor(self):
        task_app.helpers.reload_task(self.monitor_task_id)

    def ensure_monitor(self):
        task_app.helpers.restart_if_state(
            self.monitor_task_id,
            ('ERROR', 'EXCEPTION')
        )

    # SSH
    #

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

        f = self._sftp.open(destination, 'wb')
        f.write(data)
        f.close()

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
