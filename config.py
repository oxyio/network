# Oxypanel Network
# File: config.py
# Desc: network module config

from .views.public import status
from .views.dashboard import dashboard

# Basics
TITLE = 'Network'
ICON = 'globe'
COLOR = 'purple'

# Module routes
ROUTES = [
    ('', ['GET'], dashboard),
    ('/status', ['GET'], status)
]
