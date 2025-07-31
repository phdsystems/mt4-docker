#!/usr/bin/env python3
import zmq

# Create context and socket
context = zmq.Context()
socket = context.socket(zmq.SUB)

# Connect to publisher
socket.connect("tcp://localhost:5555")

# Subscribe to all messages
socket.subscribe(b"")

print("Connected to MT4 publisher at localhost:5555")
print("Waiting for messages...")

# Receive messages
while True:
    try:
        message = socket.recv_string()
        print(f"Received: {message}")
    except KeyboardInterrupt:
        break

socket.close()
context.term()