#!/bin/bash

# Unit tests for Docker configuration

# Framework is loaded by test runner

setup() {
    export ORIGINAL_DIR=$(pwd)
    cd /workspace/mt4-docker
}

teardown() {
    cd "$ORIGINAL_DIR"
}

test_dockerfile_exists() {
    assert_file_exists "Dockerfile" "Dockerfile should exist"
}

test_dockerfile_structure() {
    local content=$(cat Dockerfile)
    
    # Check base image
    assert_contains "$content" "FROM ubuntu:20.04" "Should use Ubuntu 20.04 base"
    
    # Check required packages
    assert_contains "$content" "wine" "Should install Wine"
    assert_contains "$content" "xvfb" "Should install Xvfb"
    assert_contains "$content" "x11vnc" "Should install VNC server"
    assert_contains "$content" "supervisor" "Should install Supervisor"
    
    # Check MT4 setup
    assert_contains "$content" "terminal.exe" "Should copy terminal.exe"
    assert_contains "$content" "MQL4" "Should copy MQL4 directory"
}

test_docker_compose_exists() {
    assert_file_exists "docker-compose.yml" "docker-compose.yml should exist"
}

test_docker_compose_structure() {
    local content=$(cat docker-compose.yml)
    
    # Check service definition
    assert_contains "$content" "mt4:" "Should define mt4 service"
    
    # Check volumes
    assert_contains "$content" "./MQL4:/mt4/MQL4" "Should mount MQL4 directory"
    assert_contains "$content" "./logs:/mt4/logs" "Should mount logs directory"
    
    # Check environment variables
    assert_contains "$content" "MT4_LOGIN" "Should use MT4_LOGIN env var"
    assert_contains "$content" "MT4_PASSWORD" "Should use MT4_PASSWORD env var"
    assert_contains "$content" "MT4_SERVER" "Should use MT4_SERVER env var"
    
    # Check ports
    assert_contains "$content" "5900:5900" "Should expose VNC port"
    
    # Check resource limits
    assert_contains "$content" "cpus:" "Should have CPU limits"
    assert_contains "$content" "memory:" "Should have memory limits"
}

test_supervisord_config() {
    assert_file_exists "config/docker/supervisord.conf" "Supervisord config should exist"
    
    local content=$(cat config/docker/supervisord.conf)
    
    # Check programs
    assert_contains "$content" "[program:xvfb]" "Should run Xvfb"
    assert_contains "$content" "[program:x11vnc]" "Should run VNC server"
    assert_contains "$content" "[program:mt4]" "Should run MT4"
    assert_contains "$content" "[program:auto-compile]" "Should run auto-compile"
    
    # Check VNC password
    assert_contains "$content" "VNC_PASSWORD" "VNC should use password"
}

test_env_example_exists() {
    assert_file_exists ".env.example" "Environment example should exist"
    
    local content=$(cat .env.example)
    
    # Check required variables
    assert_contains "$content" "MT4_LOGIN=" "Should have MT4_LOGIN"
    assert_contains "$content" "MT4_PASSWORD=" "Should have MT4_PASSWORD"
    assert_contains "$content" "MT4_SERVER=" "Should have MT4_SERVER"
    assert_contains "$content" "VNC_PASSWORD=" "Should have VNC_PASSWORD"
}

test_gitignore_exists() {
    assert_file_exists ".gitignore" ".gitignore should exist"
    
    local content=$(cat .gitignore)
    
    # Check critical exclusions
    assert_contains "$content" ".env" "Should ignore .env file"
    assert_contains "$content" "*.log" "Should ignore log files"
    assert_contains "$content" "*.ex4" "Should ignore compiled EA files"
}