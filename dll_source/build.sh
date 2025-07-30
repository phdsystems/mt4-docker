#!/bin/bash
# Build script for MT4ZMQ DLL

echo "Building MT4ZMQ DLL..."

# Check if MinGW is installed
if ! command -v i686-w64-mingw32-g++ &> /dev/null; then
    echo "MinGW not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y mingw-w64
fi

# Create build directory
mkdir -p build

# Compile the DLL
echo "Compiling mt4zmq.dll..."

i686-w64-mingw32-g++ \
    -shared \
    -o build/mt4zmq.dll \
    mt4zmq.cpp \
    -I/usr/include \
    -L/usr/lib \
    -lzmq \
    -lws2_32 \
    -static-libgcc \
    -static-libstdc++ \
    -Wl,--out-implib,build/mt4zmq.lib \
    -Wl,--export-all-symbols \
    -Wl,--enable-auto-import \
    -Wl,--subsystem,windows

if [ $? -eq 0 ]; then
    echo "Build successful!"
    echo "Output: build/mt4zmq.dll"
    ls -la build/
else
    echo "Build failed!"
    exit 1
fi