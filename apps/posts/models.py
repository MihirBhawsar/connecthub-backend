"""
Post domain models for ConnectHub.

Models:
    Post     — user-created content (image, video, audio, text)
    Like     — a user liking a post
    Comment  — comment / nested reply on a post
    Hashtag  — tag extracted from post captions
    Story    — 24-hour ephemeral content
"""
import logging

from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


class Post(models.Model):
    """
    The core content unit of ConnectHub.

    Counters (likes_count, comments_count) are denormalized for performance:
    they are incremented/decremented atomically via F() expressions in signals
    rather than re-counted on every request.
    """

    MEDIA_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("text", "Text"),
    ]

    author = models.ForeignKey(
        User,
        related_name="posts",
        on_delete=models.CASCADE,
    )
    caption = models.TextField(max_length=2200, blank=True, default="")
    media_file = models.FileField(upload_to="posts/", blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default="text")
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True, null=True)
    is_public = models.BooleanField(default=True)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # PostgreSQL full-text search vector — updated via signal
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["is_public", "-created_at"]),
            # GIN index for full-text search is added via migration
        ]

    def __str__(self) -> str:
        return f"Post({self.id}) by {self.author.username}"


class Like(models.Model):
    """A user liking a post. Unique per (user, post) pair."""

    user = models.ForeignKey(
        User,
        related_name="liked_posts",
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        Post,
        related_name="likes",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Like"
        verbose_name_plural = "Likes"
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_like"),
        ]
        indexes = [
            models.Index(fields=["post", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} liked Post({self.post_id})"


class Comment(models.Model):
    """
    A comment on a post, optionally nested under a parent comment (reply).

    Top-level comments have parent=None.
    Replies have parent set to the comment being replied to.
    """

    author = models.ForeignKey(
        User,
        related_name="comments",
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        Post,
        related_name="comments",
        on_delete=models.CASCADE,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="replies",
        on_delete=models.CASCADE,
    )
    body = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        indexes = [
            models.Index(fields=["post", "created_at"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self) -> str:
        return f"Comment({self.id}) by {self.author.username} on Post({self.post_id})"

    @property
    def is_reply(self) -> bool:
        """Return True if this comment is a reply to another comment."""
        return self.parent_id is not None


class Hashtag(models.Model):
    """
    A hashtag extracted from post captions.

    Posts and hashtags are linked via a many-to-many relationship.
    """

    name = models.CharField(max_length=100, unique=True)
    posts = models.ManyToManyField(Post, related_name="hashtags", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Hashtag"
        verbose_name_plural = "Hashtags"

    def __str__(self) -> str:
        return f"#{self.name}"


class Story(models.Model):
    """
    24-hour ephemeral content.

    Expired stories are deleted by the Celery Beat ``expire_stories`` task
    that runs every 15 minutes.
    """

    MEDIA_TYPES = [
        ("image", "Image"),
        ("video", "Video"),
    ]

    author = models.ForeignKey(
        User,
        related_name="stories",
        on_delete=models.CASCADE,
    )
    media_file = models.FileField(upload_to="stories/")
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Story"
        verbose_name_plural = "Stories"
        indexes = [
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Story({self.id}) by {self.author.username}"

    def save(self, *args, **kwargs) -> None:
        """Auto-set expires_at to 24 hours from creation if not provided."""
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        """Return True if this story has passed its expiry time."""
        return timezone.now() >= self.expires_at
