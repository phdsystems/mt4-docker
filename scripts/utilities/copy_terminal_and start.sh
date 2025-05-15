#!/bin/bash

echo "Copy & Start terminal.exe in MT4 Docker"
echo "====================================="
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
    
    # Kill any existing MT4 process
    echo "Stopping any existing MT4 process..."
    docker exec $CONTAINER pkill -f terminal.exe || true
    sleep 2
    
    # Start MT4 using supervisor
    echo "Starting MT4 via supervisor..."
    docker exec $CONTAINER supervisorctl restart mt4
    
    # Wait and check if MT4 started
    echo "Waiting for MT4 to start..."
    sleep 5
    
    # Verify MT4 is running
    if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
        echo "✓ MT4 is now running!"
        PID=$(docker exec $CONTAINER pgrep -f terminal.exe)
        echo "  Process ID: $PID"
        
        # Check if it's actually processing
        sleep 3
        if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
            echo "✓ MT4 is stable and running"
        else
            echo "⚠ MT4 started but exited quickly"
            echo "  Checking logs..."
            docker exec $CONTAINER tail -10 /mt4/logs/mt4.log 2>/dev/null || echo "No logs available"
        fi
    else
        echo "✗ Failed to start MT4"
        echo ""
        echo "Checking supervisor status..."
        docker exec $CONTAINER supervisorctl status mt4
        echo ""
        echo "Checking Wine errors..."
        docker exec $CONTAINER tail -20 /mt4/logs/mt4.log 2>/dev/null | grep -i error || echo "No recent errors"
    fi
    
    # Show EA status if available
    echo ""
    echo "EA Status:"
    if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_status.log 2>/dev/null; then
        echo "  $(docker exec $CONTAINER cat /mt4/MQL4/Files/ea_status.log)"
    else
        echo "  EA not active yet"
    fi
    
else
    echo ""
    echo "✗ Failed to verify terminal.exe in container"
    echo ""
    echo "Debug info:"
    docker exec $CONTAINER ls -la /mt4/
fi

echo ""
echo "Commands:"
echo "  Monitor status:  ./scripts/utilities/monitor.sh"
echo "  Check system:    ./scripts/troubleshooting/master_diagnostic.sh"
echo "  View logs:       ./scripts/utilities/view_logs.sh"