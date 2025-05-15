#!/bin/bash

echo "MT4 Docker Monitor"
echo "=================="
echo "Press Ctrl+C to stop"
echo ""

CONTAINER="mt4-docker"

# Function to check EA status
check_ea_status() {
    if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_status.log 2>/dev/null; then
        status=$(docker exec $CONTAINER cat /mt4/MQL4/Files/ea_status.log 2>/dev/null)
        echo "EA Status: $status"
    else
        echo "EA Status: Not running"
    fi
}

# Main monitoring loop
while true; do
    clear
    echo "MT4 Docker Monitor - $(date)"
    echo "============================="
    echo ""
    
    # Container status
    if docker ps | grep -q $CONTAINER; then
        echo "Container: ✓ Running"
    else
        echo "Container: ✗ Not running"
    fi
    
    # MT4 process
    if docker exec $CONTAINER pgrep -f terminal.exe > /dev/null 2>&1; then
        echo "MT4:       ✓ Running"
    else
        echo "MT4:       ✗ Not running"
    fi
    
    # EA compilation
    if docker exec $CONTAINER test -f /mt4/MQL4/Experts/AutoDeploy_EA.ex4 2>/dev/null; then
        echo "EA:        ✓ Compiled"
    else
        echo "EA:        ⚠ Not compiled"
    fi
    
    echo ""
    check_ea_status
    
    # Show recent activity
    echo ""
    echo "Recent Activity:"
    if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_activity.log 2>/dev/null; then
        docker exec $CONTAINER tail -3 /mt4/MQL4/Files/ea_activity.log 2>/dev/null
    else
        echo "No activity log found"
    fi
    
    sleep 5
done
