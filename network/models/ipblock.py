# oxy.io Network
# File: models/ipblock.py
# Desc: the ipblock object model

from netaddr import IPNetwork, AddrFormatError
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, column_property

from oxyio.app import db
from oxyio.app.module_loader import has_module
from oxyio.util import server_only
from oxyio.models.object import Object

from .ip import Ip
from ..web.views.ipblock import (
    ipblock_add_ips, ipblock_generate_ips, ipblock_auto_add_ips, ipblock_delete_ip
)


class IpBlock(Object, db.Model):
    # Config
    #

    NAME = 'network/ipblock'
    TITLE = 'IP Block'

    # No editing version
    EDIT_FIELDS = (
        ('cidr', {'title': 'CIDR'}),
    )

    # Filter, but don't list, version
    FILTER_FIELDS = (
        ('cidr', {'title': 'CIDR'}),
        ('version', {'formatter': 'v{0}'})
    )

    # List CIDR and the special ip_count attr
    LIST_FIELDS = (
        ('cidr', {'title': 'CIDR'}),
        ('ip_count', {'title': 'IPs'})
    )

    EDIT_RELATIONS = (
        ('device', 'network/device', {}),
        ('group', 'network/group', {})
    )

    ROUTES = (
        ('/add_ips', ['POST'], ipblock_add_ips, 'edit'),
        ('/auto_add_ips', ['POST'], ipblock_auto_add_ips, 'edit'),
        ('/generate_ips', ['POST'], ipblock_generate_ips, 'edit'),
        ('/delete_ip', ['POST'], ipblock_delete_ip, 'edit')
    )

    # Db columns
    #

    # CIDR representation of this IP block
    cidr = db.Column(db.String(64))

    # IP v4 or v6, autodetected
    version = db.Column(db.Enum('4', '6'), nullable=False)

    # Linked device
    device = db.relationship('Device', backref=db.backref('ipblocks'))
    device_id = db.Column(db.Integer,
        db.ForeignKey('network_device.id', ondelete='SET NULL')
    )

    # Linked device group
    group = db.relationship('DeviceGroup', backref=db.backref('ipblocks'))
    group_id = db.Column(db.Integer,
        db.ForeignKey('network_group.id', ondelete='SET NULL')
    )

    # Redefined from base model for use in ip_count
    id = db.Column(db.Integer, primary_key=True)

    ip_count = column_property(
        select([func.count(Ip.id)]).where(Ip.ipblock_id == id)
        # This line stops filters on other tables (ipblock) being pushed into this query,
        # ie this subquery will *only* touch ip.
        .correlate_except(Ip)
    )

    # @Properties
    #

    def _get_ip_count(self, status):
        results = db.session.execute((
            select([func.count(Ip.id)])
            .where(Ip.ipblock_id == self.id)
            .where(Ip.status == status)
        ))

        return list(results)[0][0]

    @property
    def used_ip_count(self):
        return self._get_ip_count('Used')

    @property
    def unused_ip_count(self):
        return self._get_ip_count('Unused')

    @property
    def reserved_ip_count(self):
        return self._get_ip_count('Reserved')

    # oxy.io
    #

    @server_only
    def pre_view(self):
        # Attach a IPNetwork object to self
        self.network = IPNetwork(self.cidr)

        # Attached a joined version of self.ips
        fields = [Ip.device]
        if has_module('cloud'):
            fields.append(Ip.service)

        self.addresses = self.ips.options(*[
            joinedload(field)
            for field in fields
        ])

    @server_only
    def is_valid(self):
        # Check CIDR
        try:
            network = IPNetwork(self.cidr)
        except AddrFormatError:
            raise self.ValidationError('Invalid CIDR')

        # Set the CIDR to the str of the IPNetwork - this means we always get IP & prefix
        self.cidr = str(network)

        # Populate version as string (for enum)
        self.version = str(network.version)
