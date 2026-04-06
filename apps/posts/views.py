"""
Post API views for ConnectHub.

Covers: home feed, post CRUD, like/unlike toggle, comments, stories,
explore (trending), hashtag feed, and full-text search.
"""
import logging

from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.db.models import F, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import FeedCursorPagination, StandardPagePagination
from apps.core.permissions import IsOwnerOrReadOnly
from apps.core.throttling import AuthRateThrottle, PostCreateThrottle
from apps.users.models import Block, Follow

from .filters import PostFilter
from .models import Comment, Like, Post, Story
from .serializers import (
    CommentSerializer,
    LikeSerializer,
    PostCreateSerializer,
    PostSerializer,
    StorySerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

FEED_CACHE_TIMEOUT = 300  # 5 minutes


def _get_blocked_ids(user) -> set:
    """Return IDs of users who have blocked or been blocked by the given user."""
    pairs = Block.objects.filter(
        Q(blocker=user) | Q(blocked=user)
    ).values_list("blocker_id", "blocked_id")
    return {uid for pair in pairs for uid in pair}


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------


@extend_schema(tags=["Posts"])
class FeedView(generics.ListAPIView):
    """
    GET /api/v1/posts/ — home feed (cursor-paginated).

    Returns posts from users the authenticated user follows,
    ordered by newest first. Results are cached per user in Redis for 5 minutes.
    Cache is invalidated on new post creation via signal.
    """

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = FeedCursorPagination

    def get_queryset(self):
        user = self.request.user
        cache_key = f"feed:{user.id}"

        # Attempt cache hit
        cached_ids = cache.get(cache_key)
        if cached_ids is not None:
            # Re-fetch from DB using cached ID list to get fresh serializable objects
            preserved_order = {pk: idx for idx, pk in enumerate(cached_ids)}
            qs = (
                Post.objects.filter(id__in=cached_ids)
                .select_related("author")
                .prefetch_related("hashtags", "likes")
            )
            return sorted(qs, key=lambda p: preserved_order.get(p.pk, 0))

        blocked_ids = _get_blocked_ids(user)
        following_ids = user.following.values_list("following_id", flat=True)

        qs = (
            Post.objects.filter(
                author_id__in=following_ids,
                is_public=True,
            )
            .exclude(author_id__in=blocked_ids)
            .select_related("author")
            .prefetch_related("hashtags", "likes")
            .order_by("-created_at")
        )

        # Cache the ordered list of IDs (not model instances — avoids serialization issues)
        post_ids = list(qs.values_list("id", flat=True)[:200])
        cache.set(cache_key, post_ids, timeout=FEED_CACHE_TIMEOUT)

        return qs


# ---------------------------------------------------------------------------
# Post CRUD
# ---------------------------------------------------------------------------


@extend_schema(tags=["Posts"])
class PostListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/posts/all/ — list public posts (with filters)
    POST /api/v1/posts/     — create a new post
    """

    permission_classes = [IsAuthenticated]
    filterset_class = PostFilter
    search_fields = ["caption", "author__username"]
    ordering_fields = ["created_at", "likes_count"]
    ordering = ["-created_at"]

    def get_throttles(self):
        if self.request.method == "POST":
            return [PostCreateThrottle()]
        return [AuthRateThrottle()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PostCreateSerializer
        return PostSerializer

    def get_queryset(self):
        blocked_ids = _get_blocked_ids(self.request.user)
        return (
            Post.objects.filter(is_public=True)
            .exclude(author_id__in=blocked_ids)
            .select_related("author")
            .prefetch_related("hashtags", "likes")
            .order_by("-created_at")
        )

    def perform_create(self, serializer) -> None:
        """Save post with author set to the authenticated user."""
        post = serializer.save(author=self.request.user)
        # Invalidate this user's followers' feeds
        _invalidate_follower_feeds(self.request.user)
        # Trigger thumbnail generation if needed
        if post.media_file and post.media_type in ("image", "video"):
            from apps.posts.tasks import generate_thumbnail
            generate_thumbnail.delay(post.id)

    def create(self, request: Request, *args, **kwargs) -> Response:
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        instance = write_serializer.instance
        read_serializer = PostSerializer(instance, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Posts"])
class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/posts/{id}/ — retrieve post
    PATCH  /api/v1/posts/{id}/ — update (author only)
    DELETE /api/v1/posts/{id}/ — delete (author only), returns 204
    """

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    throttle_classes = [AuthRateThrottle]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        blocked_ids = _get_blocked_ids(self.request.user)
        return (
            Post.objects.exclude(author_id__in=blocked_ids)
            .select_related("author")
            .prefetch_related("hashtags", "likes")
        )

    def perform_destroy(self, instance: Post) -> None:
        author_id = instance.author_id
        instance.delete()
        _invalidate_feed(author_id)


# ---------------------------------------------------------------------------
# Like / Unlike Toggle
# ---------------------------------------------------------------------------


@extend_schema(tags=["Posts"])
class LikeToggleView(APIView):
    """
    POST /api/v1/posts/{id}/like/ — toggle like/unlike.

    Returns the current like state and updated count.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request, pk: int) -> Response:
        post = generics.get_object_or_404(Post, pk=pk)

        like_qs = Like.objects.filter(user=request.user, post=post)
        if like_qs.exists():
            like_qs.delete()
            Post.objects.filter(id=post.id).update(likes_count=F("likes_count") - 1)
            post.refresh_from_db(fields=["likes_count"])
            return Response({"liked": False, "likes_count": post.likes_count}, status=status.HTTP_200_OK)

        Like.objects.create(user=request.user, post=post)
        Post.objects.filter(id=post.id).update(likes_count=F("likes_count") + 1)
        post.refresh_from_db(fields=["likes_count"])
        return Response({"liked": True, "likes_count": post.likes_count}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Posts"])
class LikesListView(generics.ListAPIView):
    """GET /api/v1/posts/{id}/likes/ — list users who liked this post."""

    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        post = generics.get_object_or_404(Post, pk=self.kwargs["pk"])
        return Like.objects.filter(post=post).select_related("user")


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@extend_schema(tags=["Posts"])
class CommentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/posts/{id}/comments/ — list top-level comments with nested replies
    POST /api/v1/posts/{id}/comments/ — add a comment
    """

    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        post = generics.get_object_or_404(Post, pk=self.kwargs["pk"])
        return (
            Comment.objects.filter(post=post, parent=None)
            .select_related("author")
            .prefetch_related("replies__author")
            .order_by("created_at")
        )

    def perform_create(self, serializer) -> None:
        post = generics.get_object_or_404(Post, pk=self.kwargs["pk"])
        comment = serializer.save(author=self.request.user, post=post)
        Post.objects.filter(id=post.id).update(comments_count=F("comments_count") + 1)


@extend_schema(tags=["Posts"])
class CommentDeleteView(generics.DestroyAPIView):
    """DELETE /api/v1/posts/comments/{id}/ — delete comment (author only), returns 204."""

    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    throttle_classes = [AuthRateThrottle]
    queryset = Comment.objects.select_related("author")

    def perform_destroy(self, instance: Comment) -> None:
        Post.objects.filter(id=instance.post_id).update(comments_count=F("comments_count") - 1)
        instance.delete()


# ---------------------------------------------------------------------------
# Explore, Hashtag Feed, Full-Text Search
# ---------------------------------------------------------------------------


@extend_schema(tags=["Posts"])
class ExploreView(generics.ListAPIView):
    """
    GET /api/v1/posts/explore/ — trending public posts ordered by likes.

    Excludes posts from blocked/blocking users.
    """

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        blocked_ids = _get_blocked_ids(self.request.user)
        return (
            Post.objects.filter(is_public=True)
            .exclude(author_id__in=blocked_ids)
            .select_related("author")
            .prefetch_related("hashtags", "likes")
            .order_by("-likes_count", "-created_at")
        )


@extend_schema(tags=["Posts"])
class HashtagFeedView(generics.ListAPIView):
    """GET /api/v1/posts/hashtag/{name}/ — posts tagged with a specific hashtag."""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = FeedCursorPagination

    def get_queryset(self):
        name = self.kwargs["name"].lower()
        blocked_ids = _get_blocked_ids(self.request.user)
        return (
            Post.objects.filter(hashtags__name=name, is_public=True)
            .exclude(author_id__in=blocked_ids)
            .select_related("author")
            .prefetch_related("hashtags", "likes")
            .order_by("-created_at")
        )


@extend_schema(
    tags=["Posts"],
    parameters=[OpenApiParameter("q", str, description="Full-text search query")],
)
class PostSearchView(generics.ListAPIView):
    """GET /api/v1/posts/search/?q= — full-text search across post captions."""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        if not query:
            return Post.objects.none()

        blocked_ids = _get_blocked_ids(self.request.user)
        search_query = SearchQuery(query)
        vector = SearchVector("caption")

        return (
            Post.objects.annotate(search=vector, rank=SearchRank(vector, search_query))
            .filter(search=search_query, is_public=True)
            .exclude(author_id__in=blocked_ids)
            .select_related("author")
            .prefetch_related("hashtags", "likes")
            .order_by("-rank", "-created_at")
        )


# ---------------------------------------------------------------------------
# Stories
# ---------------------------------------------------------------------------


@extend_schema(tags=["Stories"])
class StoryFeedView(generics.ListAPIView):
    """GET /api/v1/stories/ — active stories from followed users."""

    serializer_class = StorySerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]
    pagination_class = StandardPagePagination

    def get_queryset(self):
        from django.utils import timezone
        following_ids = self.request.user.following.values_list("following_id", flat=True)
        return (
            Story.objects.filter(
                author_id__in=following_ids,
                expires_at__gt=timezone.now(),
            )
            .select_related("author")
            .order_by("-created_at")
        )


@extend_schema(tags=["Stories"])
class StoryCreateView(generics.CreateAPIView):
    """POST /api/v1/stories/ — create a new story (auto-expires in 24h)."""

    serializer_class = StorySerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PostCreateThrottle]

    def perform_create(self, serializer) -> None:
        serializer.save(author=self.request.user)


@extend_schema(tags=["Stories"])
class StoryDeleteView(generics.DestroyAPIView):
    """DELETE /api/v1/stories/{id}/ — delete own story, returns 204."""

    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    throttle_classes = [AuthRateThrottle]

    def get_queryset(self):
        return Story.objects.filter(author=self.request.user)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invalidate_feed(user_id: int) -> None:
    """Invalidate the cached feed for a specific user."""
    cache.delete(f"feed:{user_id}")


def _invalidate_follower_feeds(user) -> None:
    """Invalidate cached feeds for all followers of the given user."""
    follower_ids = Follow.objects.filter(following=user).values_list("follower_id", flat=True)
    keys = [f"feed:{fid}" for fid in follower_ids]
    if keys:
        cache.delete_many(keys)
