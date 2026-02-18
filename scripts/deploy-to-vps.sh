#!/bin/bash

# VPS Deployment Script for Claude Code Telegram Bot
# This script automates deployment to your VPS

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=================================="
echo "Claude Code Telegram Bot"
echo "VPS Deployment Script"
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
echo -e "\n${YELLOW}Creating deployment directory...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP "mkdir -p $DEPLOY_DIR"

# Install system dependencies
echo -e "\n${YELLOW}Installing system dependencies...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<'ENDSSH'
# Update package lists
apt-get update

# Install Python 3.10+ if not installed
if ! command -v python3.10 &> /dev/null; then
    echo "Installing Python 3.10..."
    apt-get install -y python3.10 python3.10-venv python3-pip
    echo "✓ Python 3.10 installed"
else
    echo "✓ Python 3.10 already installed"
fi

# Install Poetry if not installed
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="/root/.local/bin:$PATH"
    echo 'export PATH="/root/.local/bin:$PATH"' >> ~/.bashrc
    echo "✓ Poetry installed"
else
    echo "✓ Poetry already installed"
fi

# Install Node.js (for Claude CLI) if not installed
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    echo "✓ Node.js installed"
else
    echo "✓ Node.js already installed"
fi

# Install Claude CLI if not installed
if ! command -v claude &> /dev/null; then
    echo "Installing Claude CLI..."
    npm install -g @anthropic-ai/claude-code
    echo "✓ Claude CLI installed"
else
    echo "✓ Claude CLI already installed"
fi

# Install git if not installed
if ! command -v git &> /dev/null; then
    echo "Installing git..."
    apt-get install -y git
    echo "✓ git installed"
else
    echo "✓ git already installed"
fi
ENDSSH

# Clone claude-code-telegram repository
echo -e "\n${YELLOW}Cloning claude-code-telegram repository...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<ENDSSH
cd $DEPLOY_DIR
if [ -d "claude-code-telegram" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd claude-code-telegram
    git pull
else
    echo "Cloning repository..."
    git clone https://github.com/RichardAtCT/claude-code-telegram.git
    cd claude-code-telegram
fi
echo "✓ Repository ready"
ENDSSH

# Install Poetry dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<'ENDSSH'
export PATH="/root/.local/bin:$PATH"
cd /opt/openclaw/claude-code-telegram
poetry install --no-dev
echo "✓ Dependencies installed"
ENDSSH

# Check if .env exists locally
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env file with your settings and run this script again.${NC}"
    exit 1
fi

# Copy .env file
echo -e "\n${YELLOW}Copying environment variables...${NC}"
scp -P $SSH_PORT .env $VPS_USER@$VPS_IP:$DEPLOY_DIR/claude-code-telegram/.env
echo -e "${GREEN}✓ Environment variables copied${NC}"

# Create necessary directories
echo -e "\n${YELLOW}Creating data directories...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP "cd $DEPLOY_DIR/claude-code-telegram && mkdir -p data logs"

# Claude CLI Authentication
echo -e "\n${BLUE}=================================="
echo "Claude CLI Authentication"
echo "==================================${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: You need to authenticate Claude CLI on the VPS.${NC}"
echo ""
echo "Please follow these steps:"
echo "1. SSH into your VPS: ssh -p $SSH_PORT $VPS_USER@$VPS_IP"
echo "2. Run: claude auth login"
echo "3. Follow the browser authentication flow"
echo "4. After authentication, exit the SSH session and continue here"
echo ""
read -p "Press Enter after you've completed Claude CLI authentication..."

# Verify Claude CLI authentication
echo -e "\n${YELLOW}Verifying Claude CLI authentication...${NC}"
if ssh -p $SSH_PORT $VPS_USER@$VPS_IP "claude auth status" 2>/dev/null | grep -q "Logged in"; then
    echo -e "${GREEN}✓ Claude CLI authenticated${NC}"
else
    echo -e "${RED}✗ Claude CLI not authenticated${NC}"
    echo "Please run: ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'claude auth login'"
    exit 1
fi

# Set up systemd service
echo -e "\n${YELLOW}Setting up systemd service...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP bash <<'ENDSSH'
export PATH="/root/.local/bin:$PATH"

# Create systemd service file
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/claude-telegram-bot.service <<'EOF'
[Unit]
Description=Claude Code Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/openclaw/claude-code-telegram
ExecStart=/root/.local/bin/poetry run claude-telegram-bot
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment="PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=default.target
EOF

# Enable lingering (keeps service running after logout)
loginctl enable-linger $USER

# Reload systemd
systemctl --user daemon-reload

# Enable and start service
systemctl --user enable claude-telegram-bot.service
systemctl --user start claude-telegram-bot.service

echo "✓ systemd service configured and started"
ENDSSH

# Check service status
echo -e "\n${YELLOW}Checking service status...${NC}"
ssh -p $SSH_PORT $VPS_USER@$VPS_IP "systemctl --user status claude-telegram-bot.service --no-pager"

echo -e "\n${GREEN}=================================="
echo "Deployment Complete!"
echo "==================================${NC}"
echo ""
echo "Your Claude Code Telegram bot is now running!"
echo ""
echo "Useful commands:"
echo "  View logs:      ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'journalctl --user -u claude-telegram-bot -f'"
echo "  Restart:        ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'systemctl --user restart claude-telegram-bot'"
echo "  Stop:           ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'systemctl --user stop claude-telegram-bot'"
echo "  Status:         ssh -p $SSH_PORT $VPS_USER@$VPS_IP 'systemctl --user status claude-telegram-bot'"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test your Telegram bot by sending it a message"
echo "2. Check logs if there are any issues"
echo ""
