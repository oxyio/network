# oxy.io Network
# File: config.py
# Desc: network module config

from .web.views.public import status
from .web.views.dashboard import dashboard

# Basics
TITLE = 'Network'
ICON = 'globe'
COLOR = 'purple'

# Module routes
ROUTES = (
    ('', ['GET'], dashboard),
    ('/status', ['GET'], status)
)

# Module settings (admin set overrides in database)
SETTINGS = (
    ('network.stat_interval', 10, 'Default stat interval for device monitors'),
)
