"""
Unit tests for posts app models.
"""
from django.test import TestCase

from apps.posts.models import Comment, Like, Post
from apps.users.tests.factories import UserFactory
from .factories import CommentFactory, LikeFactory, PostFactory, ReplyFactory


class PostModelTest(TestCase):

    def test_str_format(self):
        post = PostFactory()
        self.assertIn(str(post.author.username), str(post))
        self.assertIn(str(post.id), str(post))

    def test_default_likes_count_is_zero(self):
        post = PostFactory()
        self.assertEqual(post.likes_count, 0)

    def test_default_comments_count_is_zero(self):
        post = PostFactory()
        self.assertEqual(post.comments_count, 0)

    def test_post_ordering_newest_first(self):
        post1 = PostFactory()
        post2 = PostFactory()
        posts = list(Post.objects.all())
        self.assertEqual(posts[0], post2)


class LikeModelTest(TestCase):

    def test_unique_like_constraint(self):
        """Cannot like the same post twice."""
        from django.db import IntegrityError
        like = LikeFactory()
        with self.assertRaises(IntegrityError):
            Like.objects.create(user=like.user, post=like.post)

    def test_str_format(self):
        like = LikeFactory()
        result = str(like)
        self.assertIn(like.user.username, result)


class CommentModelTest(TestCase):

    def test_is_reply_false_for_top_level(self):
        comment = CommentFactory()
        self.assertFalse(comment.is_reply)

    def test_is_reply_true_for_nested(self):
        reply = ReplyFactory()
        self.assertTrue(reply.is_reply)

    def test_str_format(self):
        comment = CommentFactory()
        result = str(comment)
        self.assertIn(comment.author.username, result)
