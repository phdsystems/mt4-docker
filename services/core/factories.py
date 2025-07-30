#!/usr/bin/env python3
"""
Factory implementations for creating various components
Demonstrates Factory and Abstract Factory patterns
"""

from typing import Dict, Any, Type, Optional, List
from abc import ABC, abstractmethod
import zmq
import logging
from datetime import datetime

from .interfaces import (
    IConnection, IPublisher, ISubscriber, IDataProcessor,
    IConnectionFactory, IProcessorFactory, ILogger, IMetricsCollector,
    ConnectionConfig, ConnectionState, DataType
)


# Concrete Implementations
class ZeroMQPublisher(IPublisher):
    """ZeroMQ implementation of IPublisher"""
    
    def __init__(self, context: zmq.Context, config: ConnectionConfig):
        self._context = context
        self._config = config
        self._socket = None
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def connect(self) -> None:
        """Create and bind socket"""
        self._socket = self._context.socket(zmq.PUB)
        for address in self._config.addresses:
            self._socket.bind(address)
            self._logger.info(f"Publisher bound to {address}")
    
    async def publish(self, topic: str, data: Any) -> None:
        """Publish single message"""
        if not self._socket:
            raise RuntimeError("Not connected")
        
        import json
        message = json.dumps(data).encode('utf-8')
        await self._socket.send_multipart([topic.encode('utf-8'), message])
    
    async def publish_batch(self, messages: List[tuple]) -> None:
        """Publish multiple messages"""
        for topic, data in messages:
            await self.publish(topic, data)


class ZeroMQSubscriber(ISubscriber):
    """ZeroMQ implementation of ISubscriber"""
    
    def __init__(self, context: zmq.Context, config: ConnectionConfig):
        self._context = context
        self._config = config
        self._socket = None
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def connect(self) -> None:
        """Create and connect socket"""
        self._socket = self._context.socket(zmq.SUB)
        for address in self._config.addresses:
            self._socket.connect(address)
            self._logger.info(f"Subscriber connected to {address}")
    
    async def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        if not self._socket:
            raise RuntimeError("Not connected")
        
        for topic in topics:
            self._socket.subscribe(topic.encode('utf-8'))
    
    async def unsubscribe(self, topics: List[str]) -> None:
        """Unsubscribe from topics"""
        if not self._socket:
            raise RuntimeError("Not connected")
        
        for topic in topics:
            self._socket.unsubscribe(topic.encode('utf-8'))
    
    async def receive(self, timeout: Optional[int] = None) -> Optional[tuple]:
        """Receive message"""
        if not self._socket:
            raise RuntimeError("Not connected")
        
        if timeout:
            self._socket.setsockopt(zmq.RCVTIMEO, timeout)
        
        try:
            parts = await self._socket.recv_multipart()
            return (parts[0].decode('utf-8'), parts[1]) if parts else None
        except zmq.Again:
            return None


# Data Processors
class TickDataProcessor(IDataProcessor):
    """Process tick data"""
    
    def process(self, data: Dict[str, Any]) -> Optional[Any]:
        """Process tick data"""
        try:
            from ..models import MarketTick, Symbol, Price
            
            return MarketTick(
                symbol=Symbol(data['symbol']),
                bid=Price(data['bid']),
                ask=Price(data['ask']),
                timestamp=datetime.fromisoformat(data['timestamp']),
                volume=data.get('volume')
            )
        except (KeyError, ValueError) as e:
            logging.error(f"Error processing tick data: {e}")
            return None
    
    def validate(self, data: Any) -> bool:
        """Validate tick data"""
        if not hasattr(data, 'bid') or not hasattr(data, 'ask'):
            return False
        return data.bid.value > 0 and data.ask.value > 0


class BarDataProcessor(IDataProcessor):
    """Process bar/candle data"""
    
    def process(self, data: Dict[str, Any]) -> Optional[Any]:
        """Process bar data"""
        try:
            from ..models import MarketBar, Symbol, Price
            
            bar = MarketBar(
                symbol=Symbol(data['symbol']),
                timeframe=data['timeframe'],
                open=Price(data['open']),
                high=Price(data['high']),
                low=Price(data['low']),
                close=Price(data['close']),
                volume=data['volume'],
                timestamp=datetime.fromisoformat(data['timestamp'])
            )
            
            if self.validate(bar):
                return bar
            return None
            
        except (KeyError, ValueError) as e:
            logging.error(f"Error processing bar data: {e}")
            return None
    
    def validate(self, data: Any) -> bool:
        """Validate bar data"""
        if not hasattr(data, 'high') or not hasattr(data, 'low'):
            return False
        
        # Validate OHLC relationships
        prices = [data.open.value, data.high.value, data.low.value, data.close.value]
        if min(prices) != data.low.value or max(prices) != data.high.value:
            return False
        
        return data.volume >= 0


# Factory Implementations
class ZeroMQConnectionFactory(IConnectionFactory):
    """Factory for creating ZeroMQ connections"""
    
    def __init__(self, context: Optional[zmq.Context] = None):
        self._context = context or zmq.Context()
    
    def create_publisher(self, config: ConnectionConfig) -> IPublisher:
        """Create ZeroMQ publisher"""
        return ZeroMQPublisher(self._context, config)
    
    def create_subscriber(self, config: ConnectionConfig) -> ISubscriber:
        """Create ZeroMQ subscriber"""
        return ZeroMQSubscriber(self._context, config)


