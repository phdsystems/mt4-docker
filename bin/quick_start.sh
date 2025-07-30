#!/bin/bash

# MT4 Docker Quick Start Script
# Ensures proper startup with .env configuration

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}MT4 Docker Quick Start${NC}"
echo "===================="

# Change to project root
cd "$(dirname "$0")/.."

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Creating .env from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env with your MT4 credentials${NC}"
        exit 1
    else
        echo -e "${RED}No .env.example found either!${NC}"
        exit 1
    fi
fi

# Validate .env file
echo "Validating .env configuration..."
source .env
if [ -z "$MT4_LOGIN" ] || [ -z "$MT4_PASSWORD" ] || [ -z "$MT4_SERVER" ]; then
    echo -e "${RED}ERROR: Missing MT4 credentials in .env file!${NC}"
    echo "Please ensure these variables are set:"
    echo "  - MT4_LOGIN"
    echo "  - MT4_PASSWORD"
    echo "  - MT4_SERVER"
    exit 1
fi
echo -e "${GREEN}✓ .env file validated${NC}"

# Check for terminal.exe
if [ ! -f "terminal.exe" ]; then
    echo -e "${RED}ERROR: terminal.exe not found!${NC}"
    echo "Please copy your MT4 terminal.exe to: $(pwd)/terminal.exe"
    exit 1
fi
echo -e "${GREEN}✓ terminal.exe found${NC}"

# Update permissions
chmod +x bin/*.sh scripts/*.sh 2>/dev/null || true

# Stop existing container
if docker ps -a | grep -q mt4-docker; then
    echo "Stopping existing container..."
    docker stop mt4-docker >/dev/null 2>&1 || true
    docker rm mt4-docker >/dev/null 2>&1 || true
fi

# Build and start with proper env file
echo ""
echo "Building Docker image..."
docker compose -f infra/docker/docker-compose.yml --env-file .env build

echo ""
echo "Starting container..."
docker compose -f infra/docker/docker-compose.yml --env-file .env up -d

echo ""
echo "Waiting for services to start..."
for i in {1..10}; do
    echo -n "."
    sleep 1
done
echo ""

# Check status
echo ""
./bin/check_status.sh

# Show connection info
echo ""
echo -e "${GREEN}Quick start complete!${NC}"
echo ""
echo "Connection Information:"
echo "======================"
echo "VNC Server: localhost:5900"
echo "VNC Password: ${VNC_PASSWORD:-changeme}"
echo "MT4 Account: $MT4_LOGIN @ $MT4_SERVER"
echo ""
echo "Commands:"
echo "  Monitor: ./bin/monitor.sh"
echo "  Status:  ./bin/check_status.sh"
echo "  Logs:    ./bin/view_logs.sh"
echo "  Stop:    docker compose -f infra/docker/docker-compose.yml down"