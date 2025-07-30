#!/usr/bin/env python3
"""
MT4 Market Data Client
Connects to MT4 MarketDataStreamer EA via named pipe or file
"""

import json
import time
import sys
import os
import csv
from datetime import datetime
from typing import Dict, List, Callable, Optional
import threading
import queue

# For Windows named pipes
if sys.platform == "win32":
    import win32pipe
    import win32file
    import pywintypes

class MT4DataClient:
    """Client for receiving market data from MT4"""
    
    def __init__(self, mode: str = "pipe", pipe_name: str = "MT4_MarketData", 
                 file_path: str = "market_data.csv"):
        self.mode = mode
        self.pipe_name = pipe_name
        self.file_path = file_path
        self.running = False
        self.data_queue = queue.Queue()
        self.callbacks: Dict[str, List[Callable]] = {
            'quote': [],
            'tick': [],
            'bar': []
        }
        
    def on_quote(self, callback: Callable):
        """Register callback for quote updates"""
        self.callbacks['quote'].append(callback)
        
    def on_tick(self, callback: Callable):
        """Register callback for tick updates"""
        self.callbacks['tick'].append(callback)
        
    def on_bar(self, callback: Callable):
        """Register callback for bar updates"""
        self.callbacks['bar'].append(callback)
        
    def connect_pipe(self):
        """Connect to MT4 via named pipe"""
        if sys.platform == "win32":
            pipe_path = f"\\\\.\\pipe\\{self.pipe_name}"
            try:
                self.pipe = win32file.CreateFile(
                    pipe_path,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                print(f"Connected to pipe: {pipe_path}")
                return True
            except pywintypes.error as e:
                print(f"Failed to connect to pipe: {e}")
                return False
        else:
            # Linux/Unix named pipe (FIFO)
            pipe_path = f"/tmp/{self.pipe_name}"
            if not os.path.exists(pipe_path):
                os.mkfifo(pipe_path)
            self.pipe = open(pipe_path, 'r')
            print(f"Connected to pipe: {pipe_path}")
            return True
            
    def read_pipe_data(self):
        """Read data from named pipe"""
        if sys.platform == "win32":
            try:
                result, data = win32file.ReadFile(self.pipe, 4096)
                if result == 0:
                    return data.decode('utf-8')
            except:
                return None
        else:
            return self.pipe.readline()
            
    def process_pipe_stream(self):
        """Process incoming pipe data"""
        buffer = ""
        while self.running:
            data = self.read_pipe_data()
            if data:
                buffer += data
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line
                
                for line in lines[:-1]:
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            self.handle_message(msg)
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            
    def process_file_stream(self):
        """Process CSV file stream"""
        last_pos = 0
        while self.running:
            try:
                with open(self.file_path, 'r') as f:
                    f.seek(last_pos)
                    reader = csv.DictReader(f)
                    
                    for row in reader:
                        self.handle_csv_row(row)
                        
                    last_pos = f.tell()
                    
            except FileNotFoundError:
                print(f"Waiting for file: {self.file_path}")
                
            time.sleep(0.1)
            
    def handle_message(self, msg: dict):
        """Handle incoming JSON message"""
        msg_type = msg.get('type')
        
        if msg_type == 'header':
            print(f"Connected to MT4. Symbols: {msg.get('symbols', [])}")
            
        elif msg_type == 'quote':
            for callback in self.callbacks['quote']:
                callback(msg)
                
        elif msg_type == 'tick':
            for callback in self.callbacks['tick']:
                callback(msg)
                
    def handle_csv_row(self, row: dict):
        """Handle CSV row data"""
        # Convert CSV row to quote message format
        msg = {
            'type': 'quote',
            'symbol': row['Symbol'],
            'timestamp': row['Timestamp'],
            'bid': float(row['Bid']),
            'ask': float(row['Ask']),
            'spread': float(row['Spread']),
            'volume': int(row['Volume'])
        }
        
        if 'Open' in row:
            msg['bar'] = {
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['BarVolume'])
            }
            
        for callback in self.callbacks['quote']:
            callback(msg)
            
    def start(self):
        """Start the data client"""
        self.running = True
        
        if self.mode == "pipe":
            if self.connect_pipe():
                thread = threading.Thread(target=self.process_pipe_stream)
                thread.daemon = True
                thread.start()
            else:
                print("Failed to connect via pipe, falling back to file mode")
                self.mode = "file"
                
        if self.mode == "file":
            thread = threading.Thread(target=self.process_file_stream)
            thread.daemon = True
            thread.start()
            
    def stop(self):
        """Stop the data client"""
        self.running = False
        if hasattr(self, 'pipe'):
            if sys.platform == "win32":
                win32file.CloseHandle(self.pipe)
            else:
                self.pipe.close()


# Example usage
if __name__ == "__main__":
    # Create client
    client = MT4DataClient(mode="pipe")
    
    # Define callback functions
    def on_quote_update(quote):
        print(f"Quote: {quote['symbol']} Bid: {quote['bid']} Ask: {quote['ask']} Spread: {quote['spread']}")
        
    def on_tick_update(tick):
        print(f"Tick: {tick['symbol']} Bid: {tick['bid']} Ask: {tick['ask']} @ {tick['ms']}ms")
        
    # Register callbacks
    client.on_quote(on_quote_update)
    client.on_tick(on_tick_update)
    
    # Start client
    print("Starting MT4 Market Data Client...")
    client.start()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping client...")
        client.stop()