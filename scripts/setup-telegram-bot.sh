#!/bin/bash

# Telegram Bot Setup Script for OpenClaw
# This script helps you set up a Telegram bot for OpenClaw integration

set -e

echo "=================================="
echo "OpenClaw Telegram Bot Setup"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ -f .env ]; then
    echo -e "${YELLOW}Warning: .env file already exists.${NC}"
    read -p "Do you want to overwrite it? (y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "Using existing .env file..."
        source .env
    fi
else
    echo "Creating .env file from template..."
    cp .env.example .env
fi

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
echo "Step 1: Telegram Bot Token"
echo "-----------------------------------"
echo "To create a Telegram bot:"
echo "1. Open Telegram and search for @BotFather"
echo "2. Send /newbot command"
echo "3. Follow the prompts to set bot name and username"
echo "4. Copy the bot token"
echo ""
read -p "Enter your Telegram Bot Token: " BOT_TOKEN

if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}Error: Bot token is required${NC}"
    exit 1
fi

update_env "TELEGRAM_BOT_TOKEN" "$BOT_TOKEN"
echo -e "${GREEN}✓ Bot token saved${NC}"

echo ""
echo "Step 2: Get Your Telegram User ID"
echo "-----------------------------------"
echo "To get your Telegram user ID:"
echo "1. Open Telegram and search for @userinfobot"
echo "2. Send /start command"
echo "3. Copy your user ID"
echo ""
read -p "Enter your Telegram User ID (comma-separated for multiple users): " USER_IDS

if [ -z "$USER_IDS" ]; then
    echo -e "${YELLOW}Warning: No user IDs provided. Bot will be accessible to everyone!${NC}"
else
    update_env "TELEGRAM_ALLOWED_USERS" "$USER_IDS"
    echo -e "${GREEN}✓ User IDs saved${NC}"
fi

echo ""
echo "Step 3: AI Model Configuration"
echo "-----------------------------------"
echo "Choose your AI provider:"
echo "1. Anthropic Claude (Recommended)"
echo "2. OpenAI GPT"
echo "3. Both"
read -p "Enter your choice (1-3): " AI_CHOICE

case $AI_CHOICE in
    1)
        read -p "Enter your Anthropic API Key: " ANTHROPIC_KEY
        update_env "ANTHROPIC_API_KEY" "$ANTHROPIC_KEY"
        update_env "DEFAULT_MODEL" "claude-sonnet-4-5-20250929"
        echo -e "${GREEN}✓ Anthropic configured${NC}"
        ;;
    2)
        read -p "Enter your OpenAI API Key: " OPENAI_KEY
        update_env "OPENAI_API_KEY" "$OPENAI_KEY"
        update_env "DEFAULT_MODEL" "gpt-4"
        echo -e "${GREEN}✓ OpenAI configured${NC}"
        ;;
    3)
        read -p "Enter your Anthropic API Key: " ANTHROPIC_KEY
        read -p "Enter your OpenAI API Key: " OPENAI_KEY
        update_env "ANTHROPIC_API_KEY" "$ANTHROPIC_KEY"
        update_env "OPENAI_API_KEY" "$OPENAI_KEY"
        update_env "DEFAULT_MODEL" "claude-sonnet-4-5-20250929"
        echo -e "${GREEN}✓ Both providers configured${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo "Step 4: Domain Configuration (Optional for TLS)"
echo "-----------------------------------"
read -p "Do you have a domain name for HTTPS? (y/n): " HAS_DOMAIN

if [ "$HAS_DOMAIN" = "y" ]; then
    read -p "Enter your domain name (e.g., bot.example.com): " DOMAIN
    read -p "Enter your email for TLS certificate: " EMAIL
    update_env "DOMAIN" "$DOMAIN"
    update_env "EMAIL" "$EMAIL"
    echo -e "${GREEN}✓ Domain configured${NC}"
else
    update_env "DOMAIN" "localhost"
    echo -e "${YELLOW}Using localhost. HTTPS will not be available.${NC}"
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Review .env file and adjust settings if needed"
echo "2. Run: ./scripts/deploy-to-vps.sh (to deploy to VPS)"
echo "   OR"
echo "   Run: docker-compose up -d (to run locally)"
echo ""
echo -e "${GREEN}Your bot is ready to be deployed!${NC}"
