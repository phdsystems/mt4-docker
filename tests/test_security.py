#!/usr/bin/env python3
"""
Unit tests for SSL/TLS security implementation
"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.security.zmq_secure import (
    KeyManager, SecurityConfig, CurveSecurityMixin,
    SecureZeroMQPublisher, SecureZeroMQSubscriber
)
from services.zeromq_bridge.zmq_bridge_oop import JsonSerializer


class TestKeyManager(unittest.TestCase):
    """Test key management functionality"""
    
    def setUp(self):
        """Create temporary directory for keys"""
        self.temp_dir = tempfile.mkdtemp()
        self.key_manager = KeyManager(self.temp_dir)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_server_keys(self):
        """Test server key generation"""
        keys = self.key_manager.generate_server_keys("test_server")
        
        # Check keys were created
        self.assertTrue(os.path.exists(keys['public']))
        self.assertTrue(os.path.exists(keys['secret']))
        
        # Check permissions
        public_stat = os.stat(keys['public'])
        secret_stat = os.stat(keys['secret'])
        
        self.assertEqual(oct(public_stat.st_mode)[-3:], '644')
        self.assertEqual(oct(secret_stat.st_mode)[-3:], '600')
        
        # Check key content
        with open(keys['public'], 'rb') as f:
            public_key = f.read()
        self.assertEqual(len(public_key), 40)  # Z85 encoded key length
    
    def test_generate_client_keys(self):
        """Test client key generation"""
        keys = self.key_manager.generate_client_keys("test_client")
        
        # Check all keys were created
        self.assertTrue(os.path.exists(keys['public']))
        self.assertTrue(os.path.exists(keys['secret']))
        self.assertTrue(os.path.exists(keys['authorized']))
        
        # Check authorized key matches public key
        with open(keys['public'], 'rb') as f:
            public_key = f.read()
        with open(keys['authorized'], 'rb') as f:
            auth_key = f.read()
        
        self.assertEqual(public_key, auth_key)
    
    def test_list_authorized_clients(self):
        """Test listing authorized clients"""
        # Generate some clients
        self.key_manager.generate_client_keys("client1")
        self.key_manager.generate_client_keys("client2")
        self.key_manager.generate_client_keys("client3")
        
        # List clients
        clients = self.key_manager.list_authorized_clients()
        
        self.assertEqual(len(clients), 3)
        self.assertIn("client1", clients)
        self.assertIn("client2", clients)
        self.assertIn("client3", clients)
    
    def test_revoke_client(self):
        """Test client revocation"""
        # Generate client
        self.key_manager.generate_client_keys("revoke_test")
        
        # Verify client is authorized
        clients = self.key_manager.list_authorized_clients()
        self.assertIn("revoke_test", clients)
        
        # Revoke client
        result = self.key_manager.revoke_client("revoke_test")
        self.assertTrue(result)
        
        # Verify client is no longer authorized
        clients = self.key_manager.list_authorized_clients()
        self.assertNotIn("revoke_test", clients)
        
        # Try to revoke non-existent client
        result = self.key_manager.revoke_client("non_existent")
        self.assertFalse(result)


class TestSecurityConfig(unittest.TestCase):
    """Test security configuration"""
    
    def test_default_config(self):
        """Test default security configuration"""
        config = SecurityConfig()
        
        self.assertTrue(config.enable_curve)
        self.assertFalse(config.enable_plain)
        self.assertIsNone(config.server_secret_key_file)
        self.assertIsNone(config.username)
    
    def test_custom_config(self):
        """Test custom security configuration"""
        config = SecurityConfig(
            enable_curve=True,
            server_secret_key_file="/path/to/secret.key",
            server_public_key_file="/path/to/public.key",
            authorized_clients_dir="/path/to/clients"
        )
        
        self.assertTrue(config.enable_curve)
        self.assertEqual(config.server_secret_key_file, "/path/to/secret.key")
        self.assertEqual(config.authorized_clients_dir, "/path/to/clients")


class TestCurveSecurityMixin(unittest.TestCase):
    """Test CURVE security mixin"""
    
    def setUp(self):
        """Create temporary directory and mixin instance"""
        self.temp_dir = tempfile.mkdtemp()
        
        class TestMixin(CurveSecurityMixin):
            pass
        
        self.mixin = TestMixin()
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_keypair(self):
        """Test keypair generation"""
        public_file, secret_file = self.mixin.generate_keypair(
            self.temp_dir, "test_key"
        )
        
        # Check files exist
        self.assertTrue(os.path.exists(public_file))
        self.assertTrue(os.path.exists(secret_file))
        
        # Check file names
        self.assertTrue(public_file.endswith("test_key.key"))
        self.assertTrue(secret_file.endswith("test_key.key_secret"))
    
    def test_load_certificate(self):
        """Test certificate loading"""
        # Create test certificate
        test_cert = b"test_certificate_content"
        cert_path = os.path.join(self.temp_dir, "test.cert")
        
        with open(cert_path, 'wb') as f:
            f.write(test_cert)
        
        # Load certificate
        loaded = self.mixin.load_certificate(cert_path)
        self.assertEqual(loaded, test_cert)


class TestSecurePublisherSubscriber(unittest.TestCase):
    """Test secure publisher and subscriber"""
    
    def setUp(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.key_manager = KeyManager(self.temp_dir)
        
        # Generate keys
        self.server_keys = self.key_manager.generate_server_keys("test_server")
        self.client_keys = self.key_manager.generate_client_keys("test_client")
        
        # Create serializer
        self.serializer = JsonSerializer()
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_secure_publisher_creation(self):
        """Test secure publisher creation"""
        config = SecurityConfig(
            enable_curve=True,
            server_secret_key_file=self.server_keys['secret'],
            server_public_key_file=self.server_keys['public'],
            authorized_clients_dir=os.path.join(self.temp_dir, "authorized_clients")
        )
        
        publisher = SecureZeroMQPublisher(
            addresses=['tcp://127.0.0.1:15556'],
            security_config=config,
            serializer=self.serializer
        )
        
        self.assertIsNotNone(publisher)
        self.assertEqual(publisher._addresses[0], 'tcp://127.0.0.1:15556')
    
    def test_secure_subscriber_creation(self):
        """Test secure subscriber creation"""
        config = SecurityConfig(
            enable_curve=True,
            client_secret_key_file=self.client_keys['secret'],
            client_public_key_file=self.client_keys['public'],
            server_public_key_file=self.server_keys['public']
        )
        
        subscriber = SecureZeroMQSubscriber(
            addresses=['tcp://127.0.0.1:15556'],
            security_config=config,
            serializer=self.serializer
        )
        
        self.assertIsNotNone(subscriber)
        self.assertEqual(subscriber._addresses[0], 'tcp://127.0.0.1:15556')
    
    def test_security_config_validation(self):
        """Test security configuration validation"""
        # Test missing server public key for client
        config = SecurityConfig(
            enable_curve=True,
            client_secret_key_file=self.client_keys['secret'],
            client_public_key_file=self.client_keys['public'],
            server_public_key_file=None  # Missing
        )
        
        subscriber = SecureZeroMQSubscriber(
            addresses=['tcp://127.0.0.1:15556'],
            security_config=config,
            serializer=self.serializer
        )
        
        # Should raise error when trying to setup security
        with self.assertRaises(ValueError):
            subscriber.setup_security(config)


class TestSecurityIntegration(unittest.TestCase):
    """Integration tests for security features"""
    
    def setUp(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.key_manager = KeyManager(self.temp_dir)
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_key_generation_workflow(self):
        """Test complete key generation workflow"""
        # Generate server keys
        server_keys = self.key_manager.generate_server_keys("integration_server")
        
        # Generate multiple client keys
        clients = []
        for i in range(3):
            client_name = f"integration_client_{i}"
            client_keys = self.key_manager.generate_client_keys(client_name)
            clients.append(client_name)
        
        # Verify all clients are authorized
        authorized = self.key_manager.list_authorized_clients()
        for client in clients:
            self.assertIn(client, authorized)
        
        # Revoke one client
        self.key_manager.revoke_client(clients[1])
        
        # Verify revocation
        authorized = self.key_manager.list_authorized_clients()
        self.assertIn(clients[0], authorized)
        self.assertNotIn(clients[1], authorized)
        self.assertIn(clients[2], authorized)
    
    def test_file_permissions(self):
        """Test that generated files have correct permissions"""
        # Generate keys
        server_keys = self.key_manager.generate_server_keys("perm_test")
        client_keys = self.key_manager.generate_client_keys("perm_client")
        
        # Check server key permissions
        server_public_stat = os.stat(server_keys['public'])
        server_secret_stat = os.stat(server_keys['secret'])
        
        self.assertEqual(oct(server_public_stat.st_mode)[-3:], '644')
        self.assertEqual(oct(server_secret_stat.st_mode)[-3:], '600')
        
        # Check client key permissions
        client_public_stat = os.stat(client_keys['public'])
        client_secret_stat = os.stat(client_keys['secret'])
        
        self.assertEqual(oct(client_public_stat.st_mode)[-3:], '644')
        self.assertEqual(oct(client_secret_stat.st_mode)[-3:], '600')


if __name__ == '__main__':
    unittest.main()