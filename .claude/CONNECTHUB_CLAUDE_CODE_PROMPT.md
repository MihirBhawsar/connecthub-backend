# ConnectHub — Social Network API
## Master Build Prompt for Claude Code

> **How to use this file:**
> Open this file in VS Code, then open Claude Code terminal and paste:
> `Read the file CONNECTHUB_CLAUDE_CODE_PROMPT.md and build the entire project exactly as described. Start from scratch, create every file, install all dependencies, and confirm when done.`

---

## 🎯 Project Overview

Build a **production-grade Instagram/Twitter-style Social Network REST API** called **ConnectHub**.

This is NOT a tutorial project. Every decision must reflect real-world engineering:
- Scalable architecture
- Security best practices
- Async-first design
- Production Docker setup
- AWS-ready deployment

---

## 🏗️ Tech Stack (Exact Versions)

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | Django 4.2 + Django REST Framework 3.15 |
| Auth | SimpleJWT (JWT access + refresh tokens) |
| Database | PostgreSQL 15 |
| Cache + Broker | Redis 7 |
| Async Tasks | Celery 5 + Celery Beat |
| Real-time | Django Channels 4 + Daphne |
| File Storage | AWS S3 via django-storages + boto3 |
| Thumbnails | Pillow |
| Search | PostgreSQL Full-Text Search (django.contrib.postgres) |
| API Docs | drf-spectacular (Swagger + ReDoc) |
| Rate Limiting | django-ratelimit |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Deployment | AWS EC2 + Nginx + Gunicorn/Daphne |

---

## 📁 Exact Project Structure to Create

```
connecthub/
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── apps/
│   ├── __init__.py
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── signals.py
│   │   ├── tasks.py
│   │   └── permissions.py
│   ├── posts/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── signals.py
│   │   ├── tasks.py
│   │   └── filters.py
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── consumers.py        ← WebSocket consumer
│   └── core/
│       ├── __init__.py
│       ├── pagination.py
│       ├── throttling.py
│       ├── exceptions.py
│       └── utils.py
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py                 ← Channels routing
│   └── celery.py
├── nginx/
│   ├── nginx.conf
│   └── Dockerfile
├── scripts/
│   ├── entrypoint.sh
│   └── start-celery.sh
├── .env.example
├── .env                        ← Do not commit (in .gitignore)
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── README.md
```

---

## 🗄️ Database Models

### `apps/users/models.py`

```python
# User model extending AbstractUser
class User(AbstractUser):
    bio = TextField(blank=True)
    avatar = ImageField(upload_to='avatars/', blank=True, null=True)  # stored on S3
    website = URLField(blank=True)
    is_private = BooleanField(default=False)
    is_verified = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

class Follow(Model):
    follower = ForeignKey(User, related_name='following', on_delete=CASCADE)
    following = ForeignKey(User, related_name='followers', on_delete=CASCADE)
    created_at = DateTimeField(auto_now_add=True)
    # Unique together: (follower, following)

class Block(Model):
    blocker = ForeignKey(User, related_name='blocking', on_delete=CASCADE)
    blocked = ForeignKey(User, related_name='blocked_by', on_delete=CASCADE)
    created_at = DateTimeField(auto_now_add=True)
```

### `apps/posts/models.py`

