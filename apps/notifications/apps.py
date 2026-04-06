from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Notifications app — real-time notification delivery via WebSocket + email."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"
