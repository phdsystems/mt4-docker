#!/usr/bin/env python3
"""
Improved OOP version of ZeroMQ Bridge for MT4 Market Data
Demonstrates better OOP principles with SOLID design
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Protocol
from dataclasses import dataclass
from datetime import datetime
import zmq
import json
import time
import logging
import threading
from enum import Enum


# Domain Models using dataclasses
@dataclass
class MarketTick:
    """Value object for market tick data"""
    symbol: str
    bid: float
    ask: float
    timestamp: datetime
    volume: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'bid': self.bid,
            'ask': self.ask,
            'timestamp': self.timestamp.isoformat(),
            'volume': self.volume
        }


@dataclass
class MarketBar:
    """Value object for market bar data"""
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat()
        }


class MessageType(Enum):
    """Enumeration for message types"""
    TICK = "tick"
    BAR = "bar"
    STATUS = "status"
    ERROR = "error"


# Abstract base classes and interfaces
class IPublisher(ABC):
    """Interface for message publishers"""
    
    @abstractmethod
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish a message to a topic"""
        pass
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection"""
        pass


class IDataSource(ABC):
    """Interface for market data sources"""
    
    @abstractmethod
    def start(self) -> None:
        """Start receiving data"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop receiving data"""
        pass
    
    @abstractmethod
    def on_tick(self, callback) -> None:
        """Register tick callback"""
        pass
    
    @abstractmethod
    def on_bar(self, callback) -> None:
        """Register bar callback"""
        pass


class ISerializer(ABC):
    """Interface for message serialization"""
    
    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes"""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to data"""
        pass


# Concrete implementations
class JsonSerializer(ISerializer):
    """JSON serialization implementation"""
    
    def serialize(self, data: Any) -> bytes:
        if hasattr(data, 'to_dict'):
            data = data.to_dict()
        return json.dumps(data).encode('utf-8')
    
    def deserialize(self, data: bytes) -> Any:
        return json.loads(data.decode('utf-8'))


