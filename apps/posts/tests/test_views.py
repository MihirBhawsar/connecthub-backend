"""
API view tests for the posts app.
Covers post CRUD, feed, likes, comments, stories.
"""
from django.db.models import F
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.posts.models import Comment, Like, Post
from apps.users.models import Follow
from apps.users.tests.factories import UserFactory
from .factories import CommentFactory, LikeFactory, PostFactory, StoryFactory


class PostCreateTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("posts:post-list")

    def test_create_text_post_returns_201(self):
        data = {"caption": "Hello world", "media_type": "text"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["caption"], "Hello world")

    def test_create_post_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {"caption": "test"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PostDeleteTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.post = PostFactory(author=self.user)

    def test_author_can_delete_own_post(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("posts:post-detail", kwargs={"pk": self.post.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_non_author_cannot_delete_post(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("posts:post-detail", kwargs={"pk": self.post.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FeedViewTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("posts:feed")

    def test_feed_only_shows_followed_users_posts(self):
        followed = UserFactory()
        stranger = UserFactory()
        followed_post = PostFactory(author=followed, is_public=True)
        stranger_post = PostFactory(author=stranger, is_public=True)
        Follow.objects.create(follower=self.user, following=followed)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p["id"] for p in response.data["results"]]
        self.assertIn(followed_post.id, ids)
        self.assertNotIn(stranger_post.id, ids)

    def test_feed_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class LikeToggleViewTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.post = PostFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("posts:like-toggle", kwargs={"pk": self.post.pk})

    def test_like_post_increments_likes_count(self):
        self.client.post(self.url)
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes_count, 1)

    def test_unlike_post_decrements_likes_count(self):
        LikeFactory(user=self.user, post=self.post)
        Post.objects.filter(pk=self.post.pk).update(likes_count=F("likes_count") + 1)
        self.client.post(self.url)
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes_count, 0)

    def test_like_creates_like_object(self):
        self.client.post(self.url)
        self.assertTrue(Like.objects.filter(user=self.user, post=self.post).exists())


class CommentViewTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.post = PostFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("posts:comment-list", kwargs={"pk": self.post.pk})

    def test_add_comment_returns_201(self):
        response = self.client.post(self.url, {"body": "Great post!"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Comment.objects.filter(post=self.post, author=self.user).exists())

    def test_add_comment_increments_comments_count(self):
        self.client.post(self.url, {"body": "Nice!"})
        self.post.refresh_from_db()
        self.assertEqual(self.post.comments_count, 1)

    def test_delete_own_comment_returns_204(self):
        comment = CommentFactory(author=self.user, post=self.post)
        url = reverse("posts:comment-delete", kwargs={"pk": comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_other_comment_returns_403(self):
        other = UserFactory()
        comment = CommentFactory(author=other, post=self.post)
        url = reverse("posts:comment-delete", kwargs={"pk": comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ExploreViewTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("posts:explore")

    def test_explore_returns_public_posts(self):
        public_post = PostFactory(is_public=True)
        private_post = PostFactory(is_public=False)
        response = self.client.get(self.url)
        ids = [p["id"] for p in response.data["results"]]
        self.assertIn(public_post.id, ids)
        self.assertNotIn(private_post.id, ids)
