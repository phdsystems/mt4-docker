#!/usr/bin/env python3
import zmq
import time

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:32770")
socket.subscribe(b"")
socket.setsockopt(zmq.RCVTIMEO, 5000)

print("Waiting for data on port 32770...")
try:
    message = socket.recv_string()
    print(f"SUCCESS! Receiving data: {message}")
    for i in range(3):
        try:
            message = socket.recv_string()
            print(f"  {message}")
        except zmq.Again:
            break
except zmq.Again:
    print("No data received - EA might still be starting up")
    
socket.close()
context.term()