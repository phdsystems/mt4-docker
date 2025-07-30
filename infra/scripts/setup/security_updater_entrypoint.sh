#!/bin/bash
# Entrypoint for security updater container

set -e

# Create necessary directories
mkdir -p /app/logs /app/config

# Setup environment
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Configure Docker socket permissions if mounted
if [ -S /var/run/docker.sock ]; then
    chmod 666 /var/run/docker.sock || true
fi

# Initialize log file
touch /app/logs/security-updates.log
touch /app/logs/cron.log

# Run initial security check on startup
echo "Running initial security check..."
/app/scripts/security_monitor.py >> /app/logs/security-updates.log 2>&1

# If running as a one-shot command
if [ "$1" = "check" ]; then
    exec /app/scripts/security_updates.sh
elif [ "$1" = "monitor" ]; then
    exec python3 /app/scripts/security_monitor.py
else
    # Default: run cron daemon
    echo "Starting security update scheduler..."
    echo "Logs: /app/logs/security-updates.log"
    exec "$@"
fi