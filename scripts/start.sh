#!/bin/bash

echo "[$(date)] Starting MT4..."

# Wait for display
sleep 5

# Setup environment
export DISPLAY=:99
export WINEPREFIX=/root/.wine
export WINEARCH=win32

# Check if terminal.exe exists
if [ ! -f "/mt4/terminal.exe" ]; then
    echo "ERROR: terminal.exe not found!"
    echo "Please copy terminal.exe to the mt4-docker-complete directory"
    sleep infinity
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
wine terminal.exe /portable /config:config.ini

# Keep container running
tail -f /dev/null
