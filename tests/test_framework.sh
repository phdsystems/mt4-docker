#!/bin/bash

# MT4 Docker Test Framework
# Main test runner and utilities

# Removed set -e for debugging

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Test results array
declare -a TEST_RESULTS

# Test utilities
assert_equals() {
    local expected=$1
    local actual=$2
    local message=${3:-"Values should be equal"}
    
    if [[ "$expected" == "$actual" ]]; then
        pass "$message"
    else
        fail "$message: expected '$expected', got '$actual'"
    fi
}

assert_contains() {
    local haystack=$1
    local needle=$2
    local message=${3:-"Should contain substring"}
    
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$message"
    else
        fail "$message: '$haystack' does not contain '$needle'"
    fi
}

assert_file_exists() {
    local file=$1
    local message=${2:-"File should exist"}
    
    if [[ -f "$file" ]]; then
        pass "$message: $file"
    else
        fail "$message: $file"
    fi
}

assert_dir_exists() {
    local dir=$1
    local message=${2:-"Directory should exist"}
    
    if [[ -d "$dir" ]]; then
        pass "$message: $dir"
    else
        fail "$message: $dir"
    fi
}

assert_executable() {
    local file=$1
    local message=${2:-"File should be executable"}
    
    if [[ -x "$file" ]]; then
        pass "$message: $file"
    else
        fail "$message: $file"
    fi
}

assert_command_success() {
    local command=$1
    local message=${2:-"Command should succeed"}
    
    if eval "$command" > /dev/null 2>&1; then
        pass "$message"
    else
        fail "$message: $command"
    fi
}

assert_docker_running() {
    local container=$1
    local message=${2:-"Container should be running"}
    
    if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        pass "$message: $container"
    else
        fail "$message: $container"
    fi
}

# Test execution functions
pass() {
    local message=$1
    echo -e "  ${GREEN}✓${NC} $message"
    ((TESTS_PASSED++))
}

fail() {
    local message=$1
    echo -e "  ${RED}✗${NC} $message"
    ((TESTS_FAILED++))
    TEST_RESULTS+=("FAIL: $message")
}

skip() {
    local message=$1
    echo -e "  ${YELLOW}⚠${NC} $message (skipped)"
    ((TESTS_SKIPPED++))
}

# Test runner
run_test() {
    local test_name=$1
    local test_function=$2
    
    echo -e "\n${BLUE}Running:${NC} $test_name"
    ((TESTS_RUN++))
    
    # Run test function
    $test_function
}

# Setup and teardown
setup() {
    # Override in test files
    :
}

teardown() {
    # Override in test files
    :
}

# Test suite runner
run_test_suite() {
    local suite_name=$1
    local test_file=$2
    
    echo -e "\n${BLUE}═══ Test Suite: $suite_name ═══${NC}"
    
    # Export framework location for test files
    export TEST_FRAMEWORK_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/test_framework.sh"
    
    # Store current test functions before sourcing
    local before_functions=$(declare -F | grep "^declare -f test_" | awk '{print $3}' | sort)
    
    # Source the test file
    source "$test_file"
    
    # Run setup
    setup
    
    # Find new test functions after sourcing
    local after_functions=$(declare -F | grep "^declare -f test_" | awk '{print $3}' | sort)
    local test_functions=$(comm -13 <(echo "$before_functions") <(echo "$after_functions"))
    
    if [[ -z "$test_functions" ]]; then
        echo "No test functions found in $test_file"
    fi
    
    for test_func in $test_functions; do
        run_test "${test_func#test_}" "$test_func"
    done
    
    # Run teardown
    teardown
    
    # Unset test functions to prevent interference
    for test_func in $test_functions; do
        unset -f "$test_func" 2>/dev/null || true
    done
    unset -f setup teardown 2>/dev/null || true
}

# Final report
print_report() {
    echo -e "\n${BLUE}═══ Test Summary ═══${NC}"
    echo -e "Total tests run: $TESTS_RUN"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo -e "${YELLOW}Skipped: $TESTS_SKIPPED${NC}"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "\n${RED}Failed tests:${NC}"
        for result in "${TEST_RESULTS[@]}"; do
            echo "  - $result"
        done
        return 1
    else
        echo -e "\n${GREEN}All tests passed!${NC}"
        return 0
    fi
}

# Main test runner
main() {
    local test_patterns=("$@")
    if [[ ${#test_patterns[@]} -eq 0 ]]; then
        test_patterns=("tests/unit/*.test.sh" "tests/integration/*.test.sh")
    fi
    
    echo -e "${BLUE}MT4 Docker Test Runner${NC}"
    echo -e "Running tests matching: ${test_patterns[*]}\n"
    
    # Find and run all test files
    for pattern in "${test_patterns[@]}"; do
        for test_file in $pattern; do
            if [[ -f "$test_file" ]]; then
                run_test_suite "$(basename "$test_file" .test.sh)" "$test_file"
            fi
        done
    done
    
    # Print final report
    print_report
}

# Export functions for use in test files
export -f assert_equals assert_contains assert_file_exists assert_dir_exists
export -f assert_executable assert_command_success assert_docker_running
export -f pass fail skip run_test

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi