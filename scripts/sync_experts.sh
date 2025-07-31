#!/bin/bash

echo "[$(date)] Syncing Expert Advisors..."

# Define the list of EAs we want to keep
KEEP_EAS=(
    "AutoDeploy_EA"
    "EATester"
    "StreamingPlatform_test"
)

# Remove all .ex4 and .mq4 files except the ones we want to keep
cd /mt4/MQL4/Experts

for file in *.mq4 *.ex4; do
    if [ -f "$file" ]; then
        base_name="${file%.*}"
        keep=false
        
        for keeper in "${KEEP_EAS[@]}"; do
            if [ "$base_name" = "$keeper" ]; then
                keep=true
                break
            fi
        done
        
        if [ "$keep" = false ]; then
            echo "Removing: $file"
            rm -f "$file"
        else
            echo "Keeping: $file"
        fi
    fi
done

echo "[$(date)] Expert Advisors sync complete"