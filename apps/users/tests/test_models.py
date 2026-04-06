"""
Unit tests for users app models.
Tests cover Follow/Block logic and model methods.
"""
from django.test import TestCase

from apps.users.models import Block, Follow
from .factories import BlockFactory, FollowFactory, UserFactory


class UserModelTest(TestCase):
    """Tests for the User model."""

    def test_str_returns_at_username(self):
        user = UserFactory(username="alice")
        self.assertEqual(str(user), "@alice")

    def test_followers_count_default_zero(self):
        user = UserFactory()
        self.assertEqual(user.followers_count, 0)

    def test_following_count_default_zero(self):
        user = UserFactory()
        self.assertEqual(user.following_count, 0)

    def test_is_following_returns_true_when_following(self):
        follower = UserFactory()
        followee = UserFactory()
        FollowFactory(follower=follower, following=followee)
        self.assertTrue(follower.is_following(followee))

    def test_is_following_returns_false_when_not_following(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self.assertFalse(user1.is_following(user2))

    def test_is_blocked_by_returns_true_when_blocked(self):
        blocker = UserFactory()
        target = UserFactory()
        BlockFactory(blocker=blocker, blocked=target)
        self.assertTrue(target.is_blocked_by(blocker))

    def test_is_blocked_by_returns_false_when_not_blocked(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self.assertFalse(user1.is_blocked_by(user2))


class FollowModelTest(TestCase):
    """Tests for the Follow model."""

    def test_str_contains_both_usernames(self):
        follow = FollowFactory()
        result = str(follow)
        self.assertIn(str(follow.follower), result)
        self.assertIn(str(follow.following), result)

    def test_unique_follow_constraint(self):
        """Cannot create duplicate follow relationships."""
        from django.db import IntegrityError
        follow = FollowFactory()
        with self.assertRaises(IntegrityError):
            Follow.objects.create(follower=follow.follower, following=follow.following)

    def test_followers_count_increments(self):
        user = UserFactory()
        followers = UserFactory.create_batch(3)
        for f in followers:
            FollowFactory(follower=f, following=user)
        self.assertEqual(user.followers_count, 3)


class BlockModelTest(TestCase):
    """Tests for the Block model."""

    def test_str_contains_both_usernames(self):
        block = BlockFactory()
        result = str(block)
        self.assertIn(str(block.blocker), result)
        self.assertIn(str(block.blocked), result)

    def test_unique_block_constraint(self):
        """Cannot create duplicate block relationships."""
        from django.db import IntegrityError
        block = BlockFactory()
        with self.assertRaises(IntegrityError):
            Block.objects.create(blocker=block.blocker, blocked=block.blocked)
