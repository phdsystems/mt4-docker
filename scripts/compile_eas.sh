#!/bin/bash

echo "EA Compilation with MetaEditor"
echo "=============================="

cd /mt4

# List of EAs to compile
EAS=(
    "DataExporter"
    "SimpleMarketStreamer"
    "QuickDataStreamer"
    "MarketDataStreamer"
    "LegacyDataExporter"
    "AutoDeploy_EA"
    "SimpleTest"
)

echo "Starting compilation process..."
echo ""

for EA in "${EAS[@]}"; do
    MQ4_FILE="MQL4/Experts/$EA.mq4"
    EX4_FILE="MQL4/Experts/$EA.ex4"
    
    if [ -f "$MQ4_FILE" ]; then
        echo "Compiling $EA..."
        
        # Remove old compiled file if exists
        rm -f "$EX4_FILE"
        
        # Run MetaEditor to compile
        # MetaEditor syntax: /compile:"path" /log:"logpath" /s
        wine metaeditor.exe /compile:"$MQ4_FILE" /log:"compile_$EA.log" /s 2>/dev/null
        
        # Wait a moment for compilation
        sleep 2
        
        # Check if compiled successfully
        if [ -f "$EX4_FILE" ]; then
            echo "  ✓ $EA compiled successfully!"
            ls -lh "$EX4_FILE"
        else
            echo "  ✗ $EA compilation failed"
            # Check log if exists
            if [ -f "compile_$EA.log" ]; then
                echo "  Log output:"
                cat "compile_$EA.log" | head -10
            fi
        fi
        echo ""
    else
        echo "  ⚠ $EA.mq4 not found"
    fi
done

echo "Compilation process complete!"
echo ""
echo "Checking compiled EAs:"
find MQL4/Experts -name "*.ex4" -newer metaeditor.exe -exec ls -lh {} \;