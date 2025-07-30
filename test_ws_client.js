#!/usr/bin/env node

const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8081');

ws.on('open', () => {
    console.log('Connected to WebSocket server');
});

ws.on('message', (data) => {
    try {
        const parsed = JSON.parse(data);
        console.log(`${parsed.timestamp} - ${parsed.symbol}: Bid=${parsed.bid}, Ask=${parsed.ask}, Spread=${parsed.spread}`);
    } catch (e) {
        console.log('Raw message:', data.toString());
    }
});

ws.on('error', (error) => {
    console.error('WebSocket error:', error);
});

ws.on('close', () => {
    console.log('Disconnected from WebSocket server');
});

console.log('Attempting to connect to ws://localhost:8081...');