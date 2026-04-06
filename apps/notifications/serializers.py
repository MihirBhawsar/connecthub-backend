"""
Serializers for the notifications app.
"""
from rest_framework import serializers

from apps.users.serializers import UserMinimalSerializer

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Full notification serializer including sender and linked post."""

    sender = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "sender",
            "notification_type",
            "post",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "sender", "notification_type", "post", "created_at"]
