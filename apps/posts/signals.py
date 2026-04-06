"""
Django signals for the posts app.

Handles:
- Creating notifications on like and comment events.
- Updating post search vector when a post is saved.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Comment, Like, Post

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Like)
def notify_on_like(sender, instance: Like, created: bool, **kwargs) -> None:
    """
    Create a Notification and push it via WebSocket when a user likes a post.
    Does not notify the user if they liked their own post.
    """
    if not created:
        return
    if instance.user == instance.post.author:
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.serializers import NotificationSerializer

        notification = Notification.objects.create(
            recipient=instance.post.author,
            sender=instance.user,
            notification_type="like",
            post=instance.post,
        )

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{instance.post.author.id}",
                {
                    "type": "send_notification",
                    "data": NotificationSerializer(notification).data,
                },
            )

        # Queue email for like notification
        from apps.notifications.tasks import send_notification_email
        send_notification_email.delay(
            instance.post.author.id,
            "like",
            instance.user.username,
        )
    except Exception as exc:
        logger.exception("Error creating like notification: %s", exc)


@receiver(post_save, sender=Comment)
def notify_on_comment(sender, instance: Comment, created: bool, **kwargs) -> None:
    """
    Create a Notification when a user comments on a post or replies to a comment.
    """
    if not created:
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.serializers import NotificationSerializer

        # Notify the post author
        if instance.author != instance.post.author:
            notification_type = "reply" if instance.parent_id else "comment"
            notification = Notification.objects.create(
                recipient=instance.post.author,
                sender=instance.author,
                notification_type=notification_type,
                post=instance.post,
            )

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{instance.post.author.id}",
                    {
                        "type": "send_notification",
                        "data": NotificationSerializer(notification).data,
                    },
                )

        # If it's a reply, also notify the parent comment author
        if instance.parent_id and instance.parent.author != instance.author:
            reply_notification = Notification.objects.create(
                recipient=instance.parent.author,
                sender=instance.author,
                notification_type="reply",
                post=instance.post,
            )
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{instance.parent.author.id}",
                    {
                        "type": "send_notification",
                        "data": NotificationSerializer(reply_notification).data,
                    },
                )

    except Exception as exc:
        logger.exception("Error creating comment notification: %s", exc)


@receiver(post_save, sender=Post)
def update_search_vector(sender, instance: Post, created: bool, **kwargs) -> None:
    """Update the search_vector field whenever a post's caption changes."""
    if kwargs.get("update_fields") and "search_vector" in kwargs["update_fields"]:
        # Avoid recursion — skip if we're already updating the search vector
        return
    try:
        Post.objects.filter(pk=instance.pk).update(
            search_vector=SearchVector("caption")
        )
    except Exception as exc:
        logger.warning("Could not update search vector for Post(%s): %s", instance.pk, exc)
