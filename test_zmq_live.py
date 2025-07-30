#!/usr/bin/env python3
"""
Live test of ZeroMQ streaming - start bridge and test subscriber
"""

import subprocess
import time
import zmq
import json
import threading

def run_bridge():
    """Run the bridge in a subprocess"""
    print("Starting ZeroMQ bridge...")
    # Start fresh by removing old position
    proc = subprocess.Popen(
        ["python3", "services/zeromq_bridge/zmq_bridge.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return proc

def run_simulator():
    """Run market data simulator"""
    print("Starting market data simulator...")
    proc = subprocess.Popen(
        ["python3", "simulate_market_data.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return proc

def test_subscriber():
    """Test the subscriber"""
    time.sleep(2)  # Let bridge and simulator start
    
    print("\nTesting ZeroMQ subscriber...")
    
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://localhost:5556")
    subscriber.subscribe(b"")  # All topics
    subscriber.setsockopt(zmq.RCVTIMEO, 500)  # 500ms timeout
    
    print("Connected and subscribed to all topics")
    print("Waiting for messages...\n")
    
    messages_received = 0
    symbols_seen = set()
    start_time = time.time()
    
    while time.time() - start_time < 10:  # Run for 10 seconds
        try:
            topic, data = subscriber.recv_multipart()
            message = json.loads(data.decode('utf-8'))
            
            messages_received += 1
            symbols_seen.add(message.get('symbol', 'Unknown'))
            
            # Show first few and then every 10th
            if messages_received <= 5 or messages_received % 10 == 0:
                print(f"Message {messages_received}: {topic.decode()} -> "
                      f"{message['symbol']} @ {message.get('bid', 'N/A')}")
                
        except zmq.Again:
            print(".", end="", flush=True)
            
    subscriber.close()
    context.term()
    
    print(f"\n\nResults:")
    print(f"✓ Messages received: {messages_received}")
    print(f"✓ Symbols seen: {', '.join(sorted(symbols_seen))}")
    print(f"✓ Rate: {messages_received / 10:.1f} msg/s")
    
    return messages_received > 0

def main():
    print("=== Live ZeroMQ Streaming Test ===\n")
    
    # Start processes
    bridge_proc = run_bridge()
    time.sleep(1)
    
    simulator_proc = run_simulator()
    time.sleep(1)
    
    # Test subscriber
    success = test_subscriber()
    
    # Cleanup
    print("\nCleaning up...")
    bridge_proc.terminate()
    simulator_proc.terminate()
    bridge_proc.wait()
    simulator_proc.wait()
    
    if success:
        print("\n✅ SUCCESS: ZeroMQ streaming is working!")
        print("The publisher/subscriber pattern is functioning correctly.")
    else:
        print("\n❌ FAILED: No messages received")
        print("\nDebugging info:")
        # Check if pyzmq is installed
        try:
            import zmq
            print(f"- pyzmq installed: {zmq.pyzmq_version()}")
        except:
            print("- pyzmq NOT installed!")
        
        # Check ports
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5556))
        sock.close()
        if result == 0:
            print("- Port 5556 is open")
        else:
            print("- Port 5556 is NOT open")

if __name__ == "__main__":
    main()