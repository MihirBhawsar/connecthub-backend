"""
Admin registrations for the posts app.
"""
from django.contrib import admin

from .models import Comment, Hashtag, Like, Post, Story


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Admin for Posts."""

    list_display = ["id", "author", "media_type", "is_public", "likes_count", "comments_count", "created_at"]
    list_filter = ["media_type", "is_public", "created_at"]
    search_fields = ["author__username", "caption"]
    raw_id_fields = ["author"]
    readonly_fields = ["created_at", "updated_at", "likes_count", "comments_count", "search_vector"]
    ordering = ["-created_at"]


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    """Admin for Likes."""

    list_display = ["id", "user", "post", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "post__id"]
    raw_id_fields = ["user", "post"]
    readonly_fields = ["created_at"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin for Comments."""

    list_display = ["id", "author", "post", "parent", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["author__username", "body"]
    raw_id_fields = ["author", "post", "parent"]
    readonly_fields = ["created_at"]


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    """Admin for Hashtags."""

    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    """Admin for Stories."""

    list_display = ["id", "author", "media_type", "expires_at", "created_at"]
    list_filter = ["media_type", "created_at"]
    search_fields = ["author__username"]
    raw_id_fields = ["author"]
    readonly_fields = ["created_at"]
