#!/bin/bash
# EC2 initial setup script.
# Run once on a fresh Ubuntu 22.04 EC2 instance as the ubuntu user.

set -e

echo "==> Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

echo "==> Installing Docker..."
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
    https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "==> Adding ubuntu user to docker group..."
sudo usermod -aG docker ubuntu

echo "==> Installing Git..."
sudo apt-get install -y git

echo "==> Cloning ConnectHub repository..."
# Replace with your actual GitHub repo URL
git clone https://github.com/YOUR_USERNAME/connecthub.git /home/ubuntu/connecthub

echo ""
echo "==> EC2 setup complete!"
echo "Next steps:"
echo "  1. Upload your .env file:  scp .env ubuntu@EC2_IP:/home/ubuntu/connecthub/.env"
echo "  2. Start the stack:        cd /home/ubuntu/connecthub && docker compose -f docker-compose.prod.yml up -d --build"
echo "  3. Run migrations:         docker compose -f docker-compose.prod.yml exec web python manage.py migrate"
echo "  4. Create superuser:       docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser"
