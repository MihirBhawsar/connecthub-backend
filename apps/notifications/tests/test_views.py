"""
API view tests for the notifications app.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.tests.factories import UserFactory
from .factories import NotificationFactory


class NotificationListViewTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("notifications:list")

    def test_returns_own_notifications(self):
        NotificationFactory(recipient=self.user)
        NotificationFactory(recipient=self.user)
        # Notification for another user — should not appear
        NotificationFactory()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MarkAllReadViewTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("notifications:read-all")

    def test_marks_all_as_read(self):
        NotificationFactory(recipient=self.user, is_read=False)
        NotificationFactory(recipient=self.user, is_read=False)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["marked_read"], 2)


class UnreadCountViewTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("notifications:unread-count")

    def test_returns_correct_unread_count(self):
        NotificationFactory(recipient=self.user, is_read=False)
        NotificationFactory(recipient=self.user, is_read=False)
        NotificationFactory(recipient=self.user, is_read=True)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 2)
