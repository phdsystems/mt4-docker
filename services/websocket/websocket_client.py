#!/usr/bin/env python3
"""
WebSocket Client for MT4 Market Data
Python implementation with asyncio support
"""

import asyncio
import websockets
import json
import time
import jwt
import logging
from typing import Optional, List, Dict, Callable, Set
from datetime import datetime
import aiohttp


class MT4WebSocketClient:
    """Async WebSocket client for MT4 market data"""
    
    def __init__(self, 
                 url: str = "ws://localhost:8765",
                 token: Optional[str] = None,
                 debug: bool = False):
        """
        Initialize WebSocket client
        
        Args:
            url: WebSocket server URL
            token: JWT authentication token
            debug: Enable debug logging
        """
        self.url = url
        self.token = token
        self.debug = debug
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.client_id: Optional[str] = None
        self.authenticated = False
        self.tier = 'free'
        self.subscriptions: Set[str] = set()
        
        # Event handlers
        self.handlers: Dict[str, List[Callable]] = {}
        
        # Connection settings
        self.reconnect_interval = 5
        self.max_reconnect_attempts = 10
        self.heartbeat_interval = 30
        
        # Tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.receive_task: Optional[asyncio.Task] = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
    
    def on(self, event: str, handler: Callable):
        """Register event handler"""
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable):
        """Remove event handler"""
        if event in self.handlers and handler in self.handlers[event]:
            self.handlers[event].remove(handler)
    
    async def emit(self, event: str, data: Any):
        """Emit event to handlers"""
        if event in self.handlers:
            for handler in self.handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"Error in {event} handler: {e}")
    
    async def connect(self):
        """Connect to WebSocket server"""
        for attempt in range(self.max_reconnect_attempts):
            try:
                self.logger.info(f"Connecting to {self.url}...")
                self.ws = await websockets.connect(self.url)
                
                # Start receive loop
                self.receive_task = asyncio.create_task(self._receive_loop())
                
                # Wait for welcome message
                await asyncio.sleep(0.1)
                
                # Authenticate if token provided
                if self.token and not self.authenticated:
                    await self.authenticate(self.token)
                
                # Re-subscribe to previous subscriptions
                if self.subscriptions:
                    await self.subscribe(list(self.subscriptions))
                
                self.logger.info("Connected successfully")
                await self.emit('connected', None)
                
                return
                
            except Exception as e:
                self.logger.error(f"Connection failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_interval * (attempt + 1))
                else:
                    raise ConnectionError(f"Failed to connect after {self.max_reconnect_attempts} attempts")
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        if self.receive_task:
            self.receive_task.cancel()
        
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        self.authenticated = False
        self.client_id = None
        
        await self.emit('disconnected', None)
    
    async def authenticate(self, token: Optional[str] = None):
        """Authenticate with JWT token"""
        if token:
            self.token = token
        
        if not self.token:
            raise ValueError("No token provided")
        
        await self.send({
            'type': 'authenticate',
            'token': self.token
        })
    
    async def subscribe(self, symbols: List[str]):
        """Subscribe to market symbols"""
        if isinstance(symbols, str):
            symbols = [symbols]
        
        symbols = [s.upper() for s in symbols]
        self.subscriptions.update(symbols)
        
        await self.send({
            'type': 'subscribe',
            'symbols': symbols
        })
    
    async def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from symbols"""
        if isinstance(symbols, str):
            symbols = [symbols]
        
        symbols = [s.upper() for s in symbols]
        for symbol in symbols:
            self.subscriptions.discard(symbol)
        
        await self.send({
            'type': 'unsubscribe',
            'symbols': symbols
        })
    
    async def get_stats(self):
        """Request server statistics (premium feature)"""
        await self.send({
            'type': 'get_stats'
        })
    
    async def send(self, data: Dict):
        """Send message to server"""
        if not self.ws:
            raise ConnectionError("Not connected")
        
        if self.debug:
            self.logger.debug(f"Sending: {data}")
        
        await self.ws.send(json.dumps(data))
    
    async def _receive_loop(self):
        """Receive messages from server"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Connection closed")
            await self.emit('disconnected', None)
            # Attempt reconnection
            asyncio.create_task(self.connect())
    
    async def _handle_message(self, data: Dict):
        """Handle incoming message"""
        if self.debug:
            self.logger.debug(f"Received: {data}")
        
        msg_type = data.get('type')
        
        # Handle specific message types
        if msg_type == 'welcome':
            self.client_id = data.get('client_id')
            self.heartbeat_interval = data.get('heartbeat_interval', 30)
            # Start heartbeat
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        elif msg_type == 'auth_success':
            self.authenticated = True
            self.tier = data.get('tier', 'free')
            self.logger.info(f"Authenticated with tier: {self.tier}")
        
        elif msg_type == 'auth_failed':
            self.authenticated = False
            self.logger.error(f"Authentication failed: {data.get('error')}")
        
        elif msg_type == 'tick':
            # Emit market data event
            await self.emit('market_data', data.get('data'))
        
        elif msg_type == 'subscribed':
            self.logger.info(f"Subscribed to: {data.get('symbols')}")
        
        elif msg_type == 'error':
            self.logger.error(f"Server error: {data.get('error')}")
        
        elif msg_type == 'rate_limit':
            self.logger.warning(f"Rate limited. Retry after: {data.get('retry_after')}s")
        
        # Emit generic message event
        await self.emit('message', data)
        
        # Emit specific event
        if msg_type:
            await self.emit(msg_type, data)
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.send({'type': 'ping'})
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                break


