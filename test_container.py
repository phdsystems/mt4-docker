#!/usr/bin/env python3
import zmq
import sys

print("Testing ZeroMQ connection to MT4 via container name...")

# Try different connection methods
connections = [
    "tcp://localhost:32770",
    "tcp://127.0.0.1:32770",
    "tcp://mt4-docker:32770",
    "tcp://0.0.0.0:32770"
]

context = zmq.Context()

for conn_str in connections:
    print(f"\nTrying: {conn_str}")
    socket = context.socket(zmq.SUB)
    
    try:
        socket.connect(conn_str)
        socket.subscribe(b"")
        socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
        
        message = socket.recv_string()
        print(f"  SUCCESS! Received: {message}")
        socket.close()
        break
        
    except zmq.Again:
        print(f"  TIMEOUT - No messages received")
        socket.close()
        
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        socket.close()

context.term()