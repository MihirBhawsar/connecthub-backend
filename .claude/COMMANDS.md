# ConnectHub — Commands Reference

> All commands run from the project root (`~/Project/Python/Project/connecthub`).
> The `WARN: variable is not set` messages are harmless — Docker just substituting empty strings for unused compose variables.

---

## Start

```bash
# Start all services in background
docker compose up -d

# Start and watch logs in terminal (Ctrl+C to stop watching, containers keep running)
docker compose up
```

---

## Stop

```bash
# Stop all containers (data is preserved)
docker compose down

# Stop and wipe all volumes — full reset (loses DB data)
docker compose down -v
```

---

## After Code Changes (rebuild required)

```bash
# Rebuild image + restart all containers
docker compose up -d --build

# Rebuild only the web service (faster if only app code changed)
docker compose up -d --build web
```

---

## Migrations

> Containers must be running. Run `docker compose up -d` first if not started.

```bash
# 1. Create migration files after model changes
docker compose exec web python manage.py makemigrations

# 2. Apply all pending migrations
docker compose exec web python manage.py migrate

# Check migration status (see what is applied / pending)
docker compose exec web python manage.py showmigrations

# Roll back to a specific migration (example: posts app to 0001)
docker compose exec web python manage.py migrate posts 0001
```

---

## Logs

```bash
# Django / Daphne server logs (live, follow)
docker compose logs -f web

# Celery worker logs
docker compose logs -f celery

# Celery beat scheduler logs
docker compose logs -f celery-beat

# Database logs
docker compose logs -f db

# All services at once
docker compose logs -f

# Last 100 lines only (no follow)
docker compose logs --tail=100 web
```

---

## Container Status

```bash
# See all container states (running / exited / healthy)
docker compose ps

# Restart only the web container (e.g. after a config change)
docker compose restart web

# Restart celery worker
docker compose restart celery
```

---

## Django Management

```bash
# Django interactive shell
docker compose exec web python manage.py shell

# Create superuser
docker compose exec web python manage.py createsuperuser

# Collect static files
docker compose exec web python manage.py collectstatic --noinput

# Check for configuration errors
docker compose exec web python manage.py check

# List all registered URL routes
docker compose exec web python manage.py show_urls
```

---

## Database Shell

```bash
# Open psql inside the db container
docker compose exec db psql -U connecthub_user -d connecthub

# Useful psql commands:
#   \dt          — list all tables
#   \d tablename — describe a table
#   \q           — quit
```

---

## Run Tests

```bash
# All tests
docker compose exec web python manage.py test

# Single app
docker compose exec web python manage.py test apps.users
docker compose exec web python manage.py test apps.posts
docker compose exec web python manage.py test apps.notifications

# With coverage
docker compose exec web bash -c "coverage run manage.py test && coverage report"
```

---

## Quick Reference

| Action                  | Command                                                       |
|-------------------------|---------------------------------------------------------------|
| Start                   | `docker compose up -d`                                        |
| Stop                    | `docker compose down`                                         |
| Rebuild after changes   | `docker compose up -d --build`                                |
| Full reset (wipe DB)    | `docker compose down -v`                                      |
| Make migrations         | `docker compose exec web python manage.py makemigrations`     |
| Apply migrations        | `docker compose exec web python manage.py migrate`            |
| Logs (web)              | `docker compose logs -f web`                                  |
| Logs (all)              | `docker compose logs -f`                                      |
| Status                  | `docker compose ps`                                           |
| Shell                   | `docker compose exec web python manage.py shell`              |
| Tests                   | `docker compose exec web python manage.py test`               |

---

## Local URLs

| URL                             | Description              |
|---------------------------------|--------------------------|
| http://localhost:8000/api/docs/ | Swagger UI               |
| http://localhost:8000/api/redoc/| ReDoc                    |
| http://localhost:8000/admin/    | Django Admin             |
| http://localhost:5555/          | Flower (Celery monitor)  |

---

## Production (EC2)

> EC2 uses **`docker-compose`** (v1, with hyphen) — not `docker compose`.

```bash
# SSH in
ssh -i "Mihir_ubuntu_laptop.pem" ec2-user@ec2-13-51-238-168.eu-north-1.compute.amazonaws.com

# Go to project
cd connecthub-backend

# Pull latest code
git pull origin main
```

### Start

```bash
# Start all containers in background
docker-compose -f docker-compose.prod.yml up -d

# Rebuild + restart (after any code change)
docker-compose -f docker-compose.prod.yml up -d --build

# Start nginx (if not running)
sudo systemctl start nginx
```

### Stop

```bash
# Stop all containers (data preserved)
docker-compose -f docker-compose.prod.yml down

# Stop nginx
sudo systemctl stop nginx
```

### Migrations

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py makemigrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### Logs

```bash
# Web / Daphne
docker-compose -f docker-compose.prod.yml logs -f web

# All services
docker-compose -f docker-compose.prod.yml logs -f

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 web
```

### Status

```bash
docker-compose -f docker-compose.prod.yml ps
sudo systemctl status nginx
```

### Production URLs

| URL                                                              | Description           |
|------------------------------------------------------------------|-----------------------|
| http://13.51.238.168:8001/api/docs/                              | Swagger (direct)      |
| http://13.51.238.168:8001/admin/                                 | Admin (direct)        |
| http://ec2-13-51-238-168.eu-north-1.compute.amazonaws.com/api/docs/ | Swagger (via nginx) |
