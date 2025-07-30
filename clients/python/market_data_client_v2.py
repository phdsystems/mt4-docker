#!/usr/bin/env python3
"""
Improved Market Data Client with Better OOP Design
Demonstrates SOLID principles and design patterns
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Protocol
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import zmq
import json
import logging
import threading
import time
from collections import defaultdict
import weakref


# Domain Models
@dataclass(frozen=True)
class Symbol:
    """Value object for trading symbol"""
    name: str
    
    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Symbol name must be a non-empty string")
    
    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Price:
    """Value object for price with validation"""
    value: float
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Price cannot be negative")


@dataclass
class MarketData:
    """Base class for market data"""
    symbol: Symbol
    timestamp: datetime
    
    def age_seconds(self) -> float:
        """Calculate age of data in seconds"""
        return (datetime.now() - self.timestamp).total_seconds()


@dataclass
class Tick(MarketData):
    """Tick data model"""
    bid: Price
    ask: Price
    volume: Optional[int] = None
    
    @property
    def spread(self) -> float:
        """Calculate spread"""
        return self.ask.value - self.bid.value
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        return (self.bid.value + self.ask.value) / 2


@dataclass
class Bar(MarketData):
    """Bar/Candle data model"""
    timeframe: str
    open: Price
    high: Price
    low: Price
    close: Price
    volume: int
    
    def validate(self) -> None:
        """Validate bar data integrity"""
        if self.high.value < max(self.open.value, self.close.value):
            raise ValueError("High must be >= open and close")
        if self.low.value > min(self.open.value, self.close.value):
            raise ValueError("Low must be <= open and close")


# Interfaces and Protocols
class IConnection(ABC):
    """Interface for network connections"""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check connection status"""
        pass


class ISubscriber(ABC):
    """Interface for subscription management"""
    
    @abstractmethod
    def subscribe(self, topic: str) -> None:
        """Subscribe to topic"""
        pass
    
    @abstractmethod
    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from topic"""
        pass
    
    @abstractmethod
    def receive(self, timeout: Optional[int] = None) -> Optional[tuple]:
        """Receive message"""
        pass


class IMarketDataHandler(Protocol):
    """Protocol for market data handlers"""
    
    def on_tick(self, tick: Tick) -> None: ...
    def on_bar(self, bar: Bar) -> None: ...
    def on_error(self, error: Exception) -> None: ...
    def on_connect(self) -> None: ...
    def on_disconnect(self) -> None: ...


# Connection Implementations
class ZeroMQConnection(IConnection, ISubscriber):
    """ZeroMQ implementation of connection and subscriber"""
    
    def __init__(self, addresses: List[str], context: Optional[zmq.Context] = None):
        self._addresses = addresses
        self._context = context or zmq.Context()
        self._socket: Optional[zmq.Socket] = None
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def connect(self) -> None:
        """Connect to ZeroMQ publishers"""
        if self.is_connected():
            raise RuntimeError("Already connected")
        
        self._socket = self._context.socket(zmq.SUB)
        self._socket.setsockopt(zmq.RCVHWM, 10000)
        self._socket.setsockopt(zmq.LINGER, 0)
        
        for address in self._addresses:
            self._socket.connect(address)
            self._logger.info(f"Connected to {address}")
    
    def disconnect(self) -> None:
        """Disconnect from publishers"""
        if self._socket:
            self._socket.close()
            self._socket = None
            self._logger.info("Disconnected")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._socket is not None
    
    def subscribe(self, topic: str) -> None:
        """Subscribe to topic"""
        if not self.is_connected():
            raise RuntimeError("Not connected")
        self._socket.subscribe(topic.encode('utf-8'))
        self._logger.debug(f"Subscribed to {topic}")
    
    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from topic"""
        if not self.is_connected():
            raise RuntimeError("Not connected")
        self._socket.unsubscribe(topic.encode('utf-8'))
        self._logger.debug(f"Unsubscribed from {topic}")
    
    def receive(self, timeout: Optional[int] = None) -> Optional[tuple]:
        """Receive message with optional timeout"""
        if not self.is_connected():
            raise RuntimeError("Not connected")
        
        if timeout:
            self._socket.setsockopt(zmq.RCVTIMEO, timeout)
        
        try:
            return self._socket.recv_multipart()
        except zmq.Again:
            return None
        finally:
            if timeout:
                self._socket.setsockopt(zmq.RCVTIMEO, -1)


