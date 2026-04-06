"""
ASGI configuration for ConnectHub.

Handles both HTTP (Django) and WebSocket (Django Channels) connections.
WebSocket routes are authenticated via JWT token in the query string.

Entrypoint: daphne -b 0.0.0.0 -p 8000 config.asgi:application
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Initialize Django ASGI app early to populate the AppRegistry.
django_asgi_app = get_asgi_application()

# Import consumers AFTER get_asgi_application() to ensure apps are loaded.
from apps.notifications.consumers import NotificationConsumer  # noqa: E402

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
