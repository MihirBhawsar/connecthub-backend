"""
Testing settings for ConnectHub.

Uses SQLite so tests run without a running PostgreSQL instance.
Celery tasks run eagerly (synchronously) and Channels uses an in-memory layer.
"""
from .development import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Database — fast, in-process SQLite for tests
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ---------------------------------------------------------------------------
# Channels — no Redis needed in tests
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# ---------------------------------------------------------------------------
# Celery — tasks are NOT run eagerly; conftest.py patches apply_async so
# .delay() calls are no-ops. Task tests call task functions directly.
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = False

# ---------------------------------------------------------------------------
# Storage — local filesystem, not S3
# ---------------------------------------------------------------------------
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# ---------------------------------------------------------------------------
# Email — captured in memory, never sent
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ---------------------------------------------------------------------------
# Cache — local memory, no Redis needed
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ---------------------------------------------------------------------------
# Throttling — disable in tests so rate limits don't bleed across test cases
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# ---------------------------------------------------------------------------
# Passwords — fast hasher so test setup is not slow
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
