#!/usr/bin/env python3
"""
Secure ZeroMQ Implementation with SSL/TLS Support
Using CURVE authentication and encryption
"""

import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator
import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import secrets


@dataclass
class SecurityConfig:
    """Security configuration for ZeroMQ"""
    enable_curve: bool = True
    enable_plain: bool = False
    server_secret_key_file: Optional[str] = None
    server_public_key_file: Optional[str] = None
    client_secret_key_file: Optional[str] = None
    client_public_key_file: Optional[str] = None
    authorized_clients_dir: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class ISecureConnection(ABC):
    """Interface for secure connections"""
    
    @abstractmethod
    def setup_security(self, config: SecurityConfig) -> None:
        """Setup security for the connection"""
        pass
    
    @abstractmethod
    def generate_keypair(self, key_dir: str, key_name: str) -> Tuple[str, str]:
        """Generate a new keypair"""
        pass


class CurveSecurityMixin:
    """Mixin for CURVE security implementation"""
    
    def generate_keypair(self, key_dir: str, key_name: str) -> Tuple[str, str]:
        """Generate CURVE keypair and save to files"""
        os.makedirs(key_dir, exist_ok=True)
        
        # Generate keypair
        public_key, secret_key = zmq.curve_keypair()
        
        # Save keys
        secret_file = os.path.join(key_dir, f"{key_name}.key_secret")
        public_file = os.path.join(key_dir, f"{key_name}.key")
        
        # Save with restricted permissions
        with open(secret_file, 'wb') as f:
            f.write(secret_key)
        os.chmod(secret_file, 0o600)
        
        with open(public_file, 'wb') as f:
            f.write(public_key)
        os.chmod(public_file, 0o644)
        
        return public_file, secret_file
    
    def load_certificate(self, filename: str) -> bytes:
        """Load a certificate from file"""
        with open(filename, 'rb') as f:
            return f.read()


