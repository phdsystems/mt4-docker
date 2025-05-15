#!/bin/bash

echo "Copy terminal.exe to MT4 Docker (Windows-safe)"
echo "============================================"
echo ""

CONTAINER="mt4-docker"

# Disable MSYS path conversion for Git Bash
export MSYS_NO_PATHCONV=1

# Get to project root
if [[ "$PWD" == */scripts/utilities ]]; then
    cd ../..
fi

# Check container
echo "Checking container..."
if ! docker ps | grep -q $CONTAINER; then
    echo "Container not running. Starting..."
    docker-compose up -d
    sleep 10
fi

# Find terminal.exe
echo "Looking for terminal.exe..."
if [ -f "terminal.exe" ]; then
    echo "Found: $(pwd)/terminal.exe"
    TERMINAL_PATH="./terminal.exe"
elif [ -f "terminal.exe" ]; then
    echo "Found in current directory"
    TERMINAL_PATH="terminal.exe"
else
    echo "ERROR: terminal.exe not found"
    echo "Current directory: $(pwd)"
    echo "Please copy terminal.exe here"
    exit 1
fi

# Copy using absolute container path
echo ""
echo "Copying to container..."
docker cp "$TERMINAL_PATH" ${CONTAINER}:/mt4/terminal.exe

# Verify with multiple methods
echo ""
echo "Verifying..."

# Method 1: Direct test
if docker exec $CONTAINER test -f /mt4/terminal.exe; then
    echo "✓ Verified with test command"
    SUCCESS=true
else
    echo "⚠ Test command failed"
    SUCCESS=false
fi

# Method 2: ls check
if docker exec $CONTAINER ls -la /mt4/terminal.exe >/dev/null 2>&1; then
    echo "✓ Verified with ls command"
    docker exec $CONTAINER ls -la /mt4/terminal.exe
    SUCCESS=true
else
    echo "⚠ ls command failed"
fi

# Method 3: Find check
echo ""
echo "Searching in container..."
FOUND=$(docker exec $CONTAINER find /mt4 -name "terminal.exe" 2>/dev/null)
if [ ! -z "$FOUND" ]; then
    echo "✓ Found at: $FOUND"
    SUCCESS=true
else
    echo "⚠ Not found with find command"
fi

if [ "$SUCCESS" = true ]; then
    echo ""
    echo "✓ Terminal.exe successfully copied!"
    echo ""
    echo "Restarting MT4..."
    docker exec $CONTAINER pkill -f terminal.exe || true
    sleep 2
    echo "Done!"
else
    echo ""
    echo "✗ Failed to verify terminal.exe in container"
    echo ""
    echo "Debug info:"
    docker exec $CONTAINER ls -la /mt4/
fi

echo ""
echo "Check status with:"
echo "  ./scripts/troubleshooting/master_diagnostic.sh"