"""
WSGI configuration for ConnectHub.
Used by Gunicorn for HTTP-only serving (production without WebSocket on same process).
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()
