#!/bin/bash

echo "MT4 Docker Cleanup"
echo "================="
echo ""
echo "This will stop and remove containers."
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down
    echo "Cleanup complete"
else
    echo "Cleanup cancelled"
fi
