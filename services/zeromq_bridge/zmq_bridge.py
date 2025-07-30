#!/usr/bin/env python3
"""
ZeroMQ Bridge for MT4 Market Data
High-performance market data distribution using ZeroMQ
"""

import zmq
import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import csv
import os
import signal
import sys

class ZeroMQBridge:
    """ZeroMQ bridge for MT4 market data streaming"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.context = zmq.Context()
        self.publisher = None
        self.running = False
        self.stats = {
            'messages_sent': 0,
            'bytes_sent': 0,
            'start_time': time.time(),
            'symbols': set()
        }
        
        # Setup logging
        logging.basicConfig(
            level=config.get('log_level', 'INFO'),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('ZMQBridge')
        
    def setup_publisher(self):
        """Setup ZeroMQ publisher socket"""
        self.publisher = self.context.socket(zmq.PUB)
        
        # Bind to specified addresses
        for address in self.config.get('publish_addresses', ['tcp://*:5556']):
            self.publisher.bind(address)
            self.logger.info(f"Publisher bound to {address}")
            
        # Set socket options
        self.publisher.setsockopt(zmq.SNDHWM, self.config.get('send_hwm', 10000))
        self.publisher.setsockopt(zmq.LINGER, 0)
        
    def publish_tick(self, tick_data: Dict[str, Any]):
        """Publish tick data to subscribers"""
        if not self.publisher:
            return
            
        # Create topic for subscription filtering
        symbol = tick_data.get('symbol', 'UNKNOWN')
        topic = f"tick.{symbol}"
        
        # Prepare message
        message = {
            'type': 'tick',
            'timestamp': int(time.time() * 1000),
            **tick_data
        }
        
        # Send as multipart message [topic, data]
        try:
            self.publisher.send_multipart([
                topic.encode('utf-8'),
                json.dumps(message).encode('utf-8')
            ])
            
            self.stats['messages_sent'] += 1
            self.stats['bytes_sent'] += len(json.dumps(message))
            self.stats['symbols'].add(symbol)
            
        except zmq.ZMQError as e:
            self.logger.error(f"Failed to publish message: {e}")
            
    def publish_bar(self, bar_data: Dict[str, Any]):
        """Publish bar data to subscribers"""
        if not self.publisher:
            return
            
        symbol = bar_data.get('symbol', 'UNKNOWN')
        timeframe = bar_data.get('timeframe', 'M1')
        topic = f"bar.{symbol}.{timeframe}"
        
        message = {
            'type': 'bar',
            'timestamp': int(time.time() * 1000),
            **bar_data
        }
        
        try:
            self.publisher.send_multipart([
                topic.encode('utf-8'),
                json.dumps(message).encode('utf-8')
            ])
            
            self.stats['messages_sent'] += 1
            
        except zmq.ZMQError as e:
            self.logger.error(f"Failed to publish bar: {e}")
            
    def watch_csv_file(self, filename: str):
        """Watch CSV file for market data"""
        last_position = 0
        
        while self.running:
            try:
                if os.path.exists(filename):
                    with open(filename, 'r') as f:
                        f.seek(last_position)
                        reader = csv.DictReader(f)
                        
                        for row in reader:
                            if row and 'Symbol' in row:
                                tick_data = {
                                    'symbol': row['Symbol'],
                                    'bid': float(row['Bid']),
                                    'ask': float(row['Ask']),
                                    'spread': float(row['Spread']),
                                    'volume': int(row.get('Volume', 0))
                                }
                                self.publish_tick(tick_data)
                                
                        last_position = f.tell()
                        
            except Exception as e:
                self.logger.error(f"Error reading CSV: {e}")
                
            time.sleep(0.1)  # Check every 100ms
            
    def watch_named_pipe(self, pipe_name: str):
        """Watch named pipe for market data"""
        pipe_path = f"/tmp/{pipe_name}"
        
        while self.running:
            try:
                if os.path.exists(pipe_path):
                    with open(pipe_path, 'r') as pipe:
                        for line in pipe:
                            try:
                                data = json.loads(line.strip())
                                if data.get('type') == 'tick':
                                    self.publish_tick(data)
                                elif data.get('type') == 'bar':
                                    self.publish_bar(data)
                            except json.JSONDecodeError:
                                self.logger.warning(f"Invalid JSON: {line}")
                else:
                    time.sleep(1)  # Wait for pipe creation
                    
            except Exception as e:
                self.logger.error(f"Pipe error: {e}")
                time.sleep(1)
                
    def report_stats(self):
        """Report bridge statistics"""
        while self.running:
            time.sleep(30)  # Report every 30 seconds
            
            uptime = time.time() - self.stats['start_time']
            rate = self.stats['messages_sent'] / uptime if uptime > 0 else 0
            
            self.logger.info(
                f"Stats - Messages: {self.stats['messages_sent']}, "
                f"Rate: {rate:.1f} msg/s, "
                f"Symbols: {len(self.stats['symbols'])}, "
                f"Data: {self.stats['bytes_sent'] / 1024 / 1024:.1f} MB"
            )
            
    def start(self):
        """Start the ZeroMQ bridge"""
        self.logger.info("Starting ZeroMQ bridge...")
        self.running = True
        
        # Setup publisher
        self.setup_publisher()
        
        # Start stats reporter
        stats_thread = threading.Thread(target=self.report_stats)
        stats_thread.daemon = True
        stats_thread.start()
        
        # Start data sources
        sources = []
        
        if self.config.get('csv_file'):
            csv_thread = threading.Thread(
                target=self.watch_csv_file,
                args=(self.config['csv_file'],)
            )
            csv_thread.daemon = True
            csv_thread.start()
            sources.append(csv_thread)
            self.logger.info(f"Watching CSV file: {self.config['csv_file']}")
            
        if self.config.get('pipe_name'):
            pipe_thread = threading.Thread(
                target=self.watch_named_pipe,
                args=(self.config['pipe_name'],)
            )
            pipe_thread.daemon = True
            pipe_thread.start()
            sources.append(pipe_thread)
            self.logger.info(f"Watching named pipe: {self.config['pipe_name']}")
            
        # Wait for threads
        try:
            for thread in sources:
                thread.join()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            self.stop()
            
    def stop(self):
        """Stop the bridge"""
        self.running = False
        if self.publisher:
            self.publisher.close()
        self.context.term()
        self.logger.info("ZeroMQ bridge stopped")
        

def main():
    """Main entry point"""
    # Default configuration
    config = {
        'publish_addresses': [
            'tcp://*:5556',  # TCP for network clients
            'ipc:///tmp/mt4_market_data'  # IPC for local clients
        ],
        'csv_file': 'market_data.csv',
        'pipe_name': 'MT4_MarketData',
        'log_level': 'INFO',
        'send_hwm': 10000  # High water mark for send queue
    }
    
    # Handle signals
    def signal_handler(sig, frame):
        print("\nShutting down ZeroMQ bridge...")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start bridge
    bridge = ZeroMQBridge(config)
    bridge.start()
    

if __name__ == '__main__':
    main()