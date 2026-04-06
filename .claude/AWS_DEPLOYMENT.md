# AWS Deployment Guide — ConnectHub
## Reference for Claude Code when generating infra scripts, README, and deployment config

---

## 🏗️ AWS Architecture

```
Internet
    │
    ▼
Route 53 (DNS)
    │
    ▼
AWS Certificate Manager (SSL/TLS)
    │
    ▼
EC2 Instance (Ubuntu 22.04, t3.small)
├── Nginx (port 80/443)
│   ├── → Daphne :8000  (HTTP + WebSocket)
│   └── → Static/Media → S3 redirect
├── Docker Compose
│   ├── web (Daphne + Django)
│   ├── celery (worker)
│   ├── celery-beat (scheduler)
│   └── redis (broker + cache)
└── PostgreSQL → AWS RDS (t3.micro, postgres15)

AWS S3
└── connecthub-media bucket
    ├── avatars/
    ├── posts/
    ├── thumbnails/
    └── stories/
```

---

## 📋 Pre-Deployment Checklist

### AWS Account Setup
- [ ] Create IAM user `connecthub-app` with programmatic access
- [ ] Attach policy: `AmazonS3FullAccess` (scope to bucket in production)
- [ ] Save `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- [ ] Create S3 bucket `connecthub-media-{your-name}` in `ap-south-1`
- [ ] Launch RDS PostgreSQL 15 (t3.micro, Free Tier eligible)
- [ ] Launch EC2 Ubuntu 22.04 (t3.small minimum for Celery + Daphne)
- [ ] Create Elastic IP and attach to EC2
- [ ] Configure Security Group inbound: 22 (SSH), 80 (HTTP), 443 (HTTPS)

---

## 🪣 S3 Bucket Configuration

### Bucket Policy (allow app user access, deny public)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AppUserAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:user/connecthub-app"
      },
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::connecthub-media-YOUR-NAME/*"
    }
  ]
}
```

### CORS Configuration (for presigned URL uploads)
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedOrigins": ["https://yourdomain.com"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

### Lifecycle Rules
- Move objects to S3-IA after 90 days
- Delete expired story media after 2 days (use tags or prefix `stories/`)

---

## 🖥️ EC2 Initial Setup Script

```bash
#!/bin/bash
# scripts/ec2-setup.sh
# Run once on fresh EC2 instance as ubuntu user

set -e

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add ubuntu to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Install Git
sudo apt-get install -y git

# Clone repo
git clone https://github.com/YOUR_USERNAME/connecthub.git /home/ubuntu/connecthub
cd /home/ubuntu/connecthub

# Copy .env (you must upload this separately or set via CI/CD secrets)
# cp .env.example .env && nano .env

echo "EC2 setup complete. Upload .env file and run: docker compose -f docker-compose.prod.yml up -d"
```

---

## 🚀 Deployment Commands

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Navigate to project
cd /home/ubuntu/connecthub

# Pull latest code
git pull origin main

# Build and start (first time)
docker compose -f docker-compose.prod.yml up -d --build

# Apply migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Create superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# View logs
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f celery

# Restart a service
docker compose -f docker-compose.prod.yml restart web

# Check container status
docker compose -f docker-compose.prod.yml ps
```

---

## 🌐 Nginx + SSL Setup (on EC2, outside Docker)

```bash
# Install Nginx and Certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Create Nginx config
sudo nano /etc/nginx/sites-available/connecthub
```

```nginx
# /etc/nginx/sites-available/connecthub
upstream connecthub {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 512M;
    client_body_timeout 300s;

    # WebSocket upgrade
    location /ws/ {
        proxy_pass http://connecthub;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # API + Admin
    location / {
        proxy_pass http://connecthub;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/connecthub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (already set up by certbot, verify)
sudo certbot renew --dry-run
```

---

## 🔐 Production `.env` Values

```env
DJANGO_SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,YOUR_EC2_IP
CORS_ALLOWED_ORIGINS=https://yourdomain.com

DATABASE_URL=postgres://connecthub_user:STRONG_PASSWORD@YOUR_RDS_ENDPOINT:5432/connecthub

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=connecthub-media-your-name
AWS_S3_REGION_NAME=ap-south-1

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
DEFAULT_FROM_EMAIL=ConnectHub <your@gmail.com>

SENTRY_DSN=https://...  # optional but recommended
```

---

## 📊 Monitoring (Free Tier)

### Sentry (error tracking)
```python
# requirements/production.txt: sentry-sdk
# config/settings/production.py
import sentry_sdk
sentry_sdk.init(
    dsn=env('SENTRY_DSN', default=''),
    traces_sample_rate=0.1,
    environment='production',
)
```

### CloudWatch (AWS) — Basic metrics auto-collected:
- EC2 CPU, memory, disk
- RDS connections, CPU, storage
- Set alarms: CPU > 80%, disk > 85%

### Celery Monitoring — Flower (internal only)
```bash
# Access via SSH tunnel (never expose port 5555 publicly)
ssh -L 5555:localhost:5555 -i your-key.pem ubuntu@YOUR_EC2_IP
# Then open: http://localhost:5555
```

---

## 🔄 GitHub Actions Secrets to Configure

Go to GitHub → Repository → Settings → Secrets and Variables → Actions:

| Secret | Value |
|---|---|
| `EC2_HOST` | Your EC2 public IP or domain |
| `EC2_SSH_KEY` | Contents of your .pem private key file |
| `EC2_USER` | `ubuntu` |
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `SLACK_WEBHOOK_URL` | Optional: for deploy notifications |

---

## 💰 Estimated AWS Cost (Free Tier / Low Traffic)

| Service | Spec | Monthly Cost |
|---|---|---|
| EC2 t3.small | 2 vCPU, 2GB RAM | ~$15/mo (or Free Tier t2.micro) |
| RDS t3.micro | PostgreSQL 15, 20GB | ~$13/mo (or Free Tier) |
| S3 | 10GB storage + transfers | ~$1-3/mo |
| Elastic IP | 1 IP | Free when attached |
| Data Transfer | 1GB out | Free tier |
| **Total** | | **~$0-31/mo** |

> For resume/demo purposes: use t2.micro EC2 + t2.micro RDS (both Free Tier eligible for 12 months)

---

## 🆘 Common Deployment Issues

### Container won't start
```bash
docker compose -f docker-compose.prod.yml logs web
# Usually: missing env var, wrong DATABASE_URL, or migration not applied
```

### WebSocket connections failing
```bash
# Check Nginx config has the ws/ location block
# Check ALLOWED_HOSTS includes domain
# Check CHANNEL_LAYERS Redis URL is correct
```

### S3 upload failing (403)
```bash
# Check IAM policy allows PutObject on the bucket
# Check AWS_S3_REGION_NAME matches bucket region
# Check bucket does NOT have Block Public Access for ACLs if using ACLs
```

### Celery tasks not running
```bash
docker compose -f docker-compose.prod.yml logs celery
# Usually: broker URL wrong, or task not registered (check CELERY_IMPORTS)
```
