"""
Root pytest configuration for ConnectHub.

Applies project-wide fixtures to every test automatically.
"""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def no_celery_tasks():
    """
    Prevent any Celery task from connecting to a broker during tests.

    All .delay() / .apply_async() calls return a MagicMock immediately.
    Task tests that need real execution call the task function directly
    (e.g. `send_welcome_email(user.id)`) — those still run synchronously.
    """
    with patch(
        "celery.app.task.Task.apply_async",
        return_value=MagicMock(id="test-task-id"),
    ):
        yield


@pytest.fixture(autouse=True)
def no_throttling():
    """
    Disable all DRF rate limiting during tests.

    Patches SimpleRateThrottle.allow_request at the base class so every
    throttle subclass (LoginRateThrottle, AuthRateThrottle, etc.) returns
    True without checking the cache, regardless of how many requests the
    test has already made.
    """
    with patch(
        "rest_framework.throttling.SimpleRateThrottle.allow_request",
        return_value=True,
    ):
        yield
