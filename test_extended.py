#!/usr/bin/env python3
import zmq
import time
from datetime import datetime

print(f"[{datetime.now()}] Starting extended ZMQ test...")
print("Connecting to tcp://localhost:32770")

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:32770")
socket.subscribe(b"")

# Use polling for better control
poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)

print(f"[{datetime.now()}] Connected. Monitoring for 30 seconds...")
print("(Press Ctrl+C to stop early)")

start_time = time.time()
message_count = 0

try:
    while time.time() - start_time < 30:
        # Poll with 1 second timeout
        socks = dict(poller.poll(1000))
        
        if socket in socks and socks[socket] == zmq.POLLIN:
            message = socket.recv_string()
            message_count += 1
            print(f"[{datetime.now()}] Message #{message_count}: {message[:100]}...")
        else:
            # No message, print a dot to show we're still running
            print(".", end="", flush=True)
            
except KeyboardInterrupt:
    print("\nInterrupted by user")
except Exception as e:
    print(f"\nError: {e}")

elapsed = time.time() - start_time
print(f"\n[{datetime.now()}] Test completed")
print(f"Duration: {elapsed:.1f} seconds")
print(f"Messages received: {message_count}")

if message_count == 0:
    print("\nNo messages received. Possible reasons:")
    print("1. EA may not be attached to an active chart")
    print("2. Market may be closed for the symbol")
    print("3. EA may be waiting for initialization")
    print("4. Check MT4 via VNC on port 5900")

socket.close()
context.term()