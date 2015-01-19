# Oxypanel Network
# File: __init__.py
# Desc: load up initial bits for the network module

from os import path, listdir
from glob import glob
from importlib import import_module

from util.log import logger

from . import config


# Load up device configs
def load():
    logger.debug('  Loading device configs...')
    files = glob(path.join('modules', 'network', 'devices', '*.py'))
    devices = {}
    scripts = {}

    for file in files:
        if file.endswith('__.py'): continue

        # Load the config
        file = path.basename(file).replace('.py', '')
        logger.debug('  + {0}'.format(file))
        device_config = import_module('modules.network.devices.{0}'.format(file))
        devices[file] = device_config

        # Load the scripts
        scripts[file] = listdir(path.join('modules', 'network', 'devices', file))

    config.DEVICES = devices
    config.SCRIPTS = scripts
