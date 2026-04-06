"""
WebSocket consumer tests for the notifications app.
"""
from unittest.mock import patch

from django.test import TestCase

from apps.users.tests.factories import UserFactory


class NotificationConsumerAuthTest(TestCase):
    """
    Tests for the NotificationConsumer authentication logic.

    Full WebSocket integration tests require channels.testing.WebsocketCommunicator
    and an async test runner. These tests isolate the token extraction logic.
    """

    def test_consumer_rejects_missing_token(self):
        """Consumer's token parser returns None for missing token."""
        import asyncio
        from apps.notifications.consumers import NotificationConsumer

        consumer = NotificationConsumer()
        consumer.scope = {"query_string": b""}

        async def run():
            return await consumer._get_user_from_token()

        result = asyncio.get_event_loop().run_until_complete(run())
        self.assertIsNone(result)

    def test_consumer_rejects_invalid_token(self):
        """Consumer's token parser returns None for an invalid token string."""
        import asyncio
        from apps.notifications.consumers import NotificationConsumer

        consumer = NotificationConsumer()
        consumer.scope = {"query_string": b"token=notavalidtoken"}

        async def run():
            return await consumer._get_user_from_token()

        result = asyncio.get_event_loop().run_until_complete(run())
        self.assertIsNone(result)