class MT4WebSocketSync:
    """Synchronous wrapper for WebSocket client"""
    
    def __init__(self, url: str = "ws://localhost:8765", token: Optional[str] = None):
        self.client = MT4WebSocketClient(url, token)
        self.loop = asyncio.new_event_loop()
        self.thread = None
    
    def connect(self):
        """Connect synchronously"""
        self.loop.run_until_complete(self.client.connect())
    
    def disconnect(self):
        """Disconnect synchronously"""
        self.loop.run_until_complete(self.client.disconnect())
    
    def subscribe(self, symbols: List[str]):
        """Subscribe synchronously"""
        self.loop.run_until_complete(self.client.subscribe(symbols))
    
    def on_market_data(self, handler: Callable):
        """Register market data handler"""
        self.client.on('market_data', handler)


def generate_test_token(user_id: str = "test_user", tier: str = "free") -> str:
    """Generate test JWT token"""
    payload = {
        'user_id': user_id,
        'tier': tier,
        'exp': datetime.utcnow().timestamp() + 3600,
        'iat': datetime.utcnow().timestamp()
    }
    
    return jwt.encode(payload, 'your-secret-key', algorithm='HS256')


# Example usage
async def example():
    """Example WebSocket client usage"""
    # Create client
    client = MT4WebSocketClient("ws://localhost:8765", debug=True)
    
    # Register handlers
    @client.on('market_data')
    async def handle_market_data(data):
        print(f"Market data: {data}")
    
    @client.on('stats')
    async def handle_stats(data):
        print(f"Stats: {data}")
    
    try:
        # Connect
        await client.connect()
        
        # Generate and use test token
        token = generate_test_token("test_user", "premium")
        await client.authenticate(token)
        
        # Subscribe to symbols
        await client.subscribe(['EURUSD', 'GBPUSD', 'USDJPY'])
        
        # Get stats (premium feature)
        await client.get_stats()
        
        # Keep running
        await asyncio.sleep(60)
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.disconnect()


# REST API client for comparison
class MT4RestClient:
    """REST API client with WebSocket fallback"""
    
    def __init__(self, base_url: str = "http://localhost:5000", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = aiohttp.ClientSession()
        
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
    
    async def get_tick(self, symbol: str) -> Dict:
        """Get latest tick via REST API"""
        async with self.session.get(f"{self.base_url}/api/v1/market/tick/{symbol}") as resp:
            return await resp.json()
    
    async def get_ticks(self, symbols: List[str]) -> Dict:
        """Get multiple ticks"""
        params = {'symbols': ','.join(symbols)}
        async with self.session.get(f"{self.base_url}/api/v1/market/ticks", params=params) as resp:
            return await resp.json()
    
    async def close(self):
        """Close session"""
        await self.session.close()


if __name__ == "__main__":
    # Run example
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example())