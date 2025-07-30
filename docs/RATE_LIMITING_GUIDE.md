# Rate Limiting Guide for MT4 Docker ZeroMQ

## Overview

This guide covers the comprehensive rate limiting implementation for the MT4 Docker ZeroMQ system, protecting APIs and ZeroMQ endpoints from abuse and ensuring fair resource allocation.

## Architecture

### Components

1. **Application-Level Rate Limiting**
   - Token Bucket Algorithm
   - Sliding Window Log Algorithm
   - Redis-based Distributed Rate Limiting

2. **API Gateway Rate Limiting**
   - Nginx rate limiting
   - Geographic-based limits
   - API key tier system

3. **ZeroMQ Rate Limiting**
   - Connection limits
   - Message rate limits
   - Topic subscription limits

## Rate Limiting Strategies

### 1. Token Bucket Algorithm

Used for: API endpoints with burst allowance

```python
# Configuration
capacity = 100      # Maximum tokens
refill_rate = 10    # Tokens added per second
refill_period = 1   # Refill interval in seconds
```

**Characteristics:**
- Allows burst traffic up to capacity
- Smooth rate limiting over time
- Memory efficient

### 2. Sliding Window Log

Used for: Strict rate enforcement

```python
# Configuration
window_size = 60    # Window in seconds
max_requests = 100  # Maximum requests in window
```

**Characteristics:**
- Precise request counting
- No burst allowance beyond limit
- Higher memory usage

### 3. Redis Distributed Rate Limiting

Used for: Multi-instance deployments

```python
# Configuration
window_size = 60    # Window in seconds
max_requests = 1000 # Maximum requests in window
```

**Characteristics:**
- Shared state across instances
- Atomic operations
- Scales horizontally

## API Rate Limits

### Public Endpoints

| Endpoint | Rate Limit | Burst | Cache |
|----------|------------|-------|-------|
| `/health` | Unlimited | - | No |
| `/api/v1/market/tick/<symbol>` | 10 req/s | 20 | 1s |
| `/api/v1/market/ticks` | 1 req/s | 5 | No |

### Authenticated Endpoints

| Tier | Hourly Limit | Daily Limit | Burst |
|------|--------------|-------------|-------|
| Free | 100 | 1,000 | 10 |
| Basic | 1,000 | 10,000 | 100 |
| Premium | 10,000 | 100,000 | 1,000 |
| Enterprise | 100,000 | Unlimited | 10,000 |

## Configuration

### 1. Environment Variables

```bash
# .env
REDIS_HOST=localhost
REDIS_PORT=6379
RATE_LIMIT_WINDOW=60
RATE_LIMIT_MAX_REQUESTS=100
API_RATE_LIMIT_ENABLED=true
```

### 2. Nginx Configuration

```nginx
# Rate limit zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $http_x_api_key zone=apikey_limit:10m rate=100r/s;

# Apply rate limits
location /api/v1 {
    limit_req zone=api_limit burst=20 nodelay;
    # ... proxy configuration
}
```

### 3. API Key Management

```python
# Create API key
curl -X POST http://localhost:5000/api/v1/admin/api-keys \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tier": "premium"}'

# Response
{
  "api_key": "xPZ2K8L9mN4vQ7R3sT6Y...",
  "tier": "premium",
  "created_at": "2024-01-20T10:30:00Z"
}
```

## Implementation Examples

### 1. Python Client with Rate Limit Handling

```python
import requests
import time
from typing import Dict, Any

class RateLimitedClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'X-API-Key': api_key})
    
    def get_tick(self, symbol: str) -> Dict[str, Any]:
        """Get tick with automatic retry on rate limit"""
        url = f"{self.base_url}/api/v1/market/tick/{symbol}"
        
        while True:
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                # Rate limited - wait and retry
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
            
            else:
                response.raise_for_status()
    
    def get_remaining_quota(self) -> Dict[str, Any]:
        """Check remaining API quota"""
        response = self.session.get(f"{self.base_url}/api/v1/account/usage")
        return response.json()

# Usage
client = RateLimitedClient("your_api_key", "http://localhost")
tick = client.get_tick("EURUSD")
quota = client.get_remaining_quota()
print(f"Daily remaining: {quota['daily_remaining']}")
```

### 2. ZeroMQ Client with Rate Limiting

```python
import zmq
import time
import json
from collections import deque

class RateLimitedZMQClient:
    def __init__(self, address: str, max_rate: int = 100):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(address)
        self.socket.subscribe(b"")
        
        self.max_rate = max_rate
        self.timestamps = deque(maxlen=max_rate)
    
    def receive_message(self) -> Dict[str, Any]:
        """Receive message with rate limiting"""
        # Check rate limit
        now = time.time()
        if len(self.timestamps) == self.max_rate:
            oldest = self.timestamps[0]
            if now - oldest < 1.0:
                # Wait to maintain rate
                sleep_time = 1.0 - (now - oldest)
                time.sleep(sleep_time)
        
        # Receive message
        topic, message = self.socket.recv_multipart()
        self.timestamps.append(time.time())
        
        return {
            'topic': topic.decode(),
            'data': json.loads(message.decode())
        }

# Usage
client = RateLimitedZMQClient("tcp://localhost:5556", max_rate=50)
while True:
    msg = client.receive_message()
    print(f"Received: {msg['topic']} - {msg['data']}")
```

### 3. JavaScript/Node.js Client

