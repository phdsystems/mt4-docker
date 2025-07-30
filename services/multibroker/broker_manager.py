#!/usr/bin/env python3
"""
Multi-broker Manager for MT4
Manages multiple MT4 instances connecting to different brokers
"""

import asyncio
import json
import time
import logging
import docker
import zmq
import zmq.asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BrokerStatus(Enum):
    """Broker connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class BrokerConfig:
    """Broker configuration"""
    id: str
    name: str
    server: str
    login: str
    password: str
    symbols: List[str]
    zmq_port: int
    vnc_port: int
    container_name: str
    enabled: bool = True
    priority: int = 1
    max_spread: Dict[str, float] = None
    trading_hours: Dict[str, Dict] = None


@dataclass
class BrokerInstance:
    """Running broker instance"""
    config: BrokerConfig
    container: Any  # Docker container object
    status: BrokerStatus
    connected_at: Optional[float]
    last_tick: Optional[float]
    error_count: int
    zmq_socket: Optional[zmq.asyncio.Socket]


class BrokerManager:
    """Manages multiple MT4 broker connections"""
    
    def __init__(self, docker_client=None):
        """Initialize broker manager"""
        self.docker_client = docker_client or docker.from_env()
        self.brokers: Dict[str, BrokerInstance] = {}
        self.zmq_context = zmq.asyncio.Context()
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Aggregated market data
        self.market_data: Dict[str, Dict[str, Any]] = {}
        self.symbol_brokers: Dict[str, Set[str]] = {}  # symbol -> set of broker IDs
        
        # Configuration
        self.base_image = "mt4-docker:latest"
        self.network_name = "mt4_network"
        self.data_volume_prefix = "mt4_data_"
    
    def add_broker(self, config: BrokerConfig) -> bool:
        """Add a broker configuration"""
        if config.id in self.brokers:
            self.logger.warning(f"Broker {config.id} already exists")
            return False
        
        # Initialize broker instance
        self.brokers[config.id] = BrokerInstance(
            config=config,
            container=None,
            status=BrokerStatus.DISCONNECTED,
            connected_at=None,
            last_tick=None,
            error_count=0,
            zmq_socket=None
        )
        
        # Map symbols to brokers
        for symbol in config.symbols:
            if symbol not in self.symbol_brokers:
                self.symbol_brokers[symbol] = set()
            self.symbol_brokers[symbol].add(config.id)
        
        self.logger.info(f"Added broker: {config.name} ({config.id})")
        return True
    
    async def start_broker(self, broker_id: str) -> bool:
        """Start a specific broker instance"""
        if broker_id not in self.brokers:
            self.logger.error(f"Broker {broker_id} not found")
            return False
        
        broker = self.brokers[broker_id]
        
        if broker.status == BrokerStatus.CONNECTED:
            self.logger.info(f"Broker {broker_id} already connected")
            return True
        
        try:
            broker.status = BrokerStatus.CONNECTING
            
            # Create Docker container
            container = self.docker_client.containers.run(
                self.base_image,
                name=broker.config.container_name,
                detach=True,
                remove=True,
                network=self.network_name,
                ports={
                    '5900/tcp': broker.config.vnc_port,
                    '5556/tcp': broker.config.zmq_port
                },
                environment={
                    'MT4_SERVER': broker.config.server,
                    'MT4_LOGIN': broker.config.login,
                    'MT4_PASSWORD': broker.config.password,
                    'DISPLAY': ':1',
                    'VNC_PASSWORD': 'vncpassword',
                    'BROKER_ID': broker.config.id,
                    'SYMBOLS': ','.join(broker.config.symbols)
                },
                volumes={
                    f"{self.data_volume_prefix}{broker_id}": {
                        'bind': '/mt4',
                        'mode': 'rw'
                    }
                }
            )
            
            broker.container = container
            
            # Wait for container to be ready
            await asyncio.sleep(10)
            
            # Connect to ZeroMQ
            socket = self.zmq_context.socket(zmq.SUB)
            socket.connect(f"tcp://localhost:{broker.config.zmq_port}")
            socket.subscribe(b"")
            broker.zmq_socket = socket
            
            broker.status = BrokerStatus.CONNECTED
            broker.connected_at = time.time()
            broker.error_count = 0
            
            self.logger.info(f"Started broker: {broker.config.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start broker {broker_id}: {e}")
            broker.status = BrokerStatus.ERROR
            broker.error_count += 1
            return False
    
    async def stop_broker(self, broker_id: str) -> bool:
        """Stop a specific broker instance"""
        if broker_id not in self.brokers:
            return False
        
        broker = self.brokers[broker_id]
        
        try:
            # Close ZeroMQ socket
            if broker.zmq_socket:
                broker.zmq_socket.close()
                broker.zmq_socket = None
            
            # Stop Docker container
            if broker.container:
                broker.container.stop()
                broker.container = None
            
            broker.status = BrokerStatus.DISCONNECTED
            broker.connected_at = None
            
            self.logger.info(f"Stopped broker: {broker.config.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop broker {broker_id}: {e}")
            return False
    
    async def start_all(self):
        """Start all enabled brokers"""
        self.running = True
        
        # Start brokers
        tasks = []
        for broker_id, broker in self.brokers.items():
            if broker.config.enabled:
                tasks.append(self.start_broker(broker_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_brokers())
        asyncio.create_task(self._aggregate_market_data())
        
        success_count = sum(1 for r in results if r is True)
        self.logger.info(f"Started {success_count}/{len(tasks)} brokers")
    
    async def stop_all(self):
        """Stop all brokers"""
        self.running = False
        
        tasks = []
        for broker_id in self.brokers:
            tasks.append(self.stop_broker(broker_id))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("Stopped all brokers")
    
    async def _monitor_brokers(self):
        """Monitor broker health and restart if needed"""
        while self.running:
            for broker_id, broker in self.brokers.items():
                if not broker.config.enabled:
                    continue
                
                # Check if broker should be running
                if broker.status == BrokerStatus.CONNECTED:
                    # Check last tick time
                    if broker.last_tick and time.time() - broker.last_tick > 60:
                        self.logger.warning(f"Broker {broker_id} not receiving data")
                        broker.status = BrokerStatus.ERROR
                
                # Restart failed brokers
                elif broker.status == BrokerStatus.ERROR and broker.error_count < 5:
                    self.logger.info(f"Attempting to restart broker {broker_id}")
                    await self.stop_broker(broker_id)
                    await asyncio.sleep(5)
                    await self.start_broker(broker_id)
            
            await asyncio.sleep(30)
    
    async def _aggregate_market_data(self):
        """Aggregate market data from all brokers"""
        while self.running:
            tasks = []
            for broker_id, broker in self.brokers.items():
                if broker.status == BrokerStatus.CONNECTED and broker.zmq_socket:
                    tasks.append(self._receive_broker_data(broker_id))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            await asyncio.sleep(0.01)  # Small delay to prevent CPU spinning
    
    async def _receive_broker_data(self, broker_id: str):
        """Receive data from a specific broker"""
        broker = self.brokers[broker_id]
        
        try:
            # Non-blocking receive
            if await broker.zmq_socket.poll(timeout=0):
                topic, message = await broker.zmq_socket.recv_multipart()
                data = json.loads(message.decode())
                
                # Extract symbol from topic
                topic_str = topic.decode()
                if topic_str.startswith("tick."):
                    symbol = topic_str[5:]
                    
                    # Update broker's last tick time
                    broker.last_tick = time.time()
                    
                    # Store market data with broker info
                    data['broker_id'] = broker_id
                    data['broker_name'] = broker.config.name
                    data['received_at'] = time.time()
                    
                    # Check spread limits
                    if broker.config.max_spread and symbol in broker.config.max_spread:
                        if data.get('spread', 0) > broker.config.max_spread[symbol]:
                            data['spread_exceeded'] = True
                    
                    # Update aggregated data
                    if symbol not in self.market_data:
                        self.market_data[symbol] = {}
                    
                    self.market_data[symbol][broker_id] = data
                    
                    # Emit aggregated data
                    await self._emit_best_prices(symbol)
        
        except Exception as e:
            self.logger.error(f"Error receiving data from broker {broker_id}: {e}")
            broker.error_count += 1
    
    async def _emit_best_prices(self, symbol: str):
        """Emit best bid/ask prices across all brokers"""
        if symbol not in self.market_data:
            return
        
        best_bid = None
        best_ask = None
        best_bid_broker = None
        best_ask_broker = None
        
        # Find best prices
        for broker_id, data in self.market_data[symbol].items():
            broker = self.brokers[broker_id]
            
            # Skip if spread exceeded or data is stale
            if data.get('spread_exceeded') or time.time() - data['received_at'] > 5:
                continue
            
            # Check trading hours if configured
            if not self._is_trading_hours(broker.config, symbol):
                continue
            
            bid = data.get('bid', 0)
            ask = data.get('ask', 0)
            
            if bid > 0 and (best_bid is None or bid > best_bid['bid']):
                best_bid = data.copy()
                best_bid_broker = broker_id
            
            if ask > 0 and (best_ask is None or ask < best_ask['ask']):
                best_ask = data.copy()
                best_ask_broker = broker_id
        
        # Emit aggregated data
        if best_bid and best_ask:
            aggregated = {
                'symbol': symbol,
                'best_bid': best_bid['bid'],
                'best_bid_broker': best_bid_broker,
                'best_ask': best_ask['ask'],
                'best_ask_broker': best_ask_broker,
                'spread': best_ask['ask'] - best_bid['bid'],
                'timestamp': time.time(),
                'broker_count': len(self.market_data[symbol])
            }
            
            # This would be published to subscribers
            self.logger.debug(f"Best prices for {symbol}: Bid {aggregated['best_bid']} ({best_bid_broker}), Ask {aggregated['best_ask']} ({best_ask_broker})")
    
    def _is_trading_hours(self, config: BrokerConfig, symbol: str) -> bool:
        """Check if within trading hours for broker/symbol"""
        if not config.trading_hours or symbol not in config.trading_hours:
            return True
        
        hours = config.trading_hours[symbol]
        now = datetime.now()
        current_time = now.hour * 60 + now.minute
        
        # Check day of week
        if 'days' in hours:
            if now.weekday() not in hours['days']:
                return False
        
        # Check time range
        if 'start' in hours and 'end' in hours:
            start = hours['start']
            end = hours['end']
            
            start_minutes = start['hour'] * 60 + start['minute']
            end_minutes = end['hour'] * 60 + end['minute']
            
            if start_minutes <= end_minutes:
                return start_minutes <= current_time <= end_minutes
            else:  # Crosses midnight
                return current_time >= start_minutes or current_time <= end_minutes
        
        return True
    
    def get_broker_status(self) -> Dict[str, Any]:
        """Get status of all brokers"""
        status = {
            'brokers': {},
            'summary': {
                'total': len(self.brokers),
                'connected': 0,
                'error': 0,
                'symbols_covered': set()
            }
        }
        
        for broker_id, broker in self.brokers.items():
            broker_status = {
                'name': broker.config.name,
                'status': broker.status.value,
                'enabled': broker.config.enabled,
                'connected_duration': None,
                'error_count': broker.error_count,
                'last_tick': broker.last_tick,
                'symbols': broker.config.symbols
            }
            
            if broker.connected_at:
                broker_status['connected_duration'] = time.time() - broker.connected_at
            
            status['brokers'][broker_id] = broker_status
            
            if broker.status == BrokerStatus.CONNECTED:
                status['summary']['connected'] += 1
                status['summary']['symbols_covered'].update(broker.config.symbols)
            elif broker.status == BrokerStatus.ERROR:
                status['summary']['error'] += 1
        
        status['summary']['symbols_covered'] = list(status['summary']['symbols_covered'])
        return status
    
    def get_best_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get best bid/ask for a symbol"""
        if symbol not in self.market_data:
            return None
        
        best_bid = None
        best_ask = None
        
        for broker_id, data in self.market_data[symbol].items():
            if time.time() - data['received_at'] > 5:  # Skip stale data
                continue
            
            bid = data.get('bid', 0)
            ask = data.get('ask', 0)
            
            if bid > 0 and (best_bid is None or bid > best_bid):
                best_bid = bid
            
            if ask > 0 and (best_ask is None or ask < best_ask):
                best_ask = ask
        
        if best_bid and best_ask:
            return {
                'symbol': symbol,
                'bid': best_bid,
                'ask': best_ask,
                'spread': best_ask - best_bid,
                'timestamp': time.time()
            }
        
        return None


