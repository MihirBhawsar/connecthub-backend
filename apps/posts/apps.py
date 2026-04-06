from django.apps import AppConfig


class PostsConfig(AppConfig):
    """Posts app — handles posts, likes, comments, hashtags, and stories."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.posts"
    verbose_name = "Posts"

    def ready(self) -> None:
        import apps.posts.signals  # noqa: F401 — register signal handlers
