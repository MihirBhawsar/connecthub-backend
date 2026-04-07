# ConnectHub — Project Commands Reference

---

## First-Time Setup

```bash
# 1. Copy env file
cp .env.example .env

# 2. Build all containers
docker compose build

# 3. Start database + redis first
docker compose up -d db redis

# 4. Run migrations
docker compose run --rm web python manage.py migrate

# 5. Create superuser
docker compose run --rm web python manage.py createsuperuser

# 6. Start everything
docker compose up -d
```

---

## Start Project

```bash
# Start all services (background)
docker compose up -d

# Start with live logs
docker compose up
```

---

## Stop Project

```bash
# Stop all containers (keeps data)
docker compose down

# Stop + delete database volume (full reset)
docker compose down -v
```

---

## Migrations

```bash
# Create migrations after model changes
docker compose exec web python manage.py makemigrations

# Apply migrations
docker compose exec web python manage.py migrate

# Show migration status
docker compose exec web python manage.py showmigrations

# Roll back one migration in an app
docker compose exec web python manage.py migrate posts 0001
```

---

## Database

```bash
# Access PostgreSQL shell
docker compose exec db psql -U connecthub_user -d connecthub

# Inside psql — useful commands
\dt            # list tables
\d posts_post  # describe a table
\q             # quit
```

---

## Run Tests

```bash
# All tests
docker compose exec web python manage.py test

# Specific app
docker compose exec web python manage.py test apps.users
docker compose exec web python manage.py test apps.posts
docker compose exec web python manage.py test apps.notifications

# With verbosity
docker compose exec web python manage.py test --verbosity=2

# With coverage
docker compose exec web bash -c "coverage run manage.py test && coverage report"
```

---

## Logs

```bash
docker compose logs -f web      # Django/Daphne logs
docker compose logs -f celery   # Celery worker logs
docker compose logs -f db       # PostgreSQL logs
docker compose logs -f redis    # Redis logs
```

---

## Django Management

```bash
# Django shell
docker compose exec web python manage.py shell

# Collect static files
docker compose exec web python manage.py collectstatic --noinput

# Check for errors (no DB needed)
docker compose exec web python manage.py check

# View all URL routes
docker compose exec web python manage.py show_urls
```

---

## Container Status

```bash
docker compose ps           # see all container states
docker compose restart web  # restart just the web server
```

---

## Quick Reference

| Action      | Command                                              |
|-------------|------------------------------------------------------|
| Start       | `docker compose up -d`                               |
| Stop        | `docker compose down`                                |
| Full reset  | `docker compose down -v`                             |
| Migrate     | `docker compose exec web python manage.py migrate`   |
| Shell       | `docker compose exec web python manage.py shell`     |
| Logs        | `docker compose logs -f web`                         |
| Tests       | `docker compose exec web python manage.py test`      |

---

## Production Server (EC2)

### 1. SSH into server

```bash
ssh -i "Mihir_ubuntu_laptop.pem" ec2-user@ec2-13-51-238-168.eu-north-1.compute.amazonaws.com
```

> Make sure `Mihir_ubuntu_laptop.pem` is in your current directory, or provide the full path.

### 2. Go to project folder

```bash
cd connecthub-backend
```

### 3. Pull latest code

```bash
git pull origin main
```

### 4. Start project (production)

```bash
# Start all containers in background
docker-compose -f docker-compose.prod.yml up -d

# Start with rebuild (after code changes)
docker-compose -f docker-compose.prod.yml up -d --build

# Start nginx (if not running)
sudo systemctl start nginx
```

### 5. Stop project (production)

```bash
# Stop all containers (keeps data)
docker-compose -f docker-compose.prod.yml down

# Stop nginx
sudo systemctl stop nginx
```

### 6. Check status

```bash
# Container status
docker-compose -f docker-compose.prod.yml ps

# Live logs
docker-compose -f docker-compose.prod.yml logs -f web
```

---

## URLs — Local

| URL                              | Description       |
|----------------------------------|-------------------|
| http://localhost:8000/api/docs/  | Swagger UI        |
| http://localhost:8000/api/redoc/ | ReDoc             |
| http://localhost:8000/admin/     | Django Admin      |
| http://localhost:5555/           | Flower (Celery)   |

---

## URLs — Production (EC2)

| URL                                                                      | Description       |
|--------------------------------------------------------------------------|-------------------|
| http://13.51.238.168:8001/api/docs/                                      | Swagger UI        |
| http://13.51.238.168:8001/api/redoc/                                     | ReDoc             |
| http://13.51.238.168:8001/admin/                                         | Django Admin      |
| http://ec2-13-51-238-168.eu-north-1.compute.amazonaws.com/api/docs/     | Swagger (via nginx, port 80) |
| http://ec2-13-51-238-168.eu-north-1.compute.amazonaws.com/admin/        | Admin (via nginx, port 80)   |
| http://13.51.238.168/api/docs/                                           | Swagger (via nginx, IP)      |

> Note: Port 8001 is direct access (recommended). Port 80 routes via nginx.