```javascript
const axios = require('axios');

class RateLimitedAPIClient {
    constructor(apiKey, baseURL) {
        this.apiKey = apiKey;
        this.baseURL = baseURL;
        this.rateLimitInfo = {
            remaining: null,
            reset: null
        };
    }
    
    async request(method, path, data = null) {
        const config = {
            method,
            url: `${this.baseURL}${path}`,
            headers: {
                'X-API-Key': this.apiKey
            }
        };
        
        if (data) {
            config.data = data;
        }
        
        try {
            const response = await axios(config);
            
            // Update rate limit info
            this.rateLimitInfo.remaining = 
                parseInt(response.headers['x-ratelimit-remaining']);
            this.rateLimitInfo.reset = 
                parseInt(response.headers['x-ratelimit-reset']);
            
            return response.data;
            
        } catch (error) {
            if (error.response && error.response.status === 429) {
                // Rate limited - wait and retry
                const retryAfter = 
                    parseInt(error.response.headers['retry-after']) || 60;
                
                console.log(`Rate limited. Waiting ${retryAfter}s...`);
                await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
                
                // Retry request
                return this.request(method, path, data);
            }
            
            throw error;
        }
    }
    
    async getTick(symbol) {
        return this.request('GET', `/api/v1/market/tick/${symbol}`);
    }
    
    getRateLimitInfo() {
        return this.rateLimitInfo;
    }
}

// Usage
const client = new RateLimitedAPIClient('your_api_key', 'http://localhost');

async function main() {
    try {
        const tick = await client.getTick('EURUSD');
        console.log('Tick:', tick);
        console.log('Rate limit:', client.getRateLimitInfo());
    } catch (error) {
        console.error('Error:', error.message);
    }
}

main();
```

## Monitoring

### 1. Prometheus Metrics

Available at `http://localhost:9091/metrics`:

```
# Total requests by endpoint and status
rate_limit_requests_total{endpoint="/api/v1/market/tick",status="allowed"} 12543
rate_limit_requests_total{endpoint="/api/v1/market/tick",status="blocked"} 156

# Active rate limit keys
rate_limit_active_keys{key_type="ip"} 42
rate_limit_active_keys{key_type="api_key"} 15

# API key usage by tier
api_key_usage{tier="free",key_hash="a1b2c3d4"} 850
api_key_usage{tier="premium",key_hash="e5f6g7h8"} 5420
```

### 2. Grafana Dashboard

Import the provided dashboard for visualization:
- Request rates by endpoint
- Rate limit violations
- API key usage by tier
- Geographic distribution
- Response time histograms

### 3. Alerts

```yaml
# Prometheus alert rules
groups:
  - name: rate_limit_alerts
    rules:
      - alert: HighRateLimitViolations
        expr: rate(rate_limit_blocked_requests_total[5m]) > 10
        for: 5m
        annotations:
          summary: High rate of blocked requests
          
      - alert: APIKeyQuotaExhausted
        expr: api_key_usage / api_key_limit > 0.9
        for: 10m
        annotations:
          summary: API key approaching quota limit
```

## Best Practices

### 1. Client Implementation

- **Respect Rate Limits**: Always check headers and implement backoff
- **Use Caching**: Cache responses when appropriate
- **Batch Requests**: Use bulk endpoints when available
- **Monitor Usage**: Track your API usage to avoid surprises

### 2. Server Configuration

- **Set Reasonable Limits**: Balance between protection and usability
- **Use Multiple Strategies**: Combine algorithms for better protection
- **Monitor and Adjust**: Regularly review limits based on usage patterns
- **Provide Clear Feedback**: Return informative rate limit headers

### 3. Security Considerations

- **Protect API Keys**: Never expose keys in client-side code
- **Use HTTPS**: Always use encrypted connections
- **Implement IP Whitelisting**: For admin endpoints
- **Regular Key Rotation**: Rotate API keys periodically

## Troubleshooting

### Common Issues

1. **"429 Too Many Requests" Error**
   - Check rate limit headers
   - Implement exponential backoff
   - Consider upgrading tier

2. **Redis Connection Errors**
   - Verify Redis is running
   - Check network connectivity
   - Review Redis memory usage

3. **Inconsistent Rate Limiting**
   - Ensure time synchronization
   - Check for multiple instances
   - Verify Redis persistence

### Debug Mode

Enable debug logging:

```python
# In rate_limited_api.py
import logging
logging.basicConfig(level=logging.DEBUG)

# In nginx
error_log /var/log/nginx/error.log debug;
```

## Performance Tuning

### 1. Redis Optimization

```bash
# redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
save ""  # Disable persistence for better performance
```

### 2. Nginx Optimization

```nginx
# Increase rate limit cache
limit_req_zone $binary_remote_addr zone=api_limit:50m rate=10r/s;

# Use keepalive connections
upstream api_backend {
    server localhost:5000;
    keepalive 32;
}
```

### 3. Application Optimization

```python
# Use connection pooling
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50
)
redis_client = redis.Redis(connection_pool=redis_pool)
```

## API Reference

### Rate Limit Headers

| Header | Description | Example |
|--------|-------------|---------|
| X-RateLimit-Limit | Request limit | 100 |
| X-RateLimit-Remaining | Remaining requests | 75 |
| X-RateLimit-Reset | Reset timestamp | 1642684800 |
| Retry-After | Seconds to wait | 60 |

### Error Responses

```json
// 429 Too Many Requests
{
  "error": "Rate limit exceeded",
  "retry_after": 60,
  "message": "Too many requests. Please retry later."
}

// 401 Unauthorized (missing API key)
{
  "error": "API key required"
}
```

## Conclusion

The rate limiting system provides comprehensive protection while maintaining good user experience. Regular monitoring and adjustment of limits ensure optimal performance and fair resource allocation.