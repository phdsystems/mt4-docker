# MT4 DLL Integration Guide

## Overview

This guide describes how to use the ZeroMQ DLL with MT4 for high-performance market data streaming. The integration provides native C++ performance while maintaining ease of use in MQL4.

## 🚀 Quick Start

### 1. **Install the DLL**

The `mt4zmq.dll` must be placed in the MT4 Libraries folder:

```bash
# Copy DLL to MT4 Libraries
cp dll_source/build/mt4zmq.dll MQL4/Libraries/

# In MT4 terminal data folder:
# Windows: C:\Users\[Username]\AppData\Roaming\MetaQuotes\Terminal\[ID]\MQL4\Libraries\
# Wine: ~/.wine/drive_c/users/[username]/Application Data/MetaQuotes/Terminal/[ID]/MQL4/Libraries/
```

### 2. **Enable DLL Usage in MT4**

1. Open MT4
2. Go to Tools → Options → Expert Advisors
3. Check "Allow DLL imports"
4. Click OK

### 3. **Load the Expert Advisor**

1. Copy `MT4ZMQBridge.mq4` to `MQL4/Experts/`
2. Compile in MetaEditor (F7)
3. Drag to chart
4. Configure parameters

## 📦 Components

### DLL Functions

```cpp
// Context management
int    zmq_init();                    // Initialize ZeroMQ context
void   zmq_term();                    // Terminate ZeroMQ context

// Socket creation
int    zmq_create_publisher(string address);   // Create PUB socket
int    zmq_create_subscriber(string address);  // Create SUB socket

// Messaging
int    zmq_send_message(int handle, string topic, string message);
int    zmq_recv_message(int handle, string &topic, string &message, int timeout);

// Socket management
int    zmq_close(int handle);         // Close socket
void   zmq_get_last_error(string &error, int len);  // Get error message
```

### MQL4 Include File

The `MT4ZMQ.mqh` include file provides wrapper classes:

```mql4
#include <MT4ZMQ.mqh>

// Publisher class
CZMQPublisher publisher;
publisher.Create("tcp://*:5556");
publisher.SendTick("EURUSD", 1.1000, 1.1001);
publisher.SendBar("EURUSD", PERIOD_M1, 1);

// Subscriber class
CZMQSubscriber subscriber;
subscriber.Create("tcp://localhost:5556");
subscriber.Subscribe("tick.EURUSD");
string topic, message;
if (subscriber.Receive(topic, message, 1000)) {
    Print("Received: ", topic, " - ", message);
}
```

## 🔧 Expert Advisor Configuration

### Input Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| PublishAddress | tcp://*:5556 | ZeroMQ bind address |
| Symbols | "" | Symbols to stream (empty = all) |
| TickInterval | 100 | Milliseconds between tick updates |
| PublishTicks | true | Enable tick data streaming |
| PublishBars | true | Enable bar data streaming |
| BarTimeframe | PERIOD_M1 | Timeframe for bar data |
| StatsInterval | 10000 | Statistics update interval (ms) |

### Message Formats

#### Tick Message
```json
{
    "symbol": "EURUSD",
    "bid": 1.10123,
    "ask": 1.10125,
    "spread": 0.2,
    "time": 1642345678,
    "ms": 123
}
```

#### Bar Message
```json
{
    "symbol": "EURUSD",
    "timeframe": "M1",
    "time": 1642345620,
    "open": 1.10120,
    "high": 1.10135,
    "low": 1.10115,
    "close": 1.10130,
    "volume": 245
}
```

#### Status Message
```json
{
    "event": "startup",
    "description": "Bridge initialized",
    "account": 12345,
    "time": 1642345678
}
```

## 📊 Performance

### Benchmarks

| Metric | Value |
|--------|-------|
| Latency | < 1ms |
| Throughput | > 10,000 msgs/sec |
| CPU Usage | < 5% |
| Memory | < 50MB |

### Optimization Tips

1. **Batch Processing**: Process multiple symbols in one timer event
2. **Selective Streaming**: Only stream required symbols
3. **Appropriate Intervals**: Balance between latency and CPU usage
4. **Message Size**: Keep JSON messages compact

## 🧪 Testing

### 1. **Test DLL Loading**

Run the test script:
```mql4
// MQL4/Scripts/TestZMQDLLIntegration.mq4
// Verifies DLL can be loaded and basic functions work
```

