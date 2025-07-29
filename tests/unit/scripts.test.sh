#!/bin/bash

# Unit tests for shell scripts

# Framework is loaded by test runner

setup() {
    # Store original directory
    export ORIGINAL_DIR=$(pwd)
    cd /workspace/mt4-docker
}

teardown() {
    cd "$ORIGINAL_DIR"
}

test_all_scripts_exist() {
    local scripts=(
        "bin/quick_start.sh"
        "bin/check_status.sh"
        "bin/monitor.sh"
        "bin/deploy_ea.sh"
        "bin/view_logs.sh"
        "bin/cleanup.sh"
    )
    
    for script in "${scripts[@]}"; do
        assert_file_exists "$script" "Script should exist"
    done
}

test_all_scripts_executable() {
    for script in bin/*.sh; do
        if [[ -f "$script" ]]; then
            assert_executable "$script" "Script should be executable"
        fi
    done
}

test_deploy_ea_validates_arguments() {
    # Test missing argument - script exits with 1 when no args, which is expected
    local output=$(./bin/deploy_ea.sh 2>&1 || true)
    assert_contains "$output" "Usage:" "Should show usage when no arguments"
}

test_check_status_script_structure() {
    # Check if script has required functionality (not functions)
    local content=$(cat bin/check_status.sh)
    
    assert_contains "$content" "Container is running" "Should check container status"
    assert_contains "$content" "MT4 is running" "Should check MT4 status"
    assert_contains "$content" "EA Status:" "Should check EA status"
    assert_contains "$content" "VNC is accessible" "Should check VNC status"
}

test_monitor_script_has_loop() {
    local content=$(cat bin/monitor.sh)
    
    assert_contains "$content" "while true" "Monitor should have continuous loop"
    assert_contains "$content" "sleep" "Monitor should have sleep interval"
}

test_scripts_use_proper_shebang() {
    for script in bin/*.sh scripts/*.sh; do
        if [[ -f "$script" ]]; then
            local first_line=$(head -n1 "$script")
            assert_equals "#!/bin/bash" "$first_line" "$script should have bash shebang"
        fi
    done
}

test_scripts_handle_errors() {
    # Check if scripts use error handling
    local scripts_with_error_handling=0
    local total_scripts=0
    
    for script in bin/*.sh; do
        if [[ -f "$script" ]]; then
            ((total_scripts++))
            if grep -q "set -e\|exit 1\||| exit" "$script"; then
                ((scripts_with_error_handling++))
            fi
        fi
    done
    
    if [[ $scripts_with_error_handling -lt $((total_scripts / 2)) ]]; then
        fail "Less than half of scripts have error handling"
    else
        pass "Most scripts have error handling"
    fi
}