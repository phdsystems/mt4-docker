# Building ZeroMQ DLL for MT4

## Requirements

1. **32-bit compilation** (MT4 is 32-bit)
2. **ZeroMQ library** (libzmq)
3. **Windows compiler** (Visual Studio or MinGW)
4. **MT4 compatible exports**

## Build Instructions

### Option 1: Visual Studio

```powershell
# 1. Install vcpkg
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg
./bootstrap-vcpkg.bat
./vcpkg integrate install

# 2. Install ZeroMQ (32-bit)
./vcpkg install zeromq:x86-windows

# 3. Create Visual Studio project
# - Type: Win32 DLL
# - Platform: x86
# - Add zmq4mt4.cpp
# - Link with libzmq.lib
```

### Option 2: MinGW

```bash
# Install MinGW-w64 with 32-bit support
# Install ZeroMQ development files

# Compile
g++ -m32 -shared -o zmq4mt4.dll zmq4mt4.cpp \
    -I/path/to/zmq/include \
    -L/path/to/zmq/lib \
    -lzmq -lws2_32 \
    -static-libgcc -static-libstdc++
```

### Option 3: Docker Cross-Compilation

```dockerfile
FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    mingw-w64 \
    libzmq3-dev \
    pkg-config

# Cross compile for Windows 32-bit
RUN i686-w64-mingw32-g++ -shared -o zmq4mt4.dll zmq4mt4.cpp \
    -lzmq -lws2_32 -static
```

## Testing the DLL

1. Copy `zmq4mt4.dll` to `MT4/MQL4/Libraries/`
2. Use the `DirectZeroMQPublisher.mq4` EA
3. Run Python subscriber to verify

## Alternative: Use Existing Solutions

- **MT4-ZMQ**: https://github.com/dingmaotu/mql-zmq
- **ZeroMQ-MT4**: https://github.com/AustenConrad/ZeroMQ-MT4

These provide ready-made DLLs for MT4 ZeroMQ integration.