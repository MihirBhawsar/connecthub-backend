"""
WebSocket consumer for real-time notifications in ConnectHub.

Authentication is handled via JWT token passed in the WebSocket query string:
    ws://host/ws/notifications/?token=<access_token>

The consumer joins a per-user group named ``notifications_{user_id}``.
When a notification is created (via signal), the signal handler calls
``channel_layer.group_send`` to push the event to this group,
which triggers ``send_notification`` on each connected consumer.
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Async WebSocket consumer for real-time notifications.

    Connection lifecycle:
        connect    → authenticate → join group → accept
        receive    → handle ping/pong keepalive messages
        disconnect → leave group
    """

    async def connect(self) -> None:
        """
        Authenticate the connecting user via JWT token in query string.
        Accept the connection if valid, close with code 4001 if not.
        """
        user = await self._get_user_from_token()

        if user is None:
            logger.warning("WebSocket connection rejected: invalid or missing token.")
            await self.close(code=4001)
            return

        self.user = user
        self.group_name = f"notifications_{user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("WebSocket connected for user %s", user.id)

    async def disconnect(self, close_code: int) -> None:
        """Leave the user's notification group when the connection closes."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info("WebSocket disconnected for user %s (code=%s)", self.user.id, close_code)

    async def receive(self, text_data: str) -> None:
        """
        Handle incoming WebSocket messages from the client.

        Currently only ping/pong keepalive is supported.
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning("Received invalid JSON from WebSocket client.")
            return

        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

    async def send_notification(self, event: dict) -> None:
        """
        Called by the channel layer when a new notification is pushed to this group.

        Args:
            event: dict with keys ``type`` (= "send_notification") and ``data`` (notification payload).
        """
        await self.send(text_data=json.dumps(event["data"]))

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    async def _get_user_from_token(self):
        """
        Extract and validate the JWT access token from the query string.

        Returns the User instance if valid, or None.
        """
        query_string = self.scope.get("query_string", b"").decode()
        params = dict(param.split("=") for param in query_string.split("&") if "=" in param)
        token = params.get("token")

        if not token:
            return None

        return await self._authenticate_token(token)

    @database_sync_to_async
    def _authenticate_token(self, token: str):
        """
        Validate the JWT token synchronously (wrapped for async context).

        Returns the associated User or None if the token is invalid/expired.
        """
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        from rest_framework_simplejwt.tokens import AccessToken

        User = get_user_model()

        try:
            validated_token = AccessToken(token)
            user_id = validated_token["user_id"]
            return User.objects.get(id=user_id, is_active=True)
        except (TokenError, InvalidToken, User.DoesNotExist, KeyError) as exc:
            logger.debug("WebSocket token validation failed: %s", exc)
            return None
