# Correct ZeroMQ Architecture for MT4

## The RIGHT Way: MT4 as Publisher

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   MT4 Terminal  │      │    Subscribers   │      │                 │
│   (PUBLISHER)   │─────▶│    (CLIENTS)     │      │                 │
│                 │ TCP  │                  │      │                 │
│ ZeroMQ EA       │ 5556 │ Python Client    │      │                 │
│ (PUB Socket)    │      │ Node.js Client   │      │                 │
│                 │      │ C++ Client       │      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘
```

## The Problem

MQL4 cannot directly use ZeroMQ because:
1. MQL4 doesn't have native ZeroMQ support
2. We need a DLL to bridge MQL4 to ZeroMQ
3. MT4 has restrictions on external libraries

## Solutions

### Option 1: Direct ZeroMQ DLL (Ideal)
```mql4
// In MT4 EA
#import "mt4zmq.dll"
    int zmq_pub_init(string address);
    int zmq_pub_send(string topic, string message);
    void zmq_pub_close();
#import

// EA publishes directly
int OnInit() {
    zmq_pub_init("tcp://*:5556");
}

void OnTick() {
    string msg = StringFormat("{\"symbol\":\"%s\",\"bid\":%f}", Symbol(), Bid);
    zmq_pub_send("tick." + Symbol(), msg);
}
```

### Option 2: Windows Named Pipes (Current)
```mql4
// MT4 writes to named pipe
int pipe = FileOpen("\\\\.\\pipe\\MT4_Data", FILE_WRITE|FILE_BIN);
FileWriteString(pipe, json_data);

// Python bridge reads pipe and publishes via ZeroMQ
```

### Option 3: Shared Memory
```mql4
// MT4 writes to shared memory via DLL
// External process reads and publishes via ZeroMQ
```

## What We Actually Built

```
MT4 EA → Named Pipe/CSV → Python Bridge (ZMQ Publisher) → Subscribers
         (Not ideal but works without custom DLL)
```

## What We SHOULD Build

```
MT4 EA (with ZMQ DLL) → Direct ZeroMQ PUB → Subscribers
         (Direct, low-latency, no intermediate bridge)
```

## Required Components for Direct Publishing

1. **ZeroMQ DLL for MT4**
   - Wraps ZeroMQ C library
   - Exports functions callable from MQL4
   - Handles socket lifecycle

2. **MQL4 Include File**
   - Import DLL functions
   - Provide MQL4-friendly API
   - Handle message formatting

3. **Example Implementation**

The issue is that we need to compile a Windows DLL that MT4 can load. This requires:
- Visual Studio or MinGW
- ZeroMQ C library
- Proper export definitions
- 32-bit compilation (for MT4)