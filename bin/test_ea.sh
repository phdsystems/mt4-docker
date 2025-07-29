#!/bin/bash

# EA Testing Script
# Runs EA tests in the MT4 container

set -e

CONTAINER="mt4-docker"
EA_FILE="${1:-EATester.mq4}"
TEST_MODE="${2:-ALL}"
REPORT_DIR="./test_reports"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}MT4 EA Testing Framework${NC}"
echo "========================"

# Check if container is running
if ! docker ps | grep -q $CONTAINER; then
    echo -e "${RED}Error: MT4 container is not running${NC}"
    echo "Please start the container with: ./bin/quick_start.sh"
    exit 1
fi

# Create report directory
mkdir -p "$REPORT_DIR"

# Check if EA file exists
if [[ ! "$EA_FILE" =~ \.mq4$ ]]; then
    EA_FILE="${EA_FILE}.mq4"
fi

if ! docker exec $CONTAINER test -f "/mt4/MQL4/Experts/$EA_FILE"; then
    echo -e "${RED}Error: EA file not found: $EA_FILE${NC}"
    echo "Available EAs:"
    docker exec $CONTAINER ls /mt4/MQL4/Experts/*.mq4 2>/dev/null | xargs -n1 basename
    exit 1
fi

echo -e "Testing EA: ${GREEN}$EA_FILE${NC}"
echo -e "Test Mode: ${GREEN}$TEST_MODE${NC}"

# Deploy EATester if needed
if [[ "$EA_FILE" == "EATester.mq4" ]] && ! docker exec $CONTAINER test -f /mt4/MQL4/Experts/EATester.mq4; then
    echo "Deploying EATester..."
    docker cp MQL4/Experts/EATester.mq4 $CONTAINER:/mt4/MQL4/Experts/
fi

# Deploy test framework if needed
if ! docker exec $CONTAINER test -f /mt4/MQL4/Include/EATestFramework.mqh; then
    echo "Deploying test framework..."
    docker cp MQL4/Include/EATestFramework.mqh $CONTAINER:/mt4/MQL4/Include/
fi

# Create test configuration file
cat > /tmp/ea_test_config.ini << EOF
[Test]
Expert=$EA_FILE
Symbol=EURUSD
Period=H1
TestMode=$TEST_MODE
CreateReport=true
VerboseOutput=true
EOF

# Copy configuration to container
docker cp /tmp/ea_test_config.ini $CONTAINER:/mt4/ea_test_config.ini
rm /tmp/ea_test_config.ini

# Clear previous test results
docker exec $CONTAINER rm -f /mt4/MQL4/Files/ea_test_*.txt 2>/dev/null || true

echo -e "\n${YELLOW}Running EA tests...${NC}"

# Touch the EA file to trigger recompilation
docker exec $CONTAINER touch "/mt4/MQL4/Experts/$EA_FILE"

# Wait for compilation
echo "Waiting for EA compilation..."
sleep 5

# Check compilation status
COMPILED_FILE="${EA_FILE%.mq4}.ex4"
if ! docker exec $CONTAINER test -f "/mt4/MQL4/Experts/$COMPILED_FILE"; then
    echo -e "${RED}Error: EA compilation failed${NC}"
    echo "Checking compilation log..."
    docker exec $CONTAINER tail -n 20 /mt4/MQL4/Logs/*.log 2>/dev/null | grep -i error || true
    exit 1
fi

echo -e "${GREEN}EA compiled successfully${NC}"

# Monitor test execution
echo -e "\nMonitoring test execution..."
TIMEOUT=60
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Check if test completed
    if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_test_complete.txt 2>/dev/null; then
        echo -e "\n${GREEN}Tests completed!${NC}"
        break
    fi
    
    # Show progress
    printf "."
    sleep 2
    ((ELAPSED+=2))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "\n${YELLOW}Test timeout reached${NC}"
fi

# Retrieve test results
echo -e "\n${GREEN}Retrieving test results...${NC}"

# Copy test reports
docker exec $CONTAINER ls /mt4/MQL4/Files/ea_test_*.txt 2>/dev/null | while read -r file; do
    basename=$(basename "$file")
    docker cp "$CONTAINER:$file" "$REPORT_DIR/$basename"
    echo "  - Retrieved: $basename"
done

# Copy main report if exists
if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_test_report.txt; then
    docker cp $CONTAINER:/mt4/MQL4/Files/ea_test_report.txt "$REPORT_DIR/"
    echo -e "\n${GREEN}Test Report:${NC}"
    echo "============"
    cat "$REPORT_DIR/ea_test_report.txt"
fi

# Show summary from completion marker
if docker exec $CONTAINER test -f /mt4/MQL4/Files/ea_test_complete.txt; then
    echo -e "\n${GREEN}Test Summary:${NC}"
    docker exec $CONTAINER cat /mt4/MQL4/Files/ea_test_complete.txt
fi

# Archive reports with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_NAME="ea_test_${EA_FILE%.mq4}_${TIMESTAMP}.tar.gz"
cd "$REPORT_DIR" && tar -czf "../$ARCHIVE_NAME" *.txt 2>/dev/null && cd ..

if [ -f "$ARCHIVE_NAME" ]; then
    echo -e "\n${GREEN}Test reports archived: $ARCHIVE_NAME${NC}"
fi

echo -e "\n${GREEN}EA testing completed!${NC}"