#!/bin/bash

echo "Extracting MetaEditor from IG MT4"
echo "================================"

# Create temp directory
TEMP_DIR="/tmp/ig_mt4_extract"
mkdir -p $TEMP_DIR
cd $TEMP_DIR

# Download IG MT4 installer
echo "Downloading IG MT4 installer..."
wget -q "http://download.mql5.com/cdn/web/ig.group.limited/mt4/ig4setup.exe" -O ig4setup.exe

if [ ! -f ig4setup.exe ]; then
    echo "Failed to download IG MT4 installer"
    exit 1
fi

echo "Downloaded successfully"

# Try to extract using different methods
echo "Attempting to extract files..."

# Method 1: Try 7z
if command -v 7z >/dev/null 2>&1; then
    echo "Using 7z to extract..."
    7z x ig4setup.exe -oig_extract >/dev/null 2>&1
fi

# Method 2: Try unzip
if [ ! -d ig_extract ] && command -v unzip >/dev/null 2>&1; then
    echo "Using unzip to extract..."
    unzip -q ig4setup.exe -d ig_extract 2>/dev/null || true
fi

# Method 3: Try cabextract
if [ ! -d ig_extract ] && command -v cabextract >/dev/null 2>&1; then
    echo "Using cabextract to extract..."
    cabextract -d ig_extract ig4setup.exe 2>/dev/null || true
fi

# Method 4: Run installer with Wine to extract files
if [ ! -d ig_extract ]; then
    echo "Using Wine to extract installer..."
    mkdir -p ig_extract
    
    # Create a temporary Wine prefix
    export WINEPREFIX=$TEMP_DIR/wine_temp
    export WINEARCH=win64
    
    # Run installer in unattended mode
    timeout 30 wine ig4setup.exe /S /D=C:\\ig_mt4 2>/dev/null || true
    
    # Check if MetaEditor was extracted
    if [ -d "$WINEPREFIX/drive_c/ig_mt4" ]; then
        cp -r "$WINEPREFIX/drive_c/ig_mt4/"* ig_extract/ 2>/dev/null || true
    fi
fi

# Look for MetaEditor
echo ""
echo "Searching for MetaEditor..."
find . -name "metaeditor*.exe" -o -name "MetaEditor*.exe" 2>/dev/null | while read editor; do
    echo "Found: $editor"
    SIZE=$(ls -lh "$editor" | awk '{print $5}')
    echo "  Size: $SIZE"
done

# If we found MetaEditor in Wine prefix, copy it
EDITOR64="$WINEPREFIX/drive_c/ig_mt4/metaeditor64.exe"
EDITOR32="$WINEPREFIX/drive_c/ig_mt4/metaeditor.exe"

if [ -f "$EDITOR64" ]; then
    echo ""
    echo "Found 64-bit MetaEditor!"
    ls -lh "$EDITOR64"
    echo "This won't work with 32-bit Wine/MT4"
fi

if [ -f "$EDITOR32" ]; then
    echo ""
    echo "Found 32-bit MetaEditor!"
    ls -lh "$EDITOR32"
    cp "$EDITOR32" /workspace/mt4-docker/metaeditor.exe
    echo "Copied to /workspace/mt4-docker/metaeditor.exe"
fi

# Cleanup
echo ""
echo "Cleaning up temporary files..."
cd /
rm -rf $TEMP_DIR

echo "Done!"