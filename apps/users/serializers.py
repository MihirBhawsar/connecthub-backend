"""
Serializers for the users app.

Separate read/write serializers are used to avoid nested write issues.
"""
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Follow

logger = logging.getLogger(__name__)
User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal user representation used as a nested read-only field
    in posts, comments, notifications, etc.
    """

    class Meta:
        model = User
        fields = ["id", "username", "avatar", "is_verified"]
        read_only_fields = ["id", "username", "avatar", "is_verified"]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full public profile serializer.
    Includes follower/following counts and whether the requesting user follows this user.
    """

    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "bio",
            "avatar",
            "website",
            "is_private",
            "is_verified",
            "followers_count",
            "following_count",
            "is_following",
            "created_at",
        ]
        read_only_fields = ["id", "username", "is_verified", "created_at"]

    def get_is_following(self, obj: User) -> bool:
        """Return True if the requesting user follows this profile."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user.is_following(obj)
        return False


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating the authenticated user's own profile.
    Username and email changes are intentionally excluded here.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "bio", "avatar", "website", "is_private"]

    def validate_avatar(self, value):
        """Validate avatar image type and size."""
        from apps.core.utils import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE, validate_file_type

        try:
            validate_file_type(value, ALLOWED_IMAGE_TYPES)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        if value.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError("Avatar image must be smaller than 10 MB.")

        return value


class RegisterSerializer(serializers.ModelSerializer):
    """
    User registration serializer.
    Validates unique username/email and enforces Django password validation.
    """

    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, label="Confirm password", style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "password2"]

    def validate_email(self, value: str) -> str:
        """Ensure email is unique."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs: dict) -> dict:
        """Validate that both passwords match and pass Django validators."""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data: dict) -> User:
        """Create and return a new user with hashed password."""
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing the authenticated user's password."""

    old_password = serializers.CharField(required=True, style={"input_type": "password"})
    new_password = serializers.CharField(required=True, min_length=8, style={"input_type": "password"})
    new_password2 = serializers.CharField(required=True, label="Confirm new password", style={"input_type": "password"})

    def validate_old_password(self, value: str) -> str:
        """Verify the old password is correct."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs: dict) -> dict:
        """Ensure new passwords match and pass validators."""
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})
        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs


class FollowSerializer(serializers.ModelSerializer):
    """Serializer for Follow relationships — used in follower/following lists."""

    follower = UserMinimalSerializer(read_only=True)
    following = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ["id", "follower", "following", "created_at"]
        read_only_fields = ["id", "follower", "following", "created_at"]
