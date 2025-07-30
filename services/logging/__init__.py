"""
Logging module for MT4 Docker project
Provides centralized logging with ELK stack integration
"""

from .elk_logger import (
    ELKLogger,
    LoggerFactory,
    LogstashFormatter,
    TCPLogstashHandler,
    PerformanceLogger,
    log_function_call
)

__all__ = [
    'ELKLogger',
    'LoggerFactory',
    'LogstashFormatter',
    'TCPLogstashHandler',
    'PerformanceLogger',
    'log_function_call'
]

__version__ = '1.0.0'

# Configure default logger
LoggerFactory.configure(
    logstash_host='localhost',
    logstash_port=5000,
    console_output=True,
    level='INFO'
)