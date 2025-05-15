#!/bin/bash

echo "MT4 Docker Cleanup"
echo "================="
echo ""

read -p "Stop containers? (y/n): " stop
if [[ $stop =~ ^[Yy]$ ]]; then
    docker-compose down
fi

read -p "Remove images? (y/n): " images
if [[ $images =~ ^[Yy]$ ]]; then
    docker rmi mt4-docker-production_mt4
fi

echo "Cleanup complete!"
