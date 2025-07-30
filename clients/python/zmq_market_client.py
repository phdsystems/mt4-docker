#!/usr/bin/env python3
"""
ZeroMQ Market Data Client
High-performance subscriber for MT4 market data
"""

import zmq
import json
import time
import threading
from typing import Callable, List, Optional, Dict, Any
from datetime import datetime


class ZMQMarketClient:
    """ZeroMQ client for subscribing to MT4 market data"""
    
    def __init__(self, 
                 addresses: List[str] = None,
                 topics: List[str] = None,
                 high_water_mark: int = 1000):
        """
        Initialize ZeroMQ market data client
        
        Args:
            addresses: List of ZeroMQ addresses to connect to
            topics: List of topics to subscribe to (None = all)
            high_water_mark: Maximum messages to queue
        """
        self.addresses = addresses or ['tcp://localhost:5556']
        self.topics = topics or ['']  # Empty string subscribes to all
        self.hwm = high_water_mark
        
        self.context = zmq.Context()
        self.subscriber = None
        self.running = False
        
        # Callbacks
        self.on_tick = None
        self.on_bar = None
        self.on_error = None
        self.on_connect = None
        self.on_disconnect = None
        
        # Statistics
        self.stats = {
            'messages_received': 0,
            'bytes_received': 0,
            'start_time': None,
            'last_message_time': None,
            'symbols': set()
        }
        
    def connect(self):
        """Connect to ZeroMQ publishers"""
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.setsockopt(zmq.RCVHWM, self.hwm)
        self.subscriber.setsockopt(zmq.LINGER, 0)
        
        # Connect to all addresses
        for address in self.addresses:
            self.subscriber.connect(address)
            print(f"Connected to {address}")
            
        # Subscribe to topics
        for topic in self.topics:
            self.subscriber.subscribe(topic.encode('utf-8'))
            if topic:
                print(f"Subscribed to topic: {topic}")
            else:
                print("Subscribed to all topics")
                
        if self.on_connect:
            self.on_connect()
            
    def disconnect(self):
        """Disconnect from publishers"""
        self.running = False
        if self.subscriber:
            self.subscriber.close()
        self.context.term()
        
        if self.on_disconnect:
            self.on_disconnect()
            
    def subscribe_symbol(self, symbol: str):
        """Subscribe to specific symbol"""
        if self.subscriber:
            self.subscriber.subscribe(f"tick.{symbol}".encode('utf-8'))
            self.subscriber.subscribe(f"bar.{symbol}".encode('utf-8'))
            
    def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from specific symbol"""
        if self.subscriber:
            self.subscriber.unsubscribe(f"tick.{symbol}".encode('utf-8'))
            self.subscriber.unsubscribe(f"bar.{symbol}".encode('utf-8'))
            
    def process_message(self, topic: str, data: bytes):
        """Process received message"""
        try:
            message = json.loads(data.decode('utf-8'))
            
            # Update statistics
            self.stats['messages_received'] += 1
            self.stats['bytes_received'] += len(data)
            self.stats['last_message_time'] = time.time()
            
            # Route message by type
            msg_type = message.get('type')
            
            if msg_type == 'tick':
                self.stats['symbols'].add(message.get('symbol', 'UNKNOWN'))
                if self.on_tick:
                    self.on_tick(message)
                    
            elif msg_type == 'bar':
                if self.on_bar:
                    self.on_bar(message)
                    
        except Exception as e:
            if self.on_error:
                self.on_error(f"Message processing error: {e}")
                
    def run(self):
        """Run the subscriber loop"""
        self.running = True
        self.stats['start_time'] = time.time()
        
        while self.running:
            try:
                # Use poller for timeout support
                poller = zmq.Poller()
                poller.register(self.subscriber, zmq.POLLIN)
                
                events = dict(poller.poll(1000))  # 1 second timeout
                
                if self.subscriber in events:
                    # Receive multipart message [topic, data]
                    topic, data = self.subscriber.recv_multipart()
                    self.process_message(topic.decode('utf-8'), data)
                    
            except zmq.ZMQError as e:
                if self.on_error:
                    self.on_error(f"ZMQ error: {e}")
                if e.errno == zmq.ETERM:
                    break
                    
            except Exception as e:
                if self.on_error:
                    self.on_error(f"Unexpected error: {e}")
                    
    def start(self):
        """Start subscriber in background thread"""
        self.connect()
        
        # Run in background thread
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """Stop the subscriber"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2)
        self.disconnect()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        if self.stats['start_time']:
            uptime = time.time() - self.stats['start_time']
            rate = self.stats['messages_received'] / uptime if uptime > 0 else 0
        else:
            uptime = 0
            rate = 0
            
        return {
            'messages_received': self.stats['messages_received'],
            'bytes_received': self.stats['bytes_received'],
            'message_rate': rate,
            'symbols_count': len(self.stats['symbols']),
            'symbols': list(self.stats['symbols']),
            'uptime_seconds': uptime,
            'last_message': self.stats['last_message_time']
        }


# Example usage
if __name__ == '__main__':
    # Create client
    client = ZMQMarketClient(
        addresses=['tcp://localhost:5556', 'ipc:///tmp/mt4_market_data'],
        topics=['tick.EURUSD', 'tick.GBPUSD']  # Subscribe to specific symbols
    )
    
    # Define callbacks
    def on_tick(tick):
        print(f"Tick: {tick['symbol']} - Bid: {tick['bid']}, Ask: {tick['ask']}")
        
    def on_error(error):
        print(f"Error: {error}")
        
    def on_connect():
        print("Connected to market data feed")
        
    # Set callbacks
    client.on_tick = on_tick
    client.on_error = on_error
    client.on_connect = on_connect
    
    # Start client
    print("Starting ZeroMQ market data client...")
    client.start()
    
    try:
        # Run for 30 seconds
        time.sleep(30)
        
        # Print statistics
        stats = client.get_stats()
        print(f"\nStatistics:")
        print(f"Messages received: {stats['messages_received']}")
        print(f"Message rate: {stats['message_rate']:.1f} msg/s")
        print(f"Symbols: {', '.join(stats['symbols'])}")
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        
    finally:
        client.stop()