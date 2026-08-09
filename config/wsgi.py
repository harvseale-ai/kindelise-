"""Expose the WSGI application used by Gunicorn."""

# WHY: Gives the live Gunicorn server one supported doorway into the Django site.

# KEYWORD: WSGI — the standard doorway a traditional web server can use to pass visits into Django.


import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
