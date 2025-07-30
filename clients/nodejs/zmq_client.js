#!/usr/bin/env node
/**
 * ZeroMQ Market Data Client for Node.js
 * High-performance subscriber for MT4 market data
 */

const zmq = require('zeromq');

class ZMQMarketClient {
    constructor(config = {}) {
        this.config = {
            addresses: config.addresses || ['tcp://localhost:5556'],
            topics: config.topics || [''],  // Empty string subscribes to all
            highWaterMark: config.highWaterMark || 1000,
            ...config
        };
        
        this.subscriber = null;
        this.running = false;
        
        // Callbacks
        this.onTick = null;
        this.onBar = null;
        this.onError = null;
        this.onConnect = null;
        this.onDisconnect = null;
        
        // Statistics
        this.stats = {
            messagesReceived: 0,
            bytesReceived: 0,
            startTime: null,
            lastMessageTime: null,
            symbols: new Set()
        };
    }
    
    async connect() {
        // Create subscriber socket
        this.subscriber = new zmq.Subscriber();
        this.subscriber.receiveHighWaterMark = this.config.highWaterMark;
        
        // Connect to all addresses
        for (const address of this.config.addresses) {
            await this.subscriber.connect(address);
            console.log(`Connected to ${address}`);
        }
        
        // Subscribe to topics
        for (const topic of this.config.topics) {
            this.subscriber.subscribe(topic);
            if (topic) {
                console.log(`Subscribed to topic: ${topic}`);
            } else {
                console.log('Subscribed to all topics');
            }
        }
        
        if (this.onConnect) {
            this.onConnect();
        }
    }
    
    async disconnect() {
        this.running = false;
        
        if (this.subscriber) {
            await this.subscriber.close();
        }
        
        if (this.onDisconnect) {
            this.onDisconnect();
        }
    }
    
    subscribeSymbol(symbol) {
        if (this.subscriber) {
            this.subscriber.subscribe(`tick.${symbol}`);
            this.subscriber.subscribe(`bar.${symbol}`);
        }
    }
    
    unsubscribeSymbol(symbol) {
        if (this.subscriber) {
            this.subscriber.unsubscribe(`tick.${symbol}`);
            this.subscriber.unsubscribe(`bar.${symbol}`);
        }
    }
    
    processMessage(topic, data) {
        try {
            const message = JSON.parse(data.toString());
            
            // Update statistics
            this.stats.messagesReceived++;
            this.stats.bytesReceived += data.length;
            this.stats.lastMessageTime = Date.now();
            
            // Route message by type
            const msgType = message.type;
            
            if (msgType === 'tick') {
                this.stats.symbols.add(message.symbol || 'UNKNOWN');
                if (this.onTick) {
                    this.onTick(message);
                }
            } else if (msgType === 'bar') {
                if (this.onBar) {
                    this.onBar(message);
                }
            }
            
        } catch (error) {
            if (this.onError) {
                this.onError(`Message processing error: ${error}`);
            }
        }
    }
    
    async run() {
        this.running = true;
        this.stats.startTime = Date.now();
        
        try {
            while (this.running) {
                // Receive multipart message [topic, data]
                const [topic, data] = await this.subscriber.receive();
                this.processMessage(topic.toString(), data);
            }
        } catch (error) {
            if (this.onError) {
                this.onError(`ZMQ error: ${error}`);
            }
        }
    }
    
    async start() {
        await this.connect();
        
        // Run in background
        this.run().catch(error => {
            if (this.onError) {
                this.onError(`Runtime error: ${error}`);
            }
        });
    }
    
    async stop() {
        this.running = false;
        await this.disconnect();
    }
    
    getStats() {
        const uptime = this.stats.startTime 
            ? (Date.now() - this.stats.startTime) / 1000 
            : 0;
        
        const rate = uptime > 0 
            ? this.stats.messagesReceived / uptime 
            : 0;
        
        return {
            messagesReceived: this.stats.messagesReceived,
            bytesReceived: this.stats.bytesReceived,
            messageRate: rate,
            symbolsCount: this.stats.symbols.size,
            symbols: Array.from(this.stats.symbols),
            uptimeSeconds: uptime,
            lastMessage: this.stats.lastMessageTime
        };
    }
}

// Example usage
if (require.main === module) {
    // Create client
    const client = new ZMQMarketClient({
        addresses: ['tcp://localhost:5556'],
        topics: ['tick.EURUSD', 'tick.GBPUSD']
    });
    
    // Define callbacks
    client.onTick = (tick) => {
        console.log(`Tick: ${tick.symbol} - Bid: ${tick.bid}, Ask: ${tick.ask}`);
    };
    
    client.onError = (error) => {
        console.error(`Error: ${error}`);
    };
    
    client.onConnect = () => {
        console.log('Connected to market data feed');
    };
    
    // Start client
    console.log('Starting ZeroMQ market data client...');
    client.start();
    
    // Run for 30 seconds
    setTimeout(async () => {
        const stats = client.getStats();
        console.log('\nStatistics:');
        console.log(`Messages received: ${stats.messagesReceived}`);
        console.log(`Message rate: ${stats.messageRate.toFixed(1)} msg/s`);
        console.log(`Symbols: ${stats.symbols.join(', ')}`);
        
        await client.stop();
        process.exit(0);
    }, 30000);
    
    // Handle shutdown
    process.on('SIGINT', async () => {
        console.log('\nShutting down...');
        await client.stop();
        process.exit(0);
    });
}

module.exports = ZMQMarketClient;