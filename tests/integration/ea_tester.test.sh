#!/bin/bash

# Integration tests for EA Tester functionality

# Framework is loaded by test runner

setup() {
    export ORIGINAL_DIR=$(pwd)
    cd /workspace/mt4-docker
    
    # Ensure test EA files exist
    if [[ ! -f "MQL4/Experts/EATester.mq4" ]]; then
        echo "Warning: EATester.mq4 not found, skipping some tests"
    fi
}

teardown() {
    cd "$ORIGINAL_DIR"
}

test_ea_tester_exists() {
    assert_file_exists "MQL4/Experts/EATester.mq4" "EATester EA should exist"
}

test_ea_test_framework_exists() {
    assert_file_exists "MQL4/Include/EATestFramework.mqh" "EA Test Framework include should exist"
}

test_test_ea_script_exists() {
    assert_file_exists "bin/test_ea.sh" "test_ea.sh script should exist"
    assert_executable "bin/test_ea.sh" "test_ea.sh should be executable"
}

test_ea_tester_structure() {
    if [[ ! -f "MQL4/Experts/EATester.mq4" ]]; then
        skip "EATester.mq4 not found"
        return
    fi
    
    local content=$(cat MQL4/Experts/EATester.mq4)
    
    # Check for test modes
    assert_contains "$content" "TEST_MODE_BASIC" "Should have basic test mode"
    assert_contains "$content" "TEST_MODE_TRADING" "Should have trading test mode"
    assert_contains "$content" "TEST_MODE_INDICATORS" "Should have indicators test mode"
    assert_contains "$content" "TEST_MODE_PERFORMANCE" "Should have performance test mode"
    
    # Check for test functions
    assert_contains "$content" "RunBasicTests" "Should have basic tests function"
    assert_contains "$content" "RunTradingTests" "Should have trading tests function"
    assert_contains "$content" "RunIndicatorTests" "Should have indicator tests function"
    assert_contains "$content" "TestCase" "Should have test case function"
}

test_ea_test_framework_structure() {
    if [[ ! -f "MQL4/Include/EATestFramework.mqh" ]]; then
        skip "EATestFramework.mqh not found"
        return
    fi
    
    local content=$(cat MQL4/Include/EATestFramework.mqh)
    
    # Check for test suite class
    assert_contains "$content" "class CTestSuite" "Should have test suite class"
    
    # Check for assertions
    assert_contains "$content" "AssertTrue" "Should have AssertTrue method"
    assert_contains "$content" "AssertFalse" "Should have AssertFalse method"
    assert_contains "$content" "AssertEquals" "Should have AssertEquals method"
    assert_contains "$content" "AssertGreater" "Should have AssertGreater method"
    
    # Check for utilities
    assert_contains "$content" "CTestDataGenerator" "Should have test data generator"
    assert_contains "$content" "CPerformanceTimer" "Should have performance timer"
}

test_sample_ea_with_tests() {
    assert_file_exists "MQL4/Experts/SampleEAWithTests.mq4" "Sample EA with tests should exist"
    
    if [[ -f "MQL4/Experts/SampleEAWithTests.mq4" ]]; then
        local content=$(cat MQL4/Experts/SampleEAWithTests.mq4)
        assert_contains "$content" "RunAllTests" "Should have test runner"
        assert_contains "$content" "#include <EATestFramework.mqh>" "Should include test framework"
    fi
}

test_ea_testing_documentation() {
    assert_file_exists "docs/guides/EA_TESTING.md" "EA testing guide should exist"
    
    if [[ -f "docs/guides/EA_TESTING.md" ]]; then
        local content=$(cat docs/guides/EA_TESTING.md)
        assert_contains "$content" "EATester" "Should document EATester"
        assert_contains "$content" "CTestSuite" "Should document test suite usage"
        assert_contains "$content" "test_ea.sh" "Should document test script"
    fi
}

test_test_reports_directory() {
    # Check if test reports directory would be created
    assert_contains "$(cat bin/test_ea.sh)" "mkdir -p" "Test script should create reports directory"
    assert_contains "$(cat bin/test_ea.sh)" "test_reports" "Test script should use test_reports directory"
}

test_ea_deployment_in_container() {
    if ! docker ps | grep -q "mt4-docker"; then
        skip "MT4 container not running"
        return
    fi
    
    # Test that script can check for EA files
    local script_content=$(cat bin/test_ea.sh)
    assert_contains "$script_content" "docker exec" "Should use docker exec"
    assert_contains "$script_content" "test -f" "Should check file existence"
    assert_contains "$script_content" "MQL4/Experts" "Should check Experts directory"
}