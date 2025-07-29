#!/bin/bash

echo "MT4 Docker Quick Start"
echo "===================="

# Check for terminal.exe
if [ ! -f "terminal.exe" ]; then
    echo "ERROR: terminal.exe not found!"
    echo "Please copy your MT4 terminal.exe to this directory"
    exit 1
fi

# Update permissions
chmod +x scripts/*.sh

# Build and start
echo "Building Docker image..."
docker compose build

echo "Starting containers..."
docker compose up -d

echo "Waiting for services to start..."
sleep 10

# Check status
./check_status.sh

echo ""
echo "Quick start complete!"
echo "Monitor with: ./monitor.sh"
