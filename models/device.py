# Oxypanel Network
# File: models/device.py
# Desc: the device & virtual device models

from io import open
from socket import error as SocketError

from flask import request
from paramiko import SSHClient, AutoAddPolicy, RSAKey
from paramiko.ssh_exception import AuthenticationException

import config
from app import db
from models.base import BaseConfig, BaseObject, BaseItem

from modules.network.views.device import device_ssh, device_command
from modules.network.config import DEVICES


class DeviceGroup(BaseObject, db.Model):
    __tablename__ = 'network_device_group'
    class Config(BaseConfig):
        NAME = 'Device Group'
        NAMES = 'Device Groups'


class Device(BaseObject, db.Model):
    __tablename__ = 'network_device'
    class Config(BaseConfig):
        NAME = 'Device'
        NAMES = 'Devices'

        LIST_FIELDS = EDIT_FIELDS = [
            ('status', {'text': 'enables or disables stat/log collection & virtual devices'}),
            ('config', {'override': ('enum', 'get_configs', {})}),
            ('location', {'text': 'for display/filtering only'})
        ]
        LIST_RELATIONS = EDIT_RELATIONS = [
            ('network', 'device_group', {})
        ]

        ROUTES = [
            ('/ssh', ['POST', 'PUT'], device_ssh, 'Edit'),
            ('/command', ['POST'], device_command, 'View')
        ]

    # Should we collect stats for this device & any virtual devices
    status = db.Column(db.Enum('Active', 'Suspended'), nullable=False, default='Active', server_default='Active')
    # CentOS/Debian/Ubuntu/etc
    config = db.Column(db.String(16), nullable=False)

    # For display/filters only
    location = db.Column(db.String(64))

    # SSH info
    ssh_host = db.Column(db.String(128), nullable=False)
    ssh_port = db.Column(db.Integer, nullable=False)
    ssh_user = db.Column(db.String(64), nullable=False)
    ssh_sudo = db.Column(db.Boolean, nullable=False)

    # Virtualization
    virtualization = db.Column(db.Enum('OpenVZ', 'KVM'))

    # Stats
    stat_interval = db.Column(db.Integer, nullable=False, default=10, server_default='10')

    device_group_id = db.Column(db.Integer, db.ForeignKey('network_device_group.id', ondelete='SET NULL'))
    device_group = db.relationship('DeviceGroup', backref=db.backref('devices'))

    def get_configs(self):
        return DEVICES

    def is_valid(self, new=False):
        if new:
            # Apply SSH details
            self.ssh_host = request.form.get('ssh_host')
            self.ssh_user = request.form.get('ssh_user')
            try:
                self.ssh_port = int(request.form.get('ssh_port'))
            except ValueError:
                return False, 'Invalid SSH port'

            # Try this first to avoid pointless SSH checking
            try:
                self.stat_interval = int(request.form.get('stat_interval'))
            except ValueError:
                return False, 'Invalid stat interval'

            # Confirm SSH works
            status, error = self.check_ssh(password=request.form.get('ssh_password'))
            if not status:
                return False, error

            # Apply extra details
            self.ssh_sudo = request.form.get('ssh_sudo') == 'on'

        return True, None

    def check_ssh(self, password=None):
        kwargs = {
            'port': self.ssh_port,
            'username': self.ssh_user,
            'look_for_keys': False,
            'allow_agent': False
        }
        if not password:
            try:
                key = RSAKey.from_private_key_file(
                    filename=config.SSH_KEY[0],
                    password=config.SSH_KEY_PASS
                )
                kwargs['pkey'] = key
            except ValueError:
                return False, 'Invalid SSH key'
        else:
            kwargs['password'] = password

        ssh = SSHClient()
        # Get lost host_keys!
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        try:
            ssh.connect(self.ssh_host, **kwargs)
            # If we're passwording, let's ensure the SSH pubkey is there
            if password:
                ssh_public_key = open(config.SSH_KEY[1]).read()
                # Ensure correct files
                ssh.exec_command('mkdir -p ~/.ssh/')
                ssh.exec_command('touch ~/.ssh/authorized_keys')
                # Check if the pubkey is there
                _, stdout, _ = ssh.exec_command('cat ~/.ssh/authorized_keys | grep "{0}"'.format(ssh_public_key))
                if len(stdout.read()) == 0:
                    ssh.exec_command('echo "{0}" > ~/.ssh/authorized_keys'.format(ssh_public_key))
        except SocketError:
            ssh.close()
            return False, 'Could not connect to {0}:{1}'.format(self.ssh_host, self.ssh_port)
        except AuthenticationException:
            ssh.close()
            if password:
                return False, 'Password authentication error'
            else:
                return False, 'Key authentication error'

        ssh.close()
        return True, None

        def start_update_monitor_task(self):
            pass


class DeviceFact(BaseItem, db.Model):
    __tablename__ = 'network_device_facts'

    device_id = db.Column(db.Integer, db.ForeignKey('network_device.id', ondelete='CASCADE'), nullable=False)
    device = db.relationship('Device', backref=db.backref('facts'))
