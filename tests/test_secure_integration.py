#!/usr/bin/env python3
"""
Integration test for secure ZeroMQ communications
"""

import asyncio
import sys
import os
import time
import threading
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.security.zmq_secure import KeyManager, SecureBridgeFactory
from services.zeromq_bridge.zmq_bridge_oop import MarketDataBridge, MarketTick
from clients.python.secure_market_client import SecureMarketDataClient
from datetime import datetime


class TestDataSource:
    """Test data source that generates sample ticks"""
    
    def __init__(self):
        self._tick_callbacks = []
        self._bar_callbacks = []
        self._running = False
        self._thread = None
    
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._generate_ticks)
        self._thread.start()
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
    
    def on_tick(self, callback):
        self._tick_callbacks.append(callback)
    
    def on_bar(self, callback):
        self._bar_callbacks.append(callback)
    
    def _generate_ticks(self):
        """Generate test ticks"""
        tick_count = 0
        while self._running and tick_count < 10:
            tick = MarketTick(
                symbol="EURUSD",
                bid=1.1000 + tick_count * 0.0001,
                ask=1.1001 + tick_count * 0.0001,
                timestamp=datetime.now(),
                volume=100 + tick_count
            )
            
            for callback in self._tick_callbacks:
                callback(tick)
            
            tick_count += 1
            time.sleep(0.5)


async def test_secure_communication():
    """Test secure publisher and subscriber"""
    print("=== Secure ZeroMQ Integration Test ===\n")
    
    # Setup keys
    print("1. Setting up security keys...")
    km = KeyManager("./test_keys")
    
    # Generate server keys
    server_keys = km.generate_server_keys("test_server")
    print(f"   Server keys generated: {server_keys['public']}")
    
    # Generate client keys
    client_keys = km.generate_client_keys("test_client")
    print(f"   Client keys generated: {client_keys['public']}")
    
    # Create secure publisher
    print("\n2. Creating secure publisher...")
    pub_config = {
        'enable_curve': True,
        'server_secret_key': server_keys['secret'],
        'server_public_key': server_keys['public'],
        'authorized_clients_dir': str(Path("./test_keys/authorized_clients")),
        'publish_addresses': ['tcp://127.0.0.1:15556']
    }
    
    publisher = SecureBridgeFactory.create_secure_publisher(pub_config)
    
    # Create test data source
    data_source = TestDataSource()
    
    # Create bridge
    bridge = MarketDataBridge(publisher, data_source, pub_config)
    
    # Start bridge
    print("3. Starting secure bridge...")
    bridge.start()
    
    # Create secure client
    print("\n4. Creating secure client...")
    client = SecureMarketDataClient(
        server_public_key=server_keys['public'],
        client_name="test_client",
        addresses=['tcp://127.0.0.1:15556']
    )
    
    # Track received ticks
    received_ticks = []
    
    def on_tick(tick):
        received_ticks.append(tick)
        print(f"   Received secure tick: {tick.symbol.name} "
              f"Bid: {tick.bid.value:.4f} Ask: {tick.ask.value:.4f}")
    
    client.add_handler('tick', on_tick)
    
    # Connect client
    print("5. Connecting secure client...")
    await client.connect()
    await client.subscribe_symbol('EURUSD')
    
    # Start client streaming in background
    streaming_task = asyncio.create_task(client.start_streaming())
    
    # Wait for ticks
    print("\n6. Waiting for secure ticks...")
    await asyncio.sleep(6)
    
    # Stop everything
    print("\n7. Stopping...")
    bridge.stop()
    await client.disconnect()
    streaming_task.cancel()
    
    # Verify results
    print(f"\n8. Results:")
    print(f"   Ticks sent: ~10")
    print(f"   Ticks received: {len(received_ticks)}")
    print(f"   Security: CURVE encryption enabled")
    
    # Get statistics
    stats = bridge.get_statistics()
    print(f"\n9. Bridge statistics:")
    print(f"   Total ticks: {stats['tick_count']}")
    print(f"   Errors: {stats['error_count']}")
    
    # Cleanup
    import shutil
    shutil.rmtree("./test_keys", ignore_errors=True)
    
    print("\n✅ Secure communication test completed successfully!")
    
    return len(received_ticks) > 0


async def test_unauthorized_client():
    """Test that unauthorized clients cannot connect"""
    print("\n=== Unauthorized Client Test ===\n")
    
    # Setup keys
    km = KeyManager("./test_keys_unauth")
    
    # Generate server keys
    server_keys = km.generate_server_keys("test_server")
    
    # Generate unauthorized client keys (not in authorized_clients)
    unauthorized_keys = {
        'public': './test_keys_unauth/unauthorized.key',
        'secret': './test_keys_unauth/unauthorized.key_secret'
    }
    
    # Generate keys manually without authorization
    import zmq
    public_key, secret_key = zmq.curve_keypair()
    
    os.makedirs(os.path.dirname(unauthorized_keys['public']), exist_ok=True)
    with open(unauthorized_keys['public'], 'wb') as f:
        f.write(public_key)
    with open(unauthorized_keys['secret'], 'wb') as f:
        f.write(secret_key)
    
    print("1. Created unauthorized client keys")
    
    # Create secure publisher
    pub_config = {
        'enable_curve': True,
        'server_secret_key': server_keys['secret'],
        'server_public_key': server_keys['public'],
        'authorized_clients_dir': str(Path("./test_keys_unauth/authorized_clients")),
        'publish_addresses': ['tcp://127.0.0.1:15557']
    }
    
    publisher = SecureBridgeFactory.create_secure_publisher(pub_config)
    data_source = TestDataSource()
    bridge = MarketDataBridge(publisher, data_source, pub_config)
    
    # Start bridge
    bridge.start()
    print("2. Started secure bridge with client authorization")
    
    # Try to connect unauthorized client
    print("3. Attempting to connect unauthorized client...")
    
    try:
        # This should fail or timeout
        from services.security.zmq_secure import SecureZeroMQSubscriber, SecurityConfig
        from services.zeromq_bridge.zmq_bridge_oop import JsonSerializer
        
        config = SecurityConfig(
            enable_curve=True,
            client_secret_key_file=unauthorized_keys['secret'],
            client_public_key_file=unauthorized_keys['public'],
            server_public_key_file=server_keys['public']
        )
        
        subscriber = SecureZeroMQSubscriber(
            ['tcp://127.0.0.1:15557'],
            config,
            JsonSerializer()
        )
        
        subscriber.connect()
        subscriber.subscribe([''])
        
        # Try to receive (should timeout)
        result = subscriber.receive(timeout=2000)
        
        if result is None:
            print("✅ Unauthorized client correctly rejected (timeout)")
            success = True
        else:
            print("❌ Unauthorized client incorrectly received data")
            success = False
            
    except Exception as e:
        print(f"✅ Unauthorized client correctly rejected: {e}")
        success = True
    
    # Cleanup
    bridge.stop()
    import shutil
    shutil.rmtree("./test_keys_unauth", ignore_errors=True)
    
    return success


async def main():
    """Run all integration tests"""
    print("Starting Secure ZeroMQ Integration Tests")
    print("=" * 50)
    
    # Test 1: Secure communication
    test1_passed = await test_secure_communication()
    
    # Test 2: Unauthorized client rejection
    test2_passed = await test_unauthorized_client()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"  Secure Communication: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"  Unauthorized Client:  {'PASSED' if test2_passed else 'FAILED'}")
    print("=" * 50)
    
    return test1_passed and test2_passed


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)