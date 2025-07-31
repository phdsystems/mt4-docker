#!/bin/bash

# This script runs inside the container to resize MT4 window

export DISPLAY=:99

# Wait for MT4 window to appear
echo "Waiting for MT4 window..."
for i in {1..30}; do
    if xdotool search --name "Terminal" >/dev/null 2>&1; then
        echo "MT4 window found!"
        break
    fi
    sleep 1
done

# Try multiple methods to maximize the window
echo "Resizing MT4 window..."

# Method 1: Use xdotool to resize
WINDOW_ID=$(xdotool search --name "Terminal" | head -1)
if [ ! -z "$WINDOW_ID" ]; then
    echo "Found window ID: $WINDOW_ID"
    
    # Move to top-left corner
    xdotool windowmove $WINDOW_ID 0 0
    
    # Resize to full screen
    xdotool windowsize $WINDOW_ID 1920 1080
    
    # Try to maximize
    xdotool key --window $WINDOW_ID alt+F10
    
    # Alternative maximize
    xdotool windowactivate $WINDOW_ID
    xdotool key --clearmodifiers alt+space x
fi

# Method 2: Use wmctrl
wmctrl -r "Terminal" -b add,maximized_vert,maximized_horz

# Method 3: Send F11 for fullscreen
xdotool key --window $WINDOW_ID F11

echo "Window resize complete"