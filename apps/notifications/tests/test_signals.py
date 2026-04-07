"""
Signal tests for the notifications app.
Verifies that notifications are created on like and follow events.
"""
from unittest.mock import patch

from django.test import TestCase

from apps.notifications.models import Notification
from apps.posts.tests.factories import LikeFactory, PostFactory
from apps.users.tests.factories import FollowFactory, UserFactory


class LikeNotificationTest(TestCase):

    @patch("apps.posts.signals.get_channel_layer")
    def test_like_creates_notification_for_post_author(self, mock_channel_layer):
        mock_channel_layer.return_value = None  # Disable WebSocket push in test
        author = UserFactory()
        liker = UserFactory()
        post = PostFactory(author=author)

        LikeFactory(user=liker, post=post)

        self.assertEqual(
            Notification.objects.filter(
                recipient=author,
                sender=liker,
                notification_type="like",
            ).count(),
            1,
        )

    @patch("apps.posts.signals.get_channel_layer")
    def test_liking_own_post_does_not_create_notification(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        user = UserFactory()
        post = PostFactory(author=user)

        LikeFactory(user=user, post=post)

        self.assertEqual(Notification.objects.filter(recipient=user).count(), 0)


class FollowNotificationTest(TestCase):

    @patch("apps.users.signals.get_channel_layer")
    @patch("apps.users.tasks.send_follow_notification_email")
    def test_follow_creates_notification(self, mock_email, mock_channel_layer):
        mock_channel_layer.return_value = None
        follower = UserFactory()
        followee = UserFactory()

        FollowFactory(follower=follower, following=followee)

        self.assertEqual(
            Notification.objects.filter(
                recipient=followee,
                sender=follower,
                notification_type="follow",
            ).count(),
            1,
        )
