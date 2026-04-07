"""
Core utility views for ConnectHub.

HealthCheckView: public liveness probe — no auth required.
"""
import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Health"],
    summary="Health check",
    description="Returns the service liveness status. No authentication required.",
    responses={
        200: inline_serializer(
            name="HealthCheckResponse",
            fields={
                "status": serializers.CharField(default="ok"),
                "version": serializers.CharField(default="v1"),
            },
        )
    },
)
class HealthCheckView(APIView):
    """GET /api/v1/health/ — public liveness probe."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request) -> Response:
        return Response({"status": "ok", "version": "v1"}, status=status.HTTP_200_OK)
