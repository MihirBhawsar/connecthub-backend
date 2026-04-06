"""
Celery tasks for the notifications app.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger(__name__)
User = get_user_model()

NOTIFICATION_SUBJECTS = {
    "like": "{sender} liked your post on ConnectHub",
    "comment": "{sender} commented on your post on ConnectHub",
    "follow": "{sender} started following you on ConnectHub",
    "mention": "{sender} mentioned you in a post on ConnectHub",
    "reply": "{sender} replied to your comment on ConnectHub",
}

NOTIFICATION_MESSAGES = {
    "like": "Hi {name},\n\n@{sender} liked your post.\n\n— The ConnectHub Team",
    "comment": "Hi {name},\n\n@{sender} commented on your post.\n\n— The ConnectHub Team",
    "follow": "Hi {name},\n\n@{sender} started following you.\n\n— The ConnectHub Team",
    "mention": "Hi {name},\n\n@{sender} mentioned you in a post.\n\n— The ConnectHub Team",
    "reply": "Hi {name},\n\n@{sender} replied to your comment.\n\n— The ConnectHub Team",
}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email(self, user_id: int, notification_type: str, sender_username: str) -> None:
    """
    Send an email notification to a user about a social interaction.

    Args:
        user_id: Primary key of the recipient User.
        notification_type: One of 'like', 'comment', 'follow', 'mention', 'reply'.
        sender_username: Username of the user who triggered the notification.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    subject_template = NOTIFICATION_SUBJECTS.get(notification_type, "New notification on ConnectHub")
    message_template = NOTIFICATION_MESSAGES.get(
        notification_type,
        "Hi {name},\n\nYou have a new notification from @{sender}.\n\n— The ConnectHub Team",
    )

    name = user.first_name or user.username
    subject = subject_template.format(sender=sender_username)
    message = message_template.format(name=name, sender=sender_username)

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Notification email sent to user %s (type=%s)", user_id, notification_type)
    except Exception as exc:
        logger.warning("Failed to send notification email to user %s: %s", user_id, exc)
        raise self.retry(exc=exc)
