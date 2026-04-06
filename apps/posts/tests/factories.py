"""
Factory Boy model factories for the posts app.
"""
from datetime import timedelta

import factory
from django.utils import timezone

from apps.posts.models import Comment, Hashtag, Like, Post, Story
from apps.users.tests.factories import UserFactory


class PostFactory(factory.django.DjangoModelFactory):
    """Factory for creating test Post instances."""

    class Meta:
        model = Post

    author = factory.SubFactory(UserFactory)
    caption = factory.Faker("text", max_nb_chars=200)
    media_type = "text"
    is_public = True
    likes_count = 0
    comments_count = 0


class ImagePostFactory(PostFactory):
    """Factory for image posts."""

    media_type = "image"


class PrivatePostFactory(PostFactory):
    """Factory for private posts."""

    is_public = False


class LikeFactory(factory.django.DjangoModelFactory):
    """Factory for Like relationships."""

    class Meta:
        model = Like

    user = factory.SubFactory(UserFactory)
    post = factory.SubFactory(PostFactory)


class CommentFactory(factory.django.DjangoModelFactory):
    """Factory for Comments."""

    class Meta:
        model = Comment

    author = factory.SubFactory(UserFactory)
    post = factory.SubFactory(PostFactory)
    parent = None
    body = factory.Faker("sentence")


class ReplyFactory(CommentFactory):
    """Factory for replies (nested comments)."""

    parent = factory.SubFactory(CommentFactory)


class HashtagFactory(factory.django.DjangoModelFactory):
    """Factory for Hashtags."""

    class Meta:
        model = Hashtag

    name = factory.Sequence(lambda n: f"tag{n}")


class StoryFactory(factory.django.DjangoModelFactory):
    """Factory for Stories."""

    class Meta:
        model = Story

    author = factory.SubFactory(UserFactory)
    media_type = "image"
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=24))
