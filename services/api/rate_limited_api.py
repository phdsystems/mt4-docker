#!/usr/bin/env python3
"""
Rate Limited REST API for MT4 Market Data
Provides HTTP API with comprehensive rate limiting
"""

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import zmq
import json
import time
import redis
import hashlib
import secrets
from functools import wraps
from datetime import datetime, timedelta
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.rate_limiter.rate_limiter import (
    RateLimiter, TokenBucket, SlidingWindowLog, 
    RedisRateLimiter, APIKeyRateLimiter, RateLimitMiddleware
)


app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiters
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    RATE_LIMITER = RateLimiter(RedisRateLimiter(redis_client, window_size=60, max_requests=100))
    logger.info("Using Redis rate limiter")
except:
    RATE_LIMITER = RateLimiter(SlidingWindowLog(window_size=60, max_requests=100))
    logger.info("Using in-memory rate limiter")

# API Key rate limiter
API_KEY_LIMITER = APIKeyRateLimiter()

# ZeroMQ context
zmq_context = zmq.Context()

# Market data cache
MARKET_DATA_CACHE = {}
CACHE_EXPIRY = 1  # seconds


def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr


def rate_limit(key_type='ip'):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get identifier
            if key_type == 'ip':
                identifier = get_client_ip()
            elif key_type == 'api_key':
                api_key = request.headers.get('X-API-Key')
                if not api_key:
                    return jsonify({'error': 'API key required'}), 401
                identifier = api_key
            else:
                identifier = 'global'
            
            # Check rate limit
            if key_type == 'api_key':
                allowed, metadata = API_KEY_LIMITER.check_limit(identifier)
            else:
                allowed, metadata = RATE_LIMITER.check_rate_limit(identifier, key_type)
            
            # Add rate limit headers
            response = make_response()
            response.headers['X-RateLimit-Limit'] = str(metadata.get('X-RateLimit-Limit', 0))
            response.headers['X-RateLimit-Remaining'] = str(metadata.get('X-RateLimit-Remaining', 0))
            
            if 'X-RateLimit-Reset' in metadata:
                response.headers['X-RateLimit-Reset'] = str(metadata['X-RateLimit-Reset'])
            
            if not allowed:
                response.headers['Retry-After'] = str(metadata.get('Retry-After', 60))
                response.data = json.dumps({
                    'error': 'Rate limit exceeded',
                    'retry_after': metadata.get('Retry-After', 60)
                })
                response.status_code = 429
                return response
            
            # Call the actual function
            result = f(*args, **kwargs)
            
            # If result is already a response, merge headers
            if isinstance(result, tuple):
                data, status = result
                response.data = json.dumps(data) if isinstance(data, dict) else data
                response.status_code = status
            else:
                response = result
                for header, value in metadata.items():
                    if header.startswith('X-RateLimit'):
                        response.headers[header] = str(value)
            
            return response
        
        return wrapper
    return decorator


