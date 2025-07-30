#!/bin/bash

# Verify terminal.exe architecture

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "MT4 Terminal Verification"
echo "========================"
echo ""

if [ ! -f "terminal.exe" ]; then
    echo -e "${RED}Error: terminal.exe not found in current directory${NC}"
    exit 1
fi

# Get file size
SIZE=$(ls -lh terminal.exe | awk '{print $5}')
echo "File size: $SIZE"

# Check architecture using xxd (hex dump)
echo -n "Architecture: "
HEADER=$(xxd -p -l 2 terminal.exe)
if [ "$HEADER" = "4d5a" ]; then
    # It's a valid Windows executable, check PE header
    # Read bytes at offset 0x3c to find PE header location
    PE_OFFSET=$(xxd -s 0x3c -l 4 -e terminal.exe | awk '{print $2}' | sed 's/0x//')
    
    # Check if we can determine architecture
    if command -v od >/dev/null 2>&1; then
        # Read machine type from PE header (offset PE+4)
        MACHINE=$(od -An -tx2 -j $((0x$PE_OFFSET + 4)) -N 2 terminal.exe | tr -d ' ')
        
        case $MACHINE in
            "4c01")
                echo -e "${GREEN}32-bit (i386) - Compatible with MT4 Docker ✓${NC}"
                ARCH_OK=true
                ;;
            "6486")
                echo -e "${RED}64-bit (x86-64) - NOT compatible, need 32-bit version ✗${NC}"
                ARCH_OK=false
                ;;
            *)
                echo -e "${YELLOW}Unknown architecture${NC}"
                ARCH_OK=unknown
                ;;
        esac
    else
        echo -e "${YELLOW}Cannot determine architecture (tools missing)${NC}"
        ARCH_OK=unknown
    fi
else
    echo -e "${RED}Invalid executable file${NC}"
    exit 1
fi

echo ""

# Recommendations
if [ "$ARCH_OK" = "true" ]; then
    echo -e "${GREEN}This terminal.exe should work with MT4 Docker!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run: ./bin/quick_start.sh"
    echo "2. Connect via VNC to localhost:5900"
elif [ "$ARCH_OK" = "false" ]; then
    echo -e "${RED}This terminal.exe will NOT work with MT4 Docker${NC}"
    echo ""
    echo "You need a 32-bit version. Run:"
    echo "./bin/download_mt4_32bit.sh"
    echo ""
    echo "for download links and instructions"
else
    echo -e "${YELLOW}Could not verify architecture${NC}"
    echo "The file might work, but it's recommended to ensure you have 32-bit MT4"
fi