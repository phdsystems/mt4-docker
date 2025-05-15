#!/bin/bash

echo "MT4 Docker Quick Start"
echo "===================="

# Check for terminal.exe
if [ ! -f "terminal.exe" ]; then
    echo "WARNING: terminal.exe not found!"
    echo "You'll need to copy it later with:"
    echo "  ./scripts/utilities/copy_terminal.sh"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed!"
    echo "Please install Docker first"
    exit 1
fi

# Update permissions
chmod +x scripts/troubleshooting/*.sh
chmod +x scripts/utilities/*.sh

# Build and start
echo "Building Docker image..."
docker-compose build

echo "Starting containers..."
docker-compose up -d

echo "Waiting for services to start..."
sleep 15

# Copy terminal.exe if it exists
if [ -f "terminal.exe" ]; then
    echo "Copying terminal.exe to container..."
    docker cp terminal.exe mt4-docker:/mt4/terminal.exe
fi

# Run initial diagnostic
./scripts/troubleshooting/master_diagnostic.sh

echo ""
echo "Quick start complete!"
echo ""
echo "Next steps:"
echo "1. If terminal.exe is missing, copy it:"
echo "   ./scripts/utilities/copy_terminal.sh"
echo "2. Setup demo account:"
echo "   ./scripts/utilities/setup_demo_account.sh"
echo "3. Monitor:"
echo "   ./scripts/utilities/monitor.sh"