class SecureZeroMQPublisher(CurveSecurityMixin):
    """Secure ZeroMQ Publisher with CURVE authentication"""
    
    def __init__(self, 
                 addresses: List[str],
                 security_config: SecurityConfig,
                 serializer: Any,
                 high_water_mark: int = 10000):
        self._addresses = addresses
        self._security_config = security_config
        self._serializer = serializer
        self._hwm = high_water_mark
        self._context: Optional[zmq.Context] = None
        self._socket: Optional[zmq.Socket] = None
        self._auth: Optional[ThreadAuthenticator] = None
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def setup_security(self, config: SecurityConfig) -> None:
        """Setup CURVE security for the publisher"""
        if not config.enable_curve:
            self._logger.warning("CURVE security disabled")
            return
        
        # Start authenticator
        self._auth = ThreadAuthenticator(self._context)
        self._auth.start()
        
        # Configure authenticator
        if config.authorized_clients_dir:
            # Allow any client with a public key in the directory
            self._auth.configure_curve(domain='*', location=config.authorized_clients_dir)
        else:
            # Allow any client (not recommended for production)
            self._auth.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)
        
        # Load server keys
        if config.server_secret_key_file and config.server_public_key_file:
            server_secret = self.load_certificate(config.server_secret_key_file)
            server_public = self.load_certificate(config.server_public_key_file)
        else:
            # Generate new keys if not provided
            key_dir = "./keys/server"
            public_file, secret_file = self.generate_keypair(key_dir, "server")
            server_secret = self.load_certificate(secret_file)
            server_public = self.load_certificate(public_file)
            self._logger.info(f"Generated server keys in {key_dir}")
        
        # Configure socket for CURVE
        self._socket.curve_secretkey = server_secret
        self._socket.curve_publickey = server_public
        self._socket.curve_server = True
        
        self._logger.info("CURVE security enabled for publisher")
    
    def connect(self) -> None:
        """Establish secure ZeroMQ connections"""
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.setsockopt(zmq.SNDHWM, self._hwm)
        self._socket.setsockopt(zmq.LINGER, 0)
        
        # Setup security before binding
        self.setup_security(self._security_config)
        
        for address in self._addresses:
            self._socket.bind(address)
            self._logger.info(f"Secure publisher bound to {address}")
    
    def disconnect(self) -> None:
        """Close secure ZeroMQ connections"""
        if self._auth:
            self._auth.stop()
        if self._socket:
            self._socket.close()
        if self._context:
            self._context.term()
        self._logger.info("Secure publisher disconnected")
    
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish message securely"""
        if not self._socket:
            raise RuntimeError("Publisher not connected")
        
        try:
            serialized = self._serializer.serialize(message)
            self._socket.send_multipart([
                topic.encode('utf-8'),
                serialized
            ])
        except zmq.ZMQError as e:
            self._logger.error(f"Failed to publish: {e}")
            raise


class SecureZeroMQSubscriber(CurveSecurityMixin):
    """Secure ZeroMQ Subscriber with CURVE authentication"""
    
    def __init__(self,
                 addresses: List[str],
                 security_config: SecurityConfig,
                 serializer: Any):
        self._addresses = addresses
        self._security_config = security_config
        self._serializer = serializer
        self._context: Optional[zmq.Context] = None
        self._socket: Optional[zmq.Socket] = None
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def setup_security(self, config: SecurityConfig) -> None:
        """Setup CURVE security for the subscriber"""
        if not config.enable_curve:
            self._logger.warning("CURVE security disabled")
            return
        
        # Load client keys
        if config.client_secret_key_file and config.client_public_key_file:
            client_secret = self.load_certificate(config.client_secret_key_file)
            client_public = self.load_certificate(config.client_public_key_file)
        else:
            # Generate new keys if not provided
            key_dir = "./keys/client"
            public_file, secret_file = self.generate_keypair(key_dir, "client")
            client_secret = self.load_certificate(secret_file)
            client_public = self.load_certificate(public_file)
            self._logger.info(f"Generated client keys in {key_dir}")
        
        # Load server public key
        if config.server_public_key_file:
            server_public = self.load_certificate(config.server_public_key_file)
        else:
            raise ValueError("Server public key required for CURVE client")
        
        # Configure socket for CURVE
        self._socket.curve_secretkey = client_secret
        self._socket.curve_publickey = client_public
        self._socket.curve_serverkey = server_public
        
        self._logger.info("CURVE security enabled for subscriber")
    
    def connect(self) -> None:
        """Establish secure ZeroMQ connections"""
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.setsockopt(zmq.RCVHWM, 0)
        
        # Setup security before connecting
        self.setup_security(self._security_config)
        
        for address in self._addresses:
            self._socket.connect(address)
            self._logger.info(f"Secure subscriber connected to {address}")
    
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        if not self._socket:
            raise RuntimeError("Subscriber not connected")
        
        for topic in topics:
            self._socket.subscribe(topic.encode('utf-8'))
            self._logger.info(f"Subscribed to {topic}")
    
    def receive(self, timeout: Optional[int] = None) -> Optional[Tuple[str, Any]]:
        """Receive message securely"""
        if not self._socket:
            raise RuntimeError("Subscriber not connected")
        
        if timeout:
            self._socket.setsockopt(zmq.RCVTIMEO, timeout)
        
        try:
            topic, data = self._socket.recv_multipart()
            message = self._serializer.deserialize(data)
            return topic.decode('utf-8'), message
        except zmq.Again:
            return None
        except Exception as e:
            self._logger.error(f"Error receiving message: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close secure ZeroMQ connections"""
        if self._socket:
            self._socket.close()
        if self._context:
            self._context.term()
        self._logger.info("Secure subscriber disconnected")