```python
class Post(Model):
    MEDIA_TYPES = [('image', 'Image'), ('video', 'Video'), ('audio', 'Audio'), ('text', 'Text')]
    
    author = ForeignKey(User, related_name='posts', on_delete=CASCADE)
    caption = TextField(max_length=2200, blank=True)
    media_file = FileField(upload_to='posts/', blank=True, null=True)   # S3
    media_type = CharField(choices=MEDIA_TYPES, default='text')
    thumbnail = ImageField(upload_to='thumbnails/', blank=True, null=True)  # S3, auto-generated
    is_public = BooleanField(default=True)
    likes_count = PositiveIntegerField(default=0)    # denormalized counter
    comments_count = PositiveIntegerField(default=0) # denormalized counter
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    # PostgreSQL full-text search
    search_vector = SearchVectorField(null=True)

class Like(Model):
    user = ForeignKey(User, on_delete=CASCADE)
    post = ForeignKey(Post, related_name='likes', on_delete=CASCADE)
    created_at = DateTimeField(auto_now_add=True)

class Comment(Model):
    author = ForeignKey(User, related_name='comments', on_delete=CASCADE)
    post = ForeignKey(Post, related_name='comments', on_delete=CASCADE)
    parent = ForeignKey('self', null=True, blank=True, on_delete=CASCADE)  # nested replies
    body = TextField(max_length=500)
    created_at = DateTimeField(auto_now_add=True)

class Hashtag(Model):
    name = CharField(max_length=100, unique=True)
    posts = ManyToManyField(Post, related_name='hashtags', blank=True)

class Story(Model):
    author = ForeignKey(User, related_name='stories', on_delete=CASCADE)
    media_file = FileField(upload_to='stories/')   # S3
    media_type = CharField(choices=[('image','Image'),('video','Video')])
    expires_at = DateTimeField()   # 24 hours from created_at
    created_at = DateTimeField(auto_now_add=True)
```

### `apps/notifications/models.py`

```python
class Notification(Model):
    TYPES = [
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
        ('mention', 'Mention'),
        ('reply', 'Reply'),
    ]
    recipient = ForeignKey(User, related_name='notifications', on_delete=CASCADE)
    sender = ForeignKey(User, related_name='sent_notifications', on_delete=CASCADE)
    notification_type = CharField(choices=TYPES, max_length=20)
    post = ForeignKey(Post, null=True, blank=True, on_delete=SET_NULL)
    is_read = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
```

---

## 🔌 API Endpoints

### Auth (`/api/v1/auth/`)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/register/` | Register new user |
| POST | `/login/` | Get JWT access + refresh token |
| POST | `/token/refresh/` | Refresh access token |
| POST | `/logout/` | Blacklist refresh token |
| POST | `/password/change/` | Change password (authenticated) |
| POST | `/password/reset/` | Request password reset email |
| POST | `/password/reset/confirm/` | Confirm reset with token |

### Users (`/api/v1/users/`)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/me/` | Get own profile |
| PATCH | `/me/` | Update profile (avatar upload) |
| GET | `/{username}/` | Get public profile |
| POST | `/{username}/follow/` | Follow / unfollow toggle |
| GET | `/{username}/followers/` | List followers (paginated) |
| GET | `/{username}/following/` | List following (paginated) |
| POST | `/{username}/block/` | Block / unblock toggle |
| GET | `/search/?q=` | Search users by username/name |
| GET | `/suggestions/` | Follow suggestions (not following yet) |

### Posts (`/api/v1/posts/`)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Home feed (paginated, cursor-based) |
| POST | `/` | Create post (with optional media file) |
| GET | `/{id}/` | Get post detail |
| PATCH | `/{id}/` | Update post (author only) |
| DELETE | `/{id}/` | Delete post (author only) |
| POST | `/{id}/like/` | Like / unlike toggle |
| GET | `/{id}/likes/` | List users who liked |
| POST | `/{id}/comments/` | Add comment |
| GET | `/{id}/comments/` | List comments (with nested replies) |
| DELETE | `/comments/{id}/` | Delete comment (author only) |
| GET | `/explore/` | Trending / public posts |
| GET | `/hashtag/{name}/` | Posts by hashtag |
| GET | `/search/?q=` | Full-text search posts |

### Stories (`/api/v1/stories/`)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Stories feed (only from followed users) |
| POST | `/` | Create story (auto-expires 24h) |
| DELETE | `/{id}/` | Delete own story |

### Notifications (`/api/v1/notifications/`)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | List all notifications (paginated) |
| POST | `/read-all/` | Mark all as read |
| PATCH | `/{id}/read/` | Mark single as read |
| GET | `/unread-count/` | Get count of unread |

### WebSocket (`ws://`)
| URL | Description |
|---|---|
| `ws/notifications/` | Real-time notification stream (authenticated) |

---

## ⚙️ Core Implementation Details

### 1. JWT Authentication (SimpleJWT)

