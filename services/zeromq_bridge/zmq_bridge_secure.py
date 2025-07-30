#!/usr/bin/env python3
"""
Enhanced ZeroMQ Bridge with optional SSL/TLS security
Supports both secure and non-secure modes
"""

import logging
import argparse
import json
import sys
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.zeromq_bridge.zmq_bridge_oop import (
    MarketDataBridge, BridgeFactory, JsonSerializer
)
from services.security.zmq_secure import (
    SecureZeroMQPublisher, SecurityConfig, KeyManager
)
from services.mt4_data_reader import MT4DataReader
from datetime import datetime


class SecureBridgeFactory(BridgeFactory):
    """Extended factory with security support"""
    
    @staticmethod
    def create_bridge(config: Dict[str, Any]) -> MarketDataBridge:
        """Create bridge with optional security"""
        
        # Check if security is enabled
        if config.get('security', {}).get('enabled', False):
            return SecureBridgeFactory.create_secure_bridge(config)
        else:
            return BridgeFactory.create_zeromq_bridge(config)
    
    @staticmethod
    def create_secure_bridge(config: Dict[str, Any]) -> MarketDataBridge:
        """Create secure ZeroMQ bridge"""
        # Extract security config
        sec_config = config.get('security', {})
        
        # Create security configuration
        security_config = SecurityConfig(
            enable_curve=True,
            server_secret_key_file=sec_config.get('server_secret_key'),
            server_public_key_file=sec_config.get('server_public_key'),
            authorized_clients_dir=sec_config.get('authorized_clients_dir')
        )
        
        # Create serializer
        serializer = JsonSerializer()
        
        # Create secure publisher
        addresses = config.get('publish_addresses', ['tcp://*:5556'])
        publisher = SecureZeroMQPublisher(
            addresses=addresses,
            security_config=security_config,
            serializer=serializer,
            high_water_mark=config.get('high_water_mark', 10000)
        )
        
        # Create data source
        data_source = config.get('data_source')
        if not data_source:
            # Create default MT4 data source
            mt4_config = config.get('mt4', {})
            data_source = MT4DataReader(
                data_file=mt4_config.get('data_file', './data/mt4_data.csv'),
                update_interval=mt4_config.get('update_interval', 1.0)
            )
        
        # Create and return bridge
        return MarketDataBridge(publisher, data_source, config)


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    with open(config_file, 'r') as f:
        return json.load(f)


def setup_logging(level: str = 'INFO'):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='ZeroMQ Market Data Bridge with SSL/TLS Support'
    )
    
    parser.add_argument(
        '--config',
        default='config/bridge_config.json',
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--secure',
        action='store_true',
        help='Enable SSL/TLS security'
    )
    
    parser.add_argument(
        '--generate-keys',
        action='store_true',
        help='Generate security keys'
    )
    
    parser.add_argument(
        '--keys-dir',
        default='./keys',
        help='Directory for security keys'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Generate keys if requested
    if args.generate_keys:
        logger.info("Generating security keys...")
        km = KeyManager(args.keys_dir)
        
        # Generate server keys
        server_keys = km.generate_server_keys("mt4_bridge")
        logger.info(f"Server keys: {server_keys}")
        
        # Generate sample client keys
        for i in range(3):
            client_keys = km.generate_client_keys(f"client_{i+1}")
            logger.info(f"Client {i+1} keys: {client_keys}")
        
        logger.info("Keys generated successfully")
        return
    
    # Load configuration
    try:
        if os.path.exists(args.config):
            config = load_config(args.config)
            logger.info(f"Loaded configuration from {args.config}")
        else:
            # Use default configuration
            config = {
                "publish_addresses": ["tcp://*:5556", "tcp://*:5557"],
                "mt4": {
                    "data_file": "./data/mt4_data.csv",
                    "update_interval": 1.0
                },
                "high_water_mark": 10000,
                "log_level": args.log_level
            }
            logger.info("Using default configuration")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1
    
    # Override security settings if specified
    if args.secure:
        config['security'] = {
            'enabled': True,
            'server_secret_key': f"{args.keys_dir}/server/mt4_bridge.key_secret",
            'server_public_key': f"{args.keys_dir}/server/mt4_bridge.key",
            'authorized_clients_dir': f"{args.keys_dir}/authorized_clients"
        }
        logger.info("Security enabled")
    
    # Create and start bridge
    try:
        bridge = SecureBridgeFactory.create_bridge(config)
        
        logger.info("Starting market data bridge...")
        bridge.start()
        
        logger.info(f"Bridge running on {config.get('publish_addresses', ['tcp://*:5556'])}")
        logger.info("Security: " + ("ENABLED" if config.get('security', {}).get('enabled', False) else "DISABLED"))
        logger.info("Press Ctrl+C to stop")
        
        # Run forever
        import time
        while True:
            time.sleep(10)
            stats = bridge.get_statistics()
            logger.info(f"Statistics: {json.dumps(stats, indent=2)}")
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Bridge error: {e}")
        return 1
    finally:
        if 'bridge' in locals():
            bridge.stop()
            logger.info("Bridge stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())