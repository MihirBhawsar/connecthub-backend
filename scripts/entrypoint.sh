#!/bin/bash
# ConnectHub web container entrypoint.
# Waits for PostgreSQL, runs migrations, then starts Daphne.

#!/bin/bash
set -e

echo "==> Waiting for PostgreSQL..."

until nc -z db 5432; do
  echo "PostgreSQL is unavailable — sleeping 2s"
  sleep 2
done

echo "PostgreSQL is ready!"

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collectstatic..."
python manage.py collectstatic --noinput

echo "==> Starting server..."
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
