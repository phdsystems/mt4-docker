#!/usr/bin/env python3
"""
Test suite for rate limiting functionality
"""

import unittest
import time
import threading
import requests
import zmq
import json
from unittest.mock import Mock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rate_limiter.rate_limiter import (
    TokenBucket, SlidingWindowLog, RateLimiter,
    APIKeyRateLimiter, GeoRateLimiter
)
from services.rate_limiter.zmq_rate_limiter import (
    ZMQRateLimiter, ZMQSubscriberRateLimiter
)


class TestTokenBucket(unittest.TestCase):
    """Test token bucket algorithm"""
    
    def test_basic_limiting(self):
        """Test basic rate limiting"""
        limiter = RateLimiter(TokenBucket(capacity=5, refill_rate=1, refill_period=1))
        
        # Use all tokens
        for i in range(5):
            allowed, metadata = limiter.check_rate_limit("test_user")
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
            self.assertEqual(metadata['remaining'], 4-i)
        
        # Next request should be blocked
        allowed, metadata = limiter.check_rate_limit("test_user")
        self.assertFalse(allowed)
        self.assertEqual(metadata['remaining'], 0)
        self.assertIn('retry_after', metadata)
    
    def test_token_refill(self):
        """Test token refill mechanism"""
        limiter = RateLimiter(TokenBucket(capacity=2, refill_rate=2, refill_period=1))
        
        # Use all tokens
        limiter.check_rate_limit("test_user")
        limiter.check_rate_limit("test_user")
        
        # Should be blocked
        allowed, _ = limiter.check_rate_limit("test_user")
        self.assertFalse(allowed)
        
        # Wait for refill
        time.sleep(1.1)
        
        # Should have tokens again
        allowed, metadata = limiter.check_rate_limit("test_user")
        self.assertTrue(allowed)
        self.assertGreater(metadata['remaining'], 0)
    
    def test_multiple_users(self):
        """Test rate limiting for multiple users"""
        limiter = RateLimiter(TokenBucket(capacity=3, refill_rate=3, refill_period=60))
        
        # User 1 uses all tokens
        for _ in range(3):
            limiter.check_rate_limit("user1")
        
        # User 1 blocked
        allowed, _ = limiter.check_rate_limit("user1")
        self.assertFalse(allowed)
        
        # User 2 should still have tokens
        allowed, _ = limiter.check_rate_limit("user2")
        self.assertTrue(allowed)


class TestSlidingWindow(unittest.TestCase):
    """Test sliding window algorithm"""
    
    def test_window_limiting(self):
        """Test sliding window rate limiting"""
        limiter = RateLimiter(SlidingWindowLog(window_size=5, max_requests=3))
        
        # Make 3 requests
        for i in range(3):
            allowed, _ = limiter.check_rate_limit("test_user")
            self.assertTrue(allowed)
        
        # 4th request blocked
        allowed, _ = limiter.check_rate_limit("test_user")
        self.assertFalse(allowed)
        
        # Wait for window to slide
        time.sleep(5.1)
        
        # Should allow again
        allowed, _ = limiter.check_rate_limit("test_user")
        self.assertTrue(allowed)
    
    def test_sliding_behavior(self):
        """Test that window actually slides"""
        limiter = RateLimiter(SlidingWindowLog(window_size=3, max_requests=2))
        
        # Request at t=0
        limiter.check_rate_limit("user")
        
        # Request at t=1
        time.sleep(1)
        limiter.check_rate_limit("user")
        
        # Should be blocked at t=2
        time.sleep(1)
        allowed, _ = limiter.check_rate_limit("user")
        self.assertFalse(allowed)
        
        # Should allow at t=3.1 (first request outside window)
        time.sleep(1.1)
        allowed, _ = limiter.check_rate_limit("user")
        self.assertTrue(allowed)


