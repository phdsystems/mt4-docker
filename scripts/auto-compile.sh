#!/bin/bash

# Wait for MT4 to start
sleep 30

echo "[$(date)] Auto-compile check starting..."

# Function to check if EA is compiled
check_compiled() {
    local ea_name=$1
    if [ -f "/mt4/MQL4/Experts/${ea_name}.ex4" ]; then
        echo "✓ ${ea_name} is compiled"
        return 0
    else
        echo "⚠ ${ea_name} not compiled, triggering compilation..."
        return 1
    fi
}

# Main monitoring loop
while true; do
    # Check if MT4 is running
    if pgrep -f terminal.exe > /dev/null; then
        # Check for uncompiled EAs
        for mq4_file in /mt4/MQL4/Experts/*.mq4; do
            if [ -f "$mq4_file" ]; then
                ea_name=$(basename "$mq4_file" .mq4)
                if ! check_compiled "$ea_name"; then
                    # Touch file to trigger recompilation
                    touch "$mq4_file"
                    echo "Touched $mq4_file to trigger compilation"
                fi
            fi
        done
        
        # Check for EA activity
        if [ -f "/mt4/MQL4/Files/ea_status.log" ]; then
            echo "EA Status: $(cat /mt4/MQL4/Files/ea_status.log)"
        fi
    else
        echo "[$(date)] MT4 not running, waiting..."
        # Exit if MT4 doesn't start within 5 minutes
        if [ $SECONDS -gt 300 ]; then
            echo "ERROR: MT4 failed to start within 5 minutes"
            exit 1
        fi
    fi
    
    sleep 60
done
