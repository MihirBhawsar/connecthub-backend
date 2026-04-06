"""
Admin registrations for the notifications app.
"""
from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for Notifications."""

    list_display = ["id", "recipient", "sender", "notification_type", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["recipient__username", "sender__username"]
    raw_id_fields = ["recipient", "sender", "post"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]