class TestAPIKeyRateLimiter(unittest.TestCase):
    """Test API key rate limiting"""
    
    def test_tier_limits(self):
        """Test different tier limits"""
        limiter = APIKeyRateLimiter()
        
        # Register keys
        limiter.register_api_key("free_key", "free")
        limiter.register_api_key("premium_key", "premium")
        
        # Test free tier (lower limits)
        free_capacity = limiter.tiers['free']['rate_limiter'].strategy.capacity
        premium_capacity = limiter.tiers['premium']['rate_limiter'].strategy.capacity
        
        self.assertLess(free_capacity, premium_capacity)
    
    def test_daily_limits(self):
        """Test daily limit enforcement"""
        limiter = APIKeyRateLimiter()
        
        # Create custom tier with low daily limit
        limiter.tiers['test'] = {
            'rate_limiter': RateLimiter(TokenBucket(100, 100, 1)),
            'daily_limit': 5
        }
        
        limiter.register_api_key("test_key", "test")
        
        # Use up daily limit
        for i in range(5):
            allowed, metadata = limiter.check_limit("test_key")
            self.assertTrue(allowed)
            self.assertEqual(metadata['daily_remaining'], 4-i)
        
        # Should be blocked by daily limit
        allowed, metadata = limiter.check_limit("test_key")
        self.assertFalse(allowed)
        self.assertIn('daily_limit', metadata)


class TestZMQRateLimiter(unittest.TestCase):
    """Test ZeroMQ rate limiting"""
    
    def test_connection_limits(self):
        """Test connection limit enforcement"""
        limiter = ZMQRateLimiter(connection_limit=5)
        
        # Add connections
        for i in range(5):
            allowed = limiter.check_connection_limit("client1", f"socket{i}")
            self.assertTrue(allowed)
        
        # 6th connection should fail
        allowed = limiter.check_connection_limit("client2", "socket6")
        self.assertFalse(allowed)
    
    def test_client_banning(self):
        """Test client banning"""
        limiter = ZMQRateLimiter(ban_duration=1)
        
        # Ban a client
        limiter.ban_client("bad_client", "Test ban")
        
        # Check if banned
        self.assertTrue(limiter.is_banned("bad_client"))
        
        # Should not allow connections
        allowed = limiter.check_connection_limit("bad_client", "socket1")
        self.assertFalse(allowed)
        
        # Wait for ban to expire
        time.sleep(1.1)
        self.assertFalse(limiter.is_banned("bad_client"))
    
    def test_message_rate_limiting(self):
        """Test message rate limiting"""
        limiter = ZMQRateLimiter(message_rate_limit=5)
        
        # Send 5 messages
        for i in range(5):
            allowed, _ = limiter.check_message_rate("client1")
            self.assertTrue(allowed)
        
        # 6th message blocked
        allowed, _ = limiter.check_message_rate("client1")
        self.assertFalse(allowed)
    
    def test_pattern_detection(self):
        """Test suspicious pattern detection"""
        limiter = ZMQRateLimiter(message_rate_limit=10)
        
        # Simulate burst of messages
        for i in range(25):
            limiter.check_message_rate("suspicious_client")
        
        # Should detect pattern and ban
        self.assertTrue(limiter.is_banned("suspicious_client"))


class TestZMQSubscriberLimiter(unittest.TestCase):
    """Test subscriber rate limiting"""
    
    def test_topic_limits(self):
        """Test topic subscription limits"""
        limiter = ZMQSubscriberRateLimiter(topics_per_client=3)
        
        # Subscribe to 3 topics
        for i in range(3):
            allowed = limiter.subscribe("client1", f"topic{i}")
            self.assertTrue(allowed)
        
        # 4th topic should fail
        allowed = limiter.subscribe("client1", "topic4")
        self.assertFalse(allowed)
    
    def test_publish_rate_limiting(self):
        """Test publish rate limiting"""
        limiter = ZMQSubscriberRateLimiter(messages_per_topic=5)
        
        # Subscribe to topic
        limiter.subscribe("client1", "test_topic")
        
        # Publish 5 messages
        for i in range(5):
            allowed, _ = limiter.check_publish("test_topic")
            self.assertTrue(allowed)
        
        # 6th publish blocked
        allowed, _ = limiter.check_publish("test_topic")
        self.assertFalse(allowed)


