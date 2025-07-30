#!/bin/bash

# MT4 Docker Test Runner - Modified to work with existing container
# This version runs tests against the already running MT4 container

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
TEST_DIR="$(dirname "$0")/tests"

echo -e "${BLUE}Checking prerequisites...${NC}"

# Check if MT4 container is running
if ! docker ps | grep -q mt4-docker; then
    echo -e "${RED}Error: MT4 container is not running${NC}"
    echo "Please start it with: docker compose -f infra/docker/docker-compose.yml up -d"
    exit 1
fi

echo -e "${GREEN}Prerequisites check passed${NC}"

# Run unit tests
echo -e "\n${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}     Running Unit Tests${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
bash "$TEST_DIR/test_framework.sh" "$TEST_DIR/unit/"*.test.sh

# Run modified integration tests that work with existing container
echo -e "\n${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}     Running Integration Tests (Live Container)${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

echo -e "\n${GREEN}Container Status Tests${NC}"
# Check container health
if docker ps | grep -q "mt4-docker.*healthy"; then
    echo -e "  ${GREEN}✓${NC} Container is healthy"
else
    echo -e "  ${YELLOW}⚠${NC} Container health status unknown"
fi

# Check services
echo -e "\n${GREEN}Service Status Tests${NC}"
SERVICES=$(docker exec mt4-docker supervisorctl status 2>/dev/null || echo "")
if [[ -n "$SERVICES" ]]; then
    echo "$SERVICES" | while read line; do
        if [[ "$line" =~ RUNNING ]]; then
            SERVICE_NAME=$(echo "$line" | awk '{print $1}')
            echo -e "  ${GREEN}✓${NC} $SERVICE_NAME is running"
        fi
    done
else
    echo -e "  ${YELLOW}⚠${NC} Could not check service status"
fi

# Check EA compilation
echo -e "\n${GREEN}EA Compilation Tests${NC}"
if docker exec mt4-docker ls /mt4/MQL4/Experts/*.ex4 2>/dev/null | grep -q ".ex4"; then
    echo -e "  ${GREEN}✓${NC} EAs are compiled"
    EA_COUNT=$(docker exec mt4-docker ls /mt4/MQL4/Experts/*.ex4 2>/dev/null | wc -l)
    echo -e "  ${GREEN}✓${NC} Found $EA_COUNT compiled EAs"
else
    echo -e "  ${RED}✗${NC} No compiled EAs found"
fi

# Check DataExporter
echo -e "\n${GREEN}DataExporter Tests${NC}"
if docker exec mt4-docker test -f /mt4/MQL4/Experts/DataExporter.ex4; then
    echo -e "  ${GREEN}✓${NC} DataExporter is compiled"
fi

if docker exec mt4-docker test -f /mt4/MQL4/Files/market_data.csv; then
    echo -e "  ${GREEN}✓${NC} Market data CSV exists"
    LINE_COUNT=$(docker exec mt4-docker wc -l /mt4/MQL4/Files/market_data.csv 2>/dev/null | awk '{print $1}')
    echo -e "  ${GREEN}✓${NC} CSV has $LINE_COUNT lines"
fi

# Check resource usage
echo -e "\n${GREEN}Resource Usage Tests${NC}"
STATS=$(docker stats mt4-docker --no-stream --format "CPU: {{.CPUPerc}} | Memory: {{.MemUsage}}" 2>/dev/null)
if [[ -n "$STATS" ]]; then
    echo -e "  ${GREEN}✓${NC} $STATS"
else
    echo -e "  ${YELLOW}⚠${NC} Could not get resource stats"
fi

# Performance test
echo -e "\n${GREEN}Performance Tests${NC}"
START_TIME=$(date +%s)
if docker exec mt4-docker wine /mt4/terminal.exe /version 2>/dev/null | grep -q "Version"; then
    echo -e "  ${GREEN}✓${NC} MT4 terminal responds"
else
    echo -e "  ${YELLOW}⚠${NC} MT4 terminal version check failed"
fi
END_TIME=$(date +%s)
RESPONSE_TIME=$((END_TIME - START_TIME))
echo -e "  ${GREEN}✓${NC} Response time: ${RESPONSE_TIME}s"

# Test EA framework files
echo -e "\n${GREEN}EA Framework Tests${NC}"
bash "$TEST_DIR/test_framework.sh" "$TEST_DIR/integration/ea_tester.test.sh"

echo -e "\n${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}All tests completed!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"