"""
Admin registrations for the users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Block, Follow, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for the custom User model."""

    list_display = ["id", "username", "email", "is_verified", "is_private", "is_staff", "date_joined"]
    list_filter = ["is_verified", "is_private", "is_staff", "is_superuser", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    readonly_fields = ["date_joined", "last_login", "created_at"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Profile",
            {
                "fields": ("bio", "avatar", "website", "is_private", "is_verified"),
            },
        ),
    )


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Admin for Follow relationships."""

    list_display = ["id", "follower", "following", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["follower__username", "following__username"]
    raw_id_fields = ["follower", "following"]
    readonly_fields = ["created_at"]


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    """Admin for Block relationships."""

    list_display = ["id", "blocker", "blocked", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["blocker__username", "blocked__username"]
    raw_id_fields = ["blocker", "blocked"]
    readonly_fields = ["created_at"]