class KeyManager:
    """Manages cryptographic keys for ZeroMQ CURVE"""
    
    def __init__(self, base_dir: str = "./keys"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_server_keys(self, name: str = "server") -> Dict[str, str]:
        """Generate server keypair"""
        server_dir = self.base_dir / "server"
        server_dir.mkdir(exist_ok=True)
        
        public_key, secret_key = zmq.curve_keypair()
        
        public_file = server_dir / f"{name}.key"
        secret_file = server_dir / f"{name}.key_secret"
        
        # Save with proper permissions
        secret_file.write_bytes(secret_key)
        secret_file.chmod(0o600)
        
        public_file.write_bytes(public_key)
        public_file.chmod(0o644)
        
        return {
            'public': str(public_file),
            'secret': str(secret_file)
        }
    
    def generate_client_keys(self, name: str) -> Dict[str, str]:
        """Generate client keypair"""
        client_dir = self.base_dir / "clients"
        client_dir.mkdir(exist_ok=True)
        
        public_key, secret_key = zmq.curve_keypair()
        
        public_file = client_dir / f"{name}.key"
        secret_file = client_dir / f"{name}.key_secret"
        
        # Save with proper permissions
        secret_file.write_bytes(secret_key)
        secret_file.chmod(0o600)
        
        public_file.write_bytes(public_key)
        public_file.chmod(0o644)
        
        # Also save to authorized clients directory
        auth_dir = self.base_dir / "authorized_clients"
        auth_dir.mkdir(exist_ok=True)
        
        auth_file = auth_dir / f"{name}.key"
        auth_file.write_bytes(public_key)
        auth_file.chmod(0o644)
        
        return {
            'public': str(public_file),
            'secret': str(secret_file),
            'authorized': str(auth_file)
        }
    
    def list_authorized_clients(self) -> List[str]:
        """List all authorized client keys"""
        auth_dir = self.base_dir / "authorized_clients"
        if not auth_dir.exists():
            return []
        
        return [f.stem for f in auth_dir.glob("*.key")]
    
    def revoke_client(self, name: str) -> bool:
        """Revoke a client's authorization"""
        auth_file = self.base_dir / "authorized_clients" / f"{name}.key"
        if auth_file.exists():
            auth_file.unlink()
            return True
        return False


class SecureBridgeFactory:
    """Factory for creating secure bridges"""
    
    @staticmethod
    def create_secure_publisher(config: Dict[str, Any]) -> SecureZeroMQPublisher:
        """Create a secure publisher"""
        from ..zeromq_bridge.zmq_bridge_oop import JsonSerializer
        
        security_config = SecurityConfig(
            enable_curve=config.get('enable_curve', True),
            server_secret_key_file=config.get('server_secret_key'),
            server_public_key_file=config.get('server_public_key'),
            authorized_clients_dir=config.get('authorized_clients_dir')
        )
        
        serializer = JsonSerializer()
        addresses = config.get('publish_addresses', ['tcp://*:5556'])
        
        return SecureZeroMQPublisher(addresses, security_config, serializer)
    
    @staticmethod
    def create_secure_subscriber(config: Dict[str, Any]) -> SecureZeroMQSubscriber:
        """Create a secure subscriber"""
        from ..zeromq_bridge.zmq_bridge_oop import JsonSerializer
        
        security_config = SecurityConfig(
            enable_curve=config.get('enable_curve', True),
            client_secret_key_file=config.get('client_secret_key'),
            client_public_key_file=config.get('client_public_key'),
            server_public_key_file=config.get('server_public_key')
        )
        
        serializer = JsonSerializer()
        addresses = config.get('subscribe_addresses', ['tcp://localhost:5556'])
        
        return SecureZeroMQSubscriber(addresses, security_config, serializer)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Generate keys
    km = KeyManager()
    
    # Generate server keys
    server_keys = km.generate_server_keys("mt4_server")
    print(f"Server keys generated: {server_keys}")
    
    # Generate client keys
    client1_keys = km.generate_client_keys("python_client")
    client2_keys = km.generate_client_keys("nodejs_client")
    
    print(f"Client 1 keys: {client1_keys}")
    print(f"Client 2 keys: {client2_keys}")
    
    # List authorized clients
    clients = km.list_authorized_clients()
    print(f"Authorized clients: {clients}")