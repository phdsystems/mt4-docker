#!/bin/bash

# Deploy Market Data Streamer EA
# This script deploys and configures the market data streaming service

set -e

CONTAINER="mt4-docker"
EA_FILE="MarketDataStreamer.mq4"

echo "MT4 Market Data Streaming Setup"
echo "==============================="

# Check if container is running
if ! docker ps | grep -q $CONTAINER; then
    echo "Error: MT4 container is not running"
    echo "Please start the container with: ./bin/quick_start.sh"
    exit 1
fi

# Deploy the EA
echo "Deploying MarketDataStreamer EA..."
docker cp MQL4/Experts/$EA_FILE $CONTAINER:/mt4/MQL4/Experts/

# Create data directory
echo "Creating data directory..."
docker exec $CONTAINER mkdir -p /mt4/data

# Touch to trigger compilation
echo "Triggering EA compilation..."
docker exec $CONTAINER touch /mt4/MQL4/Experts/$EA_FILE

# Wait for compilation
echo "Waiting for compilation..."
sleep 5

# Check if compiled
if docker exec $CONTAINER test -f /mt4/MQL4/Experts/MarketDataStreamer.ex4; then
    echo "✓ EA compiled successfully"
else
    echo "✗ EA compilation failed"
    echo "Please check MT4 logs"
    exit 1
fi

echo ""
echo "Market Data Streamer deployed successfully!"
echo ""
echo "To use the streamer:"
echo "1. Open MT4 via VNC: ./bin/connect_vnc.sh"
echo "2. Attach MarketDataStreamer EA to a chart"
echo "3. Configure streaming settings in EA inputs"
echo ""
echo "Streaming options:"
echo "- File mode: Data saved to /mt4/data/market_data.csv"
echo "- Pipe mode: Named pipe 'MT4_MarketData'"
echo ""
echo "To access streamed data from host:"
echo "- File: docker exec $CONTAINER cat /mt4/data/market_data.csv"
echo "- Copy: docker cp $CONTAINER:/mt4/data/market_data.csv ./"
echo ""
echo "Client examples:"
echo "- Python: python3 clients/python/market_data_client.py"
echo "- Node.js: cd clients/nodejs && npm install && npm start"