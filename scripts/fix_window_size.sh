#!/bin/bash

# Fix MT4 window size
echo "Fixing MT4 window size..."

# Install xdotool if not present
docker exec mt4-docker bash -c "apt-get update && apt-get install -y xdotool wmctrl"

# Wait for MT4 window
sleep 2

# Get MT4 window ID and maximize it
docker exec mt4-docker bash -c "export DISPLAY=:99 && wmctrl -r 'Terminal' -b add,maximized_vert,maximized_horz"

# Alternative approach using xdotool
docker exec mt4-docker bash -c "export DISPLAY=:99 && xdotool search --name 'Terminal' windowsize %@ 1920 1080"

# Move window to top-left
docker exec mt4-docker bash -c "export DISPLAY=:99 && xdotool search --name 'Terminal' windowmove %@ 0 0"

echo "Window resize commands sent"