class ZeroMQPublisher(IPublisher):
    """ZeroMQ implementation of IPublisher"""
    
    def __init__(self, 
                 addresses: List[str],
                 serializer: ISerializer,
                 high_water_mark: int = 10000):
        self._addresses = addresses
        self._serializer = serializer
        self._hwm = high_water_mark
        self._context: Optional[zmq.Context] = None
        self._socket: Optional[zmq.Socket] = None
        self._logger = logging.getLogger(self.__class__.__name__)
        
    def connect(self) -> None:
        """Establish ZeroMQ connections"""
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.setsockopt(zmq.SNDHWM, self._hwm)
        self._socket.setsockopt(zmq.LINGER, 0)
        
        for address in self._addresses:
            self._socket.bind(address)
            self._logger.info(f"Publisher bound to {address}")
    
    def disconnect(self) -> None:
        """Close ZeroMQ connections"""
        if self._socket:
            self._socket.close()
        if self._context:
            self._context.term()
        self._logger.info("Publisher disconnected")
    
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish message to topic"""
        if not self._socket:
            raise RuntimeError("Publisher not connected")
        
        try:
            serialized = self._serializer.serialize(message)
            self._socket.send_multipart([
                topic.encode('utf-8'),
                serialized
            ])
        except zmq.ZMQError as e:
            self._logger.error(f"Failed to publish: {e}")
            raise


class MarketDataBridge:
    """Main bridge class using dependency injection"""
    
    def __init__(self,
                 publisher: IPublisher,
                 data_source: IDataSource,
                 config: Optional[Dict[str, Any]] = None):
        self._publisher = publisher
        self._data_source = data_source
        self._config = config or {}
        self._running = False
        self._stats = BridgeStatistics()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Register callbacks
        self._data_source.on_tick(self._handle_tick)
        self._data_source.on_bar(self._handle_bar)
    
    def start(self) -> None:
        """Start the bridge"""
        self._logger.info("Starting market data bridge")
        self._publisher.connect()
        self._data_source.start()
        self._running = True
        self._stats.reset()
    
    def stop(self) -> None:
        """Stop the bridge"""
        self._logger.info("Stopping market data bridge")
        self._running = False
        self._data_source.stop()
        self._publisher.disconnect()
    
    def _handle_tick(self, tick: MarketTick) -> None:
        """Handle incoming tick data"""
        if not self._running:
            return
        
        topic = f"{MessageType.TICK.value}.{tick.symbol}"
        message = {
            'type': MessageType.TICK.value,
            'timestamp': int(time.time() * 1000),
            'data': tick.to_dict()
        }
        
        try:
            self._publisher.publish(topic, message)
            self._stats.record_tick(tick.symbol)
        except Exception as e:
            self._logger.error(f"Error publishing tick: {e}")
            self._stats.record_error()
    
    def _handle_bar(self, bar: MarketBar) -> None:
        """Handle incoming bar data"""
        if not self._running:
            return
        
        topic = f"{MessageType.BAR.value}.{bar.symbol}.{bar.timeframe}"
        message = {
            'type': MessageType.BAR.value,
            'timestamp': int(time.time() * 1000),
            'data': bar.to_dict()
        }
        
        try:
            self._publisher.publish(topic, message)
            self._stats.record_bar(bar.symbol, bar.timeframe)
        except Exception as e:
            self._logger.error(f"Error publishing bar: {e}")
            self._stats.record_error()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        return self._stats.get_summary()


class BridgeStatistics:
    """Statistics collector for the bridge"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()
    
    def reset(self) -> None:
        """Reset all statistics"""
        with self._lock:
            self._start_time = time.time()
            self._tick_count = 0
            self._bar_count = 0
            self._error_count = 0
            self._symbols = set()
            self._tick_counts_by_symbol = {}
    
    def record_tick(self, symbol: str) -> None:
        """Record a tick"""
        with self._lock:
            self._tick_count += 1
            self._symbols.add(symbol)
            self._tick_counts_by_symbol[symbol] = \
                self._tick_counts_by_symbol.get(symbol, 0) + 1
    
    def record_bar(self, symbol: str, timeframe: str) -> None:
        """Record a bar"""
        with self._lock:
            self._bar_count += 1
            self._symbols.add(symbol)
    
    def record_error(self) -> None:
        """Record an error"""
        with self._lock:
            self._error_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get statistics summary"""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                'uptime_seconds': uptime,
                'tick_count': self._tick_count,
                'bar_count': self._bar_count,
                'error_count': self._error_count,
                'symbol_count': len(self._symbols),
                'symbols': list(self._symbols),
                'ticks_per_second': self._tick_count / uptime if uptime > 0 else 0,
                'tick_counts_by_symbol': dict(self._tick_counts_by_symbol)
            }


# Factory pattern for creating bridges
class BridgeFactory:
    """Factory for creating market data bridges"""
    
    @staticmethod
    def create_zeromq_bridge(config: Dict[str, Any]) -> MarketDataBridge:
        """Create a ZeroMQ-based bridge"""
        # Create serializer
        serializer = JsonSerializer()
        
        # Create publisher
        addresses = config.get('publish_addresses', ['tcp://*:5556'])
        publisher = ZeroMQPublisher(addresses, serializer)
        
        # Create data source (would be injected in real implementation)
        data_source = config.get('data_source')
        if not data_source:
            raise ValueError("No data source provided")
        
        # Create and return bridge
        return MarketDataBridge(publisher, data_source, config)


# Example usage demonstrating dependency injection
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example configuration
    config = {
        'publish_addresses': ['tcp://*:5556', 'tcp://*:5557'],
        'log_level': 'INFO'
    }
    
    # In real usage, data_source would be an actual implementation
    # For example: MT4FileDataSource, MT4PipeDataSource, etc.
    
    print("OOP ZeroMQ Bridge Example")
    print("This demonstrates improved OOP design with:")
    print("- SOLID principles")
    print("- Dependency injection")
    print("- Abstract base classes")
    print("- Factory pattern")
    print("- Value objects")
    print("- Better encapsulation")