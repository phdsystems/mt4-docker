#!/bin/bash

echo "Starting MT4 Web Data Interface"
echo "=============================="
echo ""

# Create network if it doesn't exist
docker network create mt4_network 2>/dev/null || true

# Update the main docker-compose to use the network
echo "Updating MT4 container to use shared network..."
docker network connect mt4_network mt4-docker 2>/dev/null || true

# Create a shared volume for data
echo "Creating shared data volume..."
docker volume create mt4_data 2>/dev/null || true

# Copy existing data to shared volume
echo "Syncing data files..."
docker exec mt4-docker sh -c "cp -r /mt4/MQL4/Files/* /mt4_shared/ 2>/dev/null || true"

# Start the web interface
echo "Starting web server..."
docker compose -f infra/docker/docker-compose.web.yml up -d

# Wait for startup
sleep 5

# Check if running
if docker ps | grep -q mt4-web; then
    echo ""
    echo "✅ Web interface started successfully!"
    echo ""
    echo "Access the interface at:"
    echo "  http://localhost:8080"
    echo ""
    echo "API endpoints:"
    echo "  http://localhost:8080/api/files     - List CSV files"
    echo "  http://localhost:8080/api/latest    - Get latest data"
    echo "  http://localhost:8080/health        - Health check"
    echo ""
    echo "To stop: docker compose -f infra/docker/docker-compose.web.yml down"
else
    echo "❌ Failed to start web interface"
    echo "Check logs: docker logs mt4-web"
fi