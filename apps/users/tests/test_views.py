"""
API view tests for the users app.
Covers registration, auth, profile, follow, block, search endpoints.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Block, Follow
from .factories import BlockFactory, FollowFactory, UserFactory


class RegisterViewTest(APITestCase):
    """Tests for user registration endpoint."""

    def setUp(self):
        self.url = reverse("users:register")

    def test_register_with_valid_data_returns_201(self):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_register_with_mismatched_passwords_returns_400(self):
        data = {
            "username": "newuser2",
            "email": "new2@example.com",
            "password": "SecurePass123!",
            "password2": "WrongPass!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_with_duplicate_email_returns_400(self):
        user = UserFactory(email="existing@example.com")
        data = {
            "username": "another",
            "email": "existing@example.com",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTest(APITestCase):
    """Tests for the /me/ profile endpoint."""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("users:me")

    def test_get_own_profile_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user.username)

    def test_patch_bio_updates_profile(self):
        response = self.client.patch(self.url, {"bio": "Updated bio"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, "Updated bio")

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FollowToggleViewTest(APITestCase):
    """Tests for follow/unfollow toggle."""

    def setUp(self):
        self.user = UserFactory()
        self.target = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("users:follow", kwargs={"username": self.target.username})

    def test_follow_user_creates_follow_object(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Follow.objects.filter(follower=self.user, following=self.target).exists())

    def test_follow_already_followed_user_unfollows(self):
        FollowFactory(follower=self.user, following=self.target)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["following"])
        self.assertFalse(Follow.objects.filter(follower=self.user, following=self.target).exists())

    def test_cannot_follow_yourself_returns_400(self):
        self.url = reverse("users:follow", kwargs={"username": self.user.username})
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BlockToggleViewTest(APITestCase):
    """Tests for block/unblock toggle."""

    def setUp(self):
        self.user = UserFactory()
        self.target = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("users:block", kwargs={"username": self.target.username})

    def test_block_user_creates_block_object(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Block.objects.filter(blocker=self.user, blocked=self.target).exists())

    def test_block_removes_existing_follow(self):
        FollowFactory(follower=self.user, following=self.target)
        self.client.post(self.url)
        self.assertFalse(Follow.objects.filter(follower=self.user, following=self.target).exists())

    def test_unblock_already_blocked_user(self):
        BlockFactory(blocker=self.user, blocked=self.target)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["blocked"])


class UserSearchViewTest(APITestCase):
    """Tests for the user search endpoint."""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("users:search")

    def test_search_by_username_returns_matching_users(self):
        target = UserFactory(username="findme123")
        response = self.client.get(self.url, {"q": "findme"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u["username"] for u in response.data["results"]]
        self.assertIn("findme123", usernames)

    def test_empty_query_returns_empty_list(self):
        response = self.client.get(self.url, {"q": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_blocked_users_excluded_from_search(self):
        blocked = UserFactory(username="blockeduser")
        BlockFactory(blocker=self.user, blocked=blocked)
        response = self.client.get(self.url, {"q": "blockeduser"})
        usernames = [u["username"] for u in response.data["results"]]
        self.assertNotIn("blockeduser", usernames)
