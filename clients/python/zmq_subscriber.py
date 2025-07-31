#!/usr/bin/env python3
"""
Real ZeroMQ Subscriber for MT4 Data
"""

import zmq
import json
from datetime import datetime

class MT4DataSubscriber:
    def __init__(self, host='localhost', port=5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{host}:{port}")
        
        # Subscribe to all topics by default
        self.socket.subscribe(b"")
        
        print(f"Connected to MT4 publisher at {host}:{port}")
    
    def subscribe_to_symbol(self, symbol):
        """Subscribe to specific symbol"""
        topic = f"TICK.{symbol}".encode()
        self.socket.subscribe(topic)
        print(f"Subscribed to {symbol}")
    
    def subscribe_to_account(self):
        """Subscribe to account updates"""
        self.socket.subscribe(b"ACCOUNT")
        print("Subscribed to account updates")
    
    def run(self):
        """Main receiving loop"""
        print("Listening for messages...")
        
        try:
            while True:
                # Receive message
                message = self.socket.recv_string()
                
                # Split topic and data
                parts = message.split(' ', 1)
                if len(parts) == 2:
                    topic, data = parts
                    
                    try:
                        # Parse JSON data
                        json_data = json.loads(data)
                        
                        # Handle different topics
                        if topic.startswith("TICK."):
                            self.handle_tick(topic, json_data)
                        elif topic == "ACCOUNT":
                            self.handle_account(json_data)
                        else:
                            print(f"Unknown topic: {topic}")
                    
                    except json.JSONDecodeError as e:
                        print(f"JSON parse error: {e}")
                        print(f"Raw data: {data}")
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.close()
    
    def handle_tick(self, topic, data):
        """Handle tick data"""
        symbol = data.get('symbol', 'Unknown')
        bid = data.get('bid', 0)
        ask = data.get('ask', 0)
        spread = data.get('spread', 0)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol}: "
              f"Bid={bid:.5f} Ask={ask:.5f} Spread={spread:.1f}")
    
    def handle_account(self, data):
        """Handle account data"""
        balance = data.get('balance', 0)
        equity = data.get('equity', 0)
        margin = data.get('margin', 0)
        free_margin = data.get('free_margin', 0)
        
        print(f"\n[ACCOUNT UPDATE] Balance: ${balance:.2f} | "
              f"Equity: ${equity:.2f} | "
              f"Margin: ${margin:.2f} | "
              f"Free: ${free_margin:.2f}\n")
    
    def close(self):
        """Clean up resources"""
        self.socket.close()
        self.context.term()


# Advanced subscriber with data storage
class MT4DataCollector(MT4DataSubscriber):
    def __init__(self, host='localhost', port=5555):
        super().__init__(host, port)
        self.tick_data = {}
        self.account_data = None
    
    def handle_tick(self, topic, data):
        """Store tick data"""
        symbol = data.get('symbol')
        if symbol:
            if symbol not in self.tick_data:
                self.tick_data[symbol] = []
            
            self.tick_data[symbol].append(data)
            
            # Keep only last 1000 ticks per symbol
            if len(self.tick_data[symbol]) > 1000:
                self.tick_data[symbol].pop(0)
        
        super().handle_tick(topic, data)
    
    def handle_account(self, data):
        """Store account data"""
        self.account_data = data
        super().handle_account(data)
    
    def get_latest_prices(self):
        """Get latest price for each symbol"""
        latest = {}
        for symbol, ticks in self.tick_data.items():
            if ticks:
                latest[symbol] = ticks[-1]
        return latest


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='MT4 ZeroMQ Data Subscriber')
    parser.add_argument('--host', default='localhost', help='MT4 host')
    parser.add_argument('--port', type=int, default=5555, help='Publisher port')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to subscribe')
    parser.add_argument('--collector', action='store_true', help='Use data collector mode')
    
    args = parser.parse_args()
    
    # Create subscriber
    if args.collector:
        subscriber = MT4DataCollector(args.host, args.port)
    else:
        subscriber = MT4DataSubscriber(args.host, args.port)
    
    # Subscribe to specific symbols if provided
    if args.symbols:
        for symbol in args.symbols:
            subscriber.subscribe_to_symbol(symbol)
    
    # Always subscribe to account updates
    subscriber.subscribe_to_account()
    
    # Run subscriber
    subscriber.run()