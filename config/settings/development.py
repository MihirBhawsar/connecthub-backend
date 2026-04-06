"""
Development settings for ConnectHub.
Extends base settings with developer-friendly configuration.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use local file storage in development (override S3 from base)
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Email: print to console in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Django Debug Toolbar
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# Relax CORS in development
CORS_ALLOW_ALL_ORIGINS = True

# Celery — run tasks eagerly in tests when needed (keep False for real celery in dev)
CELERY_TASK_ALWAYS_EAGER = False

# Channels — use in-memory layer when Redis not available locally
# Comment out the next block and keep CHANNEL_LAYERS from base if Redis is running.
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer",
#     }
# }
