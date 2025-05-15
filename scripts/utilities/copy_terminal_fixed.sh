#!/bin/bash

echo "Copy & Start terminal.exe in MT4 Docker (Fixed)"
echo "============================================="
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

# Make sure terminal.exe is executable
docker exec $CONTAINER chmod +x /mt4/terminal.exe

# Verify copy
echo ""
echo "Verifying..."
if docker exec $CONTAINER test -f /mt4/terminal.exe; then
    echo "✓ Terminal.exe copied successfully"
    docker exec $CONTAINER ls -la /mt4/terminal.exe
else
    echo "✗ Failed to copy terminal.exe"
    exit 1
fi

# Check supervisor status and fix if needed
echo ""
echo "Checking supervisor..."
if ! docker exec $CONTAINER supervisorctl status > /dev/null 2>&1; then
    echo "Supervisor not running. Starting supervisor..."
    docker exec $CONTAINER bash -c 'service supervisor start || /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf &'
    sleep 5
fi

# Alternative: Start MT4 directly if supervisor fails
echo ""
echo "Starting MT4..."

# First, try with supervisor
if docker exec $CONTAINER supervisorctl status > /dev/null 2>&1; then
    echo "Using supervisor to start MT4..."
    docker exec $CONTAINER supervisorctl restart mt4 || true
else
    echo "Supervisor not available. Starting MT4 directly..."
    
    # Kill any existing MT4
    docker exec $CONTAINER pkill -f terminal.exe || true
    sleep 2
    
    # Start MT4 directly
    docker exec $CONTAINER bash -c 'cd /mt4 && DISPLAY=:99 wine terminal.exe /portable /config:config.ini &' || {
        echo "Direct start failed. Trying with start script..."
        docker exec $CONTAINER bash -c '/mt4/start_mt4.sh &' || {
            echo "Start script not found. Creating and running minimal start..."
            docker exec $CONTAINER bash -c 'cd /mt4 && export DISPLAY=:99 && wine terminal.exe /portable &'
        }
    }
fi

# Wait for MT4 to start
echo ""
echo "Waiting for MT4 to start..."
sleep 8

# Check if MT4 is running
echo ""
echo "Checking MT4 status..."
if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
    echo "✓ MT4 is running!"
    PID=$(docker exec $CONTAINER pgrep -f terminal.exe)
    echo "  Process ID: $PID"
    
    # Show process details
    docker exec $CONTAINER ps aux | grep terminal.exe | grep -v grep
    
    # Check EA status
    echo ""
    echo "EA Status:"
    if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_status.log 2>/dev/null; then
        echo "  $(docker exec $CONTAINER cat /mt4/MQL4/Files/ea_status.log)"
    else
        echo "  EA not active yet (needs valid login)"
    fi
else
    echo "✗ MT4 is not running"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if Xvfb is running:"
    docker exec $CONTAINER ps aux | grep Xvfb || echo "  Xvfb not running - starting..."
    docker exec $CONTAINER bash -c 'Xvfb :99 -screen 0 1024x768x16 &' || true
    
    echo ""
    echo "2. Check Wine environment:"
    docker exec $CONTAINER wine --version || echo "  Wine not installed properly"
    
    echo ""
    echo "3. Try manual start:"
    echo "   docker exec -it $CONTAINER bash"
    echo "   cd /mt4"
    echo "   DISPLAY=:99 wine terminal.exe"
fi

echo ""
echo "========================================="
echo "Next steps:"
echo ""
echo "1. Monitor MT4:"
echo "   ./scripts/utilities/monitor.sh"
echo ""
echo "2. Check full system:"
echo "   ./scripts/troubleshooting/master_diagnostic.sh"
echo ""
echo "3. View logs:"
echo "   ./scripts/utilities/view_logs.sh"
echo ""
echo "4. Manual debugging:"
echo "   docker exec -it $CONTAINER bash"
echo ""
echo "5. Check credentials in .env file"
echo "   EA won't compile without valid login!"
