#!/usr/bin/env python3
"""
MT4 File Watcher Data Export
Monitors MT4 files and extracts market data without EAs
"""

import os
import time
import csv
from datetime import datetime
from pathlib import Path
import json

class MT4FileWatcher:
    def __init__(self):
        self.mt4_base = Path("/mt4")
        self.output_file = self.mt4_base / "MQL4/Files/market_data_export.csv"
        self.watch_paths = [
            self.mt4_base / "MQL4/Logs",
            self.mt4_base / "logs",
            self.mt4_base / "tester/logs"
        ]
        
    def extract_from_terminal_state(self):
        """Extract data from MT4 terminal state files"""
        # MT4 stores some data in binary files we can parse
        config_files = [
            self.mt4_base / "config/terminal.ini",
            self.mt4_base / "config/accounts.ini",
            self.mt4_base / "profiles/lastprofile.ini"
        ]
        
        data = {}
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-16-le', errors='ignore') as f:
                        content = f.read()
                        # Extract any price data from configs
                        if 'Price' in content or 'Rate' in content:
                            lines = content.split('\n')
                            for line in lines:
                                if '=' in line and any(x in line for x in ['Price', 'Rate', 'Bid', 'Ask']):
                                    key, value = line.split('=', 1)
                                    data[key.strip()] = value.strip()
                except Exception as e:
                    print(f"Error reading {config_file}: {e}")
        
        return data
    
    def create_data_export_script(self):
        """Create a script that can be run manually in MT4"""
        script_content = """
// Simple Data Export Script - No compilation needed
// Save this as DataExport.mq4 in MQL4/Scripts/
// Can be run from Navigator window

#property strict

void OnStart() {
    string filename = "quick_export.csv";
    int handle = FileOpen(filename, FILE_WRITE|FILE_CSV);
    
    if(handle != INVALID_HANDLE) {
        FileWrite(handle, "Time", "Symbol", "Bid", "Ask", "Spread");
        FileWrite(handle, 
            TimeToString(TimeCurrent()), 
            Symbol(), 
            Bid, 
            Ask, 
            (Ask-Bid)/Point);
        FileClose(handle);
        Alert("Data exported to " + filename);
    }
}
"""
        script_path = self.mt4_base / "MQL4/Scripts/QuickExport.mq4"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        print(f"Created script at: {script_path}")
        print("This script can be dragged onto a chart in MT4 to export current prices")
    
    def monitor_and_export(self):
        """Monitor MT4 directories and export data"""
        print("MT4 File Watcher started...")
        print(f"Output: {self.output_file}")
        
        # Ensure output directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create the manual script
        self.create_data_export_script()
        
        with open(self.output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Timestamp', 'Type', 'Data'])
            
            print("\nMonitoring MT4 files...")
            print("Alternative data export methods:")
            print("1. In MT4: Tools -> History Center -> Export")
            print("2. Right-click chart -> Save As -> CSV")
            print("3. Run the QuickExport script from Navigator")
            print("\nPress Ctrl+C to stop monitoring\n")
            
            while True:
                # Check for any new CSV files created by MT4
                csv_files = list((self.mt4_base / "MQL4/Files").glob("*.csv"))
                for csv_file in csv_files:
                    if csv_file != self.output_file:
                        mtime = datetime.fromtimestamp(csv_file.stat().st_mtime)
                        if (datetime.now() - mtime).seconds < 60:  # Modified in last minute
                            print(f"Found recent CSV: {csv_file.name}")
                            writer.writerow([datetime.now(), 'CSV_FOUND', csv_file.name])
                            csvfile.flush()
                
                # Check terminal state
                state_data = self.extract_from_terminal_state()
                if state_data:
                    writer.writerow([datetime.now(), 'STATE', json.dumps(state_data)])
                    csvfile.flush()
                
                time.sleep(5)

if __name__ == "__main__":
    watcher = MT4FileWatcher()
    try:
        watcher.monitor_and_export()
    except KeyboardInterrupt:
        print("\nFile watcher stopped.")