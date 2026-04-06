"""
Notification API views for ConnectHub.
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import NotificationPagination
from apps.core.throttling import AuthRateThrottle

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


@extend_schema(tags=["Notifications"])
class NotificationListView(generics.ListAPIView):
    """GET /api/v1/notifications/ — paginated list of notifications for the authenticated user."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = NotificationPagination

    def get_queryset(self):
        return (
            Notification.objects.filter(recipient=self.request.user)
            .select_related("sender", "post")
            .order_by("-created_at")
        )


@extend_schema(tags=["Notifications"])
class MarkAllReadView(APIView):
    """POST /api/v1/notifications/read-all/ — mark all notifications as read."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)
        return Response({"marked_read": updated}, status=status.HTTP_200_OK)


@extend_schema(tags=["Notifications"])
class MarkSingleReadView(generics.UpdateAPIView):
    """PATCH /api/v1/notifications/{id}/read/ — mark a single notification as read."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    http_method_names = ["patch", "head", "options"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


@extend_schema(tags=["Notifications"])
class UnreadCountView(APIView):
    """GET /api/v1/notifications/unread-count/ — return count of unread notifications."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def get(self, request: Request) -> Response:
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({"unread_count": count}, status=status.HTTP_200_OK)
