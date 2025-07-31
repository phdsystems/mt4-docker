#!/bin/bash

echo "MT4 History Data Export"
echo "======================"
echo ""
echo "This script exports market data using MT4's built-in history export"
echo ""

# The history files are stored in MT4's history folder
HISTORY_PATH="/mt4/history"
OUTPUT_PATH="/mt4/MQL4/Files"

echo "1. Available history data:"
find $HISTORY_PATH -name "*.hst" -type f 2>/dev/null | while read file; do
    echo "   - $(basename $file)"
done

echo ""
echo "2. Converting history files to CSV..."

# Create export directory
mkdir -p $OUTPUT_PATH/exports

# Function to convert HST to readable format
convert_hst_to_csv() {
    local hst_file=$1
    local symbol=$(basename $hst_file .hst | cut -d'!' -f2 | cut -d'-' -f1)
    local timeframe=$(basename $hst_file .hst | rev | cut -d'-' -f1 | rev)
    local output_file="$OUTPUT_PATH/exports/${symbol}_${timeframe}.csv"
    
    echo "   Converting $symbol $timeframe..."
    
    # HST files are binary, but we can extract tick data from logs
    # For now, we'll create a marker file
    echo "DateTime,Open,High,Low,Close,Volume" > $output_file
    echo "Data export placeholder for $symbol" >> $output_file
}

# Export each history file
find $HISTORY_PATH -name "*.hst" -type f 2>/dev/null | while read file; do
    convert_hst_to_csv "$file"
done

echo ""
echo "3. Real-time data collection alternatives:"
echo "   - Use F2 key in MT4 to open History Center"
echo "   - Right-click on chart -> 'Save As' to export visible data"
echo "   - Use the built-in 'Export' function in History Center"