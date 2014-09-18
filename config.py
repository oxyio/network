# Oxypanel Network
# File: config.py
# Desc: network module config

from .views.public import status
from .views.dashboard import dashboard

# Basics
NAME = 'Network'
ICON = 'globe'
COLOR = 'purple'

# Routing
ROUTES = [
    ('', ['GET'], dashboard),
    ('/status', ['GET'], status)
]

# Objects
OBJECTS = {
    'device': [
        ('device', 'Device'),
        ('device_group', 'DeviceGroup')
    ],
    'ipblock': [
        ('ipblock', 'IpBlock')
    ]
}

# Node tasks
TASKS = {
    'device': {
        'automate': 'automate.js',
        'check': 'check.js',
        'monitor': 'monitor.js'
    }
}

# Node websockets
WEBSOCKETS = {
    'device': {
        'console': 'websockets/console.js'
    }
}
