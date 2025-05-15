#!/bin/bash

export MSYS_NO_PATHCONV=1

echo "MT4 Docker Service Restart"
echo "========================="
echo ""

CONTAINER="mt4-docker"

# Check if container is running
if ! docker ps | grep -q $CONTAINER; then
    echo "Container not running. Starting..."
    docker-compose up -d
    sleep 10
fi

echo "Restarting all services in container..."

# 1. Start Xvfb (virtual display)
echo "1. Starting Xvfb..."
docker exec $CONTAINER pkill Xvfb || true
docker exec $CONTAINER bash -c 'Xvfb :99 -screen 0 1024x768x16 -ac &'
sleep 2

# 2. Start x11vnc (VNC server)
echo "2. Starting VNC server..."
docker exec $CONTAINER pkill x11vnc || true
docker exec $CONTAINER bash -c 'x11vnc -display :99 -nopw -listen 0.0.0.0 -forever -shared &'
sleep 2

# 3. Start supervisor if not running
echo "3. Checking supervisor..."
if ! docker exec $CONTAINER supervisorctl status > /dev/null 2>&1; then
    echo "Starting supervisor..."
    docker exec $CONTAINER bash -c '/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf' || {
        echo "Supervisor failed to start. Services will run directly."
    }
    sleep 3
fi

# 4. Start MT4
echo "4. Starting MT4..."
docker exec $CONTAINER pkill -f terminal.exe || true
sleep 2

# Check if terminal.exe exists
if docker exec $CONTAINER test -f /mt4/terminal.exe; then
    echo "Found terminal.exe. Starting..."
    
    # Try supervisor first
    if docker exec $CONTAINER supervisorctl status > /dev/null 2>&1; then
        docker exec $CONTAINER supervisorctl restart mt4 || true
    else
        # Direct start
        docker exec $CONTAINER bash -c 'cd /mt4 && export DISPLAY=:99 && wine terminal.exe /portable /config:config.ini &'
    fi
    
    sleep 5
    
    # Verify MT4 is running
    if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
        echo "✓ MT4 started successfully"
        docker exec $CONTAINER ps aux | grep terminal.exe | grep -v grep
    else
        echo "✗ MT4 failed to start"
    fi
else
    echo "ERROR: terminal.exe not found in container"
    echo "Run: ./scripts/utilities/copy_terminal_fixed.sh"
fi

echo ""
echo "Service status:"
echo "--------------"
echo -n "Xvfb:    "
docker exec $CONTAINER pgrep Xvfb > /dev/null && echo "✓ Running" || echo "✗ Not running"
echo -n "VNC:     "
docker exec $CONTAINER pgrep x11vnc > /dev/null && echo "✓ Running" || echo "✗ Not running"
echo -n "MT4:     "
docker exec $CONTAINER pgrep -f terminal.exe > /dev/null && echo "✓ Running" || echo "✗ Not running"

echo ""
echo "Done! Use these commands:"
echo "  Monitor:     ./scripts/utilities/monitor.sh"
echo "  VNC access:  vncviewer localhost:5900"
echo "  Logs:        ./scripts/utilities/view_logs.sh"
