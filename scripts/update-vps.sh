#!/bin/bash

# Update Script for OpenClaw on VPS
# This script updates the OpenClaw deployment without losing data

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================="
echo "OpenClaw VPS Update Script"
echo "==================================${NC}"
echo ""

# Configuration
read -p "Enter VPS IP address: " VPS_IP
read -p "Enter VPS SSH user (default: root): " VPS_USER
VPS_USER=${VPS_USER:-root}
read -p "Enter SSH port (default: 22): " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

DEPLOY_DIR="/opt/openclaw"

# Backup current configuration
echo -e "\n${YELLOW}Creating backup...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP "cd $DEPLOY_DIR && tar -czf /tmp/openclaw-backup-$(date +%Y%m%d-%H%M%S).tar.gz .env data/ config/"
echo -e "${GREEN}✓ Backup created${NC}"

# Copy updated files
echo -e "\n${YELLOW}Copying updated files...${NC}"
rsync -avz -e "ssh -p $SSH_PORT" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='data' \
    --exclude='logs' \
    --exclude='.env' \
    ./ $VPS_USER@$VPS_IP:$DEPLOY_DIR/

echo -e "${GREEN}✓ Files updated${NC}"

# Update and restart services
echo -e "\n${YELLOW}Updating and restarting services...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<ENDSSH
cd $DEPLOY_DIR
docker-compose pull
docker-compose up -d --force-recreate
docker-compose ps
ENDSSH

echo -e "\n${GREEN}=================================="
echo "Update Complete!"
echo "==================================${NC}"
echo ""
echo "Your OpenClaw bot has been updated successfully."
echo ""
