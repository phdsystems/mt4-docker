#!/bin/bash

echo "MT4 Docker Status"
echo "================"
echo ""

CONTAINER="mt4-docker"

# Container status
if docker ps | grep -q $CONTAINER; then
    echo "✓ Container is running"
else
    echo "✗ Container is not running"
    exit 1
fi

# MT4 process
echo ""
if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null; then
    echo "✓ MT4 is running"
    docker exec $CONTAINER ps aux | grep terminal.exe | grep -v grep
else
    echo "✗ MT4 is not running"
fi

# EA compilation
echo ""
echo "EA Status:"
if docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.ex4; then
    echo "  ✓ AutoDeploy_EA is compiled"
else
    echo "  ⚠ AutoDeploy_EA not compiled yet"
fi

# EA activity
if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_status.log; then
    echo "  ✓ EA is active"
    echo "  Status: $(docker exec $CONTAINER cat /mt4/MQL4/Files/ea_status.log)"
else
    echo "  ⚠ No EA activity detected"
fi

# VNC status
echo ""
if nc -z localhost 5900 2>/dev/null; then
    echo "✓ VNC is accessible on port 5900"
else
    echo "⚠ VNC is not accessible"
fi
