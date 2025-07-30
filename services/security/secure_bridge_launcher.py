#!/usr/bin/env python3
"""
Secure Bridge Launcher
Launches the ZeroMQ bridge with SSL/TLS security enabled
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.security.zmq_secure import (
    SecureZeroMQPublisher, SecurityConfig, KeyManager, SecureBridgeFactory
)
from services.zeromq_bridge.zmq_bridge_oop import (
    MarketDataBridge, IDataSource, MarketTick, MarketBar
)
from datetime import datetime
import time
import threading
import random


class MockDataSource(IDataSource):
    """Mock data source for testing secure bridge"""
    
    def __init__(self):
        self._running = False
        self._tick_callbacks = []
        self._bar_callbacks = []
        self._thread = None
        self._symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
    
    def start(self) -> None:
        """Start generating mock data"""
        self._running = True
        self._thread = threading.Thread(target=self._generate_data)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop generating data"""
        self._running = False
        if self._thread:
            self._thread.join()
    
    def on_tick(self, callback) -> None:
        """Register tick callback"""
        self._tick_callbacks.append(callback)
    
    def on_bar(self, callback) -> None:
        """Register bar callback"""
        self._bar_callbacks.append(callback)
    
    def _generate_data(self) -> None:
        """Generate mock market data"""
        base_prices = {
            'EURUSD': 1.1000,
            'GBPUSD': 1.3000,
            'USDJPY': 110.00,
            'AUDUSD': 0.7500
        }
        
        while self._running:
            for symbol in self._symbols:
                # Generate tick
                base = base_prices[symbol]
                spread = 0.0001 if 'JPY' not in symbol else 0.01
                noise = random.uniform(-0.0005, 0.0005)
                
                bid = base + noise
                ask = bid + spread
                
                tick = MarketTick(
                    symbol=symbol,
                    bid=bid,
                    ask=ask,
                    timestamp=datetime.now(),
                    volume=random.randint(100, 1000)
                )
                
                # Notify callbacks
                for callback in self._tick_callbacks:
                    try:
                        callback(tick)
                    except Exception as e:
                        logging.error(f"Tick callback error: {e}")
                
                # Update base price
                base_prices[symbol] = bid
            
            time.sleep(0.1)  # 10 ticks per second per symbol


def setup_security(args) -> Dict[str, str]:
    """Setup security keys and configuration"""
    km = KeyManager(args.keys_dir)
    
    # Generate server keys if needed
    server_key_path = Path(args.keys_dir) / "server" / f"{args.server_name}.key"
    if not server_key_path.exists() or args.regenerate_keys:
        logging.info("Generating server keys...")
        server_keys = km.generate_server_keys(args.server_name)
        logging.info(f"Server keys generated: {server_keys}")
    else:
        server_keys = {
            'public': str(server_key_path),
            'secret': str(server_key_path.with_suffix('.key_secret'))
        }
        logging.info("Using existing server keys")
    
    # Generate some client keys if requested
    if args.generate_client_keys:
        for i in range(args.generate_client_keys):
            client_name = f"client_{i+1}"
            client_keys = km.generate_client_keys(client_name)
            logging.info(f"Generated keys for {client_name}: {client_keys}")
    
    # List authorized clients
    authorized = km.list_authorized_clients()
    logging.info(f"Authorized clients: {authorized}")
    
    return server_keys


def run_secure_bridge(args):
    """Run the secure market data bridge"""
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup security
    server_keys = setup_security(args)
    
    # Create configuration
    config = {
        'enable_curve': not args.disable_security,
        'server_secret_key': server_keys['secret'],
        'server_public_key': server_keys['public'],
        'authorized_clients_dir': str(Path(args.keys_dir) / "authorized_clients"),
        'publish_addresses': args.publish_addresses
    }
    
    # Create secure publisher
    publisher = SecureBridgeFactory.create_secure_publisher(config)
    
    # Create data source
    data_source = MockDataSource()
    
    # Create bridge
    bridge = MarketDataBridge(publisher, data_source, config)
    
    try:
        # Start bridge
        logging.info("Starting secure market data bridge...")
        bridge.start()
        
        logging.info(f"Secure bridge running on {args.publish_addresses}")
        logging.info("Press Ctrl+C to stop")
        
        # Run until interrupted
        while True:
            time.sleep(10)
            stats = bridge.get_statistics()
            logging.info(f"Bridge statistics: {stats}")
            
    except KeyboardInterrupt:
        logging.info("Stopping bridge...")
    finally:
        bridge.stop()
        logging.info("Bridge stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Secure ZeroMQ Bridge Launcher')
    
    parser.add_argument(
        '--publish-addresses',
        nargs='+',
        default=['tcp://*:5556'],
        help='Publishing addresses (default: tcp://*:5556)'
    )
    
    parser.add_argument(
        '--keys-dir',
        default='./keys',
        help='Directory for storing keys (default: ./keys)'
    )
    
    parser.add_argument(
        '--server-name',
        default='mt4_server',
        help='Server key name (default: mt4_server)'
    )
    
    parser.add_argument(
        '--generate-client-keys',
        type=int,
        default=0,
        help='Number of client keys to generate'
    )
    
    parser.add_argument(
        '--regenerate-keys',
        action='store_true',
        help='Regenerate server keys'
    )
    
    parser.add_argument(
        '--disable-security',
        action='store_true',
        help='Disable CURVE security (not recommended)'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Run bridge
    run_secure_bridge(args)


if __name__ == "__main__":
    main()