"""
Django signals for the users app.

Handles:
- Sending a welcome email when a new user registers.
- Sending notification email when someone follows a user.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Follow

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def send_welcome_email_on_register(sender, instance: User, created: bool, **kwargs) -> None:
    """Queue a welcome email task when a new user account is created."""
    if created:
        try:
            from apps.users.tasks import send_welcome_email
            send_welcome_email.delay(instance.id)
        except Exception as exc:
            logger.warning("Could not queue welcome email for user %s: %s", instance.id, exc)


@receiver(post_save, sender=Follow)
def notify_on_follow(sender, instance: Follow, created: bool, **kwargs) -> None:
    """
    Create a notification and push it via WebSocket when a user gains a new follower.
    """
    if not created:
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.serializers import NotificationSerializer

        notification = Notification.objects.create(
            recipient=instance.following,
            sender=instance.follower,
            notification_type="follow",
        )

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{instance.following.id}",
                {
                    "type": "send_notification",
                    "data": NotificationSerializer(notification).data,
                },
            )

        # Queue email notification
        from apps.users.tasks import send_follow_notification_email
        send_follow_notification_email.delay(instance.following.id, instance.follower.username)

    except Exception as exc:
        logger.exception("Error creating follow notification: %s", exc)
