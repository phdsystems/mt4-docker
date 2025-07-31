#!/bin/bash

echo "Force EA Compilation Script"
echo "=========================="

# List of EAs to compile
EAS=(
    "DataExporter"
    "SimpleMarketStreamer"
    "QuickDataStreamer"
    "MarketDataStreamer"
    "LegacyDataExporter"
)

for EA in "${EAS[@]}"; do
    echo "Processing $EA.mq4..."
    
    # Create a temporary modification to force recompilation
    docker exec mt4-docker bash -c "
        if [ -f /mt4/MQL4/Experts/$EA.mq4 ]; then
            # Add a space and remove it to trigger file change
            echo '' >> /mt4/MQL4/Experts/$EA.mq4
            sed -i '$ d' /mt4/MQL4/Experts/$EA.mq4
            echo '  ✓ Modified $EA.mq4'
        fi
    "
done

echo ""
echo "Files modified. MT4 should now compile them automatically."
echo "Check Navigator window in MT4 to see if EAs appear."