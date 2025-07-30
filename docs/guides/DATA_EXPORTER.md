# DataExporter EA Guide

## Overview
DataExporter is a simple and reliable Expert Advisor for streaming market data from MT4 to CSV files.

## Features
- Exports market data every 60 seconds (configurable)
- Appends to existing CSV file
- Handles multiple symbols in one file
- Minimal resource usage
- Production tested and stable

## Installation

1. The EA is already compiled and available in MT4
2. Connect via VNC:
   ```bash
   ./bin/connect_vnc.sh
   ```
3. In MT4:
   - Open Navigator (Ctrl+N)
   - Expand "Expert Advisors"
   - Find "DataExporter"
   - Drag to desired chart

## Configuration

### Input Parameters
- **UpdateInterval**: Update frequency in seconds (default: 60)
- **FileName**: Output CSV filename (default: "market_data.csv")

### Output Format
```csv
DateTime,Symbol,Bid,Ask,Spread,Volume
2025.07.30 19:04:28,EURJPY,170.872,170.900,28.0,1230
```

## Usage

### Single Symbol
Attach DataExporter to one chart for single symbol streaming.

### Multiple Symbols
Attach DataExporter to multiple charts. All instances append to the same CSV file.

### Accessing Data

From host machine:
```bash
# View live data
docker exec mt4-docker tail -f /mt4/MQL4/Files/market_data.csv

# Copy to host
docker cp mt4-docker:/mt4/MQL4/Files/market_data.csv ./market_data.csv
```

### Data Location
- Container: `/mt4/MQL4/Files/market_data.csv`
- Updates: Every 60 seconds (configurable)

## Monitoring

Check EA status:
```bash
docker exec mt4-docker grep "DataExporter" /mt4/logs/$(date +%Y%m%d).log
```

## Notes
- File remains open while EA is running for efficiency
- Automatically creates CSV header if file is empty
- Handles MT4 restarts gracefully
- Thread-safe for multiple instances