class DataProcessorFactory(IProcessorFactory):
    """Factory for creating data processors"""
    
    def __init__(self):
        self._processors: Dict[str, Type[IDataProcessor]] = {
            'tick': TickDataProcessor,
            'bar': BarDataProcessor,
        }
    
    def create_processor(self, processor_type: str) -> IDataProcessor:
        """Create processor by type"""
        processor_class = self._processors.get(processor_type)
        if not processor_class:
            raise ValueError(f"Unknown processor type: {processor_type}")
        
        return processor_class()
    
    def get_supported_types(self) -> List[str]:
        """Get supported processor types"""
        return list(self._processors.keys())
    
    def register_processor(self, name: str, processor_class: Type[IDataProcessor]) -> None:
        """Register custom processor"""
        self._processors[name] = processor_class


# Abstract Factory Pattern
class IServiceFactory(ABC):
    """Abstract factory for creating related services"""
    
    @abstractmethod
    def create_connection_factory(self) -> IConnectionFactory:
        """Create connection factory"""
        pass
    
    @abstractmethod
    def create_processor_factory(self) -> IProcessorFactory:
        """Create processor factory"""
        pass
    
    @abstractmethod
    def create_logger(self, name: str) -> ILogger:
        """Create logger"""
        pass
    
    @abstractmethod
    def create_metrics_collector(self) -> IMetricsCollector:
        """Create metrics collector"""
        pass


class ProductionServiceFactory(IServiceFactory):
    """Production implementation of service factory"""
    
    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._zmq_context = zmq.Context()
    
    def create_connection_factory(self) -> IConnectionFactory:
        """Create production connection factory"""
        return ZeroMQConnectionFactory(self._zmq_context)
    
    def create_processor_factory(self) -> IProcessorFactory:
        """Create production processor factory"""
        return DataProcessorFactory()
    
    def create_logger(self, name: str) -> ILogger:
        """Create production logger"""
        from .logging import ProductionLogger
        return ProductionLogger(name, self._config.get('log_level', 'INFO'))
    
    def create_metrics_collector(self) -> IMetricsCollector:
        """Create production metrics collector"""
        from .metrics import PrometheusMetricsCollector
        return PrometheusMetricsCollector(self._config.get('metrics', {}))


class TestServiceFactory(IServiceFactory):
    """Test implementation of service factory"""
    
    def __init__(self):
        self._logs = []
        self._metrics = {}
    
    def create_connection_factory(self) -> IConnectionFactory:
        """Create test connection factory"""
        from .test_implementations import MockConnectionFactory
        return MockConnectionFactory()
    
    def create_processor_factory(self) -> IProcessorFactory:
        """Create test processor factory"""
        return DataProcessorFactory()
    
    def create_logger(self, name: str) -> ILogger:
        """Create test logger"""
        from .test_implementations import MockLogger
        return MockLogger(name, self._logs)
    
    def create_metrics_collector(self) -> IMetricsCollector:
        """Create test metrics collector"""
        from .test_implementations import MockMetricsCollector
        return MockMetricsCollector(self._metrics)


# Service Locator Pattern (Alternative to DI)
class ServiceLocator:
    """Service locator for managing dependencies"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
            cls._instance._factories = {}
        return cls._instance
    
    def register_service(self, name: str, service: Any) -> None:
        """Register a service"""
        self._services[name] = service
    
    def register_factory(self, name: str, factory: Callable) -> None:
        """Register a factory function"""
        self._factories[name] = factory
    
    def get_service(self, name: str) -> Any:
        """Get a service by name"""
        if name in self._services:
            return self._services[name]
        
        if name in self._factories:
            service = self._factories[name]()
            self._services[name] = service
            return service
        
        raise KeyError(f"Service not found: {name}")
    
    def clear(self) -> None:
        """Clear all services (useful for testing)"""
        self._services.clear()
        self._factories.clear()


# Dependency Injection Container
class DIContainer:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._bindings: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def bind(self, interface: Type, implementation: Callable, singleton: bool = False) -> None:
        """Bind interface to implementation"""
        self._bindings[interface] = (implementation, singleton)
    
    def resolve(self, interface: Type) -> Any:
        """Resolve interface to implementation"""
        if interface in self._singletons:
            return self._singletons[interface]
        
        if interface not in self._bindings:
            raise KeyError(f"No binding for {interface}")
        
        implementation, is_singleton = self._bindings[interface]
        instance = implementation()
        
        if is_singleton:
            self._singletons[interface] = instance
        
        return instance
    
    def clear(self) -> None:
        """Clear all bindings"""
        self._bindings.clear()
        self._singletons.clear()


# Example usage and configuration
def configure_production_container() -> DIContainer:
    """Configure DI container for production"""
    container = DIContainer()
    
    # Bind interfaces to implementations
    container.bind(IConnectionFactory, 
                   lambda: ZeroMQConnectionFactory(), 
                   singleton=True)
    
    container.bind(IProcessorFactory, 
                   lambda: DataProcessorFactory(), 
                   singleton=True)
    
    return container


def configure_test_container() -> DIContainer:
    """Configure DI container for testing"""
    container = DIContainer()
    
    # Bind interfaces to mock implementations
    from .test_implementations import MockConnectionFactory
    
    container.bind(IConnectionFactory, 
                   lambda: MockConnectionFactory(), 
                   singleton=True)
    
    container.bind(IProcessorFactory, 
                   lambda: DataProcessorFactory(), 
                   singleton=True)
    
    return container