# oxy.io Network
# File: models/ip.py
# Desc: the ip item model

from sqlalchemy import event, and_
from sqlalchemy.orm import foreign

from oxyio.app import db
from oxyio.app.module_loader import has_module
from oxyio.models.item import Item

from .device import Device

# Attempt to load the Service object
try:
    from oxyio.cloud.models.service import Service
except ImportError:
    Service = None


class Ip(Item, db.Model):
    # Config
    #

    NAME = 'network/ipblock/ip'
    TITLE = 'IP'

    # This ensures the item, when attached to objects via `object_type` and `object_id`,
    # can only be attached to objects of this type.
    MULTI_OBJECT = ('network/device', 'cloud/service')

    # Db columns
    #

    object_id = db.Column(db.Integer)
    object_type = db.Column(db.String(128))

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

    # Join load any related network device
    device = db.relationship('Device', primaryjoin=and_(
        object_type == 'network/device',
        foreign(object_id) == Device.id
    ), backref='ips')

    if Service is not None:
        # Or cloud service
        service = db.relationship('Service', primaryjoin=and_(
            object_type == 'cloud/service',
            foreign(object_id) == Service.id
        ), backref='ips')

    def __unicode__(self):
        return self.address

    # oxy.io
    #

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


def test(*args, **kwargs):
    print 'TEST', args, kwargs

event.listen(Ip, 'before_insert', test)
