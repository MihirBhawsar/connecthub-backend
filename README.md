# ConnectHub

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![DRF](https://img.shields.io/badge/DRF-3.15-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Redis](https://img.shields.io/badge/Redis-7-red)
![Celery](https://img.shields.io/badge/Celery-5-green)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

**ConnectHub** is a production-grade Instagram/Twitter-style social network REST API.
Built with Django 4.2, Django REST Framework, Django Channels (WebSocket), Celery, Redis, PostgreSQL, and AWS S3.

---

## Features

- JWT authentication (access + refresh tokens, blacklisting on logout)
- User profiles, follow/unfollow, block/unblock
- Posts with image/video/audio/text media (stored on S3)
- Automatic thumbnail generation via Celery + Pillow/ffmpeg
- Like/unlike and comment/reply on posts
- Hashtag extraction and hashtag feed
- PostgreSQL full-text search on post captions
- Real-time notifications via WebSocket (Django Channels + Redis)
- Email notifications via Celery tasks
- 24-hour expiring Stories
- Home feed with cursor-based pagination and Redis caching
- Explore page (trending posts by likes)
- Rate limiting on all endpoints (stricter on auth)
- Swagger UI + ReDoc API documentation
- Docker Compose (dev + production)
- GitHub Actions CI/CD (test + deploy to EC2)

---

## Architecture

```
Client
  │
  ▼
Nginx (TLS)
  ├── /ws/*  →  Daphne → Django Channels → Redis
  └── /api/* →  Daphne → Django → PostgreSQL / Redis / S3

Background
  Celery Worker → thumbnail generation, emails
  Celery Beat   → expire stories every 15 min
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design decisions.

---

## Local Setup (3 commands)

```bash
# 1. Copy and fill in environment variables
cp .env.example .env
# Edit .env — at minimum set DJANGO_SECRET_KEY and DATABASE_URL

# 2. Start all services
docker compose up -d --build

# 3. Create a superuser
docker compose exec web python manage.py createsuperuser
```

Visit: `http://localhost:8000/api/docs/` for the Swagger UI.

---

## API Endpoint Reference

### Auth — `/api/v1/auth/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register/` | Register new user — returns JWT tokens |
| POST | `/login/` | Login — returns JWT access + refresh |
| POST | `/token/refresh/` | Refresh access token |
| POST | `/logout/` | Blacklist refresh token |
| POST | `/password/change/` | Change password (authenticated) |

### Users — `/api/v1/users/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me/` | Get own profile |
| PATCH | `/me/` | Update profile (avatar, bio, etc.) |
| GET | `/{username}/` | Get public profile |
| POST | `/{username}/follow/` | Follow / unfollow toggle |
| GET | `/{username}/followers/` | List followers (paginated) |
| GET | `/{username}/following/` | List following (paginated) |
| POST | `/{username}/block/` | Block / unblock toggle |
| GET | `/search/?q=` | Search users by username/name |
| GET | `/suggestions/` | Follow suggestions |

### Posts — `/api/v1/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/posts/` | Home feed (cursor-paginated) |
| GET | `/posts/all/` | List all public posts (filterable) |
| POST | `/posts/all/` | Create a post |
| GET | `/posts/{id}/` | Get post detail |
| PATCH | `/posts/{id}/` | Update post (author only) |
| DELETE | `/posts/{id}/` | Delete post (author only) — 204 |
| POST | `/posts/{id}/like/` | Like / unlike toggle |
| GET | `/posts/{id}/likes/` | List users who liked |
| GET | `/posts/{id}/comments/` | List comments + replies |
| POST | `/posts/{id}/comments/` | Add comment |
| DELETE | `/posts/comments/{id}/` | Delete comment (author only) — 204 |
| GET | `/posts/explore/` | Trending public posts |
| GET | `/posts/hashtag/{name}/` | Posts by hashtag |
| GET | `/posts/search/?q=` | Full-text search |

### Stories — `/api/v1/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stories/` | Stories feed (followed users, active only) |
| POST | `/stories/create/` | Create story (auto-expires 24h) |
| DELETE | `/stories/{id}/` | Delete own story — 204 |

### Notifications — `/api/v1/notifications/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all notifications (paginated) |
| POST | `/read-all/` | Mark all as read |
| PATCH | `/{id}/read/` | Mark single as read |
| GET | `/unread-count/` | Get unread count |

### WebSocket

| URL | Description |
|-----|-------------|
| `ws://host/ws/notifications/?token=<access_token>` | Real-time notification stream |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SECRET_KEY` | Yes | Django secret key |
| `DJANGO_SETTINGS_MODULE` | Yes | `config.settings.development` or `production` |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis URL for cache |
| `CELERY_BROKER_URL` | Yes | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | Yes | Redis URL for task results |
| `AWS_ACCESS_KEY_ID` | Yes (prod) | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Yes (prod) | IAM user secret key |
| `AWS_STORAGE_BUCKET_NAME` | Yes (prod) | S3 bucket name |
| `AWS_S3_REGION_NAME` | No | Default: `ap-south-1` |
| `EMAIL_HOST_USER` | No | SMTP username |
| `EMAIL_HOST_PASSWORD` | No | SMTP password |
| `SENTRY_DSN` | No | Sentry error tracking DSN |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated allowed origins |

---

## Running Tests

```bash
# Run all tests
docker compose exec web python manage.py test

# Run a specific app
docker compose exec web python manage.py test apps.posts

# With coverage
docker compose exec web bash -c "coverage run manage.py test && coverage report"

# Or outside Docker (with venv active)
python manage.py test --verbosity=2
pytest
```

---

## Deploy to AWS EC2

### 1. Launch infrastructure

```bash
# Launch EC2 Ubuntu 22.04 (t3.small minimum)
# Attach Elastic IP
# Configure Security Group: 22, 80, 443 inbound
# Launch RDS PostgreSQL 15 (t3.micro) or use Docker postgres
# Create S3 bucket: connecthub-media-yourname in ap-south-1
# Create IAM user with S3FullAccess (scoped to bucket)
```

### 2. Set up EC2

```bash
# Upload and run the setup script
scp scripts/ec2-setup.sh ubuntu@EC2_IP:~/
ssh ubuntu@EC2_IP "bash ec2-setup.sh"

# Upload production .env
scp .env ubuntu@EC2_IP:/home/ubuntu/connecthub/.env
```

### 3. Start the stack

```bash
ssh ubuntu@EC2_IP

cd /home/ubuntu/connecthub
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 4. Configure SSL with Certbot

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 5. Point your domain

Set an A record pointing `yourdomain.com` to your EC2 Elastic IP.

---

## Celery Monitoring (Flower)

Flower is available at port 5555 in development: `http://localhost:5555`

In production, access it via SSH tunnel only (never expose port 5555 publicly):

```bash
ssh -L 5555:localhost:5555 -i your-key.pem ubuntu@EC2_IP
# Then open http://localhost:5555 in your browser
```

---

## Security Notes

- JWT tokens should be stored in `httpOnly` cookies on the client — never in `localStorage`.
- All S3 files are private; access is via presigned URLs with 1-hour expiry.
- File uploads are validated by MIME type (magic bytes), not just extension.
- Rate limits: 5 login attempts/min, 50 posts/hour, 1000 general requests/day.
- Production settings enable HSTS, SSL redirect, secure cookies, and XSS headers.
