/**
 * WebSocket Client for MT4 Market Data
 * Browser and Node.js compatible
 */

class MT4WebSocketClient {
    constructor(url = 'ws://localhost:8765', options = {}) {
        this.url = url;
        this.options = {
            reconnectInterval: 5000,
            maxReconnectAttempts: 10,
            heartbeatInterval: 30000,
            debug: false,
            ...options
        };
        
        this.ws = null;
        this.clientId = null;
        this.authenticated = false;
        this.tier = 'free';
        this.subscriptions = new Set();
        this.eventHandlers = new Map();
        this.reconnectAttempts = 0;
        this.heartbeatTimer = null;
        this.reconnectTimer = null;
        
        // Default event handlers
        this.on('welcome', (data) => {
            this.clientId = data.client_id;
            this.startHeartbeat();
            if (this.options.debug) {
                console.log('Connected to server:', data);
            }
        });
        
        this.on('auth_success', (data) => {
            this.authenticated = true;
            this.tier = data.tier;
            if (this.options.debug) {
                console.log('Authenticated with tier:', data.tier);
            }
        });
        
        this.on('tick', (data) => {
            this.emit('marketData', data.data);
        });
        
        this.on('error', (data) => {
            console.error('Server error:', data.error);
        });
        
        this.on('rate_limit', (data) => {
            console.warn('Rate limited. Retry after:', data.retry_after, 'seconds');
        });
    }
    
    /**
     * Connect to WebSocket server
     */
    connect() {
        return new Promise((resolve, reject) => {
            try {
                // Use appropriate WebSocket implementation
                const WebSocketImpl = typeof WebSocket !== 'undefined' ? WebSocket : require('ws');
                this.ws = new WebSocketImpl(this.url);
                
                this.ws.onopen = () => {
                    this.reconnectAttempts = 0;
                    resolve();
                };
                
                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    } catch (e) {
                        console.error('Failed to parse message:', e);
                    }
                };
                
                this.ws.onclose = () => {
                    this.stopHeartbeat();
                    this.emit('disconnected');
                    this.handleReconnect();
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    reject(error);
                };
                
            } catch (error) {
                reject(error);
            }
        });
    }
    
    /**
     * Disconnect from server
     */
    disconnect() {
        this.stopHeartbeat();
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        if (this.ws && this.ws.readyState === this.ws.OPEN) {
            this.ws.close();
        }
        
        this.ws = null;
        this.authenticated = false;
        this.subscriptions.clear();
    }
    
    /**
     * Authenticate with JWT token
     */
    authenticate(token) {
        return this.send({
            type: 'authenticate',
            token: token
        });
    }
    
    /**
     * Subscribe to market symbols
     */
    subscribe(symbols) {
        if (!Array.isArray(symbols)) {
            symbols = [symbols];
        }
        
        symbols.forEach(symbol => this.subscriptions.add(symbol.toUpperCase()));
        
        return this.send({
            type: 'subscribe',
            symbols: symbols
        });
    }
    
    /**
     * Unsubscribe from symbols
     */
    unsubscribe(symbols) {
        if (!Array.isArray(symbols)) {
            symbols = [symbols];
        }
        
        symbols.forEach(symbol => this.subscriptions.delete(symbol.toUpperCase()));
        
        return this.send({
            type: 'unsubscribe',
            symbols: symbols
        });
    }
    
    /**
     * Get server statistics (premium feature)
     */
    getStats() {
        return this.send({
            type: 'get_stats'
        });
    }
    
    /**
     * Send message to server
     */
    send(data) {
        return new Promise((resolve, reject) => {
            if (!this.ws || this.ws.readyState !== this.ws.OPEN) {
                reject(new Error('WebSocket not connected'));
                return;
            }
            
            try {
                this.ws.send(JSON.stringify(data));
                resolve();
            } catch (error) {
                reject(error);
            }
        });
    }
    
    /**
     * Register event handler
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }
    
    /**
     * Remove event handler
     */
    off(event, handler) {
        if (!this.eventHandlers.has(event)) return;
        
        const handlers = this.eventHandlers.get(event);
        const index = handlers.indexOf(handler);
        if (index !== -1) {
            handlers.splice(index, 1);
        }
    }
    
    /**
     * Emit event
     */
    emit(event, data) {
        if (!this.eventHandlers.has(event)) return;
        
        this.eventHandlers.get(event).forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in ${event} handler:`, error);
            }
        });
    }
    
    /**
     * Handle incoming message
     */
    handleMessage(data) {
        const messageType = data.type;
        
        if (this.options.debug) {
            console.log('Received:', data);
        }
        
        // Emit specific event
        this.emit(messageType, data);
        
        // Emit generic message event
        this.emit('message', data);
    }
    
    /**
     * Start heartbeat
     */
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.heartbeatTimer = setInterval(() => {
            this.send({ type: 'ping' }).catch(() => {
                // Connection lost
                this.stopHeartbeat();
            });
        }, this.options.heartbeatInterval);
    }
    
    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * Handle reconnection
     */
    handleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('maxReconnectAttemptsReached');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.options.reconnectInterval * this.reconnectAttempts;
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        this.reconnectTimer = setTimeout(() => {
            this.connect()
                .then(() => {
                    console.log('Reconnected successfully');
                    this.emit('reconnected');
                    
                    // Re-subscribe to symbols
                    if (this.subscriptions.size > 0) {
                        this.subscribe(Array.from(this.subscriptions));
                    }
                })
                .catch(() => {
                    // Will trigger another reconnect attempt
                });
        }, delay);
    }
}

// Export for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MT4WebSocketClient;
}

// Example usage
if (typeof window === 'undefined') {
    // Node.js example
    const client = new MT4WebSocketClient('ws://localhost:8765', { debug: true });
    
    // Register event handlers
    client.on('marketData', (data) => {
        console.log('Market data:', data);
    });
    
    client.on('subscribed', (data) => {
        console.log('Subscribed to:', data.symbols);
    });
    
    // Connect and subscribe
    async function example() {
        try {
            await client.connect();
            
            // Authenticate (optional)
            // await client.authenticate('your-jwt-token');
            
            // Subscribe to symbols
            await client.subscribe(['EURUSD', 'GBPUSD', 'USDJPY']);
            
            // Get stats (premium feature)
            // await client.getStats();
            
        } catch (error) {
            console.error('Connection error:', error);
        }
    }
    
    // Run example
    // example();
}