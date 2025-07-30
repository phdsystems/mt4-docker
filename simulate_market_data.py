#!/usr/bin/env python3
"""
Market Data Simulator
Generates simulated market data for testing
"""

import csv
import time
import random
from datetime import datetime

def generate_market_data(filename="market_data.csv", symbols=None, duration=60):
    """Generate simulated market data"""
    if symbols is None:
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
    
    # Initial prices
    prices = {
        "EURUSD": {"bid": 1.0850, "spread": 0.3},
        "GBPUSD": {"bid": 1.2680, "spread": 0.5},
        "USDJPY": {"bid": 148.50, "spread": 0.3},
        "AUDUSD": {"bid": 0.6580, "spread": 0.4}
    }
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Symbol", "Bid", "Ask", "Spread", "Volume"])
        
        print(f"Generating market data to {filename}")
        print("Press Ctrl+C to stop")
        
        start_time = time.time()
        tick_count = 0
        
        try:
            while time.time() - start_time < duration:
                for symbol in symbols:
                    if symbol in prices:
                        # Random walk
                        change = random.uniform(-0.0005, 0.0005)
                        prices[symbol]["bid"] += change
                        
                        bid = prices[symbol]["bid"]
                        spread = prices[symbol]["spread"]
                        ask = bid + spread * 0.0001
                        volume = random.randint(100, 5000)
                        
                        # Get appropriate decimal places
                        if symbol == "USDJPY":
                            decimals = 3
                        else:
                            decimals = 5
                        
                        row = [
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            symbol,
                            f"{bid:.{decimals}f}",
                            f"{ask:.{decimals}f}",
                            f"{spread:.1f}",
                            volume
                        ]
                        
                        writer.writerow(row)
                        tick_count += 1
                        
                        if tick_count % 10 == 0:
                            f.flush()  # Flush to disk
                            print(f"\rGenerated {tick_count} ticks...", end="")
                
                time.sleep(0.5)  # Update every 500ms
                
        except KeyboardInterrupt:
            print("\nStopped by user")
        
        print(f"\nGenerated {tick_count} ticks in {time.time() - start_time:.1f} seconds")

if __name__ == "__main__":
    # Run simulator
    generate_market_data(duration=300)  # Run for 5 minutes