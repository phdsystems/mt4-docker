#!/usr/bin/env python3
"""
Secure Market Data Client with SSL/TLS Support
Demonstrates secure ZeroMQ communications with CURVE authentication
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.security.zmq_secure import (
    SecureZeroMQSubscriber, SecurityConfig, KeyManager
)
from services.core.interfaces import IMarketDataHandler
from clients.python.market_data_client_v2 import (
    Symbol, Price, MarketTick, MarketDataStatistics
)


class SecureMarketDataClient:
    """Secure market data client with CURVE authentication"""
    
    def __init__(self, 
                 server_public_key: str,
                 client_name: str = "secure_client",
                 addresses: List[str] = None):
        self._server_public_key = server_public_key
        self._client_name = client_name
        self._addresses = addresses or ['tcp://localhost:5556']
        self._subscriber: Optional[SecureZeroMQSubscriber] = None
        self._running = False
        self._handlers: Dict[str, List[Callable]] = {
            'tick': [],
            'bar': [],
            'error': []
        }
        self._statistics = MarketDataStatistics()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Key management
        self._key_manager = KeyManager()
        self._client_keys: Optional[Dict[str, str]] = None
    
    async def initialize_security(self) -> None:
        """Initialize security and generate client keys if needed"""
        # Check if client keys exist
        client_key_path = Path(f"./keys/clients/{self._client_name}.key")
        
        if not client_key_path.exists():
            self._logger.info(f"Generating new keys for {self._client_name}")
            self._client_keys = self._key_manager.generate_client_keys(self._client_name)
        else:
            self._client_keys = {
                'public': str(client_key_path),
                'secret': str(client_key_path.with_suffix('.key_secret'))
            }
        
        self._logger.info(f"Client keys loaded for {self._client_name}")
    
    async def connect(self) -> None:
        """Connect to secure market data stream"""
        await self.initialize_security()
        
        # Create security config
        security_config = SecurityConfig(
            enable_curve=True,
            client_secret_key_file=self._client_keys['secret'],
            client_public_key_file=self._client_keys['public'],
            server_public_key_file=self._server_public_key
        )
        
        # Create serializer
        from services.zeromq_bridge.zmq_bridge_oop import JsonSerializer
        serializer = JsonSerializer()
        
        # Create secure subscriber
        self._subscriber = SecureZeroMQSubscriber(
            self._addresses,
            security_config,
            serializer
        )
        
        self._subscriber.connect()
        self._logger.info("Connected to secure market data stream")
    
    async def disconnect(self) -> None:
        """Disconnect from market data stream"""
        self._running = False
        if self._subscriber:
            self._subscriber.disconnect()
        self._logger.info("Disconnected from secure market data stream")
    
    async def subscribe_symbol(self, symbol: str) -> None:
        """Subscribe to a specific symbol"""
        if not self._subscriber:
            raise RuntimeError("Not connected")
        
        topics = [f"tick.{symbol}", f"bar.{symbol}"]
        self._subscriber.subscribe(topics)
        self._logger.info(f"Subscribed to {symbol}")
    
    async def subscribe_all(self) -> None:
        """Subscribe to all symbols"""
        if not self._subscriber:
            raise RuntimeError("Not connected")
        
        self._subscriber.subscribe([""])
        self._logger.info("Subscribed to all symbols")
    
    def add_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler"""
        if event_type in self._handlers:
            self._handlers[event_type].append(handler)
    
    def remove_handler(self, event_type: str, handler: Callable) -> None:
        """Remove event handler"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    async def start_streaming(self) -> None:
        """Start streaming market data"""
        if not self._subscriber:
            raise RuntimeError("Not connected")
        
        self._running = True
        self._logger.info("Started secure streaming")
        
        while self._running:
            try:
                # Receive with timeout
                result = self._subscriber.receive(timeout=1000)
                
                if result:
                    topic, message = result
                    await self._process_message(topic, message)
                
            except Exception as e:
                self._logger.error(f"Streaming error: {e}")
                self._statistics.record_error()
                
                # Notify error handlers
                for handler in self._handlers['error']:
                    try:
                        handler(e)
                    except Exception as he:
                        self._logger.error(f"Handler error: {he}")
                
                # Reconnect on error
                if self._running:
                    await asyncio.sleep(5)
                    try:
                        await self.connect()
                    except Exception as re:
                        self._logger.error(f"Reconnection failed: {re}")
    
    async def _process_message(self, topic: str, message: Dict[str, Any]) -> None:
        """Process received message"""
        try:
            if topic.startswith("tick."):
                await self._process_tick(message)
            elif topic.startswith("bar."):
                await self._process_bar(message)
            else:
                self._logger.warning(f"Unknown topic: {topic}")
        
        except Exception as e:
            self._logger.error(f"Message processing error: {e}")
            self._statistics.record_error()
    
    async def _process_tick(self, message: Dict[str, Any]) -> None:
        """Process tick message"""
        data = message.get('data', {})
        
        tick = MarketTick(
            symbol=Symbol(data['symbol']),
            bid=Price(data['bid']),
            ask=Price(data['ask']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            volume=data.get('volume')
        )
        
        self._statistics.record_tick(tick)
        
        # Notify handlers
        for handler in self._handlers['tick']:
            try:
                handler(tick)
            except Exception as e:
                self._logger.error(f"Tick handler error: {e}")
    
    async def _process_bar(self, message: Dict[str, Any]) -> None:
        """Process bar message"""
        # Implementation similar to tick processing
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics"""
        return self._statistics.get_summary()


class SecureMarketDataHandler(IMarketDataHandler):
    """Example handler for secure market data"""
    
    def __init__(self):
        self._tick_count = 0
        self._last_tick: Optional[MarketTick] = None
    
    def on_tick(self, tick: MarketTick) -> None:
        """Handle tick data"""
        self._tick_count += 1
        self._last_tick = tick
        
        if self._tick_count % 100 == 0:
            print(f"[SECURE] Processed {self._tick_count} ticks")
            print(f"[SECURE] Last: {tick.symbol.name} "
                  f"Bid: {tick.bid} Ask: {tick.ask} "
                  f"Spread: {tick.spread:.5f}")
    
    def on_bar(self, bar: Any) -> None:
        """Handle bar data"""
        pass
    
    def on_error(self, error: Exception) -> None:
        """Handle errors"""
        print(f"[SECURE] Error: {error}")


# Example usage
async def main():
    """Example secure client usage"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Server public key path (must be shared with clients)
    server_public_key = "./keys/server/mt4_server.key"
    
    # Create secure client
    client = SecureMarketDataClient(
        server_public_key=server_public_key,
        client_name="python_secure_client",
        addresses=['tcp://localhost:5556']
    )
    
    # Add handler
    handler = SecureMarketDataHandler()
    client.add_handler('tick', handler.on_tick)
    client.add_handler('error', handler.on_error)
    
    try:
        # Connect
        await client.connect()
        
        # Subscribe to symbols
        await client.subscribe_symbol('EURUSD')
        await client.subscribe_symbol('GBPUSD')
        
        # Start streaming
        print("Starting secure market data streaming...")
        print("Press Ctrl+C to stop")
        
        await client.start_streaming()
        
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await client.disconnect()
        
        # Print statistics
        stats = client.get_statistics()
        print(f"\nStatistics: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())