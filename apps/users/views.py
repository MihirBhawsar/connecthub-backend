"""
User API views for ConnectHub.

Covers: own profile CRUD, public profile, follow/unfollow toggle,
followers/following lists, block/unblock toggle, user search, suggestions,
registration, password change, and JWT auth endpoints.
"""
import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.pagination import StandardPagePagination
from apps.core.throttling import AuthRateThrottle, LoginRateThrottle

from .models import Block, Follow
from .permissions import IsAccountOwner
from .serializers import (
    ChangePasswordSerializer,
    FollowSerializer,
    RegisterSerializer,
    UserMinimalSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ---------------------------------------------------------------------------
# Auth Views
# ---------------------------------------------------------------------------


@extend_schema(tags=["Auth"])
class RegisterView(generics.CreateAPIView):
    """Register a new user account."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = _get_tokens_for_user(user)
        return Response(
            {"user": UserProfileSerializer(user, context={"request": request}).data, **tokens},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Auth"])
class LogoutView(APIView):
    """Blacklist the provided refresh token, effectively logging out the user."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        """Blacklist the refresh token."""
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": True, "status_code": 400, "message": "refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as exc:
            logger.warning("Logout failed for user %s: %s", request.user.id, exc)
            return Response(
                {"error": True, "status_code": 400, "message": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Auth"])
class ChangePasswordView(APIView):
    """Change the authenticated user's password."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Profile Views
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Auth"],
    summary="Current authenticated user",
    description=(
        "Returns the full profile of the user identified by the Bearer access token. "
        "Use this in Swagger to verify which account is currently logged in. "
        "PATCH to update bio, avatar, website, or privacy settings."
    ),
    responses={200: UserProfileSerializer},
)
class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/users/me/ — retrieve own profile
    PATCH /api/v1/users/me/ — update own profile (avatar, bio, etc.)
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self) -> User:
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PATCH",):
            return UserUpdateSerializer
        return UserProfileSerializer


@extend_schema(tags=["Users"])
class UserProfileView(generics.RetrieveAPIView):
    """GET /api/v1/users/{username}/ — retrieve a public user profile."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    lookup_field = "username"
    queryset = User.objects.all()

    def get_queryset(self):
        """Exclude users who have blocked the requesting user."""
        blocked_ids = Block.objects.filter(
            blocked=self.request.user
        ).values_list("blocker_id", flat=True)
        return User.objects.exclude(id__in=blocked_ids)


# ---------------------------------------------------------------------------
# Follow / Unfollow
# ---------------------------------------------------------------------------


@extend_schema(tags=["Users"])
class FollowToggleView(APIView):
    """
    POST /api/v1/users/{username}/follow/

    Toggle follow/unfollow. If already following, unfollows.
    Returns the updated follow state.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request, username: str) -> Response:
        target = generics.get_object_or_404(User, username=username)

        if target == request.user:
            return Response(
                {"error": True, "status_code": 400, "message": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow_qs = Follow.objects.filter(follower=request.user, following=target)
        if follow_qs.exists():
            follow_qs.delete()
            return Response({"following": False, "username": username}, status=status.HTTP_200_OK)

        Follow.objects.create(follower=request.user, following=target)
        return Response({"following": True, "username": username}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Users"])
class FollowersListView(generics.ListAPIView):
    """GET /api/v1/users/{username}/followers/ — paginated list of followers."""

    serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        user = generics.get_object_or_404(User, username=self.kwargs["username"])
        return User.objects.filter(following__following=user).select_related()


@extend_schema(tags=["Users"])
class FollowingListView(generics.ListAPIView):
    """GET /api/v1/users/{username}/following/ — paginated list of users they follow."""

    serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        user = generics.get_object_or_404(User, username=self.kwargs["username"])
        return User.objects.filter(followers__follower=user).select_related()


# ---------------------------------------------------------------------------
# Block / Unblock
# ---------------------------------------------------------------------------


@extend_schema(tags=["Users"])
class BlockToggleView(APIView):
    """
    POST /api/v1/users/{username}/block/

    Toggle block/unblock. Also removes any follow relationships.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request, username: str) -> Response:
        target = generics.get_object_or_404(User, username=username)

        if target == request.user:
            return Response(
                {"error": True, "status_code": 400, "message": "You cannot block yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        block_qs = Block.objects.filter(blocker=request.user, blocked=target)
        if block_qs.exists():
            block_qs.delete()
            return Response({"blocked": False, "username": username}, status=status.HTTP_200_OK)

        # Remove any existing follow relationships in both directions
        Follow.objects.filter(
            Q(follower=request.user, following=target) |
            Q(follower=target, following=request.user)
        ).delete()

        Block.objects.create(blocker=request.user, blocked=target)
        return Response({"blocked": True, "username": username}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Search & Suggestions
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Users"],
    parameters=[OpenApiParameter("q", str, description="Search term for username or name")],
)
class UserSearchView(generics.ListAPIView):
    """GET /api/v1/users/search/?q= — search users by username or full name."""

    serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        if not query:
            return User.objects.none()

        # Exclude blocked/blocking users
        blocked_ids = Block.objects.filter(
            Q(blocker=self.request.user) | Q(blocked=self.request.user)
        ).values_list("blocker_id", "blocked_id")
        excluded_ids = {uid for pair in blocked_ids for uid in pair}

        return (
            User.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
            .exclude(id__in=excluded_ids)
            .exclude(id=self.request.user.id)
        )


@extend_schema(tags=["Users"])
class UserSuggestionsView(generics.ListAPIView):
    """
    GET /api/v1/users/suggestions/ — suggest users the authenticated user is not yet following.

    Returns a sample of users not in their follow list, ordered by followers.
    """

    serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        following_ids = self.request.user.following.values_list("following_id", flat=True)
        blocked_ids = Block.objects.filter(
            Q(blocker=self.request.user) | Q(blocked=self.request.user)
        ).values_list("blocker_id", "blocked_id")
        excluded_ids = {uid for pair in blocked_ids for uid in pair} | set(following_ids)
        excluded_ids.add(self.request.user.id)

        return User.objects.exclude(id__in=excluded_ids).order_by("-date_joined")[:50]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tokens_for_user(user: User) -> dict:
    """Generate JWT access + refresh tokens for a given user."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
