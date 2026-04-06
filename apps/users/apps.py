from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Users app — handles profiles, following, and blocking."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Users"

    def ready(self) -> None:
        import apps.users.signals  # noqa: F401 — register signal handlers
