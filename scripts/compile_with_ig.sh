#!/bin/bash

echo "EA Compilation using IG Terminal"
echo "================================"

# Create a separate Wine prefix for 64-bit compilation
export WINEPREFIX=/root/.wine64
export WINEARCH=win64

# Copy the IG terminal for compilation
cp /workspace/mt4-docker/terminal_64bit.exe /mt4/terminal_compiler.exe

# Copy MQL4 files to compile
echo "Compiling EAs with IG terminal..."

# List of EAs to compile
EAS=(
    "DataExporter"
    "SimpleMarketStreamer"
    "QuickDataStreamer"
    "MarketDataStreamer"
    "LegacyDataExporter"
)

cd /mt4

for EA in "${EAS[@]}"; do
    if [ -f "MQL4/Experts/$EA.mq4" ]; then
        echo "Compiling $EA..."
        # Run terminal in compile mode
        timeout 30 wine terminal_compiler.exe /portable /compile:"MQL4/Experts/$EA.mq4" 2>/dev/null || true
        
        # Check if compiled
        if [ -f "MQL4/Experts/$EA.ex4" ]; then
            echo "  ✓ $EA compiled successfully"
        else
            echo "  ✗ $EA compilation failed"
        fi
    fi
done

# Clean up
rm -f terminal_compiler.exe

echo ""
echo "Compilation complete!"