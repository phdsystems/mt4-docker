#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <EA_file.mq4>"
    exit 1
fi

EA_FILE=$1
CONTAINER="mt4-docker"

if [ ! -f "$EA_FILE" ]; then
    echo "Error: $EA_FILE not found!"
    exit 1
fi

echo "Deploying $EA_FILE..."
docker cp "$EA_FILE" "${CONTAINER}:/mt4/MQL4/Experts/"
docker exec $CONTAINER touch "/mt4/MQL4/Experts/$(basename $EA_FILE)"

echo "EA deployed!"
