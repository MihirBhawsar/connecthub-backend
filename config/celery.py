"""
Celery application configuration for ConnectHub.
"""
import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("connecthub")

# Read config from Django settings using the CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Celery Beat periodic tasks
# ---------------------------------------------------------------------------
app.conf.beat_schedule = {
    "expire-stories-every-15-mins": {
        "task": "apps.posts.tasks.expire_stories",
        "schedule": crontab(minute="*/15"),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")  # noqa: T201 — intentional debug only
