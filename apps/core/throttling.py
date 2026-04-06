"""
Custom throttle classes for ConnectHub.

Rate limits are intentionally strict on auth endpoints to prevent brute-force
and on post creation to prevent spam.
"""
from rest_framework.throttling import AnonRateThrottle as BaseAnonRateThrottle
from rest_framework.throttling import UserRateThrottle


class AuthRateThrottle(UserRateThrottle):
    """General authenticated user rate limit — 1000 requests per day."""

    scope = "auth"
    rate = "1000/day"


class PostCreateThrottle(UserRateThrottle):
    """Post creation limit — 50 posts per hour."""

    scope = "post_create"
    rate = "50/hour"


class AnonRateThrottle(BaseAnonRateThrottle):
    """Anonymous user rate limit — 100 requests per hour."""

    scope = "anon"
    rate = "100/hour"


class LoginRateThrottle(BaseAnonRateThrottle):
    """Strict rate limit on login endpoint — 5 attempts per minute."""

    scope = "login"
    rate = "5/minute"
