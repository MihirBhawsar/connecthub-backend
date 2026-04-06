"""
Factory Boy model factories for the users app.
"""
import factory
from django.contrib.auth import get_user_model

from apps.users.models import Block, Follow

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating test User instances."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = factory.PostGenerationMethodCall("set_password", "testpassword123")
    is_private = False
    is_verified = False


class PrivateUserFactory(UserFactory):
    """Factory for users with private accounts."""

    is_private = True


class VerifiedUserFactory(UserFactory):
    """Factory for verified users."""

    is_verified = True


class FollowFactory(factory.django.DjangoModelFactory):
    """Factory for Follow relationships."""

    class Meta:
        model = Follow

    follower = factory.SubFactory(UserFactory)
    following = factory.SubFactory(UserFactory)


class BlockFactory(factory.django.DjangoModelFactory):
    """Factory for Block relationships."""

    class Meta:
        model = Block

    blocker = factory.SubFactory(UserFactory)
    blocked = factory.SubFactory(UserFactory)
