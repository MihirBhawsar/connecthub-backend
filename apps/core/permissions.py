"""
Shared permission classes for ConnectHub.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission: allow any authenticated user to read,
    but only the owner of the object to write/delete.

    Expects the object to have an `author` attribute pointing to its owner.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user


class IsOwner(BasePermission):
    """
    Object-level permission: only allow the owner of the object to access it.

    Expects the object to have an `author` attribute pointing to its owner.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.author == request.user


class IsSelfOrReadOnly(BasePermission):
    """
    Object-level permission for User objects: read is public,
    write is restricted to the user themselves.

    Expects the object to be a User instance.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return obj == request.user
