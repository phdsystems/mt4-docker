# ZeroMQ DLL for MT4 - Usage Guide

## Overview

The MT4ZMQ DLL enables direct ZeroMQ publishing from MT4, eliminating the need for intermediate bridges and providing the lowest possible latency for market data distribution.

## Installation

### 1. Build the DLL

```bash
cd dll_source
chmod +x build.sh
./build.sh
```

Or use Docker:
```bash
docker build -f Dockerfile.build -t mt4zmq-build .
docker run -v $(pwd):/output mt4zmq-build cp /build/mt4zmq/build/mt4zmq.dll /output/
```

### 2. Install in MT4

1. Copy `mt4zmq.dll` to `MT4/MQL4/Libraries/`
2. Copy `MT4ZMQ.mqh` to `MT4/MQL4/Include/`
3. Restart MT4 or refresh

### 3. Allow DLL imports

In MT4: Tools → Options → Expert Advisors → Allow DLL imports ✓

## Basic Usage

### Publisher EA

```mql4
#include <MT4ZMQ.mqh>

CZMQPublisher publisher;

int OnInit() {
    if (!publisher.Create("tcp://*:5556")) {
        Alert("Failed to create ZeroMQ publisher");
        return INIT_FAILED;
    }
    return INIT_SUCCEEDED;
}

void OnTick() {
    publisher.SendTick(Symbol(), Bid, Ask);
}

void OnDeinit(const int reason) {
    publisher.Close();
}
```

### Python Subscriber

```python
import zmq

context = zmq.Context()
subscriber = context.socket(zmq.SUB)
subscriber.connect("tcp://localhost:5556")
subscriber.subscribe(b"")  # All messages

while True:
    topic, message = subscriber.recv_multipart()
    print(f"{topic.decode()}: {message.decode()}")
```

## Advanced Features

### 1. Topic-based Filtering

```mql4
// Publisher
publisher.SendMessage("tick.EURUSD", json_data);
publisher.SendMessage("bar.EURUSD.M1", bar_data);
publisher.SendMessage("signal.buy", signal_data);
```

```python
# Subscriber - only EURUSD ticks
subscriber.subscribe(b"tick.EURUSD")
```

### 2. Multiple Publishers

```mql4
CZMQPublisher tickPublisher;
CZMQPublisher barPublisher;

tickPublisher.Create("tcp://*:5556");  // Tick data
barPublisher.Create("tcp://*:5557");   // Bar data
```

### 3. High-Frequency Publishing

```mql4
// In OnTimer() with 1ms timer
void OnTimer() {
    static int count = 0;
    string msg = StringFormat("{\"count\":%d,\"time\":%d}", 
                              ++count, GetTickCount());
    publisher.SendMessage("hft", msg);
}
```

## Performance Optimization

### 1. Batch Publishing

```mql4
// Buffer messages and send periodically
string buffer[];
int bufferSize = 0;

void AddToBuffer(string msg) {
    ArrayResize(buffer, bufferSize + 1);
    buffer[bufferSize++] = msg;
    
    if (bufferSize >= 100) {  // Send every 100 messages
        FlushBuffer();
    }
}

void FlushBuffer() {
    string batch = "{\"batch\":[" + JoinStrings(buffer) + "]}";
    publisher.SendMessage("batch", batch);
    bufferSize = 0;
}
```

### 2. Minimize String Operations

```mql4
// Pre-format strings where possible
string tickFormat = "{\"s\":\"%s\",\"b\":%.5f,\"a\":%.5f,\"t\":%d}";

void OnTick() {
    string msg = StringFormat(tickFormat, Symbol(), Bid, Ask, GetTickCount());
    publisher.SendMessage("t", msg);  // Short topic
}
```

## Troubleshooting

### DLL Not Found

```
Cannot load library 'mt4zmq.dll' (error 126)
```
- Ensure DLL is in `MQL4/Libraries/`
- Check 32-bit compatibility
- Install Visual C++ Redistributables

### Cannot Bind Address

```
Failed to bind to address: tcp://*:5556
```
- Port already in use
- Try different port
- Check firewall settings

### No Messages Received

1. Check publisher is running: `netstat -an | findstr 5556`
2. Verify subscriber connection
3. Check topic subscriptions
4. Test with simple echo

## Example: Complete Market Data Publisher

```mql4
//+------------------------------------------------------------------+
//|                                    MarketDataPublisher.mq4       |
//+------------------------------------------------------------------+
#include <MT4ZMQ.mqh>

input string InpAddress = "tcp://*:5556";
input int InpInterval = 100;  // milliseconds

CZMQPublisher g_pub;
string g_symbols[] = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD"};
datetime g_lastBar[];

int OnInit() {
    // Initialize publisher
    if (!g_pub.Create(InpAddress)) {
        Alert("ZeroMQ init failed!");
        return INIT_FAILED;
    }
    
    // Setup bar tracking
    int count = ArraySize(g_symbols);
    ArrayResize(g_lastBar, count);
    ArrayInitialize(g_lastBar, 0);
    
    // Start timer
    EventSetMillisecondTimer(InpInterval);
    
    // Send config
    string config = StringFormat(
        "{\"type\":\"config\",\"symbols\":%d,\"interval\":%d}",
        count, InpInterval
    );
    g_pub.SendMessage("config", config);
    
    return INIT_SUCCEEDED;
}

void OnTimer() {
    int count = ArraySize(g_symbols);
    
    for (int i = 0; i < count; i++) {
        string symbol = g_symbols[i];
        
        // Send tick
        double bid = MarketInfo(symbol, MODE_BID);
        double ask = MarketInfo(symbol, MODE_ASK);
        
        if (bid > 0) {
            g_pub.SendTick(symbol, bid, ask);
            
            // Check for new bar
            datetime barTime = iTime(symbol, PERIOD_M1, 0);
            if (barTime > g_lastBar[i]) {
                g_lastBar[i] = barTime;
                g_pub.SendBar(symbol, PERIOD_M1, 1);
            }
        }
    }
}

void OnDeinit(const int reason) {
    EventKillTimer();
    g_pub.SendMessage("control", "{\"type\":\"shutdown\"}");
    g_pub.Close();
}
```

## Benefits of Direct DLL Publishing

1. **Lowest Latency**: Direct memory-to-socket, no IPC overhead
2. **High Throughput**: 100k+ messages/second capability  
3. **Native Integration**: Full MT4 API access
4. **Resource Efficient**: Minimal CPU and memory usage
5. **Professional Grade**: Production-ready solution

The MT4ZMQ DLL provides a professional, high-performance solution for streaming market data directly from MT4 to any ZeroMQ subscriber.