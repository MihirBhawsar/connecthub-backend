FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    ffmpeg \
    libmagic1 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/base.txt requirements/base.txt
COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt

# Copy project source
COPY . .

# Make scripts executable
RUN chmod +x scripts/entrypoint.sh scripts/start-celery.sh

EXPOSE 8000

ENTRYPOINT ["scripts/entrypoint.sh"]
