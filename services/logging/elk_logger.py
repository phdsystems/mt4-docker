#!/usr/bin/env python3
"""
ELK Stack Logging Integration
Provides structured logging with automatic forwarding to Logstash
"""

import logging
import json
import socket
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import SocketHandler
import traceback


class LogstashFormatter(logging.Formatter):
    """Format logs as JSON for Logstash"""
    
    def __init__(self, app_name: str = "mt4-docker", environment: str = "production"):
        super().__init__()
        self.app_name = app_name
        self.environment = environment
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Base log data
        log_data = {
            '@timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'application': self.app_name,
            'environment': self.environment,
            'host': socket.gethostname(),
            'path': record.pathname,
            'line': record.lineno,
            'function': record.funcName,
            'thread': record.thread,
            'thread_name': record.threadName,
            'process': record.process
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'pathname', 'process', 
                          'processName', 'relativeCreated', 'thread', 
                          'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data)


class TCPLogstashHandler(SocketHandler):
    """TCP handler for sending logs to Logstash"""
    
    def __init__(self, host: str, port: int = 5000):
        super().__init__(host, port)
        self.formatter = LogstashFormatter()
    
    def makePickle(self, record: logging.LogRecord) -> bytes:
        """Override to send JSON instead of pickle"""
        msg = self.format(record)
        return (msg + '\n').encode('utf-8')


class ELKLogger:
    """Centralized logger with ELK integration"""
    
    def __init__(self, 
                 name: str,
                 logstash_host: str = "localhost",
                 logstash_port: int = 5000,
                 console_output: bool = True,
                 file_output: Optional[str] = None,
                 level: str = "INFO"):
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers = []  # Clear existing handlers
        
        # Logstash handler
        try:
            logstash_handler = TCPLogstashHandler(logstash_host, logstash_port)
            logstash_handler.setLevel(logging.INFO)
            self.logger.addHandler(logstash_handler)
        except Exception as e:
            print(f"Warning: Could not connect to Logstash: {e}")
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if file_output:
            file_handler = logging.FileHandler(file_output)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger"""
        return self.logger
    
    def log_market_tick(self, symbol: str, bid: float, ask: float, volume: Optional[int] = None):
        """Log market tick with structured data"""
        self.logger.info("Market tick received", extra={
            'event_type': 'market_tick',
            'symbol': symbol,
            'bid': bid,
            'ask': ask,
            'spread': ask - bid,
            'volume': volume,
            'tags': ['market_data', 'tick']
        })
    
    def log_security_event(self, event: str, details: Dict[str, Any]):
        """Log security event"""
        self.logger.warning(f"Security event: {event}", extra={
            'event_type': 'security',
            'security_event': event,
            'details': details,
            'tags': ['security', 'audit']
        })
    
    def log_performance_metric(self, metric: str, value: float, unit: str = "ms"):
        """Log performance metric"""
        self.logger.info(f"Performance: {metric}", extra={
            'event_type': 'performance',
            'metric': metric,
            'value': value,
            'unit': unit,
            'tags': ['performance', 'metrics']
        })
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log error with context"""
        self.logger.error(f"Error: {str(error)}", exc_info=True, extra={
            'event_type': 'error',
            'error_type': type(error).__name__,
            'context': context or {},
            'tags': ['error']
        })


class LoggerFactory:
    """Factory for creating ELK loggers"""
    
    _loggers: Dict[str, ELKLogger] = {}
    _config: Dict[str, Any] = {
        'logstash_host': 'localhost',
        'logstash_port': 5000,
        'console_output': True,
        'level': 'INFO'
    }
    
    @classmethod
    def configure(cls, **kwargs):
        """Configure logger factory"""
        cls._config.update(kwargs)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create logger"""
        if name not in cls._loggers:
            cls._loggers[name] = ELKLogger(name, **cls._config)
        return cls._loggers[name].get_logger()
    
    @classmethod
    def get_elk_logger(cls, name: str) -> ELKLogger:
        """Get or create ELK logger wrapper"""
        if name not in cls._loggers:
            cls._loggers[name] = ELKLogger(name, **cls._config)
        return cls._loggers[name]


# Context manager for performance logging
class PerformanceLogger:
    """Context manager for logging performance metrics"""
    
    def __init__(self, logger: ELKLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds() * 1000
        self.logger.log_performance_metric(self.operation, duration, "ms")
        
        if exc_type:
            self.logger.log_error(exc_val, {
                'operation': self.operation,
                'duration_ms': duration
            })


# Decorators for automatic logging
def log_function_call(logger_name: str):
    """Decorator to log function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = LoggerFactory.get_logger(logger_name)
            logger.debug(f"Calling {func.__name__}", extra={
                'event_type': 'function_call',
                'function': func.__name__,
                'args': str(args)[:100],  # Truncate for safety
                'kwargs': str(kwargs)[:100]
            })
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed {func.__name__}", extra={
                    'event_type': 'function_complete',
                    'function': func.__name__
                })
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True, extra={
                    'event_type': 'function_error',
                    'function': func.__name__
                })
                raise
        
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    # Configure factory
    LoggerFactory.configure(
        logstash_host='localhost',
        logstash_port=5000,
        console_output=True,
        level='INFO'
    )
    
    # Get logger
    logger = LoggerFactory.get_elk_logger('example')
    
    # Log various events
    logger.log_market_tick('EURUSD', 1.1000, 1.1001, 1000)
    
    logger.log_security_event('key_generated', {
        'key_type': 'client',
        'client_name': 'test_client'
    })
    
    # Performance logging
    with PerformanceLogger(logger, 'data_processing'):
        import time
        time.sleep(0.1)
    
    # Error logging
    try:
        1 / 0
    except Exception as e:
        logger.log_error(e, {'operation': 'division'})