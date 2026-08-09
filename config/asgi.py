"""Expose the standard ASGI application without WebSocket behaviour."""

# WHY: Gives compatible web servers one supported doorway into the Django site.

# KEYWORD: ASGI — the standard doorway an online server can use to pass visits into Django.


import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