def require_api_key(f):
    """Require API key authentication"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Verify API key exists
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if key_hash not in API_KEY_LIMITER.api_key_tiers:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    
    return wrapper


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint (no rate limit)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })


@app.route('/api/v1/market/tick/<symbol>', methods=['GET'])
@rate_limit('ip')
def get_tick(symbol):
    """Get latest tick for symbol"""
    # Check cache
    cache_key = f"tick:{symbol}"
    if cache_key in MARKET_DATA_CACHE:
        cached_data, cached_time = MARKET_DATA_CACHE[cache_key]
        if time.time() - cached_time < CACHE_EXPIRY:
            return jsonify(cached_data)
    
    # Connect to ZeroMQ
    try:
        socket = zmq_context.socket(zmq.SUB)
        socket.connect("tcp://localhost:5556")
        socket.subscribe(f"tick.{symbol}".encode())
        socket.setsockopt(zmq.RCVTIMEO, 1000)
        
        # Get latest tick
        topic, message = socket.recv_multipart()
        data = json.loads(message.decode())
        
        # Cache the data
        MARKET_DATA_CACHE[cache_key] = (data, time.time())
        
        socket.close()
        return jsonify(data)
        
    except zmq.Again:
        return jsonify({'error': f'No data available for {symbol}'}), 404
    except Exception as e:
        logger.error(f"Error getting tick: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/v1/market/ticks', methods=['GET'])
@rate_limit('ip')
def get_multiple_ticks():
    """Get ticks for multiple symbols"""
    symbols = request.args.get('symbols', '').split(',')
    if not symbols or len(symbols) > 10:
        return jsonify({'error': 'Invalid symbols parameter (max 10)'}), 400
    
    result = {}
    
    for symbol in symbols:
        symbol = symbol.strip().upper()
        cache_key = f"tick:{symbol}"
        
        # Try cache first
        if cache_key in MARKET_DATA_CACHE:
            cached_data, cached_time = MARKET_DATA_CACHE[cache_key]
            if time.time() - cached_time < CACHE_EXPIRY:
                result[symbol] = cached_data
                continue
        
        # Get from ZeroMQ
        try:
            socket = zmq_context.socket(zmq.SUB)
            socket.connect("tcp://localhost:5556")
            socket.subscribe(f"tick.{symbol}".encode())
            socket.setsockopt(zmq.RCVTIMEO, 100)
            
            topic, message = socket.recv_multipart()
            data = json.loads(message.decode())
            
            result[symbol] = data
            MARKET_DATA_CACHE[cache_key] = (data, time.time())
            
            socket.close()
        except:
            result[symbol] = None
    
    return jsonify(result)


@app.route('/api/v1/market/stream/<symbol>', methods=['GET'])
@require_api_key
@rate_limit('api_key')
def stream_market_data(symbol):
    """Stream market data (requires API key)"""
    def generate():
        socket = zmq_context.socket(zmq.SUB)
        socket.connect("tcp://localhost:5556")
        socket.subscribe(f"tick.{symbol}".encode())
        socket.setsockopt(zmq.RCVTIMEO, 1000)
        
        try:
            while True:
                try:
                    topic, message = socket.recv_multipart()
                    data = json.loads(message.decode())
                    yield f"data: {json.dumps(data)}\n\n"
                except zmq.Again:
                    yield f"data: {json.dumps({'keepalive': True})}\n\n"
                
        finally:
            socket.close()
    
    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/v1/account/usage', methods=['GET'])
@require_api_key
def get_usage():
    """Get API usage statistics"""
    api_key = request.headers.get('X-API-Key')
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Get tier info
    tier = API_KEY_LIMITER.api_key_tiers.get(key_hash, 'free')
    tier_config = API_KEY_LIMITER.tiers[tier]
    
    # Get usage stats
    today = datetime.now().strftime('%Y-%m-%d')
    daily_usage = API_KEY_LIMITER.daily_usage[today].get(key_hash, 0)
    
    return jsonify({
        'tier': tier,
        'daily_limit': tier_config['daily_limit'],
        'daily_usage': daily_usage,
        'daily_remaining': (tier_config['daily_limit'] or float('inf')) - daily_usage,
        'reset_time': (datetime.now() + timedelta(days=1)).replace(
            hour=0, minute=0, second=0
        ).isoformat()
    })


@app.route('/api/v1/admin/api-keys', methods=['POST'])
@rate_limit('ip')
def create_api_key():
    """Create new API key (admin endpoint)"""
    # In production, this would require admin authentication
    admin_token = request.headers.get('X-Admin-Token')
    if admin_token != os.environ.get('ADMIN_TOKEN', 'secret_admin_token'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    tier = data.get('tier', 'free')
    
    if tier not in API_KEY_LIMITER.tiers:
        return jsonify({'error': 'Invalid tier'}), 400
    
    # Generate API key
    api_key = secrets.token_urlsafe(32)
    
    # Register with rate limiter
    API_KEY_LIMITER.register_api_key(api_key, tier)
    
    return jsonify({
        'api_key': api_key,
        'tier': tier,
        'created_at': datetime.now().isoformat()
    })


@app.route('/api/v1/admin/rate-limit/status', methods=['GET'])
@rate_limit('ip')
def rate_limit_status():
    """Get rate limiting status (admin endpoint)"""
    admin_token = request.headers.get('X-Admin-Token')
    if admin_token != os.environ.get('ADMIN_TOKEN', 'secret_admin_token'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get current status
    status = {
        'active_limiters': {
            'ip': len(RATE_LIMITER.strategy.requests) if hasattr(RATE_LIMITER.strategy, 'requests') else 0,
            'api_keys': len(API_KEY_LIMITER.api_key_tiers)
        },
        'blocked_clients': len(RATE_LIMITER.blocked_keys),
        'cache_size': len(MARKET_DATA_CACHE)
    }
    
    return jsonify(status)


@app.route('/api/v1/admin/rate-limit/reset/<identifier>', methods=['POST'])
@rate_limit('ip')
def reset_rate_limit(identifier):
    """Reset rate limit for specific identifier"""
    admin_token = request.headers.get('X-Admin-Token')
    if admin_token != os.environ.get('ADMIN_TOKEN', 'secret_admin_token'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    key_type = request.json.get('key_type', 'ip')
    RATE_LIMITER.reset(identifier, key_type)
    
    return jsonify({
        'message': f'Rate limit reset for {identifier}',
        'key_type': key_type
    })


@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Handle rate limit errors"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please retry later.'
    }), 429


@app.errorhandler(500)
def internal_error(e):
    """Handle internal errors"""
    logger.error(f"Internal error: {e}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


# CLI for testing
def create_test_api_keys():
    """Create test API keys for different tiers"""
    test_keys = {
        'free': 'test_free_' + secrets.token_urlsafe(16),
        'basic': 'test_basic_' + secrets.token_urlsafe(16),
        'premium': 'test_premium_' + secrets.token_urlsafe(16),
        'enterprise': 'test_enterprise_' + secrets.token_urlsafe(16)
    }
    
    for tier, key in test_keys.items():
        API_KEY_LIMITER.register_api_key(key, tier)
        print(f"{tier.capitalize()} API Key: {key}")
    
    return test_keys


if __name__ == '__main__':
    print("=== MT4 Rate Limited API ===")
    print("\nCreating test API keys...")
    test_keys = create_test_api_keys()
    
    print("\nEndpoints:")
    print("  GET  /health - Health check (no rate limit)")
    print("  GET  /api/v1/market/tick/<symbol> - Get latest tick")
    print("  GET  /api/v1/market/ticks?symbols=EURUSD,GBPUSD - Get multiple ticks")
    print("  GET  /api/v1/market/stream/<symbol> - Stream data (requires API key)")
    print("  GET  /api/v1/account/usage - Get API usage (requires API key)")
    print("\nAdmin endpoints:")
    print("  POST /api/v1/admin/api-keys - Create API key")
    print("  GET  /api/v1/admin/rate-limit/status - Get rate limit status")
    print("  POST /api/v1/admin/rate-limit/reset/<id> - Reset rate limit")
    
    print(f"\nAdmin token: {os.environ.get('ADMIN_TOKEN', 'secret_admin_token')}")
    print("\nStarting server on http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)