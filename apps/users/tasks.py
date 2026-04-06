"""
Celery tasks for the users app.

Tasks:
    send_welcome_email            — send onboarding email to new users
    send_follow_notification_email — notify a user they have a new follower
"""
import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, user_id: int) -> None:
    """
    Send a welcome email to a newly registered user.

    Args:
        user_id: Primary key of the User to email.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # User deleted before task ran — nothing to do
        return

    try:
        send_mail(
            subject="Welcome to ConnectHub!",
            message=(
                f"Hi {user.first_name or user.username},\n\n"
                "Welcome to ConnectHub! Start exploring and connecting with people.\n\n"
                "— The ConnectHub Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Welcome email sent to user %s", user_id)
    except Exception as exc:
        logger.warning("Failed to send welcome email to user %s: %s", user_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_follow_notification_email(self, user_id: int, follower_username: str) -> None:
    """
    Notify a user that someone new is following them.

    Args:
        user_id: Primary key of the user who received a follow.
        follower_username: Username of the new follower.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    try:
        send_mail(
            subject=f"@{follower_username} started following you on ConnectHub",
            message=(
                f"Hi {user.first_name or user.username},\n\n"
                f"@{follower_username} has started following you on ConnectHub.\n\n"
                "— The ConnectHub Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Follow notification email sent to user %s", user_id)
    except Exception as exc:
        logger.warning("Failed to send follow email to user %s: %s", user_id, exc)
        raise self.retry(exc=exc)
