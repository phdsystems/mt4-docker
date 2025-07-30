#!/bin/bash
# Build unit tests for MT4ZMQ DLL

echo "Building MT4ZMQ unit tests..."

# Check if MinGW is installed
if ! command -v i686-w64-mingw32-g++ &> /dev/null; then
    echo "MinGW not found. Please install mingw-w64 first."
    exit 1
fi

# Create build directory
mkdir -p build

# Compile the test executable
echo "Compiling test_mt4zmq.exe..."

i686-w64-mingw32-g++ \
    -o build/test_mt4zmq.exe \
    test_mt4zmq.cpp \
    -static-libgcc \
    -static-libstdc++ \
    -std=c++11 \
    -O2

if [ $? -eq 0 ]; then
    echo "Build successful!"
    echo "Output: build/test_mt4zmq.exe"
    echo ""
    echo "To run the tests on Windows:"
    echo "  test_mt4zmq.exe mt4zmq.dll"
    echo ""
    ls -la build/test_mt4zmq.exe
else
    echo "Build failed!"
    exit 1
fi