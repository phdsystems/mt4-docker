#!/usr/bin/env python3
import zmq
import time

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:32770")
socket.subscribe(b"")
socket.setsockopt(zmq.RCVTIMEO, 5000)

print("Testing ZMQ connection inside container...")
try:
    message = socket.recv_string()
    print(f"SUCCESS: Received: {message}")
except zmq.Again:
    print("TIMEOUT: No messages received")
except Exception as e:
    print(f"ERROR: {e}")
    
socket.close()
context.term()