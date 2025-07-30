#!/usr/bin/env python3
"""
WebSocket Server for Real-time Market Data Streaming
Bridges ZeroMQ market data to WebSocket clients
"""

import asyncio
import websockets
import json
import zmq
import zmq.asyncio
import logging
import time
import jwt
import hashlib
from typing import Set, Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.rate_limiter.rate_limiter import RateLimiter, TokenBucket


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
WS_HOST = os.environ.get('WS_HOST', '0.0.0.0')
WS_PORT = int(os.environ.get('WS_PORT', 8765))
ZMQ_PUBLISHER = os.environ.get('ZMQ_PUBLISHER', 'tcp://localhost:5556')
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
HEARTBEAT_INTERVAL = 30  # seconds


@dataclass
class MarketTick:
    """Market tick data structure"""
    symbol: str
    bid: float
    ask: float
    spread: float
    volume: int
    timestamp: float
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self))


@dataclass
class ClientInfo:
    """WebSocket client information"""
    id: str
    websocket: websockets.WebSocketServerProtocol
    subscriptions: Set[str]
    authenticated: bool
    tier: str
    last_heartbeat: float
    message_count: int
    connected_at: float


class WebSocketManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        self.clients: Dict[str, ClientInfo] = {}
        self.symbol_subscribers: Dict[str, Set[str]] = {}
        self.rate_limiters = {
            'free': RateLimiter(TokenBucket(10, 10, 1)),      # 10 msg/sec
            'basic': RateLimiter(TokenBucket(50, 50, 1)),     # 50 msg/sec
            'premium': RateLimiter(TokenBucket(100, 100, 1)), # 100 msg/sec
            'unlimited': RateLimiter(TokenBucket(1000, 1000, 1))
        }
        self.zmq_context = zmq.asyncio.Context()
        self.market_data_cache: Dict[str, MarketTick] = {}
    
    async def register_client(self, websocket: websockets.WebSocketServerProtocol, path: str) -> ClientInfo:
        """Register new WebSocket client"""
        client_id = hashlib.sha256(
            f"{websocket.remote_address[0]}:{websocket.remote_address[1]}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        client = ClientInfo(
            id=client_id,
            websocket=websocket,
            subscriptions=set(),
            authenticated=False,
            tier='free',
            last_heartbeat=time.time(),
            message_count=0,
            connected_at=time.time()
        )
        
        self.clients[client_id] = client
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        # Send welcome message
        await self.send_to_client(client, {
            'type': 'welcome',
            'client_id': client_id,
            'server_time': time.time(),
            'heartbeat_interval': HEARTBEAT_INTERVAL
        })
        
        return client
    
    async def unregister_client(self, client_id: str):
        """Unregister WebSocket client"""
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        # Remove from all subscriptions
        for symbol in client.subscriptions:
            if symbol in self.symbol_subscribers:
                self.symbol_subscribers[symbol].discard(client_id)
                if not self.symbol_subscribers[symbol]:
                    del self.symbol_subscribers[symbol]
        
        del self.clients[client_id]
        logger.info(f"Client {client_id} disconnected")
    
    async def authenticate_client(self, client_id: str, token: str) -> bool:
        """Authenticate client with JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            
            if client_id in self.clients:
                self.clients[client_id].authenticated = True
                self.clients[client_id].tier = payload.get('tier', 'basic')
                
                await self.send_to_client(self.clients[client_id], {
                    'type': 'auth_success',
                    'tier': self.clients[client_id].tier
                })
                
                logger.info(f"Client {client_id} authenticated with tier: {self.clients[client_id].tier}")
                return True
                
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token from client {client_id}: {e}")
        
        if client_id in self.clients:
            await self.send_to_client(self.clients[client_id], {
                'type': 'auth_failed',
                'error': 'Invalid token'
            })
        
        return False
    
    async def subscribe_client(self, client_id: str, symbols: List[str]) -> bool:
        """Subscribe client to symbols"""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        
        # Check subscription limits based on tier
        limits = {
            'free': 5,
            'basic': 20,
            'premium': 50,
            'unlimited': 1000
        }
        
        max_symbols = limits.get(client.tier, 5)
        new_total = len(client.subscriptions.union(set(symbols)))
        
        if new_total > max_symbols:
            await self.send_to_client(client, {
                'type': 'subscribe_error',
                'error': f'Subscription limit exceeded. Max: {max_symbols}'
            })
            return False
        
        # Add subscriptions
        added = []
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol not in client.subscriptions:
                client.subscriptions.add(symbol)
                
                if symbol not in self.symbol_subscribers:
                    self.symbol_subscribers[symbol] = set()
                self.symbol_subscribers[symbol].add(client_id)
                
                added.append(symbol)
                
                # Send cached data if available
                if symbol in self.market_data_cache:
                    await self.send_market_data(client, self.market_data_cache[symbol])
        
        if added:
            await self.send_to_client(client, {
                'type': 'subscribed',
                'symbols': added
            })
            logger.info(f"Client {client_id} subscribed to: {added}")
        
        return True
    
    async def unsubscribe_client(self, client_id: str, symbols: List[str]) -> bool:
        """Unsubscribe client from symbols"""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        removed = []
        
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol in client.subscriptions:
                client.subscriptions.remove(symbol)
                
                if symbol in self.symbol_subscribers:
                    self.symbol_subscribers[symbol].discard(client_id)
                    if not self.symbol_subscribers[symbol]:
                        del self.symbol_subscribers[symbol]
                
                removed.append(symbol)
        
        if removed:
            await self.send_to_client(client, {
                'type': 'unsubscribed',
                'symbols': removed
            })
            logger.info(f"Client {client_id} unsubscribed from: {removed}")
        
        return True
    
    async def send_to_client(self, client: ClientInfo, data: Dict) -> bool:
        """Send data to specific client"""
        try:
            # Check rate limit
            allowed, metadata = self.rate_limiters[client.tier].check_rate_limit(client.id)
            
            if not allowed:
                # Send rate limit warning
                await client.websocket.send(json.dumps({
                    'type': 'rate_limit',
                    'retry_after': metadata.get('retry_after', 1)
                }))
                return False
            
            await client.websocket.send(json.dumps(data))
            client.message_count += 1
            return True
            
        except websockets.exceptions.ConnectionClosed:
            return False
        except Exception as e:
            logger.error(f"Error sending to client {client.id}: {e}")
            return False
    
    async def send_market_data(self, client: ClientInfo, tick: MarketTick) -> bool:
        """Send market data to client"""
        return await self.send_to_client(client, {
            'type': 'tick',
            'data': asdict(tick)
        })
    
    async def broadcast_market_data(self, tick: MarketTick):
        """Broadcast market data to subscribed clients"""
        # Update cache
        self.market_data_cache[tick.symbol] = tick
        
        # Get subscribers for this symbol
        if tick.symbol not in self.symbol_subscribers:
            return
        
        # Send to all subscribers
        disconnected = []
        for client_id in self.symbol_subscribers[tick.symbol]:
            if client_id in self.clients:
                success = await self.send_market_data(self.clients[client_id], tick)
                if not success:
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            await self.unregister_client(client_id)
    
    async def handle_heartbeat(self, client_id: str):
        """Handle client heartbeat"""
        if client_id in self.clients:
            self.clients[client_id].last_heartbeat = time.time()
            await self.send_to_client(self.clients[client_id], {
                'type': 'pong',
                'timestamp': time.time()
            })
    
    async def check_client_health(self):
        """Check and remove inactive clients"""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            
            now = time.time()
            timeout = HEARTBEAT_INTERVAL * 2
            disconnected = []
            
            for client_id, client in self.clients.items():
                if now - client.last_heartbeat > timeout:
                    logger.warning(f"Client {client_id} timed out")
                    disconnected.append(client_id)
            
            for client_id in disconnected:
                await self.unregister_client(client_id)
    
    def get_stats(self) -> Dict:
        """Get server statistics"""
        return {
            'clients_connected': len(self.clients),
            'total_subscriptions': sum(len(c.subscriptions) for c in self.clients.values()),
            'symbols_active': len(self.symbol_subscribers),
            'clients_by_tier': {
                tier: sum(1 for c in self.clients.values() if c.tier == tier)
                for tier in ['free', 'basic', 'premium', 'unlimited']
            },
            'cache_size': len(self.market_data_cache)
        }


class WebSocketServer:
    """WebSocket server for market data streaming"""
    
    def __init__(self):
        self.manager = WebSocketManager()
        self.running = False
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection"""
        client = await self.manager.register_client(websocket, path)
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(client.id, data)
                except json.JSONDecodeError:
                    await self.manager.send_to_client(client, {
                        'type': 'error',
                        'error': 'Invalid JSON'
                    })
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.manager.send_to_client(client, {
                        'type': 'error',
                        'error': str(e)
                    })
        
        finally:
            await self.manager.unregister_client(client.id)
    
    async def process_message(self, client_id: str, data: Dict):
        """Process client message"""
        msg_type = data.get('type')
        
        if msg_type == 'authenticate':
            token = data.get('token')
            if token:
                await self.manager.authenticate_client(client_id, token)
        
        elif msg_type == 'subscribe':
            symbols = data.get('symbols', [])
            if symbols:
                await self.manager.subscribe_client(client_id, symbols)
        
        elif msg_type == 'unsubscribe':
            symbols = data.get('symbols', [])
            if symbols:
                await self.manager.unsubscribe_client(client_id, symbols)
        
        elif msg_type == 'ping':
            await self.manager.handle_heartbeat(client_id)
        
        elif msg_type == 'get_stats':
            if client_id in self.manager.clients:
                client = self.manager.clients[client_id]
                if client.tier in ['premium', 'unlimited']:
                    await self.manager.send_to_client(client, {
                        'type': 'stats',
                        'data': self.manager.get_stats()
                    })
                else:
                    await self.manager.send_to_client(client, {
                        'type': 'error',
                        'error': 'Stats require premium tier'
                    })
        
        else:
            await self.manager.send_to_client(self.manager.clients.get(client_id), {
                'type': 'error',
                'error': f'Unknown message type: {msg_type}'
            })
    
    async def zmq_subscriber(self):
        """Subscribe to ZeroMQ market data"""
        socket = self.manager.zmq_context.socket(zmq.SUB)
        socket.connect(ZMQ_PUBLISHER)
        socket.subscribe(b"")
        
        logger.info(f"Connected to ZeroMQ publisher at {ZMQ_PUBLISHER}")
        
        while self.running:
            try:
                # Check for message with timeout
                if await socket.poll(1000):
                    topic, message = await socket.recv_multipart()
                    
                    # Parse message
                    data = json.loads(message.decode())
                    
                    # Extract symbol from topic (e.g., "tick.EURUSD" -> "EURUSD")
                    topic_str = topic.decode()
                    if topic_str.startswith("tick."):
                        symbol = topic_str[5:]
                        
                        # Create tick object
                        tick = MarketTick(
                            symbol=symbol,
                            bid=data.get('bid', 0),
                            ask=data.get('ask', 0),
                            spread=data.get('spread', 0),
                            volume=data.get('volume', 0),
                            timestamp=data.get('timestamp', time.time())
                        )
                        
                        # Broadcast to WebSocket clients
                        await self.manager.broadcast_market_data(tick)
            
            except Exception as e:
                logger.error(f"ZMQ subscriber error: {e}")
                await asyncio.sleep(1)
    
    async def start(self):
        """Start WebSocket server"""
        self.running = True
        
        # Start health check task
        health_task = asyncio.create_task(self.manager.check_client_health())
        
        # Start ZMQ subscriber
        zmq_task = asyncio.create_task(self.zmq_subscriber())
        
        # Start WebSocket server
        logger.info(f"Starting WebSocket server on {WS_HOST}:{WS_PORT}")
        
        async with websockets.serve(self.handle_client, WS_HOST, WS_PORT):
            await asyncio.Future()  # Run forever
    
    def stop(self):
        """Stop server"""
        self.running = False


# Utility functions for generating JWT tokens
def generate_token(user_id: str, tier: str = 'free', expires_in: int = 3600) -> str:
    """Generate JWT token for authentication"""
    payload = {
        'user_id': user_id,
        'tier': tier,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


# Admin API endpoints
class AdminAPI:
    """Admin API for managing WebSocket server"""
    
    def __init__(self, server: WebSocketServer):
        self.server = server
    
    async def get_stats(self) -> Dict:
        """Get server statistics"""
        stats = self.server.manager.get_stats()
        stats['uptime'] = time.time() - self.server.start_time if hasattr(self.server, 'start_time') else 0
        return stats
    
    async def kick_client(self, client_id: str) -> bool:
        """Kick a client"""
        if client_id in self.server.manager.clients:
            await self.server.manager.unregister_client(client_id)
            return True
        return False
    
    async def broadcast_message(self, message: Dict) -> int:
        """Broadcast message to all clients"""
        count = 0
        for client in self.server.manager.clients.values():
            if await self.server.manager.send_to_client(client, message):
                count += 1
        return count


if __name__ == "__main__":
    # Example: Generate test tokens
    print("=== WebSocket Server Test Tokens ===")
    print(f"Free tier token: {generate_token('test_free', 'free')}")
    print(f"Premium tier token: {generate_token('test_premium', 'premium')}")
    print(f"Unlimited tier token: {generate_token('test_unlimited', 'unlimited')}")
    
    # Start server
    server = WebSocketServer()
    server.start_time = time.time()
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nShutting down WebSocket server...")
        server.stop()