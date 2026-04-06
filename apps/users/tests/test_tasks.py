"""
Tests for users Celery tasks.
"""
from unittest.mock import patch

from django.test import TestCase

from apps.users.tasks import send_follow_notification_email, send_welcome_email
from .factories import UserFactory


class SendWelcomeEmailTaskTest(TestCase):

    @patch("apps.users.tasks.send_mail")
    def test_sends_email_for_existing_user(self, mock_send_mail):
        user = UserFactory()
        send_welcome_email(user.id)
        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args
        self.assertIn(user.email, call_kwargs[1]["recipient_list"])

    def test_handles_nonexistent_user_gracefully(self):
        """Task should exit silently if user was deleted before it ran."""
        result = send_welcome_email(999999)
        self.assertIsNone(result)


class SendFollowNotificationEmailTaskTest(TestCase):

    @patch("apps.users.tasks.send_mail")
    def test_sends_follow_email(self, mock_send_mail):
        user = UserFactory()
        send_follow_notification_email(user.id, "alice")
        mock_send_mail.assert_called_once()

    def test_handles_nonexistent_user_gracefully(self):
        result = send_follow_notification_email(999999, "alice")
        self.assertIsNone(result)
