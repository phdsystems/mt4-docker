#!/usr/bin/env python3
"""
ZeroMQ Bridge with ELK Logging Integration
Enhanced version with centralized logging and monitoring
"""

import sys
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.zeromq_bridge.zmq_bridge_oop import (
    MarketDataBridge, IPublisher, IDataSource, MarketTick, MarketBar
)
from services.logging.elk_logger import (
    LoggerFactory, ELKLogger, PerformanceLogger, log_function_call
)


class ELKMarketDataBridge(MarketDataBridge):
    """Enhanced bridge with ELK logging"""
    
    def __init__(self,
                 publisher: IPublisher,
                 data_source: IDataSource,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(publisher, data_source, config)
        
        # Configure ELK logging
        elk_config = config.get('elk', {})
        LoggerFactory.configure(
            logstash_host=elk_config.get('host', 'localhost'),
            logstash_port=elk_config.get('port', 5000),
            console_output=elk_config.get('console', True),
            level=config.get('log_level', 'INFO')
        )
        
        # Get ELK logger
        self._elk_logger = LoggerFactory.get_elk_logger(self.__class__.__name__)
        self._logger = self._elk_logger.get_logger()
    
    @log_function_call('MarketDataBridge')
    def start(self) -> None:
        """Start the bridge with logging"""
        self._elk_logger.get_logger().info("Starting market data bridge", extra={
            'event_type': 'bridge_start',
            'config': self._config,
            'tags': ['lifecycle', 'startup']
        })
        
        with PerformanceLogger(self._elk_logger, 'bridge_startup'):
            super().start()
        
        self._elk_logger.get_logger().info("Market data bridge started successfully", extra={
            'event_type': 'bridge_started',
            'publisher_type': type(self._publisher).__name__,
            'data_source_type': type(self._data_source).__name__,
            'tags': ['lifecycle', 'startup']
        })
    
    @log_function_call('MarketDataBridge')
    def stop(self) -> None:
        """Stop the bridge with logging"""
        stats = self.get_statistics()
        
        self._elk_logger.get_logger().info("Stopping market data bridge", extra={
            'event_type': 'bridge_stop',
            'final_statistics': stats,
            'tags': ['lifecycle', 'shutdown']
        })
        
        super().stop()
        
        self._elk_logger.get_logger().info("Market data bridge stopped", extra={
            'event_type': 'bridge_stopped',
            'tags': ['lifecycle', 'shutdown']
        })
    
    def _handle_tick(self, tick: MarketTick) -> None:
        """Handle tick with ELK logging"""
        try:
            # Log tick to ELK
            self._elk_logger.log_market_tick(
                tick.symbol,
                tick.bid,
                tick.ask,
                tick.volume
            )
            
            # Process normally
            super()._handle_tick(tick)
            
        except Exception as e:
            self._elk_logger.log_error(e, {
                'operation': 'handle_tick',
                'symbol': tick.symbol,
                'bid': tick.bid,
                'ask': tick.ask
            })
            raise
    
    def _handle_bar(self, bar: MarketBar) -> None:
        """Handle bar with ELK logging"""
        try:
            # Log bar to ELK
            self._elk_logger.get_logger().info("Market bar received", extra={
                'event_type': 'market_bar',
                'symbol': bar.symbol,
                'timeframe': bar.timeframe,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'timestamp': bar.timestamp.isoformat(),
                'tags': ['market_data', 'bar']
            })
            
            # Process normally
            super()._handle_bar(bar)
            
        except Exception as e:
            self._elk_logger.log_error(e, {
                'operation': 'handle_bar',
                'symbol': bar.symbol,
                'timeframe': bar.timeframe
            })
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics with ELK logging"""
        stats = super().get_statistics()
        
        # Log statistics to ELK
        self._elk_logger.get_logger().info("Bridge statistics", extra={
            'event_type': 'statistics',
            'stats': stats,
            'tags': ['metrics', 'statistics']
        })
        
        # Log key metrics
        if stats.get('ticks_per_second', 0) > 0:
            self._elk_logger.log_performance_metric(
                'ticks_per_second',
                stats['ticks_per_second'],
                'tps'
            )
        
        return stats


class MonitoredPublisher(IPublisher):
    """Publisher wrapper with monitoring"""
    
    def __init__(self, publisher: IPublisher):
        self._publisher = publisher
        self._elk_logger = LoggerFactory.get_elk_logger('MonitoredPublisher')
        self._publish_count = 0
        self._error_count = 0
    
    def connect(self) -> None:
        """Connect with logging"""
        self._elk_logger.get_logger().info("Publisher connecting", extra={
            'event_type': 'publisher_connect',
            'publisher_type': type(self._publisher).__name__,
            'tags': ['connection']
        })
        
        with PerformanceLogger(self._elk_logger, 'publisher_connect'):
            self._publisher.connect()
    
    def disconnect(self) -> None:
        """Disconnect with logging"""
        self._elk_logger.get_logger().info("Publisher disconnecting", extra={
            'event_type': 'publisher_disconnect',
            'total_published': self._publish_count,
            'total_errors': self._error_count,
            'tags': ['connection']
        })
        
        self._publisher.disconnect()
    
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish with monitoring"""
        start_time = time.time()
        
        try:
            self._publisher.publish(topic, message)
            self._publish_count += 1
            
            # Log performance every 1000 messages
            if self._publish_count % 1000 == 0:
                elapsed = (time.time() - start_time) * 1000
                self._elk_logger.log_performance_metric(
                    'publish_latency',
                    elapsed,
                    'ms'
                )
                
                self._elk_logger.get_logger().info("Publishing milestone", extra={
                    'event_type': 'publish_milestone',
                    'total_published': self._publish_count,
                    'topic': topic,
                    'tags': ['metrics', 'milestone']
                })
        
        except Exception as e:
            self._error_count += 1
            self._elk_logger.log_error(e, {
                'operation': 'publish',
                'topic': topic,
                'message_type': message.get('type', 'unknown')
            })
            raise


class HealthCheckService:
    """Service for health checks and monitoring"""
    
    def __init__(self, bridge: MarketDataBridge, port: int = 8080):
        self._bridge = bridge
        self._port = port
        self._elk_logger = LoggerFactory.get_elk_logger('HealthCheck')
        
    def start(self):
        """Start health check endpoint"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json
        import threading
        
        logger = self._elk_logger
        bridge = self._bridge
        
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/health':
                    # Health check
                    status = {
                        'status': 'healthy' if bridge._running else 'stopped',
                        'timestamp': datetime.utcnow().isoformat(),
                        'uptime': time.time() - bridge._stats._start_time
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(status).encode())
                    
                elif self.path == '/metrics':
                    # Metrics endpoint
                    stats = bridge.get_statistics()
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(stats).encode())
                    
                    # Log metrics request
                    logger.get_logger().debug("Metrics requested", extra={
                        'event_type': 'metrics_request',
                        'client': self.client_address[0],
                        'tags': ['monitoring']
                    })
                    
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Suppress default logging
                pass
        
        # Start server in thread
        server = HTTPServer(('0.0.0.0', self._port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        
        self._elk_logger.get_logger().info("Health check service started", extra={
            'event_type': 'health_service_start',
            'port': self._port,
            'endpoints': ['/health', '/metrics'],
            'tags': ['monitoring', 'health']
        })


# Example usage
if __name__ == "__main__":
    import asyncio
    from services.security.zmq_secure import SecureBridgeFactory
    
    # Configuration
    config = {
        'publish_addresses': ['tcp://*:5556'],
        'elk': {
            'host': 'localhost',
            'port': 5000,
            'console': True
        },
        'log_level': 'INFO',
        'security': {
            'enabled': True
        }
    }
    
    # Create components
    publisher = SecureBridgeFactory.create_secure_publisher(config)
    monitored_publisher = MonitoredPublisher(publisher)
    
    # Create data source (mock for example)
    from services.security.secure_bridge_launcher import MockDataSource
    data_source = MockDataSource()
    
    # Create ELK-enabled bridge
    bridge = ELKMarketDataBridge(monitored_publisher, data_source, config)
    
    # Create health check service
    health_service = HealthCheckService(bridge, 8080)
    health_service.start()
    
    try:
        # Start bridge
        bridge.start()
        
        print("ELK-enabled bridge running...")
        print("Health check: http://localhost:8080/health")
        print("Metrics: http://localhost:8080/metrics")
        print("Press Ctrl+C to stop")
        
        # Run forever
        while True:
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        bridge.stop()