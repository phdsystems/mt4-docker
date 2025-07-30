#!/usr/bin/env node

const MT4WebSocketBridge = require('./clients/nodejs/websocket_bridge.js');

// Create bridge with explicit file mode
const bridge = new MT4WebSocketBridge({
    mode: 'file',
    csvFile: 'market_data.csv',
    wsPort: 8080
});

console.log('Starting WebSocket bridge with config:', bridge.config);
bridge.start();