# Message Processing
class MessageParser:
    """Parse raw messages into domain objects"""
    
    @staticmethod
    def parse_tick(data: Dict[str, Any]) -> Tick:
        """Parse tick from dictionary"""
        return Tick(
            symbol=Symbol(data['symbol']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            bid=Price(data['bid']),
            ask=Price(data['ask']),
            volume=data.get('volume')
        )
    
    @staticmethod
    def parse_bar(data: Dict[str, Any]) -> Bar:
        """Parse bar from dictionary"""
        bar = Bar(
            symbol=Symbol(data['symbol']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            timeframe=data['timeframe'],
            open=Price(data['open']),
            high=Price(data['high']),
            low=Price(data['low']),
            close=Price(data['close']),
            volume=data['volume']
        )
        bar.validate()
        return bar


# Observer Pattern Implementation
class MarketDataObservable:
    """Observable for market data events"""
    
    def __init__(self):
        self._observers: List[weakref.ref] = []
        self._lock = threading.Lock()
    
    def attach(self, observer: IMarketDataHandler) -> None:
        """Attach observer"""
        with self._lock:
            self._observers.append(weakref.ref(observer))
    
    def detach(self, observer: IMarketDataHandler) -> None:
        """Detach observer"""
        with self._lock:
            self._observers = [ref for ref in self._observers 
                            if ref() is not observer]
    
    def _notify_tick(self, tick: Tick) -> None:
        """Notify observers of tick"""
        with self._lock:
            for ref in self._observers[:]:
                observer = ref()
                if observer:
                    try:
                        observer.on_tick(tick)
                    except Exception as e:
                        logging.error(f"Observer error: {e}")
                else:
                    self._observers.remove(ref)
    
    def _notify_bar(self, bar: Bar) -> None:
        """Notify observers of bar"""
        with self._lock:
            for ref in self._observers[:]:
                observer = ref()
                if observer:
                    try:
                        observer.on_bar(bar)
                    except Exception as e:
                        logging.error(f"Observer error: {e}")
                else:
                    self._observers.remove(ref)


# Strategy Pattern for Filtering
class IFilterStrategy(ABC):
    """Interface for message filtering strategies"""
    
    @abstractmethod
    def should_process(self, topic: str, data: Dict[str, Any]) -> bool:
        """Determine if message should be processed"""
        pass


class SymbolFilterStrategy(IFilterStrategy):
    """Filter by symbol list"""
    
    def __init__(self, symbols: List[str]):
        self._symbols = set(symbols)
    
    def should_process(self, topic: str, data: Dict[str, Any]) -> bool:
        """Check if symbol is in allowed list"""
        symbol = data.get('symbol', '')
        return symbol in self._symbols


class TimeFilterStrategy(IFilterStrategy):
    """Filter by time range"""
    
    def __init__(self, start_hour: int = 0, end_hour: int = 24):
        self._start_hour = start_hour
        self._end_hour = end_hour
    
    def should_process(self, topic: str, data: Dict[str, Any]) -> bool:
        """Check if current time is in range"""
        current_hour = datetime.now().hour
        return self._start_hour <= current_hour < self._end_hour


# Main Client Class
class MarketDataClient(MarketDataObservable):
    """Enhanced market data client with OOP best practices"""
    
    def __init__(self,
                 connection: IConnection,
                 parser: MessageParser,
                 filter_strategy: Optional[IFilterStrategy] = None):
        super().__init__()
        self._connection = connection
        self._parser = parser
        self._filter = filter_strategy
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._statistics = MarketDataStatistics()
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def start(self) -> None:
        """Start the client"""
        if self._running:
            raise RuntimeError("Client already running")
        
        self._connection.connect()
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_messages)
        self._worker_thread.daemon = True
        self._worker_thread.start()
        self._logger.info("Client started")
    
    def stop(self) -> None:
        """Stop the client"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self._connection.disconnect()
        self._logger.info("Client stopped")
    
    def subscribe_symbol(self, symbol: Symbol) -> None:
        """Subscribe to a symbol"""
        if isinstance(self._connection, ISubscriber):
            self._connection.subscribe(f"tick.{symbol}")
            self._connection.subscribe(f"bar.{symbol}")
    
    def _process_messages(self) -> None:
        """Process incoming messages"""
        while self._running:
            try:
                result = self._connection.receive(timeout=1000)
                if result:
                    self._handle_message(*result)
            except Exception as e:
                self._logger.error(f"Error processing message: {e}")
    
    def _handle_message(self, topic: bytes, data: bytes) -> None:
        """Handle a single message"""
        try:
            topic_str = topic.decode('utf-8')
            message = json.loads(data.decode('utf-8'))
            
            # Apply filter
            if self._filter and not self._filter.should_process(topic_str, message):
                return
            
            # Parse and notify based on type
            if topic_str.startswith('tick.'):
                tick = self._parser.parse_tick(message)
                self._statistics.record_tick(tick)
                self._notify_tick(tick)
            elif topic_str.startswith('bar.'):
                bar = self._parser.parse_bar(message)
                self._statistics.record_bar(bar)
                self._notify_bar(bar)
                
        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
            self._statistics.record_error()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics"""
        return self._statistics.get_summary()


# Statistics with better encapsulation
class MarketDataStatistics:
    """Track market data statistics"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._tick_count = 0
        self._bar_count = 0
        self._error_count = 0
        self._symbol_stats = defaultdict(lambda: {'ticks': 0, 'bars': 0})
    
    def record_tick(self, tick: Tick) -> None:
        """Record tick statistics"""
        with self._lock:
            self._tick_count += 1
            self._symbol_stats[tick.symbol.name]['ticks'] += 1
    
    def record_bar(self, bar: Bar) -> None:
        """Record bar statistics"""
        with self._lock:
            self._bar_count += 1
            self._symbol_stats[bar.symbol.name]['bars'] += 1
    
    def record_error(self) -> None:
        """Record error"""
        with self._lock:
            self._error_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get statistics summary"""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                'uptime_seconds': uptime,
                'total_ticks': self._tick_count,
                'total_bars': self._bar_count,
                'total_errors': self._error_count,
                'ticks_per_second': self._tick_count / uptime if uptime > 0 else 0,
                'symbol_count': len(self._symbol_stats),
                'symbol_stats': dict(self._symbol_stats)
            }


