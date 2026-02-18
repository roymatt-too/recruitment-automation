#!/bin/bash

# Telegram Bot Setup Script for Claude Code
# This script helps you set up a Telegram bot for Claude Code integration

set -e

echo "=================================="
echo "Claude Code Telegram Bot Setup"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ -f .env ]; then
    echo -e "${YELLOW}Warning: .env file already exists.${NC}"
    read -p "Do you want to overwrite it? (y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "Setup cancelled. Using existing .env file."
        exit 0
    fi
fi

echo "Creating .env file from template..."
cp .env.example .env

# Function to update .env file
update_env() {
    local key=$1
    local value=$2
    if grep -q "^${key}=" .env; then
        sed -i "s|^${key}=.*|${key}=${value}|" .env
    else
        echo "${key}=${value}" >> .env
    fi
}

echo ""
echo -e "${BLUE}Step 1: Telegram Bot Setup${NC}"
echo "-----------------------------------"
echo "To create a Telegram bot:"
echo "1. Open Telegram and search for @BotFather"
echo "2. Send /newbot command"
echo "3. Follow the prompts to set bot name and username"
echo "4. Copy the bot token and username"
echo ""
read -p "Enter your Telegram Bot Token: " BOT_TOKEN

if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}Error: Bot token is required${NC}"
    exit 1
fi

read -p "Enter your Telegram Bot Username (without @): " BOT_USERNAME

if [ -z "$BOT_USERNAME" ]; then
    echo -e "${RED}Error: Bot username is required${NC}"
    exit 1
fi

update_env "TELEGRAM_BOT_TOKEN" "$BOT_TOKEN"
update_env "TELEGRAM_BOT_USERNAME" "$BOT_USERNAME"
echo -e "${GREEN}✓ Bot credentials saved${NC}"

echo ""
echo -e "${BLUE}Step 2: User Access Control${NC}"
echo "-----------------------------------"
echo "To get your Telegram user ID:"
echo "1. Open Telegram and search for @userinfobot"
echo "2. Send /start command"
echo "3. Copy your user ID"
echo ""
read -p "Enter Telegram User ID(s) - comma-separated for multiple users: " USER_IDS

if [ -z "$USER_IDS" ]; then
    echo -e "${YELLOW}Warning: No user IDs provided. Bot will be accessible to everyone!${NC}"
    read -p "Are you sure? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
else
    update_env "ALLOWED_USERS" "$USER_IDS"
    echo -e "${GREEN}✓ User IDs saved${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Project Directory${NC}"
echo "-----------------------------------"
echo "This is the base directory where your projects will be accessible."
echo "Default: /opt/openclaw/projects"
echo ""
read -p "Enter project directory [/opt/openclaw/projects]: " PROJECT_DIR
PROJECT_DIR=${PROJECT_DIR:-/opt/openclaw/projects}

update_env "APPROVED_DIRECTORY" "$PROJECT_DIR"
echo -e "${GREEN}✓ Project directory configured${NC}"

echo ""
echo -e "${BLUE}=================================="
echo "Setup Complete!"
echo "==================================${NC}"
echo ""
echo -e "${GREEN}✓ Configuration saved to .env${NC}"
echo ""
echo -e "${YELLOW}Important Notes:${NC}"
echo "• This bot uses your Claude Code subscription (no API key needed!)"
echo "• You'll authenticate with Claude CLI during VPS deployment"
echo "• The bot will have access to files in: $PROJECT_DIR"
echo ""
echo "Next steps:"
echo "1. Review .env file and adjust settings if needed"
echo "2. Run: ./scripts/deploy-to-vps.sh (to deploy to VPS)"
echo ""
echo -e "${BLUE}Bot Configuration Summary:${NC}"
echo "• Bot Username: @$BOT_USERNAME"
echo "• Authorized Users: $USER_IDS"
echo "• Project Directory: $PROJECT_DIR"
echo ""
