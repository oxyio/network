# oxy.io Network
# File: web/views/ipblock.py
# Desc: ipblock views

import random

from flask import request
from netaddr import IPNetwork
from sqlalchemy.orm.exc import NoResultFound

from oxyio.app import db
from oxyio.web.util.response import redirect_or_jsonify

from ...models.ip import Ip


def _add_ips(ipblock, network):
    # Get current IP list
    current_ips = [
        ip.address
        for ip in ipblock.ips
    ]

    n_new_ips = 0
    for address in network:
        # Convert the IPAddress model to the string version
        if str(address) not in current_ips:
            db.session.add(Ip(
                address=str(address),
                ipblock=ipblock
            ))
            n_new_ips += 1

    # Write any new IPs
    db.session.commit()
    return n_new_ips


def ipblock_add_ips(ipblock):
    '''Add individual IPv4s to a block.'''

    ips = []

    lines = [
        line.strip()
        for line in request.form.get('ips', '').split('\n')
    ]

    # Remove empty lines
    lines = filter(lambda line: line, lines)

    # Build list of IPAddress models
    for cidr in lines:
        network = IPNetwork(cidr)
        ips.extend(network)

    # Check each IP is in this blocks CIDR
    ipblock_network = IPNetwork(ipblock.cidr)

    for ip in ips:
        if ip not in ipblock_network:
            return redirect_or_jsonify(ipblock.view_url,
                error='IP {0} is not in subnet {1}'.format(ip, ipblock.cidr)
            )

    n_new_ips = _add_ips(ipblock, ips)

    return redirect_or_jsonify(ipblock.view_url,
        success='{0} new IPs added'.format(n_new_ips)
    )


def ipblock_auto_add_ips(ipblock):
    '''Automatically fill out IPv4 blocks (v6 just have too many IPs!).'''

    # Add IPs from this IP blocks CIDR
    n_new_ips = _add_ips(ipblock, IPNetwork(ipblock.cidr))

    return redirect_or_jsonify(ipblock.view_url,
        success='{0} new IPs added'.format(n_new_ips)
    )


def _generate_ipv6(network, wanted_size):
    ips = []

    for _ in xrange(0, wanted_size):
        ip = random.choice(network)
        if ip not in ips:
            ips.append(ip)

    return ips


def ipblock_generate_ips(ipblock):
    '''Generate n IPs for IPv6 blocks.'''

    try:
        wanted_ips = int(request.form.get('size', ''))
    except (ValueError, TypeError):
        return redirect_or_jsonify(ipblock.view_url,
            error='Invalid number of IPs'
        )

    # Get current IP list
    current_ips = [
        ip.address
        for ip in ipblock.ips
    ]

    network = IPNetwork(ipblock.cidr)
    new_ips = []

    for address in network:
        if str(address) not in current_ips:
            new_ips.append(address)

        if len(new_ips) >= wanted_ips:
            break

    n_new_ips = _add_ips(ipblock, new_ips)

    return redirect_or_jsonify(ipblock.view_url,
        success='{0} new IPs added'.format(n_new_ips)
    )


def ipblock_delete_ip(ipblock):
    '''Delete a single IP from a block.'''

    try:
        ip_id = int(request.form.get('id', ''))
        ip = Ip.query.filter_by(id=ip_id).one()

    except (ValueError, TypeError, NoResultFound):
        return redirect_or_jsonify(ipblock.view_url,
            error='Invalid IP'
        )

    # Delete the IP from the database
    ip.delete()

    return redirect_or_jsonify(ipblock.view_url,
        success='{0} deleted'.format(ip.address)
    )
