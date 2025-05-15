#!/bin/bash

# Master MT4 Docker Diagnostic Script
CONTAINER="mt4-docker"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

echo "MT4 Docker Master Diagnostic Tool"
echo "================================"
echo "$(date)"
echo ""

# 1. Container Status
print_header "1. Container Status"
if docker ps | grep -q $CONTAINER; then
    print_success "Container is running"
else
    print_error "Container is not running"
    echo "Starting container..."
    docker-compose up -d
    sleep 10
fi
echo ""

# 2. Process Status
print_header "2. Process Status"
if docker exec $CONTAINER pgrep -f Xvfb > /dev/null; then
    print_success "Xvfb is running"
else
    print_error "Xvfb is not running"
fi

if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
    print_success "MT4 is running"
else
    print_error "MT4 is not running"
fi
echo ""

# 3. File Check
print_header "3. File Check"
if docker exec $CONTAINER test -f /mt4/terminal.exe; then
    print_success "terminal.exe found"
else
    print_error "terminal.exe missing"
    echo "  Please run: ./scripts/utilities/copy_terminal.sh"
fi

if docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.mq4; then
    print_success "AutoDeploy_EA.mq4 exists"
else
    print_error "AutoDeploy_EA.mq4 missing"
fi
echo ""

# 4. Connection Test
print_header "4. Connection Test"
MT4_LOGIN=$(docker exec $CONTAINER bash -c 'echo $MT4_LOGIN')
if [ "$MT4_LOGIN" = "your_demo_account" ]; then
    print_error "MT4 credentials not configured"
    echo "  Please update .env file"
else
    print_success "MT4 credentials configured"
fi
echo ""

# 5. EA Status
print_header "5. EA Status"
if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_status.log; then
    print_success "EA is active"
    echo "  Status: $(docker exec $CONTAINER cat /mt4/MQL4/Files/ea_status.log)"
else
    print_warning "EA not active yet"
fi
echo ""

echo "Diagnostic complete!"
