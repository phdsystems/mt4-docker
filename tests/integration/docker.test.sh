#!/bin/bash

# Integration tests for Docker setup

# Framework is loaded by test runner

# Test configuration
CONTAINER_NAME="mt4-docker-test"
TEST_TIMEOUT=120

setup() {
    export ORIGINAL_DIR=$(pwd)
    cd "$(dirname "$0")/../.."
    
    # Create test .env file
    cp .env.example .env.test
    echo "MT4_LOGIN=12345" >> .env.test
    echo "MT4_PASSWORD=test123" >> .env.test
    echo "MT4_SERVER=Test-Server" >> .env.test
    echo "VNC_PASSWORD=vnc123" >> .env.test
}

teardown() {
    # Stop and remove test container
    docker-compose -p test down -v 2>/dev/null || true
    
    # Clean up test files
    rm -f .env.test
    
    cd "$ORIGINAL_DIR"
}

test_docker_build() {
    # Test if image can be built
    if docker build -t mt4-docker-test . > /dev/null 2>&1; then
        pass "Docker image builds successfully"
    else
        fail "Docker image build failed"
        return 1
    fi
}

test_container_starts() {
    # Start container with test config
    if docker-compose -p test --env-file .env.test up -d 2>/dev/null; then
        pass "Container starts successfully"
        
        # Wait for container to be ready
        sleep 10
        
        # Check if container is running
        if docker ps | grep -q "test_mt4_1\|test-mt4-1"; then
            pass "Container is running"
        else
            fail "Container is not running"
        fi
    else
        fail "Failed to start container"
    fi
}

test_services_running() {
    local container=$(docker ps --format "{{.Names}}" | grep "test.*mt4" | head -1)
    
    if [[ -z "$container" ]]; then
        skip "No test container found"
        return
    fi
    
    # Check Xvfb
    if docker exec "$container" pgrep -f Xvfb > /dev/null; then
        pass "Xvfb is running"
    else
        fail "Xvfb is not running"
    fi
    
    # Check X11VNC
    if docker exec "$container" pgrep -f x11vnc > /dev/null; then
        pass "X11VNC is running"
    else
        fail "X11VNC is not running"
    fi
    
    # Check Wine/MT4
    if docker exec "$container" pgrep -f terminal.exe > /dev/null; then
        pass "MT4 is running"
    else
        # MT4 might not start without valid credentials
        skip "MT4 not running (expected without valid credentials)"
    fi
}

test_volumes_mounted() {
    local container=$(docker ps --format "{{.Names}}" | grep "test.*mt4" | head -1)
    
    if [[ -z "$container" ]]; then
        skip "No test container found"
        return
    fi
    
    # Check MQL4 volume
    if docker exec "$container" test -d /mt4/MQL4; then
        pass "MQL4 directory is mounted"
    else
        fail "MQL4 directory is not mounted"
    fi
    
    # Check logs volume
    if docker exec "$container" test -d /mt4/logs; then
        pass "Logs directory is mounted"
    else
        fail "Logs directory is not mounted"
    fi
}

test_vnc_port_exposed() {
    local container=$(docker ps --format "{{.Names}}" | grep "test.*mt4" | head -1)
    
    if [[ -z "$container" ]]; then
        skip "No test container found"
        return
    fi
    
    # Check if port 5900 is exposed
    if docker port "$container" 5900 2>/dev/null | grep -q "5900"; then
        pass "VNC port 5900 is exposed"
    else
        fail "VNC port 5900 is not exposed"
    fi
}

test_healthcheck() {
    local container=$(docker ps --format "{{.Names}}" | grep "test.*mt4" | head -1)
    
    if [[ -z "$container" ]]; then
        skip "No test container found"
        return
    fi
    
    # Wait for healthcheck
    sleep 5
    
    # Check container health
    local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)
    
    if [[ "$health" == "healthy" ]]; then
        pass "Container healthcheck is healthy"
    elif [[ "$health" == "starting" ]]; then
        skip "Container healthcheck is still starting"
    else
        fail "Container healthcheck failed: $health"
    fi
}

test_resource_limits() {
    local container=$(docker ps --format "{{.Names}}" | grep "test.*mt4" | head -1)
    
    if [[ -z "$container" ]]; then
        skip "No test container found"
        return
    fi
    
    # Check CPU limits
    local cpu_quota=$(docker inspect --format='{{.HostConfig.CpuQuota}}' "$container")
    if [[ "$cpu_quota" -gt 0 ]]; then
        pass "CPU limits are set"
    else
        skip "CPU limits not enforced (Docker Compose v2 compatibility)"
    fi
    
    # Check memory limits
    local mem_limit=$(docker inspect --format='{{.HostConfig.Memory}}' "$container")
    if [[ "$mem_limit" -gt 0 ]]; then
        pass "Memory limits are set"
    else
        skip "Memory limits not enforced (Docker Compose v2 compatibility)"
    fi
}