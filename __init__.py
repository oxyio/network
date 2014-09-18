from util import log

from . import config


def load():
    log.debug('  Loading device configs...')
    config.DEVICES = ['test']

    log.debug('  Loading virtual device configs...')
    config.VIRTUAL_DEVICES = ['whater']
