"""
Security module for MT4 Docker project
Provides SSL/TLS support for ZeroMQ communications
"""

from .zmq_secure import (
    SecurityConfig,
    SecureZeroMQPublisher,
    SecureZeroMQSubscriber,
    KeyManager,
    CurveSecurityMixin,
    SecureBridgeFactory
)

__all__ = [
    'SecurityConfig',
    'SecureZeroMQPublisher',
    'SecureZeroMQSubscriber',
    'KeyManager',
    'CurveSecurityMixin',
    'SecureBridgeFactory'
]

__version__ = '1.0.0'