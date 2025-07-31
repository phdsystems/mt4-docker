#!/usr/bin/env python3
"""
ZeroMQ Trading Client for MT4
Requires: pip install pyzmq
"""

import zmq
import json
import time
from datetime import datetime

class MT4TradingClient:
    def __init__(self, cmd_port=5557, status_port=5558):
        self.context = zmq.Context()
        
        # REQ socket for sending commands
        self.cmd_socket = self.context.socket(zmq.REQ)
        self.cmd_socket.connect(f"tcp://localhost:{cmd_port}")
        self.cmd_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # SUB socket for receiving status updates
        self.status_socket = self.context.socket(zmq.SUB)
        self.status_socket.connect(f"tcp://localhost:{status_port}")
        self.status_socket.subscribe(b"STATUS")
        
        # Status monitoring thread
        self.poller = zmq.Poller()
        self.poller.register(self.status_socket, zmq.POLLIN)
    
    def send_command(self, command):
        """Send command and wait for response"""
        try:
            self.cmd_socket.send_string(command)
            response = self.cmd_socket.recv_string()
            return response
        except zmq.error.Again:
            return "ERROR|Timeout waiting for response"
    
    def open_trade(self, direction, symbol, lots, sl=0, tp=0):
        """Open a new trade"""
        command = f"OPEN|{direction}|{symbol}|{lots}|{sl}|{tp}"
        return self.send_command(command)
    
    def close_trade(self, ticket):
        """Close an existing trade"""
        command = f"CLOSE|{ticket}"
        return self.send_command(command)
    
    def get_status(self):
        """Get account status"""
        return self.send_command("STATUS")
    
    def monitor_status(self, duration=None):
        """Monitor status updates"""
        start_time = time.time()
        
        while True:
            if duration and (time.time() - start_time) > duration:
                break
                
            socks = dict(self.poller.poll(100))
            
            if self.status_socket in socks:
                message = self.status_socket.recv_string()
                print(f"[{datetime.now()}] {message}")
    
    def close(self):
        """Clean up resources"""
        self.cmd_socket.close()
        self.status_socket.close()
        self.context.term()


# Example usage
if __name__ == "__main__":
    # Create client
    client = MT4TradingClient()
    
    try:
        # Check status
        print("Checking status...")
        status = client.get_status()
        print(f"Status: {status}")
        
        # Open a trade
        print("\nOpening BUY trade on EURUSD...")
        result = client.open_trade("BUY", "EURUSD", 0.01)
        print(f"Result: {result}")
        
        # Parse ticket number if successful
        if result.startswith("OK"):
            parts = result.split("|")
            ticket = int(parts[1])
            price = float(parts[2])
            print(f"Trade opened: Ticket {ticket} at price {price}")
            
            # Wait a bit
            time.sleep(5)
            
            # Close the trade
            print(f"\nClosing trade {ticket}...")
            close_result = client.close_trade(ticket)
            print(f"Close result: {close_result}")
        
        # Monitor status for 10 seconds
        print("\nMonitoring status updates for 10 seconds...")
        client.monitor_status(10)
        
    finally:
        client.close()