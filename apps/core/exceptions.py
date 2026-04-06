"""
Custom exception handler for ConnectHub.

Wraps DRF's default exception responses in a consistent envelope:
    {
        "error": true,
        "status_code": 400,
        "message": { ... }
    }
"""
import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict) -> object:
    """
    Call DRF's default exception handler first, then reformat the response
    to match ConnectHub's unified error envelope.
    """
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "error": True,
            "status_code": response.status_code,
            "message": response.data,
        }
    else:
        # Unhandled server errors — log them
        logger.exception("Unhandled exception in request: %s", exc)

    return response