```python
# config/settings/base.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### 2. S3 File Storage (django-storages)

```python
# config/settings/base.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='ap-south-1')
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'private'
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_QUERYSTRING_AUTH = True          # presigned URLs
AWS_QUERYSTRING_EXPIRE = 3600        # 1 hour expiry
```

### 3. Celery Tasks

```python
# apps/posts/tasks.py

@shared_task(bind=True, max_retries=3)
def generate_thumbnail(self, post_id):
    """Generate thumbnail for image/video posts after upload"""
    # For images: resize to 400x400 using Pillow
    # For videos: extract first frame using imageio or ffmpeg subprocess
    # Save thumbnail back to S3
    # Update post.thumbnail field

@shared_task
def expire_stories():
    """Celery Beat periodic task — runs every 15 mins"""
    Story.objects.filter(expires_at__lte=timezone.now()).delete()

@shared_task
def send_notification_email(user_id, notification_type, sender_username):
    """Send email notification via Django email backend"""
```

```python
# config/celery.py
app.conf.beat_schedule = {
    'expire-stories': {
        'task': 'apps.posts.tasks.expire_stories',
        'schedule': crontab(minute='*/15'),
    },
}
```

### 4. Django Channels WebSocket

```python
# apps/notifications/consumers.py
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Authenticate via JWT token in query string
        # Add to user-specific group: f"notifications_{user_id}"
        # Accept connection

    async def disconnect(self, close_code):
        # Leave group

    async def receive(self, text_data):
        # Handle ping/pong keepalive

    async def send_notification(self, event):
        # Called by Celery when new notification created
        # Push JSON payload to WebSocket client
```

```python
# config/asgi.py
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

### 5. Feed Algorithm (Redis Cache)

```python
# apps/posts/views.py — FeedView
class FeedView(ListAPIView):
    """
    Cursor-based paginated home feed.
    Shows posts from followed users ordered by created_at DESC.
    Cache per-user feed in Redis for 5 minutes.
    On cache miss: query DB, cache result.
    Invalidate cache on new post from followed user (via signal).
    """
    pagination_class = CursorPagination
    
    def get_queryset(self):
        cache_key = f"feed:{self.request.user.id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        following_ids = self.request.user.following.values_list('following_id', flat=True)
        qs = Post.objects.filter(
            author_id__in=following_ids,
            is_public=True
        ).select_related('author').prefetch_related('hashtags').order_by('-created_at')
        cache.set(cache_key, qs, timeout=300)
        return qs
```

### 6. Notification System (Signals + Channels + Celery)

```python
# apps/posts/signals.py
@receiver(post_save, sender=Like)
def notify_on_like(sender, instance, created, **kwargs):
    if created and instance.user != instance.post.author:
        notification = Notification.objects.create(
            recipient=instance.post.author,
            sender=instance.user,
            notification_type='like',
            post=instance.post
        )
        # Push to WebSocket via Channels layer
        async_to_sync(channel_layer.group_send)(
            f"notifications_{instance.post.author.id}",
            {"type": "send_notification", "data": NotificationSerializer(notification).data}
        )
```

### 7. Pagination

```python
# apps/core/pagination.py
class FeedCursorPagination(CursorPagination):
    """Cursor-based for feed — prevents duplicate items on new inserts"""
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'

class StandardPagePagination(PageNumberPagination):
    """Page-number for followers/following lists"""
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100
```

### 8. Rate Limiting / Throttling

```python
# apps/core/throttling.py
class AuthRateThrottle(UserRateThrottle):
    rate = '1000/day'

class PostCreateThrottle(UserRateThrottle):
    rate = '50/hour'

class AnonRateThrottle(AnonRateThrottle):
    rate = '100/hour'

# Apply per-view:
# throttle_classes = [PostCreateThrottle]
```

### 9. Search

```python
# apps/posts/filters.py
class PostFilter(FilterSet):
    """django-filter for posts"""
    author = CharFilter(field_name='author__username')
    media_type = ChoiceFilter(choices=Post.MEDIA_TYPES)
    from_date = DateFilter(field_name='created_at', lookup_expr='gte')
    to_date = DateFilter(field_name='created_at', lookup_expr='lte')

# Full-text search in PostViewSet:
# Post.objects.annotate(search=SearchVector('caption')).filter(search=query)
```

---

