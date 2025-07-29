#!/bin/bash

echo "MT4 Demo Terminal Downloader"
echo "==========================="

# Function to download and extract MT4
download_mt4() {
    echo "Downloading MT4 installer..."
    
    # Create temp directory
    mkdir -p mt4_temp
    cd mt4_temp
    
    # Download MT4 installer from MetaQuotes
    if command -v wget &> /dev/null; then
        wget -q --show-progress https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe
    elif command -v curl &> /dev/null; then
        curl -L -o mt4setup.exe https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe
    else
        echo "ERROR: wget or curl required"
        exit 1
    fi
    
    # Try to extract with different methods
    if command -v 7z &> /dev/null; then
        echo "Extracting with 7zip..."
        7z x -y mt4setup.exe > /dev/null 2>&1
        
        # Look for terminal.exe
        if find . -name "terminal.exe" -type f | head -1 | xargs -I {} cp {} ../terminal.exe 2>/dev/null; then
            echo "✓ terminal.exe extracted successfully!"
        fi
    elif command -v wine &> /dev/null; then
        echo "Using Wine to extract..."
        echo "Please follow installer and close when done..."
        wine mt4setup.exe
        
        # Try to find installed terminal.exe
        find ~/.wine -name "terminal.exe" -type f 2>/dev/null | head -1 | xargs -I {} cp {} ../terminal.exe
    else
        echo "Please install p7zip-full or wine to extract:"
        echo "  Ubuntu/Debian: sudo apt install p7zip-full"
        echo "  Or: sudo apt install wine"
        cd ..
        rm -rf mt4_temp
        exit 1
    fi
    
    # Cleanup
    cd ..
    rm -rf mt4_temp
    
    # Check if successful
    if [ -f "terminal.exe" ]; then
        echo ""
        echo "✓ Success! terminal.exe is ready"
        echo ""
        echo "Next steps:"
        echo "1. Get a demo account from any broker:"
        echo "   - IC Markets: https://www.icmarkets.com"
        echo "   - XM: https://www.xm.com"
        echo "   - Pepperstone: https://pepperstone.com"
        echo ""
        echo "2. Create .env file:"
        echo "   cp .env.example .env"
        echo ""
        echo "3. Edit .env with your demo credentials"
        echo ""
        echo "4. Run: ./quick_start.sh"
    else
        echo "Failed to extract terminal.exe"
        echo "Try manual download from a broker"
    fi
}

# Create demo .env if it doesn't exist
create_demo_env() {
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        echo ""
        echo "Creating demo .env file..."
        cat > .env << EOF
# Demo Account Configuration
# Update these with your actual demo credentials
MT4_LOGIN=YOUR_DEMO_LOGIN
MT4_PASSWORD=YOUR_DEMO_PASSWORD
MT4_SERVER=ICMarketsSC-Demo01
VNC_PASSWORD=demo_vnc_123
EOF
        echo "✓ Created .env with demo template"
        echo "  Please update with your demo account details"
    fi
}

# Main execution
if [ -f "terminal.exe" ]; then
    echo "terminal.exe already exists!"
    echo "Delete it first if you want to download again"
else
    download_mt4
fi

create_demo_env

echo ""
echo "Demo terminal setup complete!"
echo "See GET_DEMO_MT4.md for broker-specific instructions"