"""
JWT authentication endpoint tests for ConnectHub.

Covers: register, login, token refresh, logout, password change.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import UserFactory


class RegisterViewTest(APITestCase):
    """POST /api/v1/auth/register/"""

    def setUp(self):
        self.url = reverse("users:register")
        self.valid_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password2": "SecurePass123!",
        }

    def test_valid_registration_returns_201_with_tokens(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "newuser")

    def test_registration_with_duplicate_username_returns_400(self):
        UserFactory(username="newuser")
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_duplicate_email_returns_400(self):
        UserFactory(email="newuser@example.com")
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_mismatched_passwords_returns_400(self):
        data = {**self.valid_data, "password2": "DifferentPass!"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_missing_fields_returns_400(self):
        response = self.client.post(self.url, {"username": "newuser"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_does_not_require_authentication(self):
        """Register endpoint must be public (AllowAny)."""
        response = self.client.post(self.url, self.valid_data)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginViewTest(APITestCase):
    """POST /api/v1/auth/login/"""

    def setUp(self):
        self.url = reverse("users:login")
        # UserFactory uses skip_postgeneration_save=True, so set_password is called
        # but not persisted. Save explicitly so the hashed password reaches the DB.
        self.user = UserFactory()
        self.user.set_password("testpassword123")
        self.user.save()

    def test_valid_credentials_returns_200_with_tokens(self):
        response = self.client.post(
            self.url,
            {"username": self.user.username, "password": "testpassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_wrong_password_returns_401(self):
        response = self.client.post(
            self.url,
            {"username": self.user.username, "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_returns_401(self):
        response = self.client.post(
            self.url,
            {"username": "nobody", "password": "testpassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_credentials_returns_400(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url,
            {"username": self.user.username, "password": "testpassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshViewTest(APITestCase):
    """POST /api/v1/auth/token/refresh/"""

    def setUp(self):
        self.url = reverse("users:token_refresh")
        self.user = UserFactory()
        self.refresh = str(RefreshToken.for_user(self.user))

    def test_valid_refresh_token_returns_new_access_token(self):
        response = self.client.post(self.url, {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_invalid_refresh_token_returns_401(self):
        response = self.client.post(self.url, {"refresh": "not.a.valid.token"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_token_returns_400(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutViewTest(APITestCase):
    """POST /api/v1/auth/logout/"""

    def setUp(self):
        self.url = reverse("users:logout")
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.refresh = str(RefreshToken.for_user(self.user))

    def test_valid_logout_blacklists_token_and_returns_204(self):
        response = self.client.post(self.url, {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_blacklisted_token_cannot_be_used_again(self):
        self.client.post(self.url, {"refresh": self.refresh})
        # Attempting to use the same refresh token again should fail
        response = self.client.post(reverse("users:token_refresh"), {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_token_returns_400(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_with_invalid_token_returns_400(self):
        response = self.client.post(self.url, {"refresh": "bad.token.here"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_logout_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordViewTest(APITestCase):
    """POST /api/v1/auth/password/change/"""

    def setUp(self):
        self.url = reverse("users:password_change")
        self.user = UserFactory()
        self.user.set_password("testpassword123")
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_valid_password_change_returns_200(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "testpassword123",
                "new_password": "NewSecurePass456!",
                "new_password2": "NewSecurePass456!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_changed_password_works_on_login(self):
        self.client.post(
            self.url,
            {
                "old_password": "testpassword123",
                "new_password": "NewSecurePass456!",
                "new_password2": "NewSecurePass456!",
            },
        )
        self.client.force_authenticate(user=None)
        response = self.client.post(
            reverse("users:login"),
            {"username": self.user.username, "password": "NewSecurePass456!"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_wrong_old_password_returns_400(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "wrongpassword",
                "new_password": "NewSecurePass456!",
                "new_password2": "NewSecurePass456!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mismatched_new_passwords_returns_400(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "testpassword123",
                "new_password": "NewSecurePass456!",
                "new_password2": "DifferentPass789!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url,
            {
                "old_password": "testpassword123",
                "new_password": "NewSecurePass456!",
                "new_password2": "NewSecurePass456!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
