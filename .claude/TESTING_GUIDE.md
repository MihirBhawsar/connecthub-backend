# Testing Guide — ConnectHub
## Claude Code must follow this guide for every test written

---

## 🧰 Testing Stack

| Tool | Purpose |
|---|---|
| `pytest` + `pytest-django` | Test runner |
| `factory_boy` | Model factories (never use fixtures) |
| `faker` | Fake data generation |
| `unittest.mock` | Mock external services (S3, Celery, email) |
| `django.test.TestCase` | DB tests with rollback |
| `rest_framework.test.APIClient` | API endpoint testing |
| `channels.testing` | WebSocket consumer testing |
| `coverage` | Coverage reporting (target: 80%+) |

---

## 📁 Test File Structure

```
apps/users/tests/
├── __init__.py
├── factories.py        ← Model factories for this app
├── test_models.py      ← Unit tests for model methods, signals
├── test_serializers.py ← Serializer validation tests
├── test_views.py       ← API endpoint integration tests
└── test_tasks.py       ← Celery task tests (with mocks)

apps/posts/tests/
├── __init__.py
├── factories.py
├── test_models.py
├── test_serializers.py
├── test_views.py
├── test_tasks.py
└── test_filters.py

apps/notifications/tests/
├── __init__.py
├── factories.py
├── test_models.py
├── test_signals.py     ← Test that signals fire correctly
└── test_consumers.py   ← WebSocket tests
```

---

## 🏭 Factories (factory_boy) — Use These, Not Fixtures

### `apps/users/tests/factories.py`
```python
import factory
from faker import Faker
from django.contrib.auth import get_user_model
from apps.users.models import Follow, Block

fake = Faker()
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.LazyFunction(lambda: fake.unique.user_name())
    email = factory.LazyFunction(lambda: fake.unique.email())
    password = factory.PostGenerationMethodCall('set_password', 'testpassword123')
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    bio = factory.LazyFunction(fake.text)
    is_private = False


class PrivateUserFactory(UserFactory):
    is_private = True


class FollowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Follow

    follower = factory.SubFactory(UserFactory)
    following = factory.SubFactory(UserFactory)


class BlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Block

    blocker = factory.SubFactory(UserFactory)
    blocked = factory.SubFactory(UserFactory)
```

### `apps/posts/tests/factories.py`
```python
import factory
from faker import Faker
from apps.posts.models import Post, Like, Comment, Hashtag, Story
from apps.users.tests.factories import UserFactory

fake = Faker()


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    author = factory.SubFactory(UserFactory)
    caption = factory.LazyFunction(fake.text)
    media_type = 'text'
    is_public = True


class ImagePostFactory(PostFactory):
    media_type = 'image'


class LikeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Like

    user = factory.SubFactory(UserFactory)
    post = factory.SubFactory(PostFactory)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    author = factory.SubFactory(UserFactory)
    post = factory.SubFactory(PostFactory)
    body = factory.LazyFunction(fake.sentence)


class HashtagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hashtag

    name = factory.LazyFunction(lambda: fake.unique.word().lower())
```

---

## 📝 Test Naming Convention

```python
# Pattern: test_{method/action}_{condition}_{expected_result}

def test_follow_user_creates_follow_object():          ✅
def test_follow_already_followed_user_unfollows():     ✅
def test_create_post_unauthenticated_returns_401():    ✅
def test_like_post_increments_likes_count():           ✅
def test_delete_post_by_non_author_returns_403():      ✅

def test_post():    ❌ too vague
def test_api():     ❌ meaningless
```

---

## 🧪 Model Tests

```python
# apps/posts/tests/test_models.py
from django.test import TestCase
from apps.posts.tests.factories import PostFactory, LikeFactory


class PostModelTest(TestCase):

    def test_str_returns_expected_format(self):
        post = PostFactory(caption="Hello world")
        self.assertIn(str(post.author.username), str(post))

    def test_default_likes_count_is_zero(self):
        post = PostFactory()
        self.assertEqual(post.likes_count, 0)

    def test_post_ordering_newest_first(self):
        post1 = PostFactory()
        post2 = PostFactory()
        posts = list(Post.objects.all())
        self.assertEqual(posts[0], post2)  # newest first
```

---

## 🌐 API / View Tests

```python
# apps/posts/tests/test_views.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.tests.factories import UserFactory
from apps.posts.tests.factories import PostFactory


class PostCreateTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)  # Always use force_authenticate in tests
        self.url = reverse('posts:post-list')

    def test_create_text_post_returns_201(self):
        data = {'caption': 'Hello world', 'media_type': 'text'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['caption'], 'Hello world')
        self.assertEqual(response.data['author']['username'], self.user.username)

    def test_create_post_unauthenticated_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {'caption': 'test'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_feed_only_shows_followed_users_posts(self):
        followed = UserFactory()
        stranger = UserFactory()
        followed_post = PostFactory(author=followed)
        stranger_post = PostFactory(author=stranger)
        self.user.following.create(following=followed)

        response = self.client.get(reverse('posts:feed'))
        ids = [p['id'] for p in response.data['results']]

        self.assertIn(followed_post.id, ids)
        self.assertNotIn(stranger_post.id, ids)


class PostDeleteTest(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.post = PostFactory(author=self.user)

    def test_author_can_delete_own_post(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('posts:post-detail', kwargs={'pk': self.post.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_author_cannot_delete_post(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse('posts:post-detail', kwargs={'pk': self.post.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

---

## 📡 Signal Tests

```python
# apps/notifications/tests/test_signals.py
from django.test import TestCase
from apps.users.tests.factories import UserFactory
from apps.posts.tests.factories import PostFactory, LikeFactory
from apps.notifications.models import Notification


