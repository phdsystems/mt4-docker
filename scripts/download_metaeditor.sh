#!/bin/bash

echo "Downloading MT4 with MetaEditor"
echo "=============================="
echo ""

# Try IC Markets MT4 which usually includes full package
echo "Downloading IC Markets MT4..."
wget -q "https://download.mql5.com/cdn/web/international.capital.markets.pty.ltd/mt4/icmarkets4setup.exe" -O icmarkets_mt4.exe

if [ -f icmarkets_mt4.exe ]; then
    echo "Downloaded IC Markets MT4 setup"
    
    # Extract using 7z
    echo "Extracting files..."
    7z x icmarkets_mt4.exe -oic_extract -y >/dev/null 2>&1
    
    # Look for metaeditor
    echo "Searching for MetaEditor..."
    find ic_extract -name "*etaeditor*" -type f 2>/dev/null | while read file; do
        echo "Found: $file"
        # Check if it's 32-bit
        if [[ "$file" == *"metaeditor.exe"* ]] && [[ "$file" != *"64"* ]]; then
            echo "  This appears to be 32-bit MetaEditor"
            cp "$file" /workspace/mt4-docker/metaeditor.exe
            echo "  Copied to /workspace/mt4-docker/metaeditor.exe"
        fi
    done
    
    # Cleanup
    rm -rf ic_extract icmarkets_mt4.exe
else
    echo "Failed to download IC Markets MT4"
fi

# If that didn't work, try XM
if [ ! -f /workspace/mt4-docker/metaeditor.exe ]; then
    echo ""
    echo "Trying XM MT4..."
    wget -q "https://download.mql5.com/cdn/web/xm.global.limited/mt4/xmglobal4setup.exe" -O xm_mt4.exe
    
    if [ -f xm_mt4.exe ]; then
        echo "Downloaded XM MT4 setup"
        7z x xm_mt4.exe -oxm_extract -y >/dev/null 2>&1
        
        find xm_extract -name "*etaeditor*" -type f 2>/dev/null | while read file; do
            echo "Found: $file"
            if [[ "$file" == *"metaeditor.exe"* ]] && [[ "$file" != *"64"* ]]; then
                echo "  This appears to be 32-bit MetaEditor"
                cp "$file" /workspace/mt4-docker/metaeditor.exe
                echo "  Copied to /workspace/mt4-docker/metaeditor.exe"
            fi
        done
        
        rm -rf xm_extract xm_mt4.exe
    fi
fi

# Check result
if [ -f /workspace/mt4-docker/metaeditor.exe ]; then
    echo ""
    echo "Success! MetaEditor extracted:"
    ls -lh /workspace/mt4-docker/metaeditor.exe
else
    echo ""
    echo "Could not extract MetaEditor from installers."
    echo "The installers might be self-extracting executables that need to be run."
fi