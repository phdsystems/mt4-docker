#!/usr/bin/env node
/**
 * Market Data Client v2 - ES6 Classes with Better OOP
 * Demonstrates modern JavaScript OOP patterns
 */

const zmq = require('zeromq');
const EventEmitter = require('events');

// Base classes and interfaces
class IConnection {
    async connect() {
        throw new Error('Method connect() must be implemented');
    }
    
    async disconnect() {
        throw new Error('Method disconnect() must be implemented');
    }
    
    async subscribe(topic) {
        throw new Error('Method subscribe() must be implemented');
    }
    
    async receive() {
        throw new Error('Method receive() must be implemented');
    }
}

// Value Objects
class Symbol {
    constructor(name) {
        if (!name || typeof name !== 'string') {
            throw new Error('Symbol name must be a non-empty string');
        }
        this._name = name;
        Object.freeze(this);
    }
    
    get name() {
        return this._name;
    }
    
    toString() {
        return this._name;
    }
}

class Price {
    constructor(value) {
        if (typeof value !== 'number' || value < 0) {
            throw new Error('Price must be a non-negative number');
        }
        this._value = value;
        Object.freeze(this);
    }
    
    get value() {
        return this._value;
    }
    
    toString() {
        return this._value.toFixed(5);
    }
}

class MarketTick {
    constructor({ symbol, bid, ask, timestamp, volume = null }) {
        this.symbol = symbol instanceof Symbol ? symbol : new Symbol(symbol);
        this.bid = bid instanceof Price ? bid : new Price(bid);
        this.ask = ask instanceof Price ? ask : new Price(ask);
        this.timestamp = timestamp instanceof Date ? timestamp : new Date(timestamp);
        this.volume = volume;
        Object.freeze(this);
    }
    
    get spread() {
        return this.ask.value - this.bid.value;
    }
    
    get midPrice() {
        return (this.bid.value + this.ask.value) / 2;
    }
    
    toJSON() {
        return {
            symbol: this.symbol.name,
            bid: this.bid.value,
            ask: this.ask.value,
            timestamp: this.timestamp.toISOString(),
            volume: this.volume
        };
    }
}

// ZeroMQ Connection Implementation
class ZeroMQConnection extends IConnection {
    constructor(addresses = ['tcp://localhost:5556']) {
        super();
        this._addresses = addresses;
        this._socket = null;
        this._connected = false;
    }
    
    async connect() {
        if (this._connected) {
            throw new Error('Already connected');
        }
        
        this._socket = new zmq.Subscriber();
        
        for (const address of this._addresses) {
            this._socket.connect(address);
            console.log(`Connected to ${address}`);
        }
        
        this._connected = true;
    }
    
    async disconnect() {
        if (!this._connected) {
            return;
        }
        
        this._socket.close();
        this._socket = null;
        this._connected = false;
        console.log('Disconnected');
    }
    
    async subscribe(topic) {
        if (!this._connected) {
            throw new Error('Not connected');
        }
        
        this._socket.subscribe(topic);
        console.log(`Subscribed to ${topic || 'all topics'}`);
    }
    
    async receive() {
        if (!this._connected) {
            throw new Error('Not connected');
        }
        
        const [topic, message] = await this._socket.receive();
        return {
            topic: topic.toString(),
            data: JSON.parse(message.toString())
        };
    }
    
    get isConnected() {
        return this._connected;
    }
}

// Strategy Pattern for Message Processing
class MessageProcessingStrategy {
    canProcess(topic, data) {
        return true;
    }
    
    process(topic, data) {
        throw new Error('Method process() must be implemented');
    }
}

class TickProcessingStrategy extends MessageProcessingStrategy {
    canProcess(topic, data) {
        return topic.startsWith('tick.');
    }
    
    process(topic, data) {
        return new MarketTick(data);
    }
}

// Observer Pattern Implementation
class MarketDataObservable extends EventEmitter {
    constructor() {
        super();
        this._observers = new Set();
    }
    
    attach(observer) {
        if (typeof observer.update !== 'function') {
            throw new Error('Observer must implement update() method');
        }
        this._observers.add(observer);
    }
    
    detach(observer) {
        this._observers.delete(observer);
    }
    
    notify(event, data) {
        // Emit event for EventEmitter compatibility
        this.emit(event, data);
        
        // Notify observers
        for (const observer of this._observers) {
            try {
                observer.update(event, data);
            } catch (error) {
                console.error('Observer error:', error);
            }
        }
    }
}

// Main Market Data Client
class MarketDataClient extends MarketDataObservable {
    constructor(connection, strategies = []) {
        super();
        this._connection = connection;
        this._strategies = strategies;
        this._running = false;
        this._statistics = new MarketDataStatistics();
        this._messageQueue = [];
        this._processingInterval = null;
    }
    
    async start() {
        if (this._running) {
            throw new Error('Client already running');
        }
        
        await this._connection.connect();
        this._running = true;
        this._startProcessing();
        
        console.log('Market data client started');
    }
    
    async stop() {
        this._running = false;
        
        if (this._processingInterval) {
            clearInterval(this._processingInterval);
        }
        
        await this._connection.disconnect();
        console.log('Market data client stopped');
    }
    
    async subscribeSymbol(symbol) {
        const symbolObj = symbol instanceof Symbol ? symbol : new Symbol(symbol);
        await this._connection.subscribe(`tick.${symbolObj.name}`);
        await this._connection.subscribe(`bar.${symbolObj.name}`);
    }
    
    async subscribeAll() {
        await this._connection.subscribe('');
    }
    
    _startProcessing() {
        // Receive messages
        this._receiveLoop();
        
        // Process messages from queue
        this._processingInterval = setInterval(() => {
            this._processQueue();
        }, 10);
    }
    
    async _receiveLoop() {
        while (this._running) {
            try {
                const message = await this._connection.receive();
                this._messageQueue.push(message);
            } catch (error) {
                if (this._running) {
                    console.error('Receive error:', error);
                    this.notify('error', error);
                }
            }
        }
    }
    
    _processQueue() {
        while (this._messageQueue.length > 0) {
            const message = this._messageQueue.shift();
            this._processMessage(message);
        }
    }
    
    _processMessage({ topic, data }) {
        try {
            // Find appropriate strategy
            for (const strategy of this._strategies) {
                if (strategy.canProcess(topic, data)) {
                    const processed = strategy.process(topic, data);
                    this._handleProcessedData(topic, processed);
                    break;
                }
            }
        } catch (error) {
            console.error('Processing error:', error);
            this._statistics.recordError();
            this.notify('error', error);
        }
    }
    
    _handleProcessedData(topic, data) {
        if (data instanceof MarketTick) {
            this._statistics.recordTick(data);
            this.notify('tick', data);
        }
        // Add more data types as needed
    }
    
    getStatistics() {
        return this._statistics.getSummary();
    }
}

// Statistics Collector
class MarketDataStatistics {
    constructor() {
        this._startTime = Date.now();
        this._tickCount = 0;
        this._errorCount = 0;
        this._symbolStats = new Map();
    }
    
    recordTick(tick) {
        this._tickCount++;
        
        const symbolName = tick.symbol.name;
        if (!this._symbolStats.has(symbolName)) {
            this._symbolStats.set(symbolName, { ticks: 0, lastTick: null });
        }
        
        const stats = this._symbolStats.get(symbolName);
        stats.ticks++;
        stats.lastTick = tick;
    }
    
    recordError() {
        this._errorCount++;
    }
    
    getSummary() {
        const uptime = (Date.now() - this._startTime) / 1000;
        
        return {
            uptimeSeconds: uptime,
            totalTicks: this._tickCount,
            totalErrors: this._errorCount,
            ticksPerSecond: this._tickCount / uptime,
            symbolCount: this._symbolStats.size,
            symbols: Array.from(this._symbolStats.keys()),
            symbolStats: Object.fromEntries(
                Array.from(this._symbolStats.entries()).map(([symbol, stats]) => [
                    symbol,
                    {
                        ticks: stats.ticks,
                        lastBid: stats.lastTick?.bid.value,
                        lastAsk: stats.lastTick?.ask.value
                    }
                ])
            )
        };
    }
}

// Builder Pattern
class MarketDataClientBuilder {
    constructor() {
        this._addresses = ['tcp://localhost:5556'];
        this._strategies = [];
    }
    
    withAddresses(addresses) {
        this._addresses = addresses;
        return this;
    }
    
    withStrategy(strategy) {
        this._strategies.push(strategy);
        return this;
    }
    
    build() {
        const connection = new ZeroMQConnection(this._addresses);
        
        // Add default strategies if none provided
        if (this._strategies.length === 0) {
            this._strategies.push(new TickProcessingStrategy());
        }
        
        return new MarketDataClient(connection, this._strategies);
    }
}

// Example Observer
class ConsoleObserver {
    update(event, data) {
        if (event === 'tick') {
            console.log(`[TICK] ${data.symbol.name} Bid: ${data.bid} Ask: ${data.ask} Spread: ${data.spread.toFixed(5)}`);
        } else if (event === 'error') {
            console.error(`[ERROR] ${data.message}`);
        }
    }
}

// Usage Example
async function main() {
    // Build client using builder pattern
    const client = new MarketDataClientBuilder()
        .withAddresses(['tcp://localhost:5556', 'tcp://localhost:5557'])
        .withStrategy(new TickProcessingStrategy())
        .build();
    
    // Add observers
    const consoleObserver = new ConsoleObserver();
    client.attach(consoleObserver);
    
    // Add event listeners
    client.on('tick', (tick) => {
        // Additional processing
    });
    
    try {
        // Start client
        await client.start();
        
        // Subscribe to symbols
        await client.subscribeSymbol('EURUSD');
        await client.subscribeSymbol('GBPUSD');
        
        // Run for 30 seconds
        setTimeout(async () => {
            const stats = client.getStatistics();
            console.log('\nStatistics:', JSON.stringify(stats, null, 2));
            
            await client.stop();
            process.exit(0);
        }, 30000);
        
    } catch (error) {
        console.error('Client error:', error);
        process.exit(1);
    }
}

// Export for use as module
module.exports = {
    MarketDataClient,
    MarketDataClientBuilder,
    ZeroMQConnection,
    Symbol,
    Price,
    MarketTick,
    TickProcessingStrategy,
    ConsoleObserver
};

// Run if executed directly
if (require.main === module) {
    console.log('Market Data Client v2 - ES6 OOP Implementation');
    console.log('Features:');
    console.log('- ES6 Classes with inheritance');
    console.log('- Value objects with validation');
    console.log('- Strategy pattern');
    console.log('- Observer pattern');
    console.log('- Builder pattern');
    console.log('- Async/await support');
    console.log('- Event-driven architecture\n');
    
    main().catch(console.error);
}