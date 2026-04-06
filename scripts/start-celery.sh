#!/bin/bash
# Start the Celery worker.
# Used as the command for the celery service in docker-compose.

set -e

echo "==> Starting Celery worker..."
exec celery -A config.celery worker \
    --loglevel=info \
    --concurrency=4 \
    --without-heartbeat \
    --without-gossip \
    --without-mingle
