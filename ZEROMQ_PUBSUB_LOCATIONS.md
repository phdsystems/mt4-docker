# ZeroMQ Publisher/Subscriber Locations

## Architecture Overview

```
┌──────────────────┐      ┌─────────────────────────┐      ┌──────────────────┐
│   MT4 Terminal   │      │   ZeroMQ Bridge         │      │   Subscribers    │
│                  │      │   (PUBLISHER)           │      │                  │
│ ZeroMQStreamer   │─────▶│ zmq_bridge.py          │─────▶│ Python Client    │
│     EA           │ JSON │                         │ TCP  │ Node.js Client   │
│                  │ Pipe │ ● socket(zmq.PUB)      │ 5556 │ Web Dashboard    │
└──────────────────┘      │ ● bind("tcp://*:5556") │      └──────────────────┘
                          │ ● send_multipart()      │
                          └─────────────────────────┘
```

## Publisher Location

### File: `/workspace/mt4-docker/services/zeromq_bridge/zmq_bridge.py`

**Key Publisher Code:**
```python
class ZeroMQBridge:
    def setup_publisher(self):
        # Line 43: Create PUB socket
        self.publisher = self.context.socket(zmq.PUB)
        
        # Line 47: Bind to addresses (accepts connections)
        self.publisher.bind("tcp://*:5556")
        self.publisher.bind("ipc:///tmp/mt4_market_data")
    
    def publish_tick(self, tick_data):
        # Line 72-74: Send multipart message
        self.publisher.send_multipart([
            topic.encode('utf-8'),        # Topic for filtering
            json.dumps(message).encode()  # JSON data
        ])
```

**Publisher Characteristics:**
- Socket type: `zmq.PUB`
- Binds to addresses (server role)
- Sends to all connected subscribers
- Fire-and-forget (no acknowledgments)

## Subscriber Locations

### 1. Python Client: `/workspace/mt4-docker/clients/python/zmq_market_client.py`

**Key Subscriber Code:**
```python
class ZMQMarketClient:
    def connect(self):
        # Line 56: Create SUB socket
        self.subscriber = self.context.socket(zmq.SUB)
        
        # Line 62: Connect to publisher
        self.subscriber.connect("tcp://localhost:5556")
        
        # Line 67: Subscribe to topics
        self.subscriber.subscribe("tick.EURUSD".encode())
    
    def run(self):
        # Line 139: Receive messages
        topic, data = self.subscriber.recv_multipart()
```

### 2. Node.js Client: `/workspace/mt4-docker/clients/nodejs/zmq_client.js`

**Key Subscriber Code:**
```javascript
class ZMQMarketClient {
    async connect() {
        // Create SUB socket
        this.subscriber = new zmq.Subscriber();
        
        // Connect to publisher
        await this.subscriber.connect("tcp://localhost:5556");
        
        // Subscribe to topics
        this.subscriber.subscribe("tick.EURUSD");
    }
    
    async run() {
        // Receive messages
        const [topic, data] = await this.subscriber.receive();
    }
}
```

**Subscriber Characteristics:**
- Socket type: `zmq.SUB`
- Connects to addresses (client role)
- Must subscribe to topics (or "" for all)
- Can connect to multiple publishers

## Data Flow Example

1. **MT4 EA** writes to named pipe:
   ```json
   {"type":"tick","symbol":"EURUSD","bid":1.08456,"ask":1.08459}
   ```

2. **ZMQ Bridge** reads and publishes:
   ```python
   # Publishes as multipart message:
   ["tick.EURUSD", '{"type":"tick","symbol":"EURUSD",...}']
   ```

3. **Subscribers** receive based on subscription:
   ```python
   # Only receives if subscribed to "tick.EURUSD" or ""
   topic, data = subscriber.recv_multipart()
   ```

## Running the System

### Start Publisher (Bridge):
```bash
cd /workspace/mt4-docker
python services/zeromq_bridge/zmq_bridge.py
```

### Start Subscriber (Client):
```bash
# Python
python clients/python/zmq_market_client.py

# Node.js
node clients/nodejs/zmq_client.js
```

## Topic Filtering

The pub/sub pattern uses topics for message filtering:

- `tick.EURUSD` - Only EURUSD ticks
- `tick.` - All ticks
- `bar.EURUSD.M1` - EURUSD M1 bars
- `` (empty) - All messages

Subscribers only receive messages matching their subscriptions, reducing network traffic and processing overhead.