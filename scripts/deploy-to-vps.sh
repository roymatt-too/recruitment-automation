#!/bin/bash

# VPS Deployment Script for OpenClaw with Telegram Integration
# This script automates the deployment of OpenClaw to your VPS

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================="
echo "OpenClaw VPS Deployment Script"
echo "==================================${NC}"
echo ""

# Configuration
read -p "Enter VPS IP address: " VPS_IP
read -p "Enter VPS SSH user (default: root): " VPS_USER
VPS_USER=${VPS_USER:-root}
read -p "Enter SSH port (default: 22): " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

# Test SSH connection
echo -e "\n${YELLOW}Testing SSH connection...${NC}"
if ssh -p $SSH_PORT -o ConnectTimeout=10 $VPS_USER@$VPS_IP "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✓ SSH connection successful${NC}"
else
    echo -e "${RED}✗ SSH connection failed${NC}"
    echo "Please check your VPS IP, user, and port settings."
    exit 1
fi

# Create deployment directory
DEPLOY_DIR="/opt/openclaw"
echo -e "\n${YELLOW}Creating deployment directory on VPS...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP "mkdir -p $DEPLOY_DIR"

# Install Docker if not installed
echo -e "\n${YELLOW}Checking Docker installation...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<'ENDSSH'
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
    rm get-docker.sh
    echo "✓ Docker installed"
else
    echo "✓ Docker already installed"
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✓ Docker Compose installed"
else
    echo "✓ Docker Compose already installed"
fi
ENDSSH

# Copy project files to VPS
echo -e "\n${YELLOW}Copying project files to VPS...${NC}"
rsync -avz -e "ssh -p $SSH_PORT" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='data' \
    --exclude='logs' \
    ./ $VPS_USER@$VPS_IP:$DEPLOY_DIR/

echo -e "${GREEN}✓ Files copied${NC}"

# Set up firewall
echo -e "\n${YELLOW}Configuring firewall...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<'ENDSSH'
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 443/udp  # HTTP/3
    ufw reload
    echo "✓ Firewall configured"
else
    echo "⚠ UFW not installed. Please configure firewall manually."
fi
ENDSSH

# Create necessary directories on VPS
echo -e "\n${YELLOW}Creating data directories...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP "cd $DEPLOY_DIR && mkdir -p data logs config/fail2ban"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please run ./scripts/setup-telegram-bot.sh first"
    exit 1
fi

# Copy .env file
echo -e "\n${YELLOW}Copying environment variables...${NC}"
scp -P $SSH_PORT .env $VPS_USER@$VPS_IP:$DEPLOY_DIR/.env
echo -e "${GREEN}✓ Environment variables copied${NC}"

# Deploy with Docker Compose
echo -e "\n${YELLOW}Starting OpenClaw services...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<ENDSSH
cd $DEPLOY_DIR
docker-compose down 2>/dev/null || true
docker-compose pull
docker-compose up -d
echo "✓ Services started"

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 10

# Check service status
docker-compose ps
ENDSSH

# Install automatic security updates
echo -e "\n${YELLOW}Setting up automatic security updates...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<'ENDSSH'
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y unattended-upgrades
    dpkg-reconfigure -plow unattended-upgrades
    echo "✓ Automatic updates enabled"
fi
ENDSSH

# Set up log rotation
echo -e "\n${YELLOW}Configuring log rotation...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP "cat > /etc/logrotate.d/openclaw" <<'ENDSSH'
/opt/openclaw/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker-compose -f /opt/openclaw/docker-compose.yml restart openclaw >/dev/null 2>&1 || true
    endscript
}
ENDSSH

echo -e "\n${GREEN}=================================="
echo "Deployment Complete!"
echo "==================================${NC}"
echo ""
echo "Your OpenClaw bot is now running on: http://$VPS_IP"
echo ""
echo "Useful commands:"
echo "  View logs:      ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'cd $DEPLOY_DIR && docker-compose logs -f'"
echo "  Restart:        ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'cd $DEPLOY_DIR && docker-compose restart'"
echo "  Stop:           ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'cd $DEPLOY_DIR && docker-compose down'"
echo "  Update:         ./scripts/update-vps.sh"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test your Telegram bot by sending it a message"
echo "2. Configure your domain DNS to point to $VPS_IP"
echo "3. Update .env with your domain and re-deploy for HTTPS"
echo ""
