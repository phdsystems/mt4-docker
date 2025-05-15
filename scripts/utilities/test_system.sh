#!/bin/bash

CONTAINER="mt4-docker"

echo "MT4 Docker System Test"
echo "====================="
echo ""

echo "Running system test in container..."
docker exec $CONTAINER /mt4/test_system.sh

echo ""
echo "Checking file structure..."
docker exec $CONTAINER find /mt4/MQL4 -type f -name "*.mq4" -o -name "*.ex4"

echo ""
echo "Test complete!"