class TestRateLimitIntegration(unittest.TestCase):
    """Integration tests for rate limiting"""
    
    def test_temporary_blocking(self):
        """Test temporary blocking functionality"""
        limiter = RateLimiter(TokenBucket(10, 10, 60))
        
        # Block temporarily
        limiter.block_temporarily("bad_actor", 2)
        
        # Should be blocked
        allowed, metadata = limiter.check_rate_limit("bad_actor")
        self.assertFalse(allowed)
        self.assertIn('blocked', metadata)
        
        # Wait for unblock
        time.sleep(2.1)
        
        # Should be allowed now
        allowed, _ = limiter.check_rate_limit("bad_actor")
        self.assertTrue(allowed)
    
    def test_reset_functionality(self):
        """Test rate limit reset"""
        limiter = RateLimiter(TokenBucket(5, 5, 60))
        
        # Use all tokens
        for _ in range(5):
            limiter.check_rate_limit("user1")
        
        # Should be blocked
        allowed, _ = limiter.check_rate_limit("user1")
        self.assertFalse(allowed)
        
        # Reset
        limiter.reset("user1")
        
        # Should have tokens again
        allowed, metadata = limiter.check_rate_limit("user1")
        self.assertTrue(allowed)
        self.assertEqual(metadata['remaining'], 4)
    
    def test_concurrent_access(self):
        """Test thread safety"""
        limiter = RateLimiter(TokenBucket(100, 100, 1))
        results = []
        
        def make_requests():
            for _ in range(20):
                allowed, _ = limiter.check_rate_limit("shared_user")
                results.append(allowed)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=make_requests)
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should have exactly 100 allowed requests
        allowed_count = sum(1 for r in results if r)
        self.assertEqual(allowed_count, 100)


class TestGeoRateLimiter(unittest.TestCase):
    """Test geographic rate limiting"""
    
    def test_default_limits(self):
        """Test default geo limits"""
        limiter = GeoRateLimiter()
        
        # Test with unknown IP (should use default)
        allowed, metadata = limiter.check_limit("1.2.3.4")
        self.assertTrue(allowed)
        self.assertEqual(metadata['country'], 'default')
    
    @patch('geoip2.database.Reader')
    def test_country_specific_limits(self, mock_reader):
        """Test country-specific limits"""
        # Mock GeoIP response
        mock_response = Mock()
        mock_response.country.iso_code = 'US'
        mock_reader.return_value.country.return_value = mock_response
        
        limiter = GeoRateLimiter(geoip_db_path='mock.mmdb')
        
        # Should identify as US
        allowed, metadata = limiter.check_limit("8.8.8.8")
        self.assertTrue(allowed)
        self.assertEqual(metadata['country'], 'US')


class TestAPIEndpoints(unittest.TestCase):
    """Test rate limited API endpoints"""
    
    @classmethod
    def setUpClass(cls):
        """Start test API server"""
        # This would normally start the Flask app in test mode
        pass
    
    def test_health_endpoint_no_limit(self):
        """Test that health endpoint has no rate limit"""
        # Would make multiple requests to /health
        # and verify all succeed
        pass
    
    def test_api_rate_limiting(self):
        """Test API endpoint rate limiting"""
        # Would make requests exceeding rate limit
        # and verify 429 response with proper headers
        pass
    
    def test_api_key_authentication(self):
        """Test API key authentication"""
        # Would test endpoints requiring API keys
        pass


class TestPerformance(unittest.TestCase):
    """Performance tests for rate limiters"""
    
    def test_token_bucket_performance(self):
        """Test token bucket performance"""
        limiter = RateLimiter(TokenBucket(10000, 10000, 1))
        
        start = time.time()
        for i in range(10000):
            limiter.check_rate_limit(f"user{i % 100}")
        elapsed = time.time() - start
        
        # Should handle 10k checks in under 1 second
        self.assertLess(elapsed, 1.0)
        ops_per_sec = 10000 / elapsed
        print(f"Token bucket: {ops_per_sec:.0f} ops/sec")
    
    def test_sliding_window_performance(self):
        """Test sliding window performance"""
        limiter = RateLimiter(SlidingWindowLog(60, 1000))
        
        start = time.time()
        for i in range(10000):
            limiter.check_rate_limit(f"user{i % 100}")
        elapsed = time.time() - start
        
        # Should handle 10k checks in under 2 seconds
        self.assertLess(elapsed, 2.0)
        ops_per_sec = 10000 / elapsed
        print(f"Sliding window: {ops_per_sec:.0f} ops/sec")


if __name__ == '__main__':
    unittest.main(verbosity=2)