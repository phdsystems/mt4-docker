#!/bin/bash

# Script to set up auto-loading EA without VNC

EA_NAME=${1:-"Moving Average"}
SYMBOL=${2:-"EURUSD"}
PERIOD=${3:-"H1"}

echo "Setting up auto-load for: $EA_NAME on $SYMBOL $PERIOD"

# Create a startup configuration
cat > config/startup.ini << EOF
[Startup]
Expert=Experts\\${EA_NAME}
ExpertParameters=
Symbol=${SYMBOL}
Period=${PERIOD}
EOF

# Copy to container
docker cp config/startup.ini mt4-docker:/mt4/config/

echo "Configuration updated. Restart MT4 to apply:"
echo "docker compose restart"