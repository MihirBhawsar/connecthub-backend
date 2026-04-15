# ConnectHub — Claude Code Session Rules
## This file is read automatically by Claude Code on every session

---

## 🎯 Project Identity

**Project**: ConnectHub — Production Social Network REST API  
**Stack**: Django 4.2 + DRF + Channels + Celery + Redis + PostgreSQL + S3  
**Goal**: Resume-quality, interview-ready, production-grade codebase  
**Standard**: Senior Django engineer level — no shortcuts, no placeholders

---

## 📋 Before You Write Any Code

1. Read `DJANGO_BEST_PRACTICES.md` — every rule applies to every file
2. Read `TESTING_GUIDE.md` before writing any test
3. Check `CONNECTHUB_CLAUDE_CODE_PROMPT.md` for the exact spec of what you're building
4. If deploying or writing infra scripts, read `AWS_DEPLOYMENT.md`

---

## 🔁 Workflow Rules

### Git Branching & PR Workflow
- **Branch flow**: `feature/*` → `develop` → `main` (always via PR, never direct push)
- When user asks to push/deploy, follow this sequence:
  1. Commit changes on the current feature branch
  2. Push the feature branch to origin
  3. Create a PR from the feature branch → `develop`
  4. Once merged to `develop`, create a PR from `develop` → `main`
- Never push directly to `develop` or `main`
- Use `gh` CLI to create PRs (authenticated via token)

### When creating a new file
- Check if a similar file already exists first — never duplicate
- Always follow the exact app structure from `CONNECTHUB_CLAUDE_CODE_PROMPT.md`
- Register new models in `admin.py` immediately after creating them
- Add URL patterns to `config/urls.py` immediately after creating `urls.py`

### When editing an existing file
- Read the full file before making changes
- Never remove existing working code unless explicitly asked
- Preserve all existing imports at the top

### When you're unsure
- Look at existing similar files in the project for patterns
- Default to the pattern used in `apps/users/` as the reference implementation
- When in doubt between two approaches, pick the more explicit one

---

## 📁 File Naming Conventions

| What | Convention | Example |
|---|---|---|
| Apps | lowercase, singular | `users`, `posts` |
| Models | PascalCase, singular | `Post`, `Follow` |
| Serializers | ModelName + Serializer | `PostSerializer` |
| ViewSets | ModelName + ViewSet | `PostViewSet` |
| Tasks | snake_case verb | `generate_thumbnail` |
| Signals | notify_on_event | `notify_on_like` |
| Tests | test_what_it_tests | `test_follow_creates_notification` |
| URL names | app:action | `posts:list`, `users:profile` |

---

## 🔒 Hard Rules — Never Break These

1. **No `pass` or `# TODO`** in any file — complete every implementation
2. **No hardcoded secrets** — always `env('VAR_NAME')`
3. **No `fields = '__all__'`** in any serializer
4. **No raw SQL** unless there is no ORM equivalent (document why)
5. **No `print()`** — use `logger = logging.getLogger(__name__)`
6. **No bare `except:`** — always catch specific exception types
7. **No model instances in Celery task arguments** — pass PKs only
8. **No N+1 queries** — every list view must use `select_related`/`prefetch_related`
9. **Every endpoint has explicit `permission_classes`**
10. **Every delete endpoint returns `204 No Content`**

---

## 🧱 App Boundaries

- `apps/core/` — shared utilities only. No models. No business logic.
- `apps/users/` — user profiles, follow, block. No post logic here.
- `apps/posts/` — posts, likes, comments, hashtags, stories. No auth logic here.
- `apps/notifications/` — notification model + WebSocket consumer. Reads from other apps but never imports their views.
- Cross-app signals live in the app that **owns the triggering model** (e.g. like signal lives in `apps/posts/signals.py`)

---

## 📦 Import Order (enforce in every file)

```python
# 1. Standard library
import os
import logging
from datetime import timedelta

# 2. Django core
from django.db import models
from django.contrib.auth import get_user_model

# 3. Django REST Framework
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated

# 4. Third-party packages
import boto3
from celery import shared_task

# 5. Local apps (relative imports within same app, absolute for cross-app)
from apps.core.pagination import FeedCursorPagination
from .models import Post
from .serializers import PostSerializer
```

---

## 🗣️ Communication Style

- When starting a build session, list the files you plan to create/modify first
- After creating each file, print the file path and a one-line summary
- When you hit an error, explain what went wrong before fixing it
- When a design decision has tradeoffs, briefly note why you chose the approach
- After completing the full build, print a checklist of what was created

---

## 🔢 Environment

- Python: 3.11
- Django settings module: `config.settings.development` (local), `config.settings.production` (EC2)
- Database: PostgreSQL via `DATABASE_URL` env var (use `dj-database-url` or `django-environ`)
- Run server: `daphne -b 0.0.0.0 -p 8000 config.asgi:application` (not `runserver`)
- Migrations: always run `python manage.py makemigrations` after model changes
- Static files: `python manage.py collectstatic` before Docker build

---

## ✅ Definition of Done

A feature is only "done" when:
- [ ] Model created with all fields, Meta, `__str__`, indexes
- [ ] Migration created and applied
- [ ] Serializer with explicit fields and validation
- [ ] ViewSet with permissions, throttling, pagination, filtering
- [ ] URL registered in app `urls.py` AND in `config/urls.py`
- [ ] Registered in `admin.py`
- [ ] Signal/task wired up if async work needed
- [ ] At least one test written
- [ ] Swagger `@extend_schema` decorator added
