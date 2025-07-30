#!/usr/bin/env python3
"""
Simple demonstration of market data streaming
"""

import csv
import time
import threading

def stream_csv_data(filename="market_data.csv", duration=10):
    """Stream CSV data"""
    print("\n=== MT4 Market Data Streaming Demo ===\n")
    print(f"Reading from: {filename}")
    print("Streaming for {} seconds...\n".format(duration))
    
    quotes_count = 0
    symbols_seen = set()
    last_position = 0
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        try:
            with open(filename, 'r') as f:
                # Skip to last position
                f.seek(last_position)
                
                reader = csv.DictReader(f)
                for row in reader:
                    if row and 'Symbol' in row:
                        quotes_count += 1
                        symbols_seen.add(row['Symbol'])
                        
                        # Show first 5 and every 10th quote
                        if quotes_count <= 5 or quotes_count % 10 == 0:
                            print(f"Quote #{quotes_count}: {row['Symbol']} - "
                                  f"Bid: {row['Bid']}, Ask: {row['Ask']}, "
                                  f"Spread: {row['Spread']} pips")
                
                # Remember position for next iteration
                last_position = f.tell()
                
        except Exception as e:
            pass  # File might be locked during write
            
        time.sleep(0.1)  # Check for new data every 100ms
    
    print(f"\n=== Streaming Complete ===")
    print(f"Total quotes: {quotes_count}")
    print(f"Symbols tracked: {', '.join(sorted(symbols_seen))}")
    print(f"Average rate: {quotes_count/duration:.1f} quotes/second")

if __name__ == "__main__":
    # Start the simulator in background
    from simulate_market_data import generate_market_data
    
    print("Starting market data simulator...")
    simulator = threading.Thread(target=generate_market_data, kwargs={'duration': 15})
    simulator.daemon = True
    simulator.start()
    
    time.sleep(1)  # Give simulator time to start
    
    # Stream the data
    stream_csv_data(duration=10)