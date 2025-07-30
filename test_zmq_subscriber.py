#!/usr/bin/env python3
"""
Test if ZeroMQ subscriber actually receives data
"""

import zmq
import json
import time

print("Testing ZeroMQ Subscriber Connection...")

# Create context and socket
context = zmq.Context()
subscriber = context.socket(zmq.SUB)

# Connect to the bridge
print("Connecting to tcp://localhost:5556...")
subscriber.connect("tcp://localhost:5556")

# Subscribe to all messages
subscriber.subscribe(b"")  # Empty = all topics
print("Subscribed to all topics")

# Set timeout
subscriber.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout

# Try to receive messages
print("\nWaiting for messages...")
messages_received = 0
start_time = time.time()

try:
    while time.time() - start_time < 5:  # Run for 5 seconds
        try:
            # Receive multipart message
            topic, data = subscriber.recv_multipart()
            message = json.loads(data.decode('utf-8'))
            
            messages_received += 1
            
            # Show first few messages
            if messages_received <= 3:
                print(f"Message {messages_received}: {topic.decode()} -> {message['symbol']} @ {message.get('bid', 'N/A')}")
            elif messages_received == 4:
                print("... (continuing to receive)")
                
        except zmq.Again:
            print(".", end="", flush=True)
            continue
        except Exception as e:
            print(f"Error: {e}")
            
except KeyboardInterrupt:
    print("\nInterrupted")
    
print(f"\n\nResults:")
print(f"- Messages received: {messages_received}")
print(f"- Time elapsed: {time.time() - start_time:.1f}s")
print(f"- Rate: {messages_received / (time.time() - start_time):.1f} msg/s")

# Cleanup
subscriber.close()
context.term()

if messages_received > 0:
    print("\n✓ SUCCESS: ZeroMQ is working! Received real market data.")
else:
    print("\n✗ FAILED: No messages received. Checking why...")
    print("\nPossible issues:")
    print("1. Bridge might have already processed all CSV data")
    print("2. No new data being generated")
    print("3. Network/firewall issues")