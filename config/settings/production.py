"""
Production settings for ConnectHub.
Extends base with security hardening and Sentry integration.
"""
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *  # noqa: F401, F403
from .base import env

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# ---------------------------------------------------------------------------
# Static files (WhiteNoise or S3)
# ---------------------------------------------------------------------------
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production",
    )

# ---------------------------------------------------------------------------
# Logging — production adds structured output
# ---------------------------------------------------------------------------
LOGGING = {  # type: ignore[assignment]
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
