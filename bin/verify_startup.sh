#!/bin/bash

# MT4 Docker Startup Verification
# Ensures everything is working properly

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}MT4 Docker Startup Verification${NC}"
echo "==============================="
echo ""

ERRORS=0
WARNINGS=0

# 1. Check Docker
echo -n "1. Docker daemon: "
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    ((ERRORS++))
fi

# 2. Check container
echo -n "2. MT4 container: "
if docker ps | grep -q mt4-docker; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    ((ERRORS++))
fi

# 3. Check environment variables
echo -n "3. Environment variables: "
ENV_CHECK=$(docker exec mt4-docker env 2>/dev/null | grep -E "MT4_LOGIN|MT4_PASSWORD|MT4_SERVER" | wc -l || echo "0")
if [ "$ENV_CHECK" -eq "3" ]; then
    echo -e "${GREEN}✓ Loaded${NC}"
else
    echo -e "${RED}✗ Not loaded properly${NC}"
    ((ERRORS++))
fi

# 4. Check VNC
echo -n "4. VNC server: "
if docker exec mt4-docker pgrep x11vnc >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    ((ERRORS++))
fi

# 5. Check X server
echo -n "5. X server (Xvfb): "
if docker exec mt4-docker pgrep Xvfb >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    ((ERRORS++))
fi

# 6. Check Wine
echo -n "6. Wine environment: "
if docker exec mt4-docker wine --version >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Available${NC}"
else
    echo -e "${RED}✗ Not available${NC}"
    ((ERRORS++))
fi

# 7. Check MT4 terminal
echo -n "7. MT4 terminal.exe: "
if docker exec mt4-docker test -f /mt4/terminal.exe; then
    echo -e "${GREEN}✓ Present${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
    ((ERRORS++))
fi

# 8. Check auto-compile service
echo -n "8. Auto-compile service: "
if docker exec mt4-docker pgrep -f auto-compile >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}⚠ Not running${NC}"
    ((WARNINGS++))
fi

# 9. Check MQL4 directory
echo -n "9. MQL4 directory: "
if docker exec mt4-docker test -d /mt4/MQL4/Experts; then
    echo -e "${GREEN}✓ Mounted${NC}"
else
    echo -e "${RED}✗ Not mounted${NC}"
    ((ERRORS++))
fi

# 10. Check port accessibility
echo -n "10. VNC port 5900: "
if nc -z localhost 5900 2>/dev/null; then
    echo -e "${GREEN}✓ Accessible${NC}"
else
    echo -e "${YELLOW}⚠ Not accessible${NC}"
    ((WARNINGS++))
fi

# Summary
echo ""
echo "==============================="
if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}All checks passed!${NC}"
        echo ""
        echo "MT4 Docker is ready to use:"
        echo "- VNC: localhost:5900"
        echo "- Password: Check your .env file"
        exit 0
    else
        echo -e "${YELLOW}Verification completed with $WARNINGS warnings${NC}"
        echo "The system should work but check the warnings above."
        exit 0
    fi
else
    echo -e "${RED}Verification failed with $ERRORS errors${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Run: ./bin/quick_start.sh"
    echo "2. Check logs: ./bin/view_logs.sh"
    echo "3. Ensure .env file has valid credentials"
    exit 1
fi