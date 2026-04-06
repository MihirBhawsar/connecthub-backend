"""
User-specific permission classes for ConnectHub.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAccountOwner(BasePermission):
    """Allow access only to the user who owns the account."""

    def has_object_permission(self, request, view, obj) -> bool:
        return obj == request.user
