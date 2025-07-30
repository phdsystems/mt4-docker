#!/bin/bash

echo "[$(date)] Starting MT4..."

# Wait for display
sleep 5

# Setup environment
export DISPLAY=:99
export WINEPREFIX=/root/.wine
export WINEARCH=win32

# Note: MT4 requires 32-bit Wine even for newer versions

# Check if terminal.exe exists
if [ ! -f "/mt4/terminal.exe" ]; then
    echo "ERROR: terminal.exe not found!"
    echo "Please copy terminal.exe to the mt4-docker-complete directory"
    echo "Container will exit in 30 seconds..."
    sleep 30
    exit 1
fi

cd /mt4

# Create configuration with environment variables
if [ -f "/mt4/config/server-config.ini" ]; then
    envsubst < /mt4/config/server-config.ini > /mt4/config.ini
fi

# Touch all .mq4 files to trigger compilation
find /mt4/MQL4 -name "*.mq4" -exec touch {} \;

# Start MT4
echo "Starting MT4 terminal..."
wine terminal.exe /portable /config:config.ini &
MT4_PID=$!

# Monitor MT4 process
while true; do
    if ! kill -0 $MT4_PID 2>/dev/null; then
        echo "[$(date)] MT4 process died, attempting restart..."
        wine terminal.exe /portable /config:config.ini &
        MT4_PID=$!
    fi
    sleep 30
done