class LikeNotificationTest(TestCase):

    def test_like_creates_notification_for_post_author(self):
        author = UserFactory()
        liker = UserFactory()
        post = PostFactory(author=author)

        LikeFactory(user=liker, post=post)

        self.assertEqual(Notification.objects.filter(
            recipient=author,
            sender=liker,
            notification_type='like'
        ).count(), 1)

    def test_liking_own_post_does_not_create_notification(self):
        user = UserFactory()
        post = PostFactory(author=user)

        LikeFactory(user=user, post=post)

        self.assertEqual(Notification.objects.filter(recipient=user).count(), 0)
```

---

## ⚡ Celery Task Tests

```python
# apps/posts/tests/test_tasks.py
from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.posts.tasks import generate_thumbnail
from apps.posts.tests.factories import ImagePostFactory


class ThumbnailTaskTest(TestCase):

    @patch('apps.posts.tasks.default_storage')
    @patch('apps.posts.tasks.Image')
    def test_generate_thumbnail_updates_post(self, mock_image, mock_storage):
        """Thumbnail task should save thumbnail and update post"""
        post = ImagePostFactory()
        mock_img = MagicMock()
        mock_image.open.return_value.__enter__ = lambda s: mock_img
        mock_image.open.return_value.__exit__ = MagicMock(return_value=False)

        generate_thumbnail(post.id)

        post.refresh_from_db()
        # Assert thumbnail field was set (or mock_storage.save was called)
        mock_storage.save.assert_called_once()

    def test_generate_thumbnail_handles_deleted_post_gracefully(self):
        """If post is deleted before task runs, task should exit cleanly"""
        result = generate_thumbnail(999999)  # Non-existent ID
        self.assertIsNone(result)  # Should not raise
```

---

## 🔌 WebSocket Consumer Tests

```python
# apps/notifications/tests/test_consumers.py
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from django.test import TestCase
from config.asgi import application
from apps.users.tests.factories import UserFactory
import json


class NotificationConsumerTest(TestCase):

    async def test_authenticated_user_can_connect(self):
        user = await sync_to_async(UserFactory)()
        token = await sync_to_async(get_access_token)(user)

        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/?token={token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_unauthenticated_user_is_rejected(self):
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        connected, code = await communicator.connect()
        self.assertFalse(connected)
```

---

## 🎯 What to Test (Priority Order)

### Must test (P0 — blocking)
- Authentication: register, login, token refresh, logout
- Post CRUD: create, read, update, delete with ownership checks
- Follow/unfollow toggle logic
- Like/unlike toggle + counter accuracy
- Notification creation on like, comment, follow
- File type and size validation on upload

### Should test (P1 — important)
- Feed only shows followed users' posts
- Private account posts not visible to non-followers
- Blocked users excluded from feed and search
- Cursor pagination returns correct pages
- Search returns relevant results
- Rate limiting blocks excessive requests

### Nice to test (P2 — coverage)
- Celery tasks with mocked S3
- WebSocket connect/disconnect
- Story expiration logic
- Admin registrations work
- Serializer validation edge cases

---

## 🚫 Testing Anti-Patterns — Never Do These

```python
# ❌ NEVER — Creating users manually in tests
user = User.objects.create_user(username='testuser', password='pass')
# ✅ ALWAYS — Use factories
user = UserFactory()

# ❌ NEVER — Hardcoded URLs
response = self.client.get('/api/v1/posts/')
# ✅ ALWAYS — Use reverse()
response = self.client.get(reverse('posts:post-list'))

# ❌ NEVER — Testing implementation details
self.assertTrue(Post.objects._cache is not None)
# ✅ ALWAYS — Test behavior and outcomes
self.assertEqual(response.status_code, 201)

# ❌ NEVER — Making real S3/email/external calls in tests
# ✅ ALWAYS — Mock them
@patch('storages.backends.s3boto3.S3Boto3Storage.save')

# ❌ NEVER — Tests that depend on each other
# ✅ ALWAYS — Every test is fully independent (setUp creates fresh data)

# ❌ NEVER — Skipping the teardown (factories auto-clean with TestCase)
```

---

## ▶️ Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app
python manage.py test apps.posts

# Run specific test class
python manage.py test apps.posts.tests.test_views.PostCreateTest

# With coverage report
coverage run manage.py test
coverage report --fail-under=80
coverage html  # generates htmlcov/index.html

# Pytest style (if using pytest-django)
pytest
pytest apps/posts/
pytest -k "test_like"
pytest --cov=apps --cov-report=html
```

---

## ⚙️ pytest.ini / setup.cfg

```ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = config.settings.development
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*

[coverage:run]
source = apps
omit =
    */migrations/*
    */tests/*
    */admin.py

[coverage:report]
fail_under = 80
show_missing = True
```
