"""
Tests for posts Celery tasks.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.posts.tasks import expire_stories, generate_thumbnail
from .factories import ImagePostFactory, PostFactory, StoryFactory


class GenerateThumbnailTaskTest(TestCase):

    def test_handles_deleted_post_gracefully(self):
        """Task should exit cleanly if post was deleted before it ran."""
        result = generate_thumbnail(999999)
        self.assertIsNone(result)

    def test_handles_post_without_media_gracefully(self):
        """Task should exit cleanly for text posts with no media file."""
        post = PostFactory(media_type="text", media_file=None)
        result = generate_thumbnail(post.id)
        self.assertIsNone(result)

    @patch("apps.posts.tasks._generate_image_thumbnail")
    def test_generate_image_thumbnail_called_for_image_post(self, mock_generate):
        """For image posts with media, _generate_image_thumbnail should be called."""
        post = ImagePostFactory()
        # Simulate a media_file being set
        post.media_file = "posts/test.jpg"
        post.save(update_fields=["media_file"])

        generate_thumbnail(post.id)
        mock_generate.assert_called_once()


class ExpireStoriesTaskTest(TestCase):

    def test_expired_stories_are_deleted(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.posts.models import Story

        expired = StoryFactory(expires_at=timezone.now() - timedelta(hours=1))
        active = StoryFactory(expires_at=timezone.now() + timedelta(hours=23))

        expire_stories()

        self.assertFalse(Story.objects.filter(pk=expired.pk).exists())
        self.assertTrue(Story.objects.filter(pk=active.pk).exists())
