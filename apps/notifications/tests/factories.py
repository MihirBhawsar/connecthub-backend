"""
Factory Boy model factories for the notifications app.
"""
import factory

from apps.notifications.models import Notification
from apps.users.tests.factories import UserFactory


class NotificationFactory(factory.django.DjangoModelFactory):
    """Factory for creating test Notification instances."""

    class Meta:
        model = Notification

    recipient = factory.SubFactory(UserFactory)
    sender = factory.SubFactory(UserFactory)
    notification_type = "like"
    post = None
    is_read = False
