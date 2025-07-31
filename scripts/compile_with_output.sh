#!/bin/bash

echo "EA Compilation with MetaEditor (with explicit paths)"
echo "==================================================="

cd /mt4

# Create a test to see if MetaEditor is working
echo "Testing MetaEditor..."
wine metaeditor.exe /? 2>&1 | head -5 || echo "MetaEditor help not available"

echo ""
echo "Attempting compilation with different methods..."

# Method 1: Direct compilation
echo ""
echo "Method 1: Direct compilation of DataExporter"
wine metaeditor.exe /compile:"Z:\\mt4\\MQL4\\Experts\\DataExporter.mq4" 2>&1 | grep -v "fixme" | head -20

# Wait for any background processes
sleep 3

# Method 2: Using terminal.exe for compilation
echo ""
echo "Method 2: Using terminal.exe for compilation"
wine terminal.exe /portable /compile:"MQL4\\Experts\\DataExporter" 2>&1 | grep -v "fixme" | head -20

# Wait again
sleep 3

# Check results
echo ""
echo "Checking for compiled files:"
find MQL4/Experts -name "*.ex4" -type f -ls | tail -20

echo ""
echo "Checking MQL4 folders for any ex4 files:"
find MQL4 -name "*.ex4" -type f | wc -l
echo "ex4 files found"