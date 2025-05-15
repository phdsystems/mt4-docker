#!/bin/bash

echo "Connecting to MT4 via VNC..."

if ! command -v vncviewer &> /dev/null; then
    echo "VNC viewer not found. Please install:"
    echo "  Ubuntu: sudo apt-get install tigervnc-viewer"
    echo "  macOS: brew install tiger-vnc"
    exit 1
fi

vncviewer localhost:5900
