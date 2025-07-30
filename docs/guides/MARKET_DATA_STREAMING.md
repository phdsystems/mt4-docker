# Market Data Streaming Guide

This guide explains how to stream real-time market data from MT4 using the MarketDataStreamer EA.

## Overview

The MarketDataStreamer EA provides multiple methods to stream market data:
- **File-based streaming** - CSV files for simple integration
- **Named pipe streaming** - Low-latency IPC for real-time applications
- **WebSocket bridge** - Stream data to web applications

## Quick Start

### 1. Deploy the Streamer

```bash
./bin/deploy_market_streamer.sh
```

### 2. Configure in MT4

1. Connect via VNC:
   ```bash
   ./bin/connect_vnc.sh
   ```

2. In MT4, drag MarketDataStreamer EA to any chart

3. Configure EA settings:
   - **Stream Mode**: FILE, PIPE, or ALL
   - **Symbols**: Comma-separated list (e.g., "EURUSD,GBPUSD")
   - **Update Interval**: Milliseconds between updates
   - **Stream Ticks**: Enable tick-by-tick data
   - **Stream Bars**: Include OHLC data

## Streaming Methods

### File-Based Streaming

Data is written to CSV file at `/mt4/data/market_data.csv`

**CSV Format:**
```csv
Timestamp,Symbol,Bid,Ask,Spread,Volume,Open,High,Low,Close,BarVolume
2024-01-29 12:34:56,EURUSD,1.08562,1.08565,0.3,1234,1.08550,1.08570,1.08540,1.08562,5678
```

**Access from host:**
```bash
# View live data
docker exec mt4-docker tail -f /mt4/data/market_data.csv

# Copy to host
docker cp mt4-docker:/mt4/data/market_data.csv ./
```

### Named Pipe Streaming

Real-time JSON streaming via named pipe.

**JSON Format:**
```json
{
  "type": "quote",
  "symbol": "EURUSD",
  "timestamp": 1706539496,
  "bid": 1.08562,
  "ask": 1.08565,
  "spread": 0.3,
  "volume": 1234,
  "bar": {
    "open": 1.08550,
    "high": 1.08570,
    "low": 1.08540,
    "close": 1.08562,
    "volume": 5678
  }
}
```

**Tick Data Format:**
```json
{
  "type": "tick",
  "symbol": "EURUSD",
  "timestamp": 1706539496,
  "ms": 123,
  "bid": 1.08562,
  "ask": 1.08565
}
```

## Client Examples

### Python Client

```python
from clients.python.market_data_client import MT4DataClient

# Create client
client = MT4DataClient(mode="pipe")

# Define callbacks
def on_quote(quote):
    print(f"{quote['symbol']}: {quote['bid']}/{quote['ask']}")

# Register and start
client.on_quote(on_quote)
client.start()
```

### Node.js WebSocket Bridge

```bash
cd clients/nodejs
npm install
npm run start:with-client
```

Access web interface at http://localhost:8081

### Custom Integration

**Reading CSV in Python:**
```python
import pandas as pd

# Read live data
df = pd.read_csv('market_data.csv')
latest_quotes = df.groupby('Symbol').last()
```

**Connecting to pipe in C++:**
```cpp
#include <windows.h>
#include <iostream>

HANDLE hPipe = CreateFile(
    TEXT("\\\\.\\pipe\\MT4_MarketData"),
    GENERIC_READ,
    0,
    NULL,
    OPEN_EXISTING,
    0,
    NULL
);
```

## Advanced Configuration

### Multiple Symbol Streaming

```mql4
// In EA inputs
input string InpSymbols = "EURUSD,GBPUSD,USDJPY,AUDUSD,NZDUSD,USDCAD,USDCHF";
```

### High-Frequency Tick Streaming

```mql4
input int InpUpdateIntervalMs = 10;     // 10ms updates
input bool InpStreamTicks = true;       // Enable tick streaming
input bool InpStreamBars = false;       // Disable bar data for performance
```

### Custom Pipe Names

```mql4
input string InpPipeName = "MyCustomPipe";  // Custom pipe name
```

## Performance Considerations

1. **Update Interval**: Lower intervals = more data but higher CPU usage
2. **Symbol Count**: Each symbol adds processing overhead
3. **Data Types**: Tick data generates much more volume than quote data
4. **File vs Pipe**: Pipes are faster but require active consumer

### Recommended Settings

**Low Latency (Trading)**
- Mode: PIPE
- Update Interval: 50-100ms
- Stream Ticks: Yes
- Symbols: Only required pairs

**Data Collection (Analysis)**
- Mode: FILE
- Update Interval: 1000ms
- Stream Ticks: No
- Stream Bars: Yes

**Web Dashboard**
- Mode: ALL
- Update Interval: 500ms
- Use WebSocket bridge

## Troubleshooting

### EA not streaming data
- Check EA is attached to chart
- Verify EA is enabled (smiley face)
- Check Expert Advisors are allowed in MT4

### No data in CSV file
- Ensure `/mt4/data` directory exists
- Check file permissions
- Verify symbols are valid

### Pipe connection failed
- On Windows: Check pipe name format
- On Linux: Ensure FIFO exists
- Verify no other process is using pipe

### WebSocket bridge issues
- Check port 8080 is not in use
- Ensure Node.js dependencies installed
- Check firewall settings

## Security Notes

- Pipe access is local only by default
- CSV files are inside container
- WebSocket bridge should use SSL in production
- Consider authentication for production use

## Example Use Cases

### 1. Real-time Dashboard
```javascript
// Subscribe to multiple symbols
ws.send(JSON.stringify({
    type: 'subscribe',
    symbols: ['EURUSD', 'GBPUSD', 'USDJPY']
}));
```

### 2. Data Logger
```python
import csv
import time

with open('price_log.csv', 'a') as f:
    writer = csv.writer(f)
    client.on_quote(lambda q: writer.writerow([
        time.time(), q['symbol'], q['bid'], q['ask']
    ]))
```

### 3. Price Alerts
```python
def check_price_alert(quote):
    if quote['symbol'] == 'EURUSD' and quote['bid'] > 1.0900:
        send_alert(f"EURUSD above 1.0900: {quote['bid']}")
```

### 4. Spread Monitor
```python
def monitor_spread(quote):
    if quote['spread'] > 2.0:
        log_high_spread(quote['symbol'], quote['spread'])
```