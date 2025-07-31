#!/usr/bin/env python3
"""
MT4 Log Data Collector
Extracts market data from MT4 logs without needing compiled EAs
"""

import re
import os
import csv
import time
from datetime import datetime
from pathlib import Path

class MT4LogDataCollector:
    def __init__(self, log_dir="/mt4/logs", output_file="/mt4/MQL4/Files/market_data.csv"):
        self.log_dir = Path(log_dir)
        self.output_file = Path(output_file)
        self.last_position = {}
        
    def parse_log_line(self, line):
        """Extract market data from MT4 log lines"""
        # Look for price quotes in logs
        # Pattern: "2025.07.30 12:34:56.789 EURUSD,H1: Bid: 1.08765 Ask: 1.08775"
        price_pattern = r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\.\d+\s+(\w+),\w+:\s+Bid:\s+([\d.]+)\s+Ask:\s+([\d.]+)'
        
        match = re.search(price_pattern, line)
        if match:
            timestamp_str, symbol, bid, ask = match.groups()
            timestamp = datetime.strptime(timestamp_str, "%Y.%m.%d %H:%M:%S")
            return {
                'timestamp': timestamp,
                'symbol': symbol,
                'bid': float(bid),
                'ask': float(ask),
                'spread': round((float(ask) - float(bid)) * 10000, 1)  # in points
            }
        return None
    
    def collect_from_logs(self):
        """Continuously collect data from MT4 logs"""
        print(f"Starting log data collection...")
        print(f"Log directory: {self.log_dir}")
        print(f"Output file: {self.output_file}")
        
        # Ensure output directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Open CSV file for writing
        with open(self.output_file, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'symbol', 'bid', 'ask', 'spread']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            print("Monitoring logs for market data...")
            while True:
                # Find the latest log file
                log_files = list(self.log_dir.glob("*.log"))
                if not log_files:
                    print("No log files found. Waiting...")
                    time.sleep(5)
                    continue
                
                # Get the most recent log file
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                
                # Read new lines from the log
                if latest_log not in self.last_position:
                    self.last_position[latest_log] = 0
                
                try:
                    with open(latest_log, 'r', encoding='utf-16-le', errors='ignore') as f:
                        f.seek(self.last_position[latest_log])
                        
                        for line in f:
                            data = self.parse_log_line(line)
                            if data:
                                writer.writerow(data)
                                csvfile.flush()
                                print(f"Collected: {data['symbol']} Bid:{data['bid']} Ask:{data['ask']}")
                        
                        self.last_position[latest_log] = f.tell()
                
                except Exception as e:
                    print(f"Error reading log: {e}")
                
                time.sleep(1)  # Check every second

if __name__ == "__main__":
    collector = MT4LogDataCollector()
    try:
        collector.collect_from_logs()
    except KeyboardInterrupt:
        print("\nData collection stopped.")