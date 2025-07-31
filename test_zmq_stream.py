#!/usr/bin/env python3
"""
Test ZeroMQ streaming from MT4
"""
import zmq
import json
import signal
import sys
from datetime import datetime

def signal_handler(sig, frame):
    print("\nShutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Create context and socket
context = zmq.Context()
socket = context.socket(zmq.SUB)

# Connect to MT4 publisher on port 32770
print(f"[{datetime.now()}] Connecting to MT4 ZeroMQ publisher at localhost:32770...")
try:
    socket.connect("tcp://localhost:32770")
except Exception as e:
    print(f"Connection error: {e}")
    sys.exit(1)

# Subscribe to all messages
socket.subscribe(b"")

print(f"[{datetime.now()}] Connected! Waiting for live market data...")
print("Press Ctrl+C to stop\n")

message_count = 0
last_symbols = {}

# Receive messages
while True:
    try:
        # Set timeout to detect if no messages are coming
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        try:
            message = socket.recv_string()
            message_count += 1
            
            # Try to parse as JSON
            try:
                data = json.loads(message)
                symbol = data.get("symbol", "UNKNOWN")
                
                # Track last price for each symbol
                if "bid" in data and "ask" in data:
                    last_symbols[symbol] = {
                        "bid": data["bid"],
                        "ask": data["ask"],
                        "time": data.get("time", "")
                    }
                
                print(f"[{datetime.now()}] #{message_count} {symbol}: Bid={data.get('bid', 'N/A')}, Ask={data.get('ask', 'N/A')}, Time={data.get('time', 'N/A')}")
                
                # Every 10 messages, show summary
                if message_count % 10 == 0:
                    print(f"\n--- Summary: Received {message_count} messages from {len(last_symbols)} symbols ---")
                    for sym, prices in last_symbols.items():
                        print(f"  {sym}: {prices['bid']}/{prices['ask']}")
                    print()
                    
            except json.JSONDecodeError:
                # If not JSON, just print raw message
                print(f"[{datetime.now()}] #{message_count} Raw: {message}")
                
        except zmq.Again:
            print(f"[{datetime.now()}] No messages received in 5 seconds. Is MT4 running and EA loaded?")
            print("Make sure StreamingPlatform_test.ex4 is attached to a chart in MT4.")
            
    except Exception as e:
        print(f"Error: {e}")
        break

socket.close()
context.term()