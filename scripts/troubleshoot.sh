#!/bin/bash

# Troubleshooting Script for OpenClaw
# This script helps diagnose common issues

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================="
echo "OpenClaw Troubleshooting"
echo "==================================${NC}"
echo ""

# Configuration
read -p "Is this for VPS or local? (vps/local): " LOCATION

if [ "$LOCATION" = "vps" ]; then
    read -p "Enter VPS IP address: " VPS_IP
    read -p "Enter VPS SSH user (default: root): " VPS_USER
    VPS_USER=${VPS_USER:-root}
    read -p "Enter SSH port (default: 22): " SSH_PORT
    SSH_PORT=${SSH_PORT:-22}
    DEPLOY_DIR="/opt/openclaw"
    CMD_PREFIX="ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'cd $DEPLOY_DIR &&"
    CMD_SUFFIX="'"
else
    CMD_PREFIX=""
    CMD_SUFFIX=""
fi

echo -e "\n${YELLOW}Checking Docker status...${NC}"
eval "${CMD_PREFIX} docker --version ${CMD_SUFFIX}" 2>&1
eval "${CMD_PREFIX} docker-compose --version ${CMD_SUFFIX}" 2>&1

echo -e "\n${YELLOW}Checking container status...${NC}"
eval "${CMD_PREFIX} docker-compose ps ${CMD_SUFFIX}" 2>&1

echo -e "\n${YELLOW}Checking container logs (last 50 lines)...${NC}"
echo -e "${BLUE}--- OpenClaw Logs ---${NC}"
eval "${CMD_PREFIX} docker-compose logs --tail=50 openclaw ${CMD_SUFFIX}" 2>&1

echo -e "\n${BLUE}--- Caddy Logs ---${NC}"
eval "${CMD_PREFIX} docker-compose logs --tail=50 caddy ${CMD_SUFFIX}" 2>&1

echo -e "\n${YELLOW}Checking .env file...${NC}"
if [ "$LOCATION" = "local" ]; then
    if [ -f .env ]; then
        echo -e "${GREEN}✓ .env file exists${NC}"
        echo "Checking required variables..."
        for var in TELEGRAM_BOT_TOKEN ANTHROPIC_API_KEY OPENAI_API_KEY; do
            if grep -q "^${var}=" .env && ! grep -q "^${var}=your_" .env; then
                echo -e "${GREEN}✓ ${var} is set${NC}"
            else
                echo -e "${YELLOW}⚠ ${var} is not set or using placeholder${NC}"
            fi
        done
    else
        echo -e "${RED}✗ .env file not found${NC}"
        echo "Please run: ./scripts/setup-telegram-bot.sh"
    fi
else
    eval "${CMD_PREFIX} test -f .env && echo '.env exists' || echo '.env not found' ${CMD_SUFFIX}"
fi

echo -e "\n${YELLOW}Checking network connectivity...${NC}"
eval "${CMD_PREFIX} docker network ls | grep openclaw ${CMD_SUFFIX}" 2>&1

echo -e "\n${YELLOW}Checking disk space...${NC}"
eval "${CMD_PREFIX} df -h | grep -E '(Filesystem|/$)' ${CMD_SUFFIX}" 2>&1

echo -e "\n${YELLOW}Checking memory usage...${NC}"
eval "${CMD_PREFIX} free -h ${CMD_SUFFIX}" 2>&1

echo -e "\n${YELLOW}Checking Docker resource usage...${NC}"
eval "${CMD_PREFIX} docker stats --no-stream ${CMD_SUFFIX}" 2>&1

echo -e "\n${BLUE}=================================="
echo "Common Issues & Solutions"
echo "==================================${NC}"
echo ""
echo "1. Bot not responding:"
echo "   - Check TELEGRAM_BOT_TOKEN is correct"
echo "   - Verify bot is started with @BotFather"
echo "   - Check logs for errors"
echo ""
echo "2. API errors:"
echo "   - Verify ANTHROPIC_API_KEY or OPENAI_API_KEY"
echo "   - Check API key has sufficient credits"
echo "   - Check API rate limits"
echo ""
echo "3. Container not starting:"
echo "   - Check Docker daemon is running"
echo "   - Verify .env file exists and is valid"
echo "   - Check port conflicts"
echo ""
echo "4. Cannot connect to VPS:"
echo "   - Verify firewall allows ports 80, 443"
echo "   - Check domain DNS settings"
echo "   - Verify Caddy configuration"
echo ""
echo "For more help, check the logs above or visit:"
echo "https://docs.openclaw.ai"
echo ""
