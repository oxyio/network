# Oxypanel Network
# File: models/ipblock.py
# Desc: the ipblock & ip models

from app import db
from models.base import BaseConfig, BaseObject, BaseItem


class IpBlock(BaseObject, db.Model):
    __tablename__ = 'network_ipblock'
    class Config(BaseConfig):
        NAME = 'IP Block'
        NAMES = 'IP Blocks'

        LIST_FIELDS = EDIT_FIELDS = [
            ('version', {})
        ]
        LIST_RELATIONS = EDIT_RELATIONS = [
            ('network', 'device', {}),
            ('network', 'device_group', {})
        ]

    version = db.Column(db.Enum('4', '6'), nullable=False)

    device_id = db.Column(db.Integer, db.ForeignKey('network_device.id', ondelete='SET NULL'))
    device = db.relationship('Device', backref=db.backref('ipblocks'))

    device_group_id = db.Column(db.Integer, db.ForeignKey('network_device_group.id', ondelete='SET NULL'))
    device_group = db.relationship('DeviceGroup', backref=db.backref('ipblocks'))


class IpBlockIp(BaseItem, db.Model):
    __tablename__ = 'network_ipblock_ip'

    address = db.Column(db.String(128), nullable=False)
    hostname = db.Column(db.String(128))
    status = db.Column(db.Enum('Used', 'Unused', 'Reserved'), nullable=False, default='Unused', server_default='Unused')

    ipblock_id = db.Column(db.Integer, db.ForeignKey('network_ipblock.id', ondelete='CASCADE'), nullable=False)
    ipblock = db.relationship('IpBlock', backref=db.backref('ips'))