## 🐳 Docker Setup

### `Dockerfile`
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt
COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .
RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["scripts/entrypoint.sh"]
```

### `docker-compose.yml` (Development)
```yaml
version: '3.9'

services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: connecthub
      POSTGRES_USER: connecthub_user
      POSTGRES_PASSWORD: connecthub_pass
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 config.asgi:application
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A config.celery worker --loglevel=info --concurrency=4
    volumes:
      - .:/app
    env_file: .env
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    env_file: .env
    depends_on:
      - db
      - redis

  flower:
    build: .
    command: celery -A config.celery flower --port=5555
    ports:
      - "5555:5555"
    env_file: .env
    depends_on:
      - redis

volumes:
  postgres_data:
```

### `docker-compose.prod.yml` (Production)
```yaml
# Same as above but:
# - No volume mounts (code baked into image)
# - Nginx service added
# - Gunicorn for HTTP, Daphne for WebSocket
# - No Flower exposed publicly
# - SSL termination at Nginx
```

---

## 🌐 Nginx Config

### `nginx/nginx.conf`
```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location /ws/ {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_redirect off;
    }
}
```

---

## 🔐 Environment Variables

### `.env.example`
```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=config.settings.development
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://connecthub_user:connecthub_pass@db:5432/connecthub

# Redis
REDIS_URL=redis://redis:6379/0

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=connecthub-media
AWS_S3_REGION_NAME=ap-south-1

# Email (for password reset / notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=ConnectHub <your@gmail.com>

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

---

## 🚀 GitHub Actions CI/CD

### `.github/workflows/ci-cd.yml`
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_connecthub
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: --health-cmd "redis-cli ping" --health-interval 10s

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements/development.txt
      - name: Run migrations
        run: python manage.py migrate
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test_connecthub
          DJANGO_SETTINGS_MODULE: config.settings.development
          DJANGO_SECRET_KEY: test-secret-key
      - name: Run tests
        run: python manage.py test --verbosity=2
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test_connecthub
          DJANGO_SETTINGS_MODULE: config.settings.development
          DJANGO_SECRET_KEY: test-secret-key

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to EC2
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ubuntu
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /home/ubuntu/connecthub
            git pull origin main
            docker compose -f docker-compose.prod.yml build
            docker compose -f docker-compose.prod.yml up -d
            docker compose -f docker-compose.prod.yml exec web python manage.py migrate
            docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

---

## 📦 Requirements Files

### `requirements/base.txt`
```
django==4.2.16
djangorestframework==3.15.2
djangorestframework-simplejwt==5.3.1
django-channels==4.1.0
channels-redis==4.2.0
daphne==4.1.2
celery==5.4.0
django-celery-beat==2.6.0
redis==5.0.8
django-storages==1.14.4
boto3==1.35.0
Pillow==10.4.0
psycopg2-binary==2.9.9
drf-spectacular==0.27.2
django-filter==24.3
django-ratelimit==4.1.0
django-environ==0.11.2
django-cors-headers==4.4.0
djangorestframework-camel-case==1.4.2
```

### `requirements/development.txt`
```
-r base.txt
django-debug-toolbar==4.4.6
pytest-django==4.9.0
factory-boy==3.3.1
faker==30.0.0
coverage==7.6.1
ipython==8.27.0
```

### `requirements/production.txt`
```
-r base.txt
gunicorn==23.0.0
sentry-sdk==2.14.0
django-redis==5.4.0
```

---

## 🧪 Tests to Write

Create tests in each app's `tests/` directory:

```
apps/users/tests/
├── test_models.py      ← Follow/block logic
├── test_auth.py        ← JWT register/login/refresh
├── test_views.py       ← Profile, follow, search endpoints
apps/posts/tests/
├── test_models.py      ← Post creation, like counter signals
├── test_views.py       ← CRUD, feed, search
├── test_tasks.py       ← Celery thumbnail task (mock S3)
apps/notifications/tests/
├── test_signals.py     ← Notification created on like/follow
├── test_consumers.py   ← WebSocket connect/auth
```

---

## 📖 API Documentation

