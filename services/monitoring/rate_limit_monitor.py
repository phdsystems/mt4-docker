#!/usr/bin/env python3
"""
Rate Limit Monitoring Service
Exports metrics to Prometheus
"""

import os
import time
import redis
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Info
import schedule
import threading


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
PROMETHEUS_PORT = int(os.environ.get('PROMETHEUS_PORT', 9091))

# Prometheus metrics
rate_limit_requests = Counter(
    'rate_limit_requests_total',
    'Total rate limit requests',
    ['endpoint', 'status']
)

rate_limit_active_keys = Gauge(
    'rate_limit_active_keys',
    'Number of active rate limit keys',
    ['key_type']
)

rate_limit_blocked_requests = Counter(
    'rate_limit_blocked_requests_total',
    'Total blocked requests',
    ['reason']
)

api_key_usage = Gauge(
    'api_key_usage',
    'API key usage by tier',
    ['tier', 'key_hash']
)

rate_limit_response_time = Histogram(
    'rate_limit_check_duration_seconds',
    'Time to check rate limit',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

redis_connection_status = Gauge(
    'redis_connection_status',
    'Redis connection status (1=connected, 0=disconnected)'
)

rate_limit_info = Info(
    'rate_limit_config',
    'Rate limiting configuration'
)

# Set configuration info
rate_limit_info.info({
    'redis_host': REDIS_HOST,
    'redis_port': str(REDIS_PORT),
    'monitoring_interval': '60s'
})


class RateLimitMonitor:
    """Monitor rate limiting metrics"""
    
    def __init__(self):
        """Initialize monitor"""
        self.redis_client = None
        self.connect_redis()
        self.stats = defaultdict(lambda: defaultdict(int))
    
    def connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True
            )
            self.redis_client.ping()
            redis_connection_status.set(1)
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            redis_connection_status.set(0)
            logger.error(f"Failed to connect to Redis: {e}")
    
    def collect_metrics(self):
        """Collect metrics from Redis"""
        if not self.redis_client:
            self.connect_redis()
            if not self.redis_client:
                return
        
        try:
            # Count active rate limit keys
            ip_keys = len(self.redis_client.keys("rate_limit:ip:*"))
            api_keys = len(self.redis_client.keys("rate_limit:api_key:*"))
            
            rate_limit_active_keys.labels(key_type="ip").set(ip_keys)
            rate_limit_active_keys.labels(key_type="api_key").set(api_keys)
            
            # Collect API key usage
            for key in self.redis_client.keys("api_usage:*"):
                try:
                    tier = key.split(":")[1]
                    key_hash = key.split(":")[2]
                    usage = int(self.redis_client.get(key) or 0)
                    api_key_usage.labels(tier=tier, key_hash=key_hash[:8]).set(usage)
                except:
                    pass
            
            # Collect request statistics
            request_stats = self.redis_client.hgetall("rate_limit:stats")
            for stat_key, value in request_stats.items():
                try:
                    endpoint, status = stat_key.split(":")
                    count = int(value)
                    rate_limit_requests.labels(
                        endpoint=endpoint,
                        status=status
                    )._value.set(count)
                except:
                    pass
            
            redis_connection_status.set(1)
            
        except Exception as e:
            redis_connection_status.set(0)
            logger.error(f"Error collecting metrics: {e}")
    
    def analyze_patterns(self):
        """Analyze rate limiting patterns"""
        try:
            # Get all rate limit keys
            keys = self.redis_client.keys("rate_limit:*")
            
            suspicious_ips = []
            for key in keys:
                if ":ip:" in key:
                    # Check for suspicious patterns
                    score = self.redis_client.zscore(key, "requests")
                    if score and score > 1000:  # High request count
                        ip = key.split(":")[-1]
                        suspicious_ips.append(ip)
            
            if suspicious_ips:
                logger.warning(f"Suspicious IPs detected: {suspicious_ips}")
                
                # Log to Redis for other services
                self.redis_client.setex(
                    "suspicious_ips",
                    300,  # 5 minute expiry
                    json.dumps(suspicious_ips)
                )
        
        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
    
    def cleanup_old_data(self):
        """Clean up old rate limit data"""
        try:
            # Clean up old keys
            cutoff = time.time() - 3600  # 1 hour ago
            
            for key in self.redis_client.keys("rate_limit:*"):
                try:
                    # Remove old entries from sorted sets
                    if self.redis_client.type(key) == 'zset':
                        self.redis_client.zremrangebyscore(key, 0, cutoff)
                        
                        # Delete empty sets
                        if self.redis_client.zcard(key) == 0:
                            self.redis_client.delete(key)
                except:
                    pass
            
            logger.info("Cleaned up old rate limit data")
            
        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")
    
    def generate_report(self):
        """Generate rate limit report"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'active_ips': self.redis_client.scard("active_ips"),
                'blocked_ips': self.redis_client.scard("blocked_ips"),
                'total_requests': sum(
                    int(v) for v in self.redis_client.hvals("rate_limit:stats").values()
                ),
                'top_endpoints': [],
                'top_ips': []
            }
            
            # Get top endpoints
            endpoint_stats = defaultdict(int)
            for key, value in self.redis_client.hgetall("rate_limit:stats").items():
                if ":allowed" in key:
                    endpoint = key.split(":")[0]
                    endpoint_stats[endpoint] += int(value)
            
            report['top_endpoints'] = sorted(
                endpoint_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Save report
            self.redis_client.setex(
                f"rate_limit:report:{datetime.now().strftime('%Y%m%d_%H')}",
                86400,  # 24 hour expiry
                json.dumps(report)
            )
            
            logger.info(f"Generated rate limit report: {report}")
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")


def run_monitoring():
    """Run monitoring loop"""
    monitor = RateLimitMonitor()
    
    # Schedule tasks
    schedule.every(10).seconds.do(monitor.collect_metrics)
    schedule.every(5).minutes.do(monitor.analyze_patterns)
    schedule.every(30).minutes.do(monitor.cleanup_old_data)
    schedule.every(1).hours.do(monitor.generate_report)
    
    # Initial collection
    monitor.collect_metrics()
    
    while True:
        schedule.run_pending()
        time.sleep(1)


def simulate_traffic():
    """Simulate traffic for testing"""
    if not os.environ.get('SIMULATE_TRAFFIC'):
        return
    
    logger.info("Starting traffic simulation...")
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        
        endpoints = ['/api/v1/market/tick', '/api/v1/market/ticks', '/api/v1/account/usage']
        statuses = ['allowed', 'blocked']
        
        while True:
            # Simulate requests
            for endpoint in endpoints:
                for status in statuses:
                    key = f"{endpoint}:{status}"
                    r.hincrby("rate_limit:stats", key, 1)
            
            # Simulate active IPs
            for i in range(10):
                r.zadd(f"rate_limit:ip:192.168.1.{i}", {"requests": i * 10})
            
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"Simulation error: {e}")


if __name__ == "__main__":
    # Start Prometheus HTTP server
    start_http_server(PROMETHEUS_PORT)
    logger.info(f"Prometheus metrics available at http://localhost:{PROMETHEUS_PORT}/metrics")
    
    # Start traffic simulation in background if enabled
    if os.environ.get('SIMULATE_TRAFFIC'):
        sim_thread = threading.Thread(target=simulate_traffic, daemon=True)
        sim_thread.start()
    
    # Run monitoring
    run_monitoring()