#!/bin/bash
# Deploy pre-compiled EA to MT4

EA_PATH=$1
EA_NAME=$(basename "$EA_PATH")

if [ -z "$EA_PATH" ]; then
    echo "Usage: $0 <path_to_compiled_ea.ex4>"
    exit 1
fi

if [ ! -f "$EA_PATH" ]; then
    echo "Error: EA file not found: $EA_PATH"
    exit 1
fi

# Copy to container
docker cp "$EA_PATH" mt4-docker:/mt4/MQL4/Experts/

# Set permissions
docker exec mt4-docker chmod 644 "/mt4/MQL4/Experts/$EA_NAME"

echo "EA deployed: $EA_NAME"
echo "Now connect via VNC to attach it to a chart"