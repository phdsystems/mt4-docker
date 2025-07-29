#!/bin/bash

# Simple test to verify framework

# Framework is loaded by test runner

setup() {
    echo "Setup called"
}

teardown() {
    echo "Teardown called"
}

test_simple() {
    echo "In test_simple"
    assert_equals "1" "1" "Simple equality test"
    echo "After assert_equals"
}

test_another() {
    echo "In test_another"
    assert_contains "hello world" "world" "Contains test"
    echo "After assert_contains"
}