# ConnectHub — Command Reference

> **Global commands reference:** `~/.claude/command.md`
> This file contains project-specific commands. Where a command is shared/global, it is marked **[GLOBAL]**.

---

## 1. Project Overview

### Description
ConnectHub is a production-grade Instagram/Twitter-style social network REST API.
Features: JWT auth, user profiles, posts with media (image/video/audio), real-time WebSocket notifications,
Celery async tasks, hashtag feeds, full-text search, stories, rate limiting, and AWS S3 storage.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Framework | Django 4.2.16 + Django REST Framework 3.15.2 |
| Real-Time | Django Channels 4.1.0 + Daphne 4.1.2 (ASGI) |
| Task Queue | Celery 5.4.0 + Celery Beat + Flower |
| Database | PostgreSQL 15 |
| Cache / Broker | Redis 7-alpine |
| File Storage | AWS S3 (Boto3 + django-storages) |
| API Docs | Swagger / ReDoc (drf-spectacular) |
| Auth | JWT with token blacklisting (djangorestframework-simplejwt) |
| Server (Dev) | Daphne 4.1.2 (ASGI) |
| Server (Prod) | Gunicorn 23.0.0 + Nginx (host-managed) |
| Error Tracking | Sentry (production only) |
| Containerization | Docker Compose (separate dev + prod configs) |
| CI/CD | GitHub Actions (auto-deploy on push to `main`) |

---

## 2. Project Setup (Local Development)

### Clone the Repo

```bash
git clone https://github.com/MihirBhawsar/connecthub-backend.git
cd connecthub
```

### Environment Setup

```bash
# Copy the example env file
cp .env.example .env

# Open and fill in required values
nano .env
```

**Required variables in `.env`:**

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Random secret key (generate one) |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` |
| `DEBUG` | `True` for local dev |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `DATABASE_URL` | `postgres://user:pass@db:5432/dbname` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` |
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `AWS_STORAGE_BUCKET_NAME` | Your S3 bucket name |
| `AWS_S3_REGION_NAME` | e.g., `ap-south-1` |
| `EMAIL_HOST_USER` | SMTP email address |
| `EMAIL_HOST_PASSWORD` | SMTP email password |

### Dependencies (Docker handles this)

```bash
# First-time build — installs all dependencies inside Docker
cd ~/Project/Python/Project/connecthub
docker compose build
```

---

## 3. Run Project (Local) [GLOBAL]

```bash
cd ~/Project/Python/Project/connecthub

# First-time or after major changes
docker compose up -d --build

# Daily start (no rebuild needed)
docker compose up -d
```

**Services started:**
- `db` — PostgreSQL 15 (port 5432)
- `redis` — Redis 7 (port 6379)
- `web` — Daphne ASGI server (port 8000)
- `celery` — Celery worker (4 concurrent processes)
- `celery-beat` — Celery Beat scheduler
- `flower` — Celery monitoring UI (port 5555)

---

## 4. Stop Project [GLOBAL]

```bash
cd ~/Project/Python/Project/connecthub
docker compose down
```

---

## 5. Migrations [GLOBAL]

```bash
# Create new migration files (after model changes)
docker compose exec web python manage.py makemigrations

# Apply migrations to database
docker compose exec web python manage.py migrate
```

---

## 6. Create Superuser [GLOBAL]

```bash
docker compose exec web python manage.py createsuperuser
```

---

## 7. Logs [GLOBAL]

```bash
# Web server logs (Daphne/Django)
docker compose logs -f web

# Celery worker logs
docker compose logs -f celery

# Celery beat logs
docker compose logs -f celery-beat

# All containers
docker compose logs -f

# Last 100 lines of web logs
docker compose logs --tail=100 web
```

---

## 8. Access URLs (Local)

| Page | URL |
|------|-----|
| Swagger API Docs | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/redoc/ |
| Admin Panel | http://localhost:8000/admin/ |
| Health Check | http://localhost:8000/api/v1/health/ |
| Flower (Celery Monitor) | http://localhost:5555 |
| WebSocket | `ws://localhost:8000/ws/notifications/?token=<access_token>` |

---

## 9. EC2 Server Access [GLOBAL]

```bash
# SSH into EC2
ssh mihir-ec2

# Navigate to the project directory
cd /var/www/connecthub
```

> `mihir-ec2` is an SSH alias. Make sure it is configured in `~/.ssh/config`.
> Full SSH patterns are available in `~/.claude/command.md`.

---

## 10. Run Project on Server [GLOBAL]

```bash
ssh mihir-ec2
cd /var/www/connecthub

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
```

---

## 11. Stop Project on Server [GLOBAL]

```bash
ssh mihir-ec2
cd /var/www/connecthub
docker compose -f docker-compose.prod.yml down
```

---

## 12. Migrations on Server [GLOBAL]

```bash
ssh mihir-ec2
cd /var/www/connecthub
docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate
```

---

## 13. Logs on Server [GLOBAL]

```bash
ssh mihir-ec2
cd /var/www/connecthub

# Web server logs
docker compose -f docker-compose.prod.yml logs -f web

# Celery logs
docker compose -f docker-compose.prod.yml logs -f celery

# All services logs
docker compose -f docker-compose.prod.yml logs -f

# Last 200 lines
docker compose -f docker-compose.prod.yml logs --tail=200 web
```

---

## 14. Restart Project

### Local Restart

```bash
cd ~/Project/Python/Project/connecthub
docker compose restart
```

### Restart a Single Container (Local)

```bash
docker compose restart web
docker compose restart celery
```

### Server — Manual Deploy + Restart [GLOBAL]

```bash
ssh mihir-ec2
cd /var/www/connecthub
git pull origin main
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

### Auto Deploy via GitHub Actions [GLOBAL]

```bash
git add .
git commit -m "your message"
git push origin main
# GitHub Actions → EC2 auto deploy
```

> Monitor CI/CD: https://github.com/MihirBhawsar/connecthub-backend/actions

---

## Extra / Utility Commands [PROJECT-SPECIFIC]

```bash
# Django shell (interactive)
docker compose exec web python manage.py shell

# Run tests
docker compose exec web python manage.py test

# Check container resource usage
docker stats

# Disk usage check (if space issues)
df -h /
docker system df

# Clean unused Docker resources (careful!)
docker system prune -af
```

---

## Server Access URLs

| Page | URL |
|------|-----|
| Swagger API Docs | http://13.63.167.53:8001/api/docs/ |
| ReDoc | http://13.63.167.53:8001/api/redoc/ |
| Admin Panel | http://13.63.167.53:8001/admin/ |
| Health Check | http://13.63.167.53:8001/api/v1/health/ |

---

## Quick Reference

| Task | Command |
|------|---------|
| First-time setup | `docker compose up -d --build` |
| Daily start | `docker compose up -d` |
| Stop | `docker compose down` |
| Migrations | `docker compose exec web python manage.py migrate` |
| Superuser | `docker compose exec web python manage.py createsuperuser` |
| Logs (web) | `docker compose logs -f web` |
| Logs (celery) | `docker compose logs -f celery` |
| SSH to server | `ssh mihir-ec2` |
| Server deploy | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |
| Server logs | `docker compose -f docker-compose.prod.yml logs -f web` |
