# Exporting Market Data from MT4 Without EAs

Since we cannot compile EAs, here are alternative methods to export market data:

## Method 1: Manual Export via MT4 Interface

1. **Connect via VNC**: `vncviewer localhost:5900`
2. **In MT4**:
   - Press `F2` to open History Center
   - Select your symbol (e.g., EURUSD)
   - Select timeframe (e.g., M1 for 1-minute data)
   - Click "Export" button
   - Save as CSV file

## Method 2: Chart Export

1. **Open a chart** for your desired symbol
2. **Right-click** on the chart
3. Select **"Save As"**
4. Choose **"CSV (*.csv)"** format
5. This exports all visible chart data

## Method 3: Using Scripts (No Compilation Needed)

We've created scripts that can help:

### Python Log Collector
```bash
docker exec -it mt4-docker python3 /scripts/log_data_collector.py
```

### File Watcher
```bash
docker exec -it mt4-docker python3 /scripts/file_watcher_export.py
```

## Method 4: Copy Data from MT4 Windows

1. **Select data** in Market Watch window
2. **Press** `Ctrl+C` to copy
3. **Paste** into Excel or text file
4. Save as CSV

## Method 5: Use Existing Indicators

Some built-in indicators can write data:
1. Attach any indicator to a chart
2. In the "Common" tab, check "Save data"
3. Data will be saved to `MQL4/Files/`

## Automated Alternative

Since DataExporter EA compiled successfully (0 errors), you can:
1. Get it compiled on a Windows MT4 installation
2. Copy the `.ex4` file back to Docker
3. Place it in `/mt4/MQL4/Experts/`

## Quick Data Access

To quickly see current market data:
```bash
# View MT4 logs for price data
docker exec mt4-docker tail -f /mt4/logs/*.log | grep -E "(Bid|Ask|EURUSD)"

# Check for any CSV files created
docker exec mt4-docker find /mt4/MQL4/Files -name "*.csv" -ls
```