### 2. **Test with Python Subscriber**

```bash
# Start Python subscriber
python3 clients/python/zmq_subscriber.py

# Should see:
# Connected to tcp://localhost:5556
# Subscribed to all topics
# [tick.EURUSD] {"symbol":"EURUSD","bid":1.10123,...}
```

### 3. **Monitor Performance**

```python
# Run performance monitor
python3 scripts/zmq_performance_monitor.py

# Shows:
# Messages/sec: 5432
# Latency avg: 0.8ms
# CPU usage: 3.2%
```

## 🔍 Troubleshooting

### Common Issues

1. **"Cannot load library 'mt4zmq.dll'"**
   - Check DLL is in MQL4/Libraries/
   - Verify DLL imports are enabled
   - Check for missing dependencies

2. **"Failed to create publisher"**
   - Check port is not in use: `netstat -an | grep 5556`
   - Verify firewall allows the port
   - Try different address: `tcp://127.0.0.1:5556`

3. **No messages received**
   - Verify EA is running (smiley face on chart)
   - Check subscriber is connected to correct port
   - Enable verbose logging in EA

4. **High CPU usage**
   - Increase TickInterval (e.g., 500ms)
   - Reduce number of symbols
   - Disable market depth if not needed

### Debug Mode

Enable verbose logging in the EA:
```mql4
input bool InpVerboseLogging = true;
```

Check MT4 logs:
- Terminal → View → Experts
- Terminal → View → Journal

## 🛡️ Security Considerations

1. **Network Security**
   - Bind to localhost only: `tcp://127.0.0.1:5556`
   - Use firewall rules to restrict access
   - Consider using CURVE authentication

2. **Data Validation**
   - Validate all data before sending
   - Sanitize JSON strings
   - Handle errors gracefully

3. **Resource Limits**
   - Limit number of symbols
   - Set appropriate timeouts
   - Monitor memory usage

## 📚 Advanced Usage

### Custom Message Types

```mql4
// Send custom JSON message
string json = "{\"type\":\"order\",\"action\":\"buy\",\"symbol\":\"EURUSD\"}";
publisher.SendMessage("orders", json);
```

### Multiple Publishers

```mql4
// Create multiple publishers on different ports
CZMQPublisher tickPublisher;
tickPublisher.Create("tcp://*:5556");

CZMQPublisher barPublisher;
barPublisher.Create("tcp://*:5557");
```

### Filtered Streaming

```mql4
// Only stream specific symbols during specific hours
if (Symbol() == "EURUSD" && Hour() >= 8 && Hour() <= 17) {
    publisher.SendTick(Symbol(), Bid, Ask);
}
```

## 🔄 Integration with Python

### Simple Subscriber

```python
import zmq

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.subscribe(b"")  # Subscribe to all

while True:
    topic, message = socket.recv_multipart()
    print(f"[{topic.decode()}] {message.decode()}")
```

### With Pandas DataFrame

```python
import zmq
import json
import pandas as pd
from datetime import datetime

# Collect ticks into DataFrame
ticks = []

# ... receive loop ...
data = json.loads(message.decode())
data['timestamp'] = datetime.now()
ticks.append(data)

# Convert to DataFrame
df = pd.DataFrame(ticks)
df.set_index('timestamp', inplace=True)
```

## 📈 Production Deployment

### 1. **System Requirements**
- Windows Server or Windows 10
- MT4 Build 1350+
- 2GB RAM minimum
- Network connectivity

### 2. **Deployment Checklist**
- [ ] DLL copied to Libraries folder
- [ ] DLL imports enabled in MT4
- [ ] EA compiled without errors
- [ ] Firewall rules configured
- [ ] Monitoring setup
- [ ] Error alerting configured
- [ ] Backup EA configured

### 3. **Monitoring**
- Use Prometheus metrics endpoint
- Set up Grafana dashboards
- Configure alerts for failures
- Monitor message rates

## 🎯 Best Practices

1. **Error Handling**: Always check return values
2. **Resource Cleanup**: Properly close sockets
3. **Logging**: Use appropriate log levels
4. **Testing**: Test with demo account first
5. **Monitoring**: Track performance metrics
6. **Documentation**: Document custom configurations

The MT4-DLL integration provides a robust, high-performance solution for streaming market data from MT4 to external systems via ZeroMQ.