# Builder Pattern for Client Construction
class MarketDataClientBuilder:
    """Builder for constructing market data clients"""
    
    def __init__(self):
        self._addresses: List[str] = []
        self._filter_strategy: Optional[IFilterStrategy] = None
        self._context: Optional[zmq.Context] = None
    
    def with_addresses(self, addresses: List[str]) -> 'MarketDataClientBuilder':
        """Set connection addresses"""
        self._addresses = addresses
        return self
    
    def with_symbol_filter(self, symbols: List[str]) -> 'MarketDataClientBuilder':
        """Add symbol filter"""
        self._filter_strategy = SymbolFilterStrategy(symbols)
        return self
    
    def with_time_filter(self, start: int, end: int) -> 'MarketDataClientBuilder':
        """Add time filter"""
        self._filter_strategy = TimeFilterStrategy(start, end)
        return self
    
    def with_context(self, context: zmq.Context) -> 'MarketDataClientBuilder':
        """Use existing ZMQ context"""
        self._context = context
        return self
    
    def build(self) -> MarketDataClient:
        """Build the client"""
        if not self._addresses:
            raise ValueError("No addresses specified")
        
        connection = ZeroMQConnection(self._addresses, self._context)
        parser = MessageParser()
        
        return MarketDataClient(connection, parser, self._filter_strategy)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Build client using builder pattern
    client = (MarketDataClientBuilder()
             .with_addresses(['tcp://localhost:5556'])
             .with_symbol_filter(['EURUSD', 'GBPUSD'])
             .build())
    
    # Example observer
    class MyHandler:
        def on_tick(self, tick: Tick):
            print(f"Tick: {tick.symbol} Bid: {tick.bid.value} Ask: {tick.ask.value}")
        
        def on_bar(self, bar: Bar):
            print(f"Bar: {bar.symbol} Close: {bar.close.value}")
    
    handler = MyHandler()
    client.attach(handler)
    
    print("Enhanced OOP Market Data Client")
    print("Features:")
    print("- Value objects with validation")
    print("- Interface segregation")
    print("- Dependency injection")
    print("- Observer pattern")
    print("- Strategy pattern")
    print("- Builder pattern")
    print("- Better encapsulation")