class BrokerArbirtageDetector:
    """Detect arbitrage opportunities between brokers"""
    
    def __init__(self, manager: BrokerManager):
        self.manager = manager
        self.opportunities = []
        self.min_profit_pips = 2  # Minimum profit in pips
        self.logger = logging.getLogger(__name__)
    
    def check_arbitrage(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Check for arbitrage opportunities"""
        if symbol not in self.manager.market_data:
            return None
        
        brokers_data = []
        
        # Collect valid quotes from all brokers
        for broker_id, data in self.manager.market_data[symbol].items():
            if time.time() - data['received_at'] < 1:  # Only fresh quotes
                brokers_data.append({
                    'broker_id': broker_id,
                    'bid': data.get('bid', 0),
                    'ask': data.get('ask', 0)
                })
        
        if len(brokers_data) < 2:
            return None
        
        # Find best bid and ask across brokers
        best_bid = max(brokers_data, key=lambda x: x['bid'])
        best_ask = min(brokers_data, key=lambda x: x['ask'])
        
        # Check if arbitrage exists
        if best_bid['broker_id'] != best_ask['broker_id']:
            profit = best_bid['bid'] - best_ask['ask']
            
            # Convert to pips (assuming 5 decimal places for forex)
            profit_pips = profit * 10000 if symbol != 'USDJPY' else profit * 100
            
            if profit_pips >= self.min_profit_pips:
                opportunity = {
                    'symbol': symbol,
                    'buy_broker': best_ask['broker_id'],
                    'buy_price': best_ask['ask'],
                    'sell_broker': best_bid['broker_id'],
                    'sell_price': best_bid['bid'],
                    'profit': profit,
                    'profit_pips': profit_pips,
                    'timestamp': time.time()
                }
                
                self.opportunities.append(opportunity)
                self.logger.info(f"Arbitrage opportunity: {symbol} - Buy at {best_ask['ask']} ({best_ask['broker_id']}), Sell at {best_bid['bid']} ({best_bid['broker_id']}), Profit: {profit_pips:.1f} pips")
                
                return opportunity
        
        return None


# Example configuration
def create_example_brokers():
    """Create example broker configurations"""
    brokers = [
        BrokerConfig(
            id="broker1",
            name="Demo Broker 1",
            server="demo1.metaquotes.net:443",
            login="demo1",
            password="password1",
            symbols=["EURUSD", "GBPUSD", "USDJPY"],
            zmq_port=5556,
            vnc_port=5901,
            container_name="mt4_broker1",
            max_spread={"EURUSD": 2.0, "GBPUSD": 3.0, "USDJPY": 2.5}
        ),
        BrokerConfig(
            id="broker2",
            name="Demo Broker 2",
            server="demo2.metaquotes.net:443",
            login="demo2",
            password="password2",
            symbols=["EURUSD", "GBPUSD", "XAUUSD"],
            zmq_port=5557,
            vnc_port=5902,
            container_name="mt4_broker2",
            priority=2
        ),
        BrokerConfig(
            id="broker3",
            name="Demo Broker 3",
            server="demo3.metaquotes.net:443",
            login="demo3",
            password="password3",
            symbols=["EURUSD", "USDJPY", "XAUUSD", "BTCUSD"],
            zmq_port=5558,
            vnc_port=5903,
            container_name="mt4_broker3",
            trading_hours={
                "BTCUSD": {
                    "days": [0, 1, 2, 3, 4],  # Monday to Friday
                    "start": {"hour": 0, "minute": 0},
                    "end": {"hour": 23, "minute": 59}
                }
            }
        )
    ]
    
    return brokers


async def main():
    """Example usage"""
    logging.basicConfig(level=logging.INFO)
    
    # Create broker manager
    manager = BrokerManager()
    
    # Add brokers
    for broker_config in create_example_brokers():
        manager.add_broker(broker_config)
    
    # Create arbitrage detector
    arbitrage = BrokerArbirtageDetector(manager)
    
    try:
        # Start all brokers
        await manager.start_all()
        
        # Monitor for 60 seconds
        for i in range(60):
            await asyncio.sleep(1)
            
            # Check arbitrage opportunities
            for symbol in ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]:
                arbitrage.check_arbitrage(symbol)
            
            # Print status every 10 seconds
            if i % 10 == 0:
                status = manager.get_broker_status()
                print(f"\nBroker Status: {status['summary']['connected']}/{status['summary']['total']} connected")
                print(f"Symbols covered: {', '.join(status['summary']['symbols_covered'])}")
        
    finally:
        # Stop all brokers
        await manager.stop_all()


if __name__ == "__main__":
    asyncio.run(main())