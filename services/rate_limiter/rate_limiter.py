#!/usr/bin/env python3
"""
Rate Limiter for API Protection
Implements token bucket and sliding window algorithms
"""

import time
import threading
import redis
import json
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import hashlib
import logging


class RateLimitStrategy(ABC):
    """Abstract base class for rate limiting strategies"""
    
    @abstractmethod
    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """Check if request is allowed"""
        pass
    
    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        pass


class TokenBucket(RateLimitStrategy):
    """Token bucket algorithm implementation"""
    
    def __init__(self, capacity: int, refill_rate: float, refill_period: float = 1.0):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Number of tokens to add per period
            refill_period: Time period in seconds for refill
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_period = refill_period
        self.buckets: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def _refill_tokens(self, bucket: Dict) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - bucket['last_refill']
        
        # Calculate tokens to add
        tokens_to_add = (elapsed / self.refill_period) * self.refill_rate
        
        # Update bucket
        bucket['tokens'] = min(self.capacity, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = now
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """Check if request is allowed"""
        with self.lock:
            # Get or create bucket
            if key not in self.buckets:
                self.buckets[key] = {
                    'tokens': self.capacity,
                    'last_refill': time.time()
                }
            
            bucket = self.buckets[key]
            
            # Refill tokens
            self._refill_tokens(bucket)
            
            # Check if tokens available
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True, {
                    'remaining': int(bucket['tokens']),
                    'capacity': self.capacity,
                    'refill_rate': self.refill_rate
                }
            
            return False, {
                'remaining': 0,
                'capacity': self.capacity,
                'retry_after': self.refill_period / self.refill_rate
            }
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        with self.lock:
            if key in self.buckets:
                self.buckets[key] = {
                    'tokens': self.capacity,
                    'last_refill': time.time()
                }


class SlidingWindowLog(RateLimitStrategy):
    """Sliding window log algorithm implementation"""
    
    def __init__(self, window_size: int, max_requests: int):
        """
        Initialize sliding window
        
        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests allowed in window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """Check if request is allowed"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_size
            
            # Remove old requests outside window
            while self.requests[key] and self.requests[key][0] < window_start:
                self.requests[key].popleft()
            
            # Check if under limit
            current_count = len(self.requests[key])
            if current_count < self.max_requests:
                self.requests[key].append(now)
                return True, {
                    'remaining': self.max_requests - current_count - 1,
                    'window_size': self.window_size,
                    'max_requests': self.max_requests
                }
            
            # Calculate when oldest request expires
            oldest_request = self.requests[key][0]
            retry_after = oldest_request + self.window_size - now
            
            return False, {
                'remaining': 0,
                'window_size': self.window_size,
                'retry_after': retry_after
            }
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        with self.lock:
            self.requests[key].clear()


class RedisRateLimiter(RateLimitStrategy):
    """Redis-based distributed rate limiter"""
    
    def __init__(self, redis_client: redis.Redis, window_size: int, max_requests: int):
        """
        Initialize Redis rate limiter
        
        Args:
            redis_client: Redis client instance
            window_size: Window size in seconds
            max_requests: Maximum requests allowed in window
        """
        self.redis = redis_client
        self.window_size = window_size
        self.max_requests = max_requests
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict]:
        """Check if request is allowed using Redis"""
        now = time.time()
        window_start = now - self.window_size
        
        # Use Redis sorted set for sliding window
        redis_key = f"rate_limit:{key}"
        
        # Lua script for atomic operation
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        
        -- Remove old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        
        -- Count current requests
        local current_count = redis.call('ZCARD', key)
        
        if current_count < max_requests then
            -- Add new request
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, ARGV[4])
            return {1, max_requests - current_count - 1}
        else
            -- Get oldest request
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            if #oldest > 0 then
                return {0, oldest[2]}
            else
                return {0, 0}
            end
        end
        """
        
        try:
            result = self.redis.eval(
                lua_script,
                1,
                redis_key,
                now,
                window_start,
                self.max_requests,
                self.window_size + 1
            )
            
            if result[0] == 1:
                return True, {
                    'remaining': int(result[1]),
                    'window_size': self.window_size,
                    'max_requests': self.max_requests
                }
            else:
                retry_after = float(result[1]) + self.window_size - now if result[1] else 0
                return False, {
                    'remaining': 0,
                    'window_size': self.window_size,
                    'retry_after': max(0, retry_after)
                }
        except Exception as e:
            # Fallback to allow on Redis error
            logging.error(f"Redis rate limit error: {e}")
            return True, {'error': str(e)}
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        redis_key = f"rate_limit:{key}"
        self.redis.delete(redis_key)


class RateLimiter:
    """Main rate limiter with multiple strategies"""
    
    def __init__(self, strategy: RateLimitStrategy):
        """
        Initialize rate limiter
        
        Args:
            strategy: Rate limiting strategy to use
        """
        self.strategy = strategy
        self.blocked_keys: Dict[str, float] = {}
        self.lock = threading.Lock()
    
    def check_rate_limit(self, 
                        identifier: str, 
                        key_type: str = "ip") -> Tuple[bool, Dict]:
        """
        Check if request is rate limited
        
        Args:
            identifier: Unique identifier (IP, API key, etc.)
            key_type: Type of identifier
            
        Returns:
            Tuple of (allowed, metadata)
        """
        # Create composite key
        key = f"{key_type}:{identifier}"
        
        # Check if temporarily blocked
        with self.lock:
            if key in self.blocked_keys:
                if time.time() < self.blocked_keys[key]:
                    return False, {
                        'blocked': True,
                        'blocked_until': self.blocked_keys[key]
                    }
                else:
                    del self.blocked_keys[key]
        
        # Check rate limit
        allowed, metadata = self.strategy.is_allowed(key)
        
        # Add rate limit headers info
        metadata['X-RateLimit-Limit'] = metadata.get('max_requests', metadata.get('capacity', 0))
        metadata['X-RateLimit-Remaining'] = metadata.get('remaining', 0)
        
        if not allowed and 'retry_after' in metadata:
            metadata['X-RateLimit-Reset'] = int(time.time() + metadata['retry_after'])
            metadata['Retry-After'] = int(metadata['retry_after'])
        
        return allowed, metadata
    
    def block_temporarily(self, identifier: str, duration: int, key_type: str = "ip"):
        """Temporarily block an identifier"""
        key = f"{key_type}:{identifier}"
        with self.lock:
            self.blocked_keys[key] = time.time() + duration
    
    def reset(self, identifier: str, key_type: str = "ip"):
        """Reset rate limit for identifier"""
        key = f"{key_type}:{identifier}"
        
        # Remove from blocked list
        with self.lock:
            if key in self.blocked_keys:
                del self.blocked_keys[key]
        
        # Reset in strategy
        self.strategy.reset(key)


class RateLimitMiddleware:
    """Middleware for web frameworks"""
    
    def __init__(self, rate_limiter: RateLimiter, 
                 identifier_func=None,
                 on_limited_func=None):
        """
        Initialize middleware
        
        Args:
            rate_limiter: RateLimiter instance
            identifier_func: Function to extract identifier from request
            on_limited_func: Function to call when rate limited
        """
        self.rate_limiter = rate_limiter
        self.identifier_func = identifier_func or self._default_identifier
        self.on_limited_func = on_limited_func or self._default_on_limited
    
    def _default_identifier(self, request):
        """Default identifier extraction (IP address)"""
        # Handle X-Forwarded-For
        if 'X-Forwarded-For' in request.headers:
            return request.headers['X-Forwarded-For'].split(',')[0].strip()
        return request.remote_addr
    
    def _default_on_limited(self, request, metadata):
        """Default rate limit response"""
        return {
            'error': 'Rate limit exceeded',
            'retry_after': metadata.get('retry_after', 60)
        }, 429
    
    def process_request(self, request):
        """Process request through rate limiter"""
        identifier = self.identifier_func(request)
        allowed, metadata = self.rate_limiter.check_rate_limit(identifier)
        
        if not allowed:
            return self.on_limited_func(request, metadata)
        
        # Add rate limit headers to response
        request.rate_limit_metadata = metadata
        return None


class APIKeyRateLimiter:
    """Rate limiter for API keys with different tiers"""
    
    def __init__(self):
        """Initialize API key rate limiter"""
        self.tiers = {
            'free': {
                'rate_limiter': RateLimiter(TokenBucket(100, 100, 3600)),  # 100/hour
                'daily_limit': 1000
            },
            'basic': {
                'rate_limiter': RateLimiter(TokenBucket(1000, 1000, 3600)),  # 1000/hour
                'daily_limit': 10000
            },
            'premium': {
                'rate_limiter': RateLimiter(TokenBucket(10000, 10000, 3600)),  # 10000/hour
                'daily_limit': 100000
            },
            'enterprise': {
                'rate_limiter': RateLimiter(TokenBucket(100000, 100000, 3600)),  # 100000/hour
                'daily_limit': None  # Unlimited
            }
        }
        self.daily_usage = defaultdict(lambda: defaultdict(int))
        self.api_key_tiers = {}  # API key -> tier mapping
    
    def register_api_key(self, api_key: str, tier: str):
        """Register an API key with a tier"""
        if tier not in self.tiers:
            raise ValueError(f"Invalid tier: {tier}")
        
        # Hash API key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self.api_key_tiers[key_hash] = tier
    
    def check_limit(self, api_key: str) -> Tuple[bool, Dict]:
        """Check rate limit for API key"""
        # Hash API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Get tier
        tier = self.api_key_tiers.get(key_hash, 'free')
        tier_config = self.tiers[tier]
        
        # Check daily limit
        today = datetime.now().strftime('%Y-%m-%d')
        daily_count = self.daily_usage[today][key_hash]
        
        if tier_config['daily_limit'] and daily_count >= tier_config['daily_limit']:
            return False, {
                'error': 'Daily limit exceeded',
                'tier': tier,
                'daily_limit': tier_config['daily_limit'],
                'reset_time': (datetime.now() + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0
                ).timestamp()
            }
        
        # Check rate limit
        allowed, metadata = tier_config['rate_limiter'].check_rate_limit(key_hash, 'api_key')
        
        if allowed:
            self.daily_usage[today][key_hash] += 1
            metadata['tier'] = tier
            metadata['daily_remaining'] = (tier_config['daily_limit'] or float('inf')) - daily_count - 1
        
        return allowed, metadata


class GeoRateLimiter:
    """Geographic-based rate limiting"""
    
    def __init__(self, geoip_db_path: Optional[str] = None):
        """Initialize geo rate limiter"""
        self.country_limits = {
            'default': RateLimiter(TokenBucket(1000, 100, 60)),
            'US': RateLimiter(TokenBucket(2000, 200, 60)),
            'CN': RateLimiter(TokenBucket(500, 50, 60)),
            'RU': RateLimiter(TokenBucket(500, 50, 60))
        }
        
        # GeoIP database (optional)
        self.geoip = None
        if geoip_db_path:
            try:
                import geoip2.database
                self.geoip = geoip2.database.Reader(geoip_db_path)
            except ImportError:
                logging.warning("geoip2 not installed, using default limits")
    
    def get_country(self, ip_address: str) -> str:
        """Get country from IP address"""
        if not self.geoip:
            return 'default'
        
        try:
            response = self.geoip.country(ip_address)
            return response.country.iso_code
        except:
            return 'default'
    
    def check_limit(self, ip_address: str) -> Tuple[bool, Dict]:
        """Check rate limit based on geographic location"""
        country = self.get_country(ip_address)
        rate_limiter = self.country_limits.get(country, self.country_limits['default'])
        
        allowed, metadata = rate_limiter.check_rate_limit(ip_address)
        metadata['country'] = country
        
        return allowed, metadata


# Example usage and testing
if __name__ == "__main__":
    # Test token bucket
    print("=== Token Bucket Test ===")
    bucket_limiter = RateLimiter(TokenBucket(capacity=10, refill_rate=1, refill_period=1))
    
    # Simulate requests
    for i in range(15):
        allowed, metadata = bucket_limiter.check_rate_limit("127.0.0.1")
        print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'} - {metadata}")
        if i == 10:
            time.sleep(5)  # Wait for refill
    
    print("\n=== Sliding Window Test ===")
    window_limiter = RateLimiter(SlidingWindowLog(window_size=10, max_requests=5))
    
    # Simulate burst
    for i in range(10):
        allowed, metadata = window_limiter.check_rate_limit("192.168.1.1")
        print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'} - {metadata}")
        time.sleep(1)
    
    print("\n=== API Key Tier Test ===")
    api_limiter = APIKeyRateLimiter()
    api_limiter.register_api_key("test_free_key", "free")
    api_limiter.register_api_key("test_premium_key", "premium")
    
    # Test different tiers
    for key, name in [("test_free_key", "Free"), ("test_premium_key", "Premium")]:
        print(f"\n{name} tier:")
        for i in range(5):
            allowed, metadata = api_limiter.check_limit(key)
            print(f"  Request {i+1}: {'Allowed' if allowed else 'Blocked'} - Daily remaining: {metadata.get('daily_remaining', 'N/A')}")