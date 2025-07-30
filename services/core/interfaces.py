#!/usr/bin/env python3
"""
Core interfaces and abstract base classes for the MT4 Docker project
Defines contracts for all major components
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Protocol
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto


# Enumerations
class ConnectionState(Enum):
    """Connection state enumeration"""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTING = auto()
    ERROR = auto()


class DataType(Enum):
    """Market data type enumeration"""
    TICK = "tick"
    BAR = "bar"
    DEPTH = "depth"
    TRADE = "trade"


# Domain Models
@dataclass
class ConnectionConfig:
    """Configuration for connections"""
    addresses: List[str]
    timeout: int = 5000
    retry_count: int = 3
    retry_delay: int = 1000
    heartbeat_interval: int = 30000


# Core Interfaces
class ILifecycle(ABC):
    """Interface for components with lifecycle"""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the component"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the component"""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if component is running"""
        pass


class IConnection(ABC):
    """Interface for network connections"""
    
    @abstractmethod
    async def connect(self, config: ConnectionConfig) -> None:
        """Establish connection"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection"""
        pass
    
    @abstractmethod
    def get_state(self) -> ConnectionState:
        """Get current connection state"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check"""
        pass


class IPublisher(ABC):
    """Interface for message publishers"""
    
    @abstractmethod
    async def publish(self, topic: str, data: Any) -> None:
        """Publish data to topic"""
        pass
    
    @abstractmethod
    async def publish_batch(self, messages: List[tuple]) -> None:
        """Publish multiple messages"""
        pass


class ISubscriber(ABC):
    """Interface for message subscribers"""
    
    @abstractmethod
    async def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, topics: List[str]) -> None:
        """Unsubscribe from topics"""
        pass
    
    @abstractmethod
    async def receive(self, timeout: Optional[int] = None) -> Optional[tuple]:
        """Receive message"""
        pass


class IDataSource(ABC):
    """Interface for market data sources"""
    
    @abstractmethod
    def register_handler(self, data_type: DataType, handler: Callable) -> None:
        """Register data handler"""
        pass
    
    @abstractmethod
    def unregister_handler(self, data_type: DataType) -> None:
        """Unregister data handler"""
        pass
    
    @abstractmethod
    async def start_streaming(self) -> None:
        """Start data streaming"""
        pass
    
    @abstractmethod
    async def stop_streaming(self) -> None:
        """Stop data streaming"""
        pass


class IDataProcessor(ABC):
    """Interface for data processors"""
    
    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Optional[Any]:
        """Process raw data"""
        pass
    
    @abstractmethod
    def validate(self, data: Any) -> bool:
        """Validate processed data"""
        pass


class IDataStore(ABC):
    """Interface for data storage"""
    
    @abstractmethod
    async def save(self, key: str, data: Any) -> None:
        """Save data"""
        pass
    
    @abstractmethod
    async def load(self, key: str) -> Optional[Any]:
        """Load data"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete data"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass


class IMetricsCollector(ABC):
    """Interface for metrics collection"""
    
    @abstractmethod
    def increment(self, metric: str, value: float = 1.0, tags: Optional[Dict] = None) -> None:
        """Increment a counter"""
        pass
    
    @abstractmethod
    def gauge(self, metric: str, value: float, tags: Optional[Dict] = None) -> None:
        """Set a gauge value"""
        pass
    
    @abstractmethod
    def histogram(self, metric: str, value: float, tags: Optional[Dict] = None) -> None:
        """Record a histogram value"""
        pass
    
    @abstractmethod
    def timing(self, metric: str, value: float, tags: Optional[Dict] = None) -> None:
        """Record a timing"""
        pass


class ILogger(ABC):
    """Interface for logging"""
    
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        pass
    
    @abstractmethod
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log error message"""
        pass


# Protocol Classes (for type checking)
class MarketDataHandler(Protocol):
    """Protocol for market data handlers"""
    
    def on_tick(self, symbol: str, bid: float, ask: float, timestamp: datetime) -> None:
        """Handle tick data"""
        ...
    
    def on_bar(self, symbol: str, timeframe: str, ohlcv: Dict[str, float], timestamp: datetime) -> None:
        """Handle bar data"""
        ...
    
    def on_error(self, error: Exception) -> None:
        """Handle error"""
        ...


class ConfigProvider(Protocol):
    """Protocol for configuration providers"""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        ...
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        ...
    
    def reload(self) -> None:
        """Reload configuration"""
        ...


# Factory Interfaces
class IConnectionFactory(ABC):
    """Factory interface for creating connections"""
    
    @abstractmethod
    def create_publisher(self, config: ConnectionConfig) -> IPublisher:
        """Create publisher connection"""
        pass
    
    @abstractmethod
    def create_subscriber(self, config: ConnectionConfig) -> ISubscriber:
        """Create subscriber connection"""
        pass


class IProcessorFactory(ABC):
    """Factory interface for creating processors"""
    
    @abstractmethod
    def create_processor(self, processor_type: str) -> IDataProcessor:
        """Create data processor"""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """Get list of supported processor types"""
        pass


# Service Interfaces
class IService(ILifecycle):
    """Base interface for services"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get service name"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check"""
        pass


class IBridge(IService):
    """Interface for bridge services"""
    
    @abstractmethod
    def set_source(self, source: IDataSource) -> None:
        """Set data source"""
        pass
    
    @abstractmethod
    def set_publisher(self, publisher: IPublisher) -> None:
        """Set publisher"""
        pass
    
    @abstractmethod
    def add_processor(self, processor: IDataProcessor) -> None:
        """Add data processor"""
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        pass


# Repository Pattern
class IRepository(ABC):
    """Generic repository interface"""
    
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[Any]:
        """Find entity by ID"""
        pass
    
    @abstractmethod
    async def find_all(self, filters: Optional[Dict] = None) -> List[Any]:
        """Find all entities matching filters"""
        pass
    
    @abstractmethod
    async def save(self, entity: Any) -> str:
        """Save entity and return ID"""
        pass
    
    @abstractmethod
    async def update(self, id: str, entity: Any) -> bool:
        """Update entity"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity"""
        pass


# Unit of Work Pattern
class IUnitOfWork(ABC):
    """Interface for unit of work pattern"""
    
    @abstractmethod
    async def __aenter__(self):
        """Enter context"""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        pass
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit changes"""
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        """Rollback changes"""
        pass
    
    @abstractmethod
    def get_repository(self, name: str) -> IRepository:
        """Get repository by name"""
        pass