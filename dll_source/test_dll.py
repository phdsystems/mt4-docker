#!/usr/bin/env python3
"""Test the compiled MT4ZMQ DLL functionality"""

import ctypes
import sys
import time
import threading

# Load the DLL
try:
    dll = ctypes.CDLL('./build/mt4zmq.dll')
    print("✓ DLL loaded successfully")
except Exception as e:
    print(f"✗ Failed to load DLL: {e}")
    sys.exit(1)

# Define function signatures
dll.zmq_init.restype = ctypes.c_int
dll.zmq_init.argtypes = []

dll.zmq_create_publisher.restype = ctypes.c_int
dll.zmq_create_publisher.argtypes = [ctypes.c_wchar_p]

dll.zmq_create_subscriber.restype = ctypes.c_int
dll.zmq_create_subscriber.argtypes = [ctypes.c_wchar_p]

dll.zmq_send_message.restype = ctypes.c_int
dll.zmq_send_message.argtypes = [ctypes.c_int, ctypes.c_wchar_p, ctypes.c_wchar_p]

dll.zmq_subscribe.restype = ctypes.c_int
dll.zmq_subscribe.argtypes = [ctypes.c_int, ctypes.c_wchar_p]

dll.zmq_recv_message.restype = ctypes.c_int
dll.zmq_recv_message.argtypes = [ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int, 
                                 ctypes.c_wchar_p, ctypes.c_int, ctypes.c_int]

dll.zmq_close.restype = ctypes.c_int
dll.zmq_close.argtypes = [ctypes.c_int]

dll.zmq_term.restype = None
dll.zmq_term.argtypes = []

dll.zmq_version.restype = None
dll.zmq_version.argtypes = [ctypes.c_wchar_p, ctypes.c_int]

# Test 1: Initialize
print("\nTest 1: Initialize ZeroMQ")
result = dll.zmq_init()
if result == 0:
    print("✓ ZeroMQ initialized")
else:
    print("✗ Failed to initialize ZeroMQ")
    sys.exit(1)

# Test 2: Get version
print("\nTest 2: Get version")
version = ctypes.create_unicode_buffer(256)
dll.zmq_version(version, 256)
print(f"✓ Version: {version.value}")

# Test 3: Create publisher
print("\nTest 3: Create publisher")
pub_handle = dll.zmq_create_publisher("tcp://*:5556")
if pub_handle > 0:
    print(f"✓ Publisher created with handle: {pub_handle}")
else:
    print("✗ Failed to create publisher")

# Test 4: Create subscriber
print("\nTest 4: Create subscriber")
sub_handle = dll.zmq_create_subscriber("tcp://127.0.0.1:5556")
if sub_handle > 0:
    print(f"✓ Subscriber created with handle: {sub_handle}")
    dll.zmq_subscribe(sub_handle, "")
    print("✓ Subscribed to all topics")
else:
    print("✗ Failed to create subscriber")

# Test 5: Send and receive messages
print("\nTest 5: Send and receive messages")

def receive_messages():
    topic = ctypes.create_unicode_buffer(256)
    message = ctypes.create_unicode_buffer(1024)
    
    for i in range(3):
        result = dll.zmq_recv_message(sub_handle, topic, 256, message, 1024, 1000)
        if result == 0:
            print(f"✓ Received: [{topic.value}] {message.value}")
        else:
            print("✗ No message received (timeout)")

# Start receiver thread
receiver = threading.Thread(target=receive_messages)
receiver.start()

# Give subscriber time to connect
time.sleep(0.1)

# Send messages
messages = [
    ("tick.EURUSD", '{"bid":1.0850,"ask":1.0852}'),
    ("tick.GBPUSD", '{"bid":1.2550,"ask":1.2552}'),
    ("signal", '{"type":"buy","symbol":"EURUSD"}')
]

for topic, msg in messages:
    result = dll.zmq_send_message(pub_handle, topic, msg)
    if result == 0:
        print(f"✓ Sent: [{topic}] {msg}")
    else:
        print(f"✗ Failed to send message")
    time.sleep(0.1)

# Wait for receiver
receiver.join()

# Test 6: Cleanup
print("\nTest 6: Cleanup")
dll.zmq_close(pub_handle)
print("✓ Publisher closed")
dll.zmq_close(sub_handle)
print("✓ Subscriber closed")
dll.zmq_term()
print("✓ ZeroMQ terminated")

print("\n=== All tests completed ===")