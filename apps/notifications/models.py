"""
Notification model for ConnectHub.

Notifications are created via signals in apps/posts/signals.py and
apps/users/signals.py. They are delivered in real-time via WebSocket
(Django Channels) and optionally via email (Celery task).
"""
import logging

from django.contrib.auth import get_user_model
from django.db import models

logger = logging.getLogger(__name__)
User = get_user_model()


class Notification(models.Model):
    """
    A notification generated when a social interaction occurs.

    Types:
        like    — someone liked the user's post
        comment — someone commented on the user's post
        follow  — someone started following the user
        mention — someone mentioned the user in a caption/comment
        reply   — someone replied to the user's comment
    """

    TYPES = [
        ("like", "Like"),
        ("comment", "Comment"),
        ("follow", "Follow"),
        ("mention", "Mention"),
        ("reply", "Reply"),
    ]

    recipient = models.ForeignKey(
        User,
        related_name="notifications",
        on_delete=models.CASCADE,
    )
    sender = models.ForeignKey(
        User,
        related_name="sent_notifications",
        on_delete=models.CASCADE,
    )
    notification_type = models.CharField(max_length=20, choices=TYPES)
    post = models.ForeignKey(
        "posts.Post",
        null=True,
        blank=True,
        related_name="notifications",
        on_delete=models.SET_NULL,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"Notification({self.id}) [{self.notification_type}] "
            f"from {self.sender} to {self.recipient}"
        )
