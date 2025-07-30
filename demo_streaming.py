#!/usr/bin/env python3
"""
Demonstrate market data streaming capability
"""

import time
import threading
from simulate_market_data import generate_market_data
from clients.python.market_data_client import MT4DataClient

def start_simulator():
    """Start market data simulator in background"""
    print("Starting market data simulator...")
    thread = threading.Thread(target=generate_market_data, kwargs={'duration': 30})
    thread.daemon = True
    thread.start()
    time.sleep(1)  # Give it time to start

def demo_streaming():
    """Demonstrate streaming functionality"""
    print("\n=== MT4 Market Data Streaming Demo ===\n")
    
    # Start simulator
    start_simulator()
    
    # Create client
    print("Creating MT4 data client...")
    client = MT4DataClient(mode="file", file_path="market_data.csv")
    
    # Track quotes
    quotes_received = 0
    symbols_seen = set()
    
    def on_tick(data):
        nonlocal quotes_received
        quotes_received += 1
        symbols_seen.add(data.get('symbol', 'Unknown'))
        
        if quotes_received <= 5 or quotes_received % 10 == 0:
            print(f"Quote #{quotes_received}: {data['symbol']} - "
                  f"Bid: {data['bid']}, Ask: {data['ask']}, "
                  f"Spread: {data['spread']}")
    
    def on_error(error):
        print(f"Error: {error}")
    
    # Connect callbacks
    client.on_tick = on_tick
    client.on_error = on_error
    
    # Start streaming
    print("\nStarting to stream market data...")
    print("(Showing first 5 quotes, then every 10th quote)\n")
    
    try:
        client.start()
        
        # Run for 20 seconds
        for i in range(20):
            time.sleep(1)
            if i == 10:
                print(f"\n10 seconds elapsed - {quotes_received} quotes received")
                print(f"Symbols tracked: {', '.join(sorted(symbols_seen))}\n")
        
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        client.stop()
        
    print(f"\n=== Demo Complete ===")
    print(f"Total quotes received: {quotes_received}")
    print(f"Symbols tracked: {', '.join(sorted(symbols_seen))}")
    print(f"Average rate: {quotes_received/20:.1f} quotes/second")

if __name__ == "__main__":
    demo_streaming()