Configure drf-spectacular in `config/settings/base.py`:

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'ConnectHub API',
    'DESCRIPTION': 'Production-grade social network REST API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': ['Auth', 'Users', 'Posts', 'Stories', 'Notifications'],
}

# URLs in config/urls.py:
# /api/schema/          ← Raw OpenAPI schema
# /api/docs/            ← Swagger UI
# /api/redoc/           ← ReDoc UI
```

Decorate every ViewSet with `@extend_schema` tags and response examples.

---

## 🛡️ Security Checklist

Implement all of these:

- [ ] `SECURE_SSL_REDIRECT = True` in production
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] JWT refresh token rotation + blacklisting
- [ ] `django-cors-headers` with explicit `CORS_ALLOWED_ORIGINS`
- [ ] File type validation on upload (not just extension — check magic bytes)
- [ ] Max file size enforcement: images 10MB, videos 500MB, audio 50MB
- [ ] Rate limiting on auth endpoints (stricter: 5/min on login)
- [ ] Block users excluded from all queries automatically
- [ ] Private account posts only visible to followers
- [ ] Users can only edit/delete their own content (object-level permissions)

---

## 🔑 Key Engineering Decisions to Document

Write a `ARCHITECTURE.md` explaining:

1. **Why cursor-based pagination for feed** — not page numbers (avoids duplicate items when new posts arrive)
2. **Why denormalized counters** (`likes_count`, `comments_count`) — avoids expensive COUNT queries on hot paths
3. **Why Redis for feed cache** — PostgreSQL query on large follower graphs is slow; cache fan-out per user
4. **Why Celery for thumbnails** — never block the HTTP request/response cycle with image processing
5. **Why Channels + Redis channel layer** — enables horizontal scaling of WebSocket servers
6. **Why S3 presigned URLs** — never proxy media through Django; let clients download directly from S3

---

## 🚀 AWS EC2 Deployment Steps

Document in `README.md`:

```bash
# 1. Launch EC2 (Ubuntu 22.04, t3.small minimum)
# 2. Install Docker + Docker Compose
# 3. Clone repo, copy .env file
# 4. Create S3 bucket, set CORS policy
# 5. Create RDS PostgreSQL (or use Docker postgres for start)
# 6. Configure security groups: 80, 443, 22 inbound
# 7. Run:
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
# 8. Point domain → EC2 public IP
# 9. Set up SSL with Let's Encrypt + Certbot
```

---

## ✅ Build Order for Claude Code

Build in this exact sequence to avoid import errors:

1. `requirements/` files → install all dependencies
2. `config/settings/base.py` → core settings
3. `config/settings/development.py` + `production.py`
4. `config/celery.py` → Celery app init
5. `apps/core/` → pagination, throttling, exceptions, utils
6. `apps/users/models.py` → User, Follow, Block
7. `apps/users/` → serializers, views, urls, signals, tasks, permissions
8. `apps/posts/models.py` → Post, Like, Comment, Hashtag, Story
9. `apps/posts/` → serializers, views, urls, signals, tasks, filters
10. `apps/notifications/models.py` → Notification
11. `apps/notifications/consumers.py` → WebSocket consumer
12. `apps/notifications/` → serializers, views, urls
13. `config/asgi.py` → Channels routing
14. `config/urls.py` → all URL includes + Swagger
15. `Dockerfile` + `docker-compose.yml`
16. `nginx/nginx.conf`
17. `scripts/entrypoint.sh`
18. `.env.example` + `.gitignore`
19. `tests/` in each app
20. `.github/workflows/ci-cd.yml`
21. `README.md` + `ARCHITECTURE.md`

---

## 📝 README.md Must Include

- Project description + feature list
- Architecture diagram (ASCII or text)
- Local setup with Docker (3 commands to run)
- API endpoint reference table
- Environment variables table
- How to run tests
- How to deploy to EC2
- Tech stack badges

---

## 🎯 Final Instruction to Claude Code

> Build every file listed above completely — no placeholders, no `# TODO`, no `pass` statements.
> Every model, serializer, view, URL, task, consumer, signal, and config must be fully implemented.
> Use `django-environ` to read all secrets from `.env`.
> Add docstrings to every class and complex method.
> The project must start successfully with `docker compose up` after filling in `.env`.
