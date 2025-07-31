#!/usr/bin/env python3
"""
Read and analyze historic data exported from MT4
"""
import json
import pandas as pd
from datetime import datetime
import os
import glob

def read_mt4_json(filename):
    """Read JSON file exported from MT4"""
    with open(filename, 'r') as f:
        data = json.load(f)
    return data

def json_to_dataframe(json_data):
    """Convert MT4 JSON data to pandas DataFrame"""
    if isinstance(json_data, list):
        # Simple array format
        df = pd.DataFrame(json_data)
    else:
        # Nested format with metadata
        dfs = {}
        for symbol, bars in json_data.get('data', {}).items():
            df = pd.DataFrame(bars)
            df['symbol'] = symbol
            dfs[symbol] = df
        return dfs
    
    # Convert timestamp to datetime if present
    if 'timestamp' in df.columns:
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('datetime', inplace=True)
    
    return df

def analyze_data(df):
    """Basic analysis of historic data"""
    print("\n=== Data Analysis ===")
    print(f"Total bars: {len(df)}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    
    if 'close' in df.columns:
        print(f"\nPrice Statistics:")
        print(f"  Mean: {df['close'].mean():.5f}")
        print(f"  Std:  {df['close'].std():.5f}")
        print(f"  Min:  {df['close'].min():.5f}")
        print(f"  Max:  {df['close'].max():.5f}")
    
    if 'volume' in df.columns:
        print(f"\nVolume Statistics:")
        print(f"  Total: {df['volume'].sum():,}")
        print(f"  Mean:  {df['volume'].mean():.0f}")

def find_mt4_files():
    """Find MT4 data files in common locations"""
    # Check local directory
    local_files = glob.glob("*.json")
    
    # Check MT4 Files directory if mounted
    mt4_files = []
    mt4_path = "/mt4/MQL4/Files"
    if os.path.exists(mt4_path):
        mt4_files = glob.glob(f"{mt4_path}/*.json")
    
    return local_files + mt4_files

def main():
    print("MT4 Historic Data Reader")
    print("========================")
    
    # Find available files
    files = find_mt4_files()
    
    if not files:
        print("No JSON files found.")
        print("\nTo export data from MT4:")
        print("1. Attach HistoricDataExporter EA to a chart")
        print("2. Data will be saved to MQL4/Files/historic_data.json")
        return
    
    print(f"\nFound {len(files)} data file(s):")
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
    
    # Read and analyze each file
    for filename in files:
        print(f"\n\nProcessing: {filename}")
        print("-" * 50)
        
        try:
            data = read_mt4_json(filename)
            
            if isinstance(data, dict) and 'data' in data:
                # Multi-symbol format
                print(f"Export time: {data.get('export_time', 'Unknown')}")
                print(f"Timeframe: {data.get('timeframe', 'Unknown')}")
                
                dfs = json_to_dataframe(data)
                for symbol, df in dfs.items():
                    print(f"\n--- {symbol} ---")
                    analyze_data(df)
            else:
                # Single dataset format
                df = json_to_dataframe(data)
                analyze_data(df)
                
        except Exception as e:
            print(f"Error reading {filename}: {e}")

if __name__ == "__main__":
    main()