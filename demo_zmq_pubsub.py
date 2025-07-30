#!/usr/bin/env python3
"""
Simple demonstration of ZeroMQ Publisher/Subscriber pattern
Shows exactly where the publisher and subscriber are
"""

import zmq
import json
import time
import threading

def publisher_demo():
    """
    PUBLISHER - Sends market data
    Location: services/zeromq_bridge/zmq_bridge.py
    """
    print("=== PUBLISHER (Bridge Service) ===")
    print("Location: services/zeromq_bridge/zmq_bridge.py")
    print("This is what happens inside the ZeroMQ bridge:\n")
    
    # Create context and publisher socket
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)  # <-- PUB socket type
    publisher.bind("tcp://*:5558")  # <-- Binds to accept connections
    
    print("1. Publisher socket created (zmq.PUB)")
    print("2. Bound to tcp://*:5558")
    print("3. Starting to publish market data...\n")
    
    # Simulate publishing market data
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    for i in range(10):
        for symbol in symbols:
            # Create market data
            tick = {
                "type": "tick",
                "symbol": symbol,
                "bid": 1.08456 + i * 0.0001,
                "ask": 1.08459 + i * 0.0001,
                "timestamp": int(time.time() * 1000)
            }
            
            # Topic for filtering
            topic = f"tick.{symbol}"
            
            # Send multipart message [topic, data]
            publisher.send_multipart([
                topic.encode('utf-8'),
                json.dumps(tick).encode('utf-8')
            ])
            
            if i == 0:  # Show first message details
                print(f"Publishing: [{topic}] {json.dumps(tick)[:60]}...")
        
        time.sleep(0.5)
    
    print("\n✓ Published 30 messages (10 ticks × 3 symbols)")
    publisher.close()
    context.term()

def subscriber_demo():
    """
    SUBSCRIBER - Receives market data
    Location: clients/python/zmq_market_client.py
    """
    time.sleep(0.5)  # Let publisher start first
    
    print("\n=== SUBSCRIBER (Client) ===")
    print("Location: clients/python/zmq_market_client.py")
    print("This is what happens in the client:\n")
    
    # Create context and subscriber socket
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)  # <-- SUB socket type
    subscriber.connect("tcp://localhost:5558")  # <-- Connects to publisher
    
    # Subscribe to specific topics
    subscriber.subscribe("tick.EURUSD".encode('utf-8'))  # <-- Topic filter
    subscriber.subscribe("tick.GBPUSD".encode('utf-8'))
    
    print("1. Subscriber socket created (zmq.SUB)")
    print("2. Connected to tcp://localhost:5558")
    print("3. Subscribed to: tick.EURUSD, tick.GBPUSD")
    print("4. Receiving messages...\n")
    
    # Receive messages
    messages_received = 0
    subscriber.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
    
    start_time = time.time()
    while time.time() - start_time < 5:  # Run for 5 seconds
        try:
            # Receive multipart message [topic, data]
            topic, data = subscriber.recv_multipart()
            tick = json.loads(data.decode('utf-8'))
            
            messages_received += 1
            if messages_received <= 3:  # Show first 3 messages
                print(f"Received: [{topic.decode()}] {tick['symbol']} @ {tick['bid']}")
            elif messages_received == 4:
                print("...")
                
        except zmq.Again:
            continue
    
    print(f"\n✓ Received {messages_received} messages")
    print("  (Note: Didn't receive USDJPY because we didn't subscribe to it)")
    
    subscriber.close()
    context.term()

def show_file_locations():
    """Show where the actual code is located"""
    print("\n=== ACTUAL FILE LOCATIONS ===\n")
    
    print("PUBLISHER (ZeroMQ Bridge):")
    print("├── File: services/zeromq_bridge/zmq_bridge.py")
    print("├── Class: ZeroMQBridge")
    print("├── Key methods:")
    print("│   ├── setup_publisher() - Creates PUB socket")
    print("│   ├── publish_tick() - Publishes tick data")
    print("│   └── publish_bar() - Publishes bar data")
    print("└── Binds to: tcp://*:5556, ipc:///tmp/mt4_market_data")
    
    print("\nSUBSCRIBER (Python Client):")
    print("├── File: clients/python/zmq_market_client.py")
    print("├── Class: ZMQMarketClient")
    print("├── Key methods:")
    print("│   ├── connect() - Creates SUB socket")
    print("│   ├── subscribe_symbol() - Subscribes to topics")
    print("│   └── run() - Receives messages")
    print("└── Connects to: tcp://localhost:5556")
    
    print("\nSUBSCRIBER (Node.js Client):")
    print("├── File: clients/nodejs/zmq_client.js")
    print("├── Class: ZMQMarketClient")
    print("└── Same pattern as Python client")
    
    print("\nDATA FLOW:")
    print("MT4 EA → Named Pipe → ZMQ Bridge (PUB) → Network → Clients (SUB)")

def main():
    print("ZeroMQ Publisher/Subscriber Demonstration\n")
    
    # Run publisher in background
    pub_thread = threading.Thread(target=publisher_demo)
    pub_thread.start()
    
    # Run subscriber
    subscriber_demo()
    
    # Wait for publisher to finish
    pub_thread.join()
    
    # Show file locations
    show_file_locations()

if __name__ == "__main__":
    main()