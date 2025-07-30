#!/usr/bin/env python3
"""
ZeroMQ-specific Rate Limiter
Protects ZeroMQ endpoints from excessive connections and message rates
"""

import zmq
import json
import time
import threading
from typing import Dict, Optional, Set, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
from .rate_limiter import RateLimiter, TokenBucket, SlidingWindowLog


class ZMQRateLimiter:
    """Rate limiter for ZeroMQ connections"""
    
    def __init__(self, 
                 message_rate_limit: int = 1000,
                 connection_limit: int = 100,
                 ban_duration: int = 3600):
        """
        Initialize ZMQ rate limiter
        
        Args:
            message_rate_limit: Max messages per second per client
            connection_limit: Max concurrent connections
            ban_duration: Ban duration in seconds for violators
        """
        self.message_limiter = RateLimiter(
            TokenBucket(message_rate_limit, message_rate_limit, 1.0)
        )
        self.connection_limit = connection_limit
        self.ban_duration = ban_duration
        
        # Track connections and bans
        self.active_connections: Dict[str, Set[str]] = defaultdict(set)
        self.banned_clients: Dict[str, float] = {}
        self.message_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_loop(self):
        """Cleanup expired bans and old data"""
        while True:
            time.sleep(60)  # Run every minute
            
            with self.lock:
                # Remove expired bans
                now = time.time()
                expired = [k for k, v in self.banned_clients.items() if v < now]
                for client in expired:
                    del self.banned_clients[client]
                    self.logger.info(f"Ban expired for {client}")
                
                # Clean old message counts
                cutoff = now - 300  # 5 minutes
                for client in list(self.message_counts.keys()):
                    self.message_counts[client] = deque(
                        (t for t in self.message_counts[client] if t > cutoff),
                        maxlen=1000
                    )
    
    def is_banned(self, client_id: str) -> bool:
        """Check if client is banned"""
        with self.lock:
            if client_id in self.banned_clients:
                if time.time() < self.banned_clients[client_id]:
                    return True
                else:
                    del self.banned_clients[client_id]
        return False
    
    def ban_client(self, client_id: str, reason: str = "Rate limit violation"):
        """Ban a client"""
        with self.lock:
            self.banned_clients[client_id] = time.time() + self.ban_duration
            self.logger.warning(f"Banned client {client_id}: {reason}")
            
            # Disconnect all connections from this client
            if client_id in self.active_connections:
                del self.active_connections[client_id]
    
    def check_connection_limit(self, client_id: str, socket_id: str) -> bool:
        """Check if client can create new connection"""
        with self.lock:
            if self.is_banned(client_id):
                return False
            
            # Check global connection limit
            total_connections = sum(len(conns) for conns in self.active_connections.values())
            if total_connections >= self.connection_limit:
                self.logger.warning(f"Global connection limit reached: {total_connections}")
                return False
            
            # Check per-client connection limit (max 10 per client)
            client_connections = self.active_connections[client_id]
            if len(client_connections) >= 10:
                self.logger.warning(f"Client {client_id} exceeded connection limit")
                self.ban_client(client_id, "Too many connections")
                return False
            
            # Register connection
            client_connections.add(socket_id)
            return True
    
    def remove_connection(self, client_id: str, socket_id: str):
        """Remove a connection"""
        with self.lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].discard(socket_id)
                if not self.active_connections[client_id]:
                    del self.active_connections[client_id]
    
    def check_message_rate(self, client_id: str) -> Tuple[bool, Dict]:
        """Check if client can send message"""
        if self.is_banned(client_id):
            return False, {'banned': True, 'ban_expires': self.banned_clients.get(client_id, 0)}
        
        # Check rate limit
        allowed, metadata = self.message_limiter.check_rate_limit(client_id)
        
        # Track message for pattern analysis
        with self.lock:
            self.message_counts[client_id].append(time.time())
            
            # Check for suspicious patterns
            if len(self.message_counts[client_id]) >= 100:
                # Calculate message rate over last minute
                now = time.time()
                minute_ago = now - 60
                recent_messages = sum(1 for t in self.message_counts[client_id] if t > minute_ago)
                
                if recent_messages > self.message_limiter.strategy.capacity * 2:
                    self.ban_client(client_id, f"Suspicious pattern: {recent_messages} msgs/min")
                    return False, {'banned': True, 'reason': 'Suspicious pattern detected'}
        
        return allowed, metadata


class ZMQRateLimitProxy:
    """Rate limiting proxy for ZeroMQ"""
    
    def __init__(self,
                 frontend_address: str,
                 backend_address: str,
                 rate_limiter: ZMQRateLimiter):
        """
        Initialize rate limiting proxy
        
        Args:
            frontend_address: Address to bind frontend socket
            backend_address: Address to connect backend socket
            rate_limiter: Rate limiter instance
        """
        self.frontend_address = frontend_address
        self.backend_address = backend_address
        self.rate_limiter = rate_limiter
        self.context = zmq.Context()
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the proxy"""
        self.running = True
        
        # Create sockets
        frontend = self.context.socket(zmq.XSUB)
        frontend.bind(self.frontend_address)
        
        backend = self.context.socket(zmq.XPUB)
        backend.connect(self.backend_address)
        
        # Create monitoring socket
        monitor = self.context.socket(zmq.PULL)
        monitor.bind("inproc://monitor")
        
        # Poller
        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(backend, zmq.POLLIN)
        poller.register(monitor, zmq.POLLIN)
        
        self.logger.info(f"Rate limiting proxy started: {self.frontend_address} -> {self.backend_address}")
        
        while self.running:
            try:
                events = dict(poller.poll(1000))
                
                # Handle frontend to backend
                if frontend in events:
                    message = frontend.recv_multipart()
                    
                    # Extract client info (assuming first frame is client ID)
                    if message:
                        client_id = message[0].decode('utf-8', errors='ignore')
                        
                        # Check rate limit
                        allowed, metadata = self.rate_limiter.check_message_rate(client_id)
                        
                        if allowed:
                            backend.send_multipart(message)
                        else:
                            self.logger.warning(f"Rate limited message from {client_id}: {metadata}")
                
                # Handle backend to frontend
                if backend in events:
                    message = backend.recv_multipart()
                    frontend.send_multipart(message)
                
                # Handle monitoring messages
                if monitor in events:
                    cmd = monitor.recv_json()
                    self._handle_monitor_command(cmd)
                    
            except zmq.ZMQError as e:
                if e.errno != zmq.ETERM:
                    self.logger.error(f"Proxy error: {e}")
        
        # Cleanup
        frontend.close()
        backend.close()
        monitor.close()
    
    def _handle_monitor_command(self, cmd: Dict):
        """Handle monitoring commands"""
        if cmd.get('action') == 'stop':
            self.running = False
        elif cmd.get('action') == 'stats':
            # Return statistics
            stats = {
                'active_connections': len(self.rate_limiter.active_connections),
                'banned_clients': len(self.rate_limiter.banned_clients)
            }
            self.logger.info(f"Stats: {stats}")
    
    def stop(self):
        """Stop the proxy"""
        monitor = self.context.socket(zmq.PUSH)
        monitor.connect("inproc://monitor")
        monitor.send_json({'action': 'stop'})
        monitor.close()


class ZMQSubscriberRateLimiter:
    """Rate limiter for ZeroMQ subscribers"""
    
    def __init__(self, 
                 topics_per_client: int = 10,
                 messages_per_topic: int = 100):
        """
        Initialize subscriber rate limiter
        
        Args:
            topics_per_client: Max topics per client
            messages_per_topic: Max messages per topic per second
        """
        self.topics_per_client = topics_per_client
        self.topic_limiters: Dict[str, RateLimiter] = {}
        self.client_topics: Dict[str, Set[str]] = defaultdict(set)
        self.messages_per_topic = messages_per_topic
        self.lock = threading.Lock()
    
    def subscribe(self, client_id: str, topic: str) -> bool:
        """Check if client can subscribe to topic"""
        with self.lock:
            # Check topic limit
            if len(self.client_topics[client_id]) >= self.topics_per_client:
                return False
            
            # Create rate limiter for topic if needed
            if topic not in self.topic_limiters:
                self.topic_limiters[topic] = RateLimiter(
                    TokenBucket(self.messages_per_topic, self.messages_per_topic, 1.0)
                )
            
            self.client_topics[client_id].add(topic)
            return True
    
    def unsubscribe(self, client_id: str, topic: str):
        """Unsubscribe client from topic"""
        with self.lock:
            self.client_topics[client_id].discard(topic)
            if not self.client_topics[client_id]:
                del self.client_topics[client_id]
    
    def check_publish(self, topic: str) -> Tuple[bool, Dict]:
        """Check if message can be published to topic"""
        with self.lock:
            if topic not in self.topic_limiters:
                # Allow publishing to topics with no subscribers
                return True, {'subscribers': 0}
            
            allowed, metadata = self.topic_limiters[topic].check_rate_limit(topic)
            metadata['subscribers'] = sum(1 for topics in self.client_topics.values() if topic in topics)
            
            return allowed, metadata


class SecureZMQRateLimiter:
    """Secure rate limiter with authentication"""
    
    def __init__(self, 
                 auth_db: Dict[str, str],
                 rate_limits: Dict[str, Dict]):
        """
        Initialize secure rate limiter
        
        Args:
            auth_db: Authentication database (user -> password hash)
            rate_limits: Rate limits per user type
        """
        self.auth_db = auth_db
        self.rate_limiters = {}
        self.authenticated_clients: Dict[str, str] = {}  # client_id -> user
        
        # Create rate limiters for each user type
        for user_type, limits in rate_limits.items():
            self.rate_limiters[user_type] = RateLimiter(
                TokenBucket(
                    limits['capacity'],
                    limits['refill_rate'],
                    limits.get('refill_period', 1.0)
                )
            )
    
    def authenticate(self, client_id: str, credentials: Dict) -> bool:
        """Authenticate client"""
        username = credentials.get('username')
        password_hash = credentials.get('password_hash')
        
        if username in self.auth_db and self.auth_db[username] == password_hash:
            self.authenticated_clients[client_id] = username
            return True
        return False
    
    def check_rate(self, client_id: str) -> Tuple[bool, Dict]:
        """Check rate limit for authenticated client"""
        if client_id not in self.authenticated_clients:
            return False, {'error': 'Not authenticated'}
        
        username = self.authenticated_clients[client_id]
        user_type = self._get_user_type(username)
        
        if user_type not in self.rate_limiters:
            return False, {'error': 'Invalid user type'}
        
        return self.rate_limiters[user_type].check_rate_limit(username)
    
    def _get_user_type(self, username: str) -> str:
        """Get user type from username"""
        # Simple example - in production, this would query a database
        if username.startswith('admin_'):
            return 'admin'
        elif username.startswith('premium_'):
            return 'premium'
        else:
            return 'basic'


# Integration example
class RateLimitedZMQServer:
    """Example ZMQ server with rate limiting"""
    
    def __init__(self, address: str):
        """Initialize rate limited server"""
        self.address = address
        self.context = zmq.Context()
        self.rate_limiter = ZMQRateLimiter(
            message_rate_limit=100,
            connection_limit=50
        )
        self.subscriber_limiter = ZMQSubscriberRateLimiter()
    
    def run(self):
        """Run the server"""
        socket = self.context.socket(zmq.PUB)
        socket.bind(self.address)
        
        # Monitor socket for connections
        monitor = socket.get_monitor_socket()
        
        poller = zmq.Poller()
        poller.register(monitor, zmq.POLLIN)
        
        print(f"Rate limited ZMQ server running on {self.address}")
        
        while True:
            # Check monitor events
            events = dict(poller.poll(100))
            
            if monitor in events:
                event = monitor.recv_multipart()
                event_type = int.from_bytes(event[0], 'big')
                
                if event_type == zmq.EVENT_ACCEPTED:
                    # New connection
                    client_addr = event[1].decode('utf-8', errors='ignore')
                    print(f"New connection from {client_addr}")
                
                elif event_type == zmq.EVENT_DISCONNECTED:
                    # Client disconnected
                    client_addr = event[1].decode('utf-8', errors='ignore')
                    print(f"Client disconnected: {client_addr}")
            
            # Publish test data (rate limited)
            topic = "market.EURUSD"
            allowed, metadata = self.subscriber_limiter.check_publish(topic)
            
            if allowed:
                data = {
                    'symbol': 'EURUSD',
                    'bid': 1.1000,
                    'ask': 1.1001,
                    'timestamp': time.time()
                }
                socket.send_multipart([
                    topic.encode(),
                    json.dumps(data).encode()
                ])
            
            time.sleep(0.01)  # 100Hz max


if __name__ == "__main__":
    # Test rate limited server
    logging.basicConfig(level=logging.INFO)
    server = RateLimitedZMQServer("tcp://*:5557")
    server.run()