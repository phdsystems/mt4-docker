#!/bin/bash
# Build script for MT4ZMQ DLL using Windows Sockets

echo "Building MT4ZMQ DLL (Windows Socket implementation)..."

# Check if MinGW is installed
if ! command -v i686-w64-mingw32-g++ &> /dev/null; then
    echo "MinGW not found. Please install mingw-w64 first."
    exit 1
fi

# Create build directory
mkdir -p build

# Compile the DLL
echo "Compiling mt4zmq.dll..."

i686-w64-mingw32-g++ \
    -shared \
    -o build/mt4zmq.dll \
    mt4zmq_winsock.cpp \
    -lws2_32 \
    -static-libgcc \
    -static-libstdc++ \
    -std=c++11 \
    -O2 \
    -Wl,--out-implib,build/mt4zmq.lib \
    -Wl,--export-all-symbols \
    -Wl,--enable-auto-import \
    -Wl,--subsystem,windows

if [ $? -eq 0 ]; then
    echo "Build successful!"
    echo "Output: build/mt4zmq.dll"
    echo ""
    echo "This implementation provides ZeroMQ-like pub/sub functionality using Windows sockets."
    echo "It's compatible with MT4 and provides basic publisher/subscriber patterns."
    echo ""
    
    # Show exported functions
    echo "Exported functions:"
    i686-w64-mingw32-objdump -p build/mt4zmq.dll | grep -A 20 "Export"
    
    ls -la build/
else
    echo "Build failed!"
    exit 1
fi