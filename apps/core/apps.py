from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Core shared utilities — no models, no business logic."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"
