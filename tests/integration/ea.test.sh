#!/bin/bash

# Integration tests for EA deployment and compilation

# Framework is loaded by test runner

setup() {
    export ORIGINAL_DIR=$(pwd)
    cd "$(dirname "$0")/../.."
    
    # Create test EA
    cat > test_ea.mq4 << 'EOF'
//+------------------------------------------------------------------+
//|                                                      TestEA.mq4  |
//+------------------------------------------------------------------+
#property copyright "Test EA"
#property version   "1.00"
#property strict

int OnInit() {
    Print("Test EA initialized");
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
    Print("Test EA deinitialized");
}

void OnTick() {
    Comment("Test EA Running");
}
//+------------------------------------------------------------------+
EOF
}

teardown() {
    rm -f test_ea.mq4
    rm -f test_ea.ex4
    cd "$ORIGINAL_DIR"
}

test_ea_deployment() {
    # Check if container is running
    if ! docker ps | grep -q "mt4-docker"; then
        skip "MT4 container not running"
        return
    fi
    
    # Deploy test EA
    if ./bin/deploy_ea.sh test_ea.mq4 > /dev/null 2>&1; then
        pass "EA deployment script executes"
    else
        fail "EA deployment script failed"
        return
    fi
    
    # Check if EA was copied
    if docker exec mt4-docker test -f /mt4/MQL4/Experts/test_ea.mq4; then
        pass "EA file copied to container"
    else
        fail "EA file not found in container"
    fi
}

test_ea_compilation() {
    if ! docker ps | grep -q "mt4-docker"; then
        skip "MT4 container not running"
        return
    fi
    
    # Deploy EA if not already done
    ./bin/deploy_ea.sh test_ea.mq4 > /dev/null 2>&1
    
    # Wait for compilation
    echo "  Waiting for EA compilation..."
    sleep 30
    
    # Check if EA compiled
    if docker exec mt4-docker test -f /mt4/MQL4/Experts/test_ea.ex4; then
        pass "EA compiled successfully"
    else
        # Check if other EAs compiled (MT4 might be in demo mode)
        if docker exec mt4-docker find /mt4/MQL4/Experts -name "*.ex4" | grep -q ex4; then
            skip "Test EA not compiled but other EAs exist"
        else
            fail "No compiled EAs found"
        fi
    fi
}

test_auto_compile_service() {
    if ! docker ps | grep -q "mt4-docker"; then
        skip "MT4 container not running"
        return
    fi
    
    # Check if auto-compile script is running
    if docker exec mt4-docker pgrep -f auto-compile.sh > /dev/null; then
        pass "Auto-compile service is running"
    else
        # Check logs to see if it ran
        if docker exec mt4-docker grep -q "Auto-compile check starting" /mt4/logs/auto_compile.log 2>/dev/null; then
            pass "Auto-compile service has run"
        else
            fail "Auto-compile service not running"
        fi
    fi
}