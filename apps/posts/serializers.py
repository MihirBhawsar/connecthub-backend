"""
Serializers for the posts app.
"""
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.core.utils import (
    ALLOWED_AUDIO_TYPES,
    ALLOWED_IMAGE_TYPES,
    ALLOWED_VIDEO_TYPES,
    extract_hashtags,
    get_max_file_size,
    validate_file_type,
)
from apps.users.serializers import UserMinimalSerializer

from .models import Comment, Hashtag, Like, Post, Story

logger = logging.getLogger(__name__)
User = get_user_model()

MEDIA_TYPE_MIME_MAP = {
    "image": ALLOWED_IMAGE_TYPES,
    "video": ALLOWED_VIDEO_TYPES,
    "audio": ALLOWED_AUDIO_TYPES,
}


class HashtagSerializer(serializers.ModelSerializer):
    """Minimal hashtag representation."""

    class Meta:
        model = Hashtag
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class PostSerializer(serializers.ModelSerializer):
    """
    Full post serializer.

    Used for list and detail responses. Author is a nested read-only field.
    Hashtags are extracted from caption automatically on create/update.
    """

    author = UserMinimalSerializer(read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)
    is_liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "caption",
            "media_file",
            "media_type",
            "thumbnail",
            "is_public",
            "likes_count",
            "comments_count",
            "hashtags",
            "is_liked_by_me",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author",
            "thumbnail",
            "likes_count",
            "comments_count",
            "hashtags",
            "created_at",
            "updated_at",
        ]

    def get_is_liked_by_me(self, obj: Post) -> bool:
        """Return True if the requesting user has liked this post."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def validate_caption(self, value: str) -> str:
        """Strip leading/trailing whitespace and enforce length."""
        value = value.strip()
        if len(value) > 2200:
            raise serializers.ValidationError("Caption must be 2200 characters or fewer.")
        return value

    def validate_media_file(self, value):
        """Validate MIME type and file size for uploaded media."""
        media_type = self.initial_data.get("media_type", "text")
        allowed_types = MEDIA_TYPE_MIME_MAP.get(media_type, ALLOWED_IMAGE_TYPES)

        try:
            mime = validate_file_type(value, allowed_types)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        max_size = get_max_file_size(mime)
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size {value.size} exceeds the maximum of {max_size} bytes."
            )

        return value

    def create(self, validated_data: dict) -> Post:
        """Create a post and link extracted hashtags."""
        caption = validated_data.get("caption", "")
        post = Post.objects.create(**validated_data)
        self._sync_hashtags(post, caption)
        return post

    def update(self, instance: Post, validated_data: dict) -> Post:
        """Update a post and re-sync hashtags if caption changed."""
        caption = validated_data.get("caption", instance.caption)
        post = super().update(instance, validated_data)
        self._sync_hashtags(post, caption)
        return post

    @staticmethod
    def _sync_hashtags(post: Post, caption: str) -> None:
        """Extract hashtags from caption and link them to the post."""
        tag_names = extract_hashtags(caption)
        hashtags = []
        for name in tag_names:
            hashtag, _ = Hashtag.objects.get_or_create(name=name)
            hashtags.append(hashtag)
        post.hashtags.set(hashtags)


class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer used exclusively for creating posts (write-only fields exposed)."""

    class Meta:
        model = Post
        fields = ["caption", "media_file", "media_type", "is_public"]

    def validate_caption(self, value: str) -> str:
        return value.strip()

    def validate_media_file(self, value):
        if value is None:
            return value
        media_type = self.initial_data.get("media_type", "text")
        allowed_types = MEDIA_TYPE_MIME_MAP.get(media_type, ALLOWED_IMAGE_TYPES)
        try:
            mime = validate_file_type(value, allowed_types)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        max_size = get_max_file_size(mime)
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size {value.size} exceeds the maximum of {max_size} bytes."
            )
        return value


class CommentSerializer(serializers.ModelSerializer):
    """
    Comment serializer.

    Top-level comments and replies share this serializer.
    Replies embed nested replies up to one level deep.
    """

    author = UserMinimalSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "author", "post", "parent", "body", "replies", "created_at"]
        read_only_fields = ["id", "author", "post", "created_at"]

    def get_replies(self, obj: Comment) -> list:
        """Return one level of nested replies for top-level comments only."""
        if obj.parent_id is not None:
            return []
        replies = obj.replies.select_related("author").all()
        return CommentSerializer(replies, many=True, context=self.context).data

    def validate_body(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Comment body cannot be empty.")
        if len(value) > 500:
            raise serializers.ValidationError("Comment must be 500 characters or fewer.")
        return value


class LikeSerializer(serializers.ModelSerializer):
    """Serializer for the list of users who liked a post."""

    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ["id", "user", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class StorySerializer(serializers.ModelSerializer):
    """
    Story serializer.

    expires_at is automatically set to 24 hours from creation.
    """

    author = UserMinimalSerializer(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "author",
            "media_file",
            "media_type",
            "expires_at",
            "is_expired",
            "created_at",
        ]
        read_only_fields = ["id", "author", "expires_at", "is_expired", "created_at"]

    def validate_media_file(self, value):
        """Validate media file type (image or video only for stories)."""
        allowed_types = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES
        try:
            validate_file_type(value, allowed_types)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def create(self, validated_data: dict) -> Story:
        """Set expires_at to 24 hours from now before creating."""
        validated_data["expires_at"] = timezone.now() + timedelta(hours=24)
        return Story.objects.create(**validated_data)
