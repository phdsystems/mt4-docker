#!/usr/bin/env python3
"""
MT4 Prometheus Exporter - Exposes MT4 metrics for Prometheus monitoring
"""

import os
import time
import logging
import re
from datetime import datetime
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Info
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
mt4_info = Info('mt4_terminal', 'MT4 Terminal information')
mt4_connection_status = Gauge('mt4_connection_status', 'MT4 connection status (1=connected, 0=disconnected)')
mt4_account_balance = Gauge('mt4_account_balance', 'Account balance')
mt4_account_equity = Gauge('mt4_account_equity', 'Account equity')
mt4_account_margin = Gauge('mt4_account_margin', 'Account margin')
mt4_account_free_margin = Gauge('mt4_account_free_margin', 'Account free margin')
mt4_open_positions = Gauge('mt4_open_positions', 'Number of open positions')
mt4_pending_orders = Gauge('mt4_pending_orders', 'Number of pending orders')

# Performance metrics
mt4_tick_count = Counter('mt4_tick_count_total', 'Total number of ticks received', ['symbol'])
mt4_tick_latency = Histogram('mt4_tick_latency_seconds', 'Tick processing latency', ['symbol'])
mt4_order_execution_time = Histogram('mt4_order_execution_time_seconds', 'Order execution time')
mt4_cpu_usage = Gauge('mt4_cpu_usage_percent', 'MT4 CPU usage percentage')
mt4_memory_usage = Gauge('mt4_memory_usage_bytes', 'MT4 memory usage in bytes')

# Error tracking
mt4_errors_total = Counter('mt4_errors_total', 'Total number of MT4 errors', ['error_type'])
mt4_reconnects_total = Counter('mt4_reconnects_total', 'Total number of reconnection attempts')

class MT4MetricsHandler(FileSystemEventHandler):
    """Watches MT4 log files and extracts metrics"""
    
    def __init__(self, log_dir):
        self.log_dir = log_dir
        self.last_position = {}
        self.connection_pattern = re.compile(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+(.+)')
        self.account_pattern = re.compile(r'Account: (\d+), Balance: ([\d.]+), Equity: ([\d.]+), Margin: ([\d.]+), Free Margin: ([\d.]+)')
        self.tick_pattern = re.compile(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+(\w+)\s+Bid: ([\d.]+)\s+Ask: ([\d.]+)')
        self.error_pattern = re.compile(r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+Error:?\s+(.+)')
        
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.log'):
            return
            
        self.parse_log_file(event.src_path)
    
    def parse_log_file(self, filepath):
        """Parse MT4 log file and update metrics"""
        try:
            filename = os.path.basename(filepath)
            
            # Get last read position
            last_pos = self.last_position.get(filename, 0)
            
            with open(filepath, 'r', encoding='utf-16-le', errors='ignore') as f:
                f.seek(last_pos)
                
                for line in f:
                    self.process_log_line(line.strip())
                
                # Update last position
                self.last_position[filename] = f.tell()
                
        except Exception as e:
            logger.error(f"Error parsing log file {filepath}: {e}")
            mt4_errors_total.labels(error_type='log_parse').inc()
    
    def process_log_line(self, line):
        """Process a single log line and update metrics"""
        if not line:
            return
        
        # Check for connection status
        if 'connected to' in line.lower():
            mt4_connection_status.set(1)
            logger.info("MT4 connected to server")
        elif 'disconnected' in line.lower() or 'connection lost' in line.lower():
            mt4_connection_status.set(0)
            mt4_reconnects_total.inc()
            logger.warning("MT4 disconnected from server")
        
        # Check for account information
        account_match = self.account_pattern.search(line)
        if account_match:
            account_num, balance, equity, margin, free_margin = account_match.groups()
            mt4_account_balance.set(float(balance))
            mt4_account_equity.set(float(equity))
            mt4_account_margin.set(float(margin))
            mt4_account_free_margin.set(float(free_margin))
            logger.debug(f"Updated account metrics: Balance={balance}, Equity={equity}")
        
        # Check for tick data
        tick_match = self.tick_pattern.search(line)
        if tick_match:
            timestamp, symbol, bid, ask = tick_match.groups()
            mt4_tick_count.labels(symbol=symbol).inc()
            # Calculate latency if possible
            try:
                tick_time = datetime.strptime(timestamp, '%Y.%m.%d %H:%M:%S')
                latency = (datetime.now() - tick_time).total_seconds()
                if latency >= 0 and latency < 60:  # Sanity check
                    mt4_tick_latency.labels(symbol=symbol).observe(latency)
            except:
                pass
        
        # Check for errors
        error_match = self.error_pattern.search(line)
        if error_match:
            timestamp, error_msg = error_match.groups()
            error_type = 'unknown'
            if 'trade' in error_msg.lower():
                error_type = 'trade'
            elif 'connection' in error_msg.lower():
                error_type = 'connection'
            elif 'memory' in error_msg.lower():
                error_type = 'memory'
            
            mt4_errors_total.labels(error_type=error_type).inc()
            logger.error(f"MT4 Error: {error_msg}")

class MT4StatusChecker:
    """Periodically checks MT4 status"""
    
    def __init__(self, mt4_dir):
        self.mt4_dir = mt4_dir
        self.status_file = os.path.join(mt4_dir, 'data', 'status.json')
    
    def check_status(self):
        """Check MT4 status from status file"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                
                # Update metrics from status
                mt4_open_positions.set(status.get('open_positions', 0))
                mt4_pending_orders.set(status.get('pending_orders', 0))
                
                # Update terminal info
                mt4_info.info({
                    'version': status.get('version', 'unknown'),
                    'build': status.get('build', 'unknown'),
                    'server': status.get('server', 'unknown'),
                    'account': str(status.get('account', 'unknown'))
                })
                
                # Check if terminal is running
                if status.get('last_update'):
                    last_update = datetime.fromisoformat(status['last_update'])
                    if (datetime.now() - last_update).total_seconds() > 60:
                        mt4_connection_status.set(0)
                    else:
                        mt4_connection_status.set(1)
                        
        except Exception as e:
            logger.error(f"Error checking MT4 status: {e}")
            mt4_errors_total.labels(error_type='status_check').inc()
    
    def check_resource_usage(self):
        """Check MT4 process resource usage"""
        try:
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                if 'terminal.exe' in proc.info['name'].lower():
                    mt4_cpu_usage.set(proc.info['cpu_percent'])
                    mt4_memory_usage.set(proc.info['memory_info'].rss)
                    break
                    
        except Exception as e:
            logger.error(f"Error checking resource usage: {e}")

def main():
    """Main exporter function"""
    # Configuration
    port = int(os.environ.get('EXPORTER_PORT', 9101))
    mt4_dir = os.environ.get('MT4_DIR', '/mt4')
    log_dir = os.path.join(mt4_dir, 'logs')
    
    logger.info(f"Starting MT4 Prometheus Exporter on port {port}")
    logger.info(f"Monitoring MT4 directory: {mt4_dir}")
    
    # Start HTTP server for Prometheus
    start_http_server(port)
    
    # Initialize components
    metrics_handler = MT4MetricsHandler(log_dir)
    status_checker = MT4StatusChecker(mt4_dir)
    
    # Set up file system observer
    observer = Observer()
    observer.schedule(metrics_handler, log_dir, recursive=False)
    observer.start()
    
    try:
        while True:
            # Periodic status checks
            status_checker.check_status()
            status_checker.check_resource_usage()
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Shutting down MT4 Exporter")
        observer.stop()
    
    observer.join()

if __name__ == '__main__':
    main()