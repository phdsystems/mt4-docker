#!/usr/bin/env python3
import zmq
import sys

print("Testing ZeroMQ connection to MT4...")
print("Creating context...")
context = zmq.Context()

print("Creating SUB socket...")
socket = context.socket(zmq.SUB)

print("Connecting to tcp://localhost:32770...")
socket.connect("tcp://localhost:32770")

print("Subscribing to all messages...")
socket.subscribe(b"")

print("Setting receive timeout to 3 seconds...")
socket.setsockopt(zmq.RCVTIMEO, 3000)

print("Waiting for message...")
try:
    message = socket.recv_string()
    print(f"SUCCESS! Received: {message}")
except zmq.Again:
    print("TIMEOUT - No messages received in 3 seconds")
    print("\nPossible issues:")
    print("1. EA might not be actively publishing data")
    print("2. EA might be waiting for market to be open") 
    print("3. EA might have encountered an error")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\nCleaning up...")
socket.close()
context.term()
print("Done.")