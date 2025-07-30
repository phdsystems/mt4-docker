#!/bin/bash

# Script to help download and verify 32-bit MT4

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}MT4 32-bit Download Helper${NC}"
echo "=========================="
echo ""

echo -e "${YELLOW}Popular brokers with 32-bit MT4:${NC}"
echo ""
echo "1. IC Markets"
echo "   URL: https://www.icmarkets.com/global/en/trading-platforms/metatrader-4"
echo "   - Download 'MT4 for Windows'"
echo "   - Extract and find terminal.exe"
echo ""
echo "2. Pepperstone"
echo "   URL: https://pepperstone.com/en/trading-platforms/metatrader-4/"
echo "   - Download 'MT4 for Windows Desktop'"
echo ""
echo "3. XM"
echo "   URL: https://www.xm.com/mt4"
echo "   - Download 'MT4 for PC'"
echo ""
echo "4. FXCM"
echo "   URL: https://www.fxcm.com/uk/trading-platforms/metatrader-4/"
echo "   - Download 'MT4 Setup'"
echo ""
echo "5. Oanda"
echo "   URL: https://www.oanda.com/forex-trading/platform/download/"
echo "   - Select 'MT4' and 'Windows'"
echo ""

echo -e "${GREEN}Steps to get 32-bit MT4:${NC}"
echo "1. Visit one of the broker URLs above"
echo "2. Download MT4 for Windows (usually ~1-5MB installer)"
echo "3. Run the installer or extract the files"
echo "4. Find terminal.exe (usually in installation directory)"
echo "5. Copy terminal.exe to this project directory"
echo ""

# Check if terminal.exe exists
if [ -f "terminal.exe" ]; then
    echo -e "${YELLOW}Current terminal.exe found. Checking version...${NC}"
    
    # Check in container
    if docker ps | grep -q mt4-docker; then
        FILE_INFO=$(docker exec mt4-docker file /mt4/terminal.exe 2>/dev/null || echo "unknown")
        if echo "$FILE_INFO" | grep -q "PE32+"; then
            echo -e "${RED}✗ Current terminal.exe is 64-bit (PE32+)${NC}"
            echo -e "${RED}  You need to replace it with a 32-bit version${NC}"
        elif echo "$FILE_INFO" | grep -q "PE32"; then
            echo -e "${GREEN}✓ Current terminal.exe appears to be 32-bit${NC}"
        else
            echo -e "${YELLOW}⚠ Cannot determine version${NC}"
        fi
    fi
    
    # Show file size
    SIZE=$(ls -lh terminal.exe | awk '{print $5}')
    echo -e "  Size: $SIZE"
    echo ""
fi

echo -e "${BLUE}After downloading:${NC}"
echo "1. Replace terminal.exe:"
echo "   cp /path/to/downloaded/terminal.exe ./terminal.exe"
echo ""
echo "2. Restart MT4 Docker:"
echo "   ./bin/quick_start.sh"
echo ""
echo "3. Verify it works:"
echo "   ./bin/verify_startup.sh"
echo ""

echo -e "${YELLOW}Tips:${NC}"
echo "- 32-bit MT4 terminal.exe is usually 10-25MB"
echo "- If the installer is very small (<5MB), it might download files during install"
echo "- You can install MT4 in a Windows VM or Wine to extract terminal.exe"
echo "- Some brokers package both 32 and 64-bit - choose 32-bit/x86"