#!/bin/bash

# Validate and fix .env file for MT4 Docker

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}MT4 Docker .env Validator${NC}"
echo "========================="
echo ""

cd "$(dirname "$0")/.."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    
    if [ -f ".env.example" ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env with your MT4 credentials${NC}"
        exit 1
    else
        echo "Creating new .env file..."
        cat > .env << 'EOF'
# MT4 Account Configuration
# Copy this file to .env and fill in your account details

# MT4 Account Login (numeric account ID)
MT4_LOGIN=

# MT4 Account Password
MT4_PASSWORD=

# MT4 Server (e.g., "ICMarkets-Demo01" or your broker's server)
MT4_SERVER=

# VNC Password (optional, for secure VNC access)
VNC_PASSWORD=changeme
EOF
        echo -e "${YELLOW}Created .env file. Please edit it with your MT4 credentials.${NC}"
        exit 1
    fi
fi

# Source the .env file
set -a
source .env
set +a

# Validate required fields
ERRORS=0

echo "Checking required fields..."
echo ""

# MT4_LOGIN
echo -n "MT4_LOGIN: "
if [ -z "$MT4_LOGIN" ]; then
    echo -e "${RED}✗ Missing${NC}"
    ((ERRORS++))
elif ! [[ "$MT4_LOGIN" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}✗ Invalid (must be numeric)${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✓ Set (${MT4_LOGIN})${NC}"
fi

# MT4_PASSWORD
echo -n "MT4_PASSWORD: "
if [ -z "$MT4_PASSWORD" ]; then
    echo -e "${RED}✗ Missing${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✓ Set (hidden)${NC}"
fi

# MT4_SERVER
echo -n "MT4_SERVER: "
if [ -z "$MT4_SERVER" ]; then
    echo -e "${RED}✗ Missing${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✓ Set (${MT4_SERVER})${NC}"
fi

# VNC_PASSWORD
echo -n "VNC_PASSWORD: "
if [ -z "$VNC_PASSWORD" ] || [ "$VNC_PASSWORD" = "changeme" ]; then
    echo -e "${YELLOW}⚠ Using default (recommend changing)${NC}"
else
    echo -e "${GREEN}✓ Set (hidden)${NC}"
fi

echo ""
echo "========================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ .env validation passed!${NC}"
    
    # Test if container can see the env vars
    if docker ps | grep -q mt4-docker; then
        echo ""
        echo "Checking container environment..."
        CONTAINER_CHECK=$(docker exec mt4-docker sh -c 'echo "$MT4_LOGIN"' 2>/dev/null || echo "")
        if [ -n "$CONTAINER_CHECK" ]; then
            echo -e "${GREEN}✓ Container has access to environment variables${NC}"
        else
            echo -e "${YELLOW}⚠ Container may need restart to load new environment${NC}"
            echo "  Run: docker compose -f infra/docker/docker-compose.yml restart"
        fi
    fi
    
    exit 0
else
    echo -e "${RED}✗ Validation failed with $ERRORS errors${NC}"
    echo ""
    echo "Please edit .env file and set:"
    echo "  - MT4_LOGIN: Your numeric account ID"
    echo "  - MT4_PASSWORD: Your account password"
    echo "  - MT4_SERVER: Your broker's server name"
    echo ""
    echo "Example:"
    echo "  MT4_LOGIN=12345"
    echo "  MT4_PASSWORD=mypassword"
    echo "  MT4_SERVER=ICMarkets-Demo01"
    exit 1
fi