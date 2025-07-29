#!/bin/bash

# MT4 Docker Test Runner
# Main script to run all tests

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
TEST_DIR="$(dirname "$0")/tests"
COVERAGE_DIR="$TEST_DIR/coverage"

# Parse command line arguments
TEST_TYPE="${1:-all}"
VERBOSE="false"

# Check for verbose flag
if [[ "$2" == "verbose" ]] || [[ "$1" == "verbose" ]]; then
    VERBOSE="true"
fi

# Print usage
usage() {
    echo "Usage: $0 [test-type] [verbose]"
    echo ""
    echo "Test types:"
    echo "  all         - Run all tests (default)"
    echo "  unit        - Run unit tests only"
    echo "  integration - Run integration tests only"
    echo "  quick       - Run unit tests only (alias for unit)"
    echo ""
    echo "Options:"
    echo "  verbose     - Show detailed test output"
    echo ""
    echo "Examples:"
    echo "  $0                  # Run all tests"
    echo "  $0 unit             # Run unit tests only"
    echo "  $0 integration true # Run integration tests with verbose output"
}

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon is not running${NC}"
        exit 1
    fi
    
    # Check test framework
    if [[ ! -f "$TEST_DIR/test_framework.sh" ]]; then
        echo -e "${RED}Error: Test framework not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Prerequisites check passed${NC}"
}

# Run unit tests
run_unit_tests() {
    echo -e "\n${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}     Running Unit Tests${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    
    if [[ "$VERBOSE" == "true" ]]; then
        bash "$TEST_DIR/test_framework.sh" "$TEST_DIR/unit/"*.test.sh
    else
        bash "$TEST_DIR/test_framework.sh" "$TEST_DIR/unit/"*.test.sh
    fi
}

# Run integration tests
run_integration_tests() {
    echo -e "\n${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}     Running Integration Tests${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    
    # Build test image first
    echo -e "\n${YELLOW}Building test image...${NC}"
    if docker build -t mt4-docker-test . > /dev/null 2>&1; then
        echo -e "${GREEN}Test image built successfully${NC}"
    else
        echo -e "${RED}Failed to build test image${NC}"
        return 1
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        bash "$TEST_DIR/test_framework.sh" "$TEST_DIR/integration/"*.test.sh
    else
        bash "$TEST_DIR/test_framework.sh" "$TEST_DIR/integration/"*.test.sh
    fi
    
    # Cleanup test containers
    echo -e "\n${YELLOW}Cleaning up test containers...${NC}"
    docker compose -p test down -v 2>/dev/null || true
    docker container prune -f > /dev/null 2>&1
}

# Generate coverage report
generate_coverage() {
    echo -e "\n${BLUE}Generating coverage report...${NC}"
    
    mkdir -p "$COVERAGE_DIR"
    
    # Simple coverage: count tested vs total functions
    local total_scripts=$(find bin scripts -name "*.sh" -type f | wc -l)
    local tested_scripts=$(grep -h "assert_.*" tests/unit/*.test.sh tests/integration/*.test.sh | grep -oE "bin/[^\"']+|scripts/[^\"']+" | sort -u | wc -l)
    
    local coverage=$((tested_scripts * 100 / total_scripts))
    
    cat > "$COVERAGE_DIR/report.txt" << EOF
MT4 Docker Test Coverage Report
==============================

Total scripts: $total_scripts
Scripts with tests: $tested_scripts
Coverage: $coverage%

Timestamp: $(date)
EOF
    
    echo -e "${GREEN}Coverage: $coverage%${NC}"
}

# Main execution
main() {
    case "$TEST_TYPE" in
        all)
            check_prerequisites
            run_unit_tests
            local unit_exit=$?
            run_integration_tests
            local integration_exit=$?
            generate_coverage
            
            if [[ $unit_exit -eq 0 && $integration_exit -eq 0 ]]; then
                echo -e "\n${GREEN}All tests completed successfully!${NC}"
                exit 0
            else
                echo -e "\n${RED}Some tests failed!${NC}"
                exit 1
            fi
            ;;
        unit|quick)
            check_prerequisites
            run_unit_tests
            exit $?
            ;;
        integration)
            check_prerequisites
            run_integration_tests
            exit $?
            ;;
        -h|--help|help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
            usage
            exit 1
            ;;
    esac
}

# Run main
main