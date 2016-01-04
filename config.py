# Oxypanel Network
# File: config.py
# Desc: network module config

from .web.views.public import status
from .web.views.dashboard import dashboard

# Basics
TITLE = 'Network'
ICON = 'globe'
COLOR = 'purple'

# Module routes
ROUTES = [
    ('', ['GET'], dashboard),
    ('/status', ['GET'], status)
]
