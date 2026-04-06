"""
User domain models for ConnectHub.

Models:
    User    — extended AbstractUser with profile fields
    Follow  — directional follow relationship between users
    Block   — block relationship to hide content
"""
import logging

from django.contrib.auth.models import AbstractUser
from django.db import models

logger = logging.getLogger(__name__)


class User(AbstractUser):
    """
    Custom user model for ConnectHub.

    Extends AbstractUser with social profile fields.
    Always use AUTH_USER_MODEL / get_user_model() to reference this model.
    """

    bio = models.TextField(blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    website = models.URLField(blank=True, default="")
    is_private = models.BooleanField(
        default=False,
        help_text="When True, posts are only visible to approved followers.",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Verified badge — set by admin only.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"@{self.username}"

    @property
    def followers_count(self) -> int:
        """Number of users who follow this user."""
        return self.followers.count()

    @property
    def following_count(self) -> int:
        """Number of users this user follows."""
        return self.following.count()

    def is_following(self, other_user: "User") -> bool:
        """Return True if self follows other_user."""
        return self.following.filter(following=other_user).exists()

    def is_blocked_by(self, other_user: "User") -> bool:
        """Return True if other_user has blocked self."""
        return self.blocked_by.filter(blocker=other_user).exists()


class Follow(models.Model):
    """
    Directional follow relationship.

    ``follower`` follows ``following``.
    The unique_together constraint prevents duplicate follows.
    """

    follower = models.ForeignKey(
        User,
        related_name="following",
        on_delete=models.CASCADE,
    )
    following = models.ForeignKey(
        User,
        related_name="followers",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Follow"
        verbose_name_plural = "Follows"
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow"),
        ]
        indexes = [
            models.Index(fields=["follower", "-created_at"]),
            models.Index(fields=["following", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.follower} → {self.following}"


class Block(models.Model):
    """
    Block relationship.

    ``blocker`` blocks ``blocked``. Blocked users are excluded from all
    queries automatically through queryset filtering in views.
    """

    blocker = models.ForeignKey(
        User,
        related_name="blocking",
        on_delete=models.CASCADE,
    )
    blocked = models.ForeignKey(
        User,
        related_name="blocked_by",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Block"
        verbose_name_plural = "Blocks"
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block"),
        ]
        indexes = [
            models.Index(fields=["blocker"]),
            models.Index(fields=["blocked"]),
        ]

    def __str__(self) -> str:
        return f"{self.blocker} blocks {self.blocked}"
