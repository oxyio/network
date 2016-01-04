# oxy.io Network
# File: models/ip.py
# Desc: the ip item model

from oxyio.app import db
from oxyio.app.module_loader import has_module
from oxyio.models.base import Item


class Ip(Item, db.Model):
    NAME = 'network/ipblock/ip'
    TITLE = 'IP'

    address = db.Column(db.String(128), nullable=False, unique=True)
    hostname = db.Column(db.String(128))

    status = db.Column(
        db.Enum('Used', 'Unused', 'Reserved'),
        nullable=False, default='Unused', server_default='Unused'
    )

    # IPs must *always* be attached to an IP block
    ipblock_id = db.Column(
        db.Integer,
        db.ForeignKey('network_ipblock.id', ondelete='CASCADE'),
        nullable=False
    )
    ipblock = db.relationship('IpBlock', backref=db.backref('ips', lazy='dynamic'))

    device_id = db.Column(
        db.Integer,
        db.ForeignKey('network_device.id', ondelete='SET NULL')
    )
    device = db.relationship('Device', backref=db.backref('ips'))

    # Since oxy.io modules are all optional, the cloud/service module may not exist
    # but we still want a ForeignKey when it is present. Note this means once you install
    # cloud/service, there's no going back!
    if has_module('cloud'):
        service_id = db.Column(
            db.Integer,
            db.ForeignKey('cloud_service.id', ondelete='SET NULL')
        )
        service = db.relationship('Service', backref=db.backref('ips'))

    def __unicode__(self):
        return self.address

    def save(self):
        '''
        Populate the IPs status field dependent on having a device or service attached.
        '''

        # Skip reserved IPs
        if self.status != 'Reserved':
            if self.device_id:
                self.status = 'Used'

            elif has_module('cloud') and self.service_id:
                self.status = 'Used'

        super(Ip, self).save()
