#!/bin/bash

export DISPLAY=:99

# Function to wait for window
wait_for_window() {
    local window_name=$1
    local max_attempts=30
    
    for i in $(seq 1 $max_attempts); do
        if xdotool search --name "$window_name" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

# Function to resize window properly
resize_window() {
    local window_name=$1
    local width=$2
    local height=$3
    
    # Get window ID
    local window_id=$(xdotool search --name "$window_name" | head -1)
    
    if [ ! -z "$window_id" ]; then
        # Unmaximize first
        wmctrl -i -r $window_id -b remove,maximized_vert,maximized_horz
        
        # Move to top-left
        xdotool windowmove $window_id 0 0
        
        # Set size
        xdotool windowsize $window_id $width $height
        
        # Activate window
        xdotool windowactivate $window_id
        
        return 0
    fi
    return 1
}

# Main loop
while true; do
    # Wait for login window
    if wait_for_window "Login"; then
        echo "Login window detected, resizing..."
        resize_window "Login" 640 480
    fi
    
    # Wait for main MT4 window
    if wait_for_window "MetaTrader"; then
        echo "MT4 window detected, resizing..."
        resize_window "MetaTrader" 1900 1060
    fi
    
    sleep 5
done