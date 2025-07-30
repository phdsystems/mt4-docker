# ZeroMQ Architecture for MT4 Market Data Streaming

## Overview

ZeroMQ provides a high-performance, low-latency messaging system perfect for financial market data distribution. This architecture enables MT4 to stream market data to multiple subscribers with minimal overhead.

## Architecture Design

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│   MT4 Terminal  │────▶│  ZeroMQ Bridge   │────▶│   Subscribers   │
│   (Publisher)   │     │    (Proxy)       │     │   (Clients)     │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
       │                         │                        │
       │                         │                        ├── Python Client
       ├── DLL/Named Pipe       ├── PUB Socket          ├── Node.js Client
       └── CSV File             └── XPUB Socket         └── C++ Client
```

## Components

### 1. MT4 Publisher
- Publishes market data via DLL or named pipe
- Minimal latency impact on trading
- Configurable symbols and update frequency

### 2. ZeroMQ Bridge Service
- Runs outside MT4 for stability
- Implements PUB-SUB pattern for scalability
- Optional XPUB-XSUB for subscription tracking

### 3. Subscribers
- Connect via TCP or IPC
- Subscribe to specific symbols or all data
- Automatic reconnection handling

## Message Format

### JSON Format (Default)
```json
{
  "type": "tick",
  "symbol": "EURUSD",
  "timestamp": 1706548800000,
  "bid": 1.08456,
  "ask": 1.08459,
  "spread": 0.3,
  "volume": 1234
}
```

### Binary Format (High Performance)
```
[MSG_TYPE:1][SYMBOL:8][TIMESTAMP:8][BID:8][ASK:8][SPREAD:4][VOLUME:4]
```

## Socket Patterns

### 1. PUB-SUB Pattern
- Simple one-way data flow
- Fire-and-forget semantics
- No subscriber feedback

### 2. XPUB-XSUB Pattern
- Subscription tracking
- Dynamic topic filtering
- Better resource management

### 3. PUSH-PULL Pattern (Alternative)
- Load balancing across workers
- Guaranteed delivery to one subscriber
- Good for processing pipelines

## Performance Characteristics

- **Latency**: < 1ms local, < 5ms network
- **Throughput**: 1M+ messages/second
- **Scalability**: Unlimited subscribers
- **Memory**: ~100MB for 1M messages/second

## Security Considerations

- Use ZeroMQ CURVE for encryption
- Implement IP whitelisting
- Add authentication tokens
- Monitor subscription patterns

## Deployment Options

### 1. Local Deployment
- Bridge on same machine as MT4
- Use IPC sockets for best performance
- Minimal network overhead

### 2. Network Deployment
- Bridge on dedicated server
- TCP sockets for remote access
- Consider firewall rules

### 3. Docker Deployment
- Bridge in separate container
- Use Docker networking
- Easy scaling and management