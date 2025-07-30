#!/usr/bin/env node
/**
 * MT4 WebSocket Bridge
 * Bridges MT4 market data to WebSocket clients
 */

const fs = require('fs');
const net = require('net');
const WebSocket = require('ws');
const readline = require('readline');
const path = require('path');

class MT4WebSocketBridge {
    constructor(config = {}) {
        this.config = {
            wsPort: config.wsPort || 8080,
            pipeName: config.pipeName || 'MT4_MarketData',
            csvFile: config.csvFile || 'market_data.csv',
            mode: config.mode || 'file', // 'pipe' or 'file' - defaulting to file
            ...config
        };
        
        this.clients = new Set();
        this.lastData = new Map();
        this.stats = {
            messagesReceived: 0,
            messagesSent: 0,
            clientsConnected: 0
        };
    }
    
    start() {
        // Start WebSocket server
        this.wss = new WebSocket.Server({ port: this.config.wsPort });
        console.log(`WebSocket server started on port ${this.config.wsPort}`);
        
        this.wss.on('connection', (ws, req) => {
            const clientIp = req.socket.remoteAddress;
            console.log(`New WebSocket client connected from ${clientIp}`);
            
            this.clients.add(ws);
            this.stats.clientsConnected = this.clients.size;
            
            // Send current data snapshot
            this.sendSnapshot(ws);
            
            ws.on('message', (message) => {
                this.handleClientMessage(ws, message);
            });
            
            ws.on('close', () => {
                this.clients.delete(ws);
                this.stats.clientsConnected = this.clients.size;
                console.log(`Client disconnected. Active clients: ${this.clients.size}`);
            });
            
            ws.on('error', (error) => {
                console.error('WebSocket error:', error);
            });
        });
        
        // Connect to MT4 data source
        if (this.config.mode === 'pipe') {
            this.connectToPipe();
        } else {
            this.watchCsvFile();
        }
        
        // Start stats reporting
        setInterval(() => this.reportStats(), 30000);
    }
    
    connectToPipe() {
        const pipePath = process.platform === 'win32' 
            ? `\\\\.\\pipe\\${this.config.pipeName}`
            : `/tmp/${this.config.pipeName}`;
            
        console.log(`Connecting to pipe: ${pipePath}`);
        
        if (process.platform === 'win32') {
            // Windows named pipe
            const client = net.connect(pipePath);
            
            client.on('connect', () => {
                console.log('Connected to MT4 pipe');
            });
            
            client.on('data', (data) => {
                this.processPipeData(data.toString());
            });
            
            client.on('error', (err) => {
                console.error('Pipe error:', err);
                setTimeout(() => this.connectToPipe(), 5000);
            });
            
            client.on('end', () => {
                console.log('Pipe disconnected, reconnecting...');
                setTimeout(() => this.connectToPipe(), 5000);
            });
            
            this.pipeClient = client;
        } else {
            // Unix named pipe (FIFO)
            if (!fs.existsSync(pipePath)) {
                console.log('Creating FIFO...');
                require('child_process').execSync(`mkfifo ${pipePath}`);
            }
            
            const stream = fs.createReadStream(pipePath);
            const rl = readline.createInterface({
                input: stream,
                crlfDelay: Infinity
            });
            
            rl.on('line', (line) => {
                this.processPipeData(line);
            });
            
            rl.on('error', (err) => {
                console.error('Pipe error:', err);
                setTimeout(() => this.connectToPipe(), 5000);
            });
        }
    }
    
    watchCsvFile() {
        console.log(`Watching CSV file: ${this.config.csvFile}`);
        
        let lastSize = 0;
        
        const processFile = () => {
            fs.stat(this.config.csvFile, (err, stats) => {
                if (err) {
                    console.error('File not found:', this.config.csvFile);
                    return;
                }
                
                if (stats.size > lastSize) {
                    const stream = fs.createReadStream(this.config.csvFile, {
                        start: lastSize,
                        end: stats.size
                    });
                    
                    const rl = readline.createInterface({
                        input: stream,
                        crlfDelay: Infinity
                    });
                    
                    rl.on('line', (line) => {
                        this.processCsvLine(line);
                    });
                    
                    lastSize = stats.size;
                }
            });
        };
        
        // Initial read
        processFile();
        
        // Watch for changes
        fs.watchFile(this.config.csvFile, { interval: 100 }, processFile);
    }
    
    processPipeData(data) {
        const lines = data.split('\n');
        
        for (const line of lines) {
            if (line.trim()) {
                try {
                    const message = JSON.parse(line);
                    this.handleMarketData(message);
                } catch (e) {
                    console.error('JSON parse error:', e);
                }
            }
        }
    }
    
    processCsvLine(line) {
        if (!line.trim() || line.startsWith('Timestamp')) return;
        
        const parts = line.split(',');
        if (parts.length >= 6) {
            const message = {
                type: 'quote',
                symbol: parts[1],
                timestamp: parts[0],
                bid: parseFloat(parts[2]),
                ask: parseFloat(parts[3]),
                spread: parseFloat(parts[4]),
                volume: parseInt(parts[5])
            };
            
            if (parts.length >= 11) {
                message.bar = {
                    open: parseFloat(parts[6]),
                    high: parseFloat(parts[7]),
                    low: parseFloat(parts[8]),
                    close: parseFloat(parts[9]),
                    volume: parseInt(parts[10])
                };
            }
            
            this.handleMarketData(message);
        }
    }
    
    handleMarketData(message) {
        this.stats.messagesReceived++;
        
        // Store latest data
        if (message.symbol) {
            this.lastData.set(message.symbol, message);
        }
        
        // Broadcast to all clients
        this.broadcast(message);
    }
    
    broadcast(message) {
        const data = JSON.stringify(message);
        
        this.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(data);
                this.stats.messagesSent++;
            }
        });
    }
    
    sendSnapshot(ws) {
        // Send current snapshot of all symbols
        const snapshot = {
            type: 'snapshot',
            data: Array.from(this.lastData.values())
        };
        
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(snapshot));
        }
    }
    
    handleClientMessage(ws, message) {
        try {
            const msg = JSON.parse(message);
            
            switch (msg.type) {
                case 'subscribe':
                    // Handle symbol subscription
                    console.log(`Client subscribed to: ${msg.symbols}`);
                    break;
                    
                case 'ping':
                    ws.send(JSON.stringify({ type: 'pong' }));
                    break;
                    
                default:
                    console.log('Unknown message type:', msg.type);
            }
        } catch (e) {
            console.error('Invalid client message:', e);
        }
    }
    
    reportStats() {
        console.log('--- Statistics ---');
        console.log(`Messages received: ${this.stats.messagesReceived}`);
        console.log(`Messages sent: ${this.stats.messagesSent}`);
        console.log(`Active clients: ${this.stats.clientsConnected}`);
        console.log(`Symbols tracked: ${this.lastData.size}`);
    }
}

// Simple web client for testing
const htmlClient = `
<!DOCTYPE html>
<html>
<head>
    <title>MT4 Market Data</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .bid { color: blue; }
        .ask { color: red; }
        .up { background-color: #e8f5e9; }
        .down { background-color: #ffebee; }
    </style>
</head>
<body>
    <h1>MT4 Real-Time Market Data</h1>
    <div id="status">Connecting...</div>
    <div id="stats"></div>
    <table id="quotes">
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Bid</th>
                <th>Ask</th>
                <th>Spread</th>
                <th>Time</th>
            </tr>
        </thead>
        <tbody></tbody>
    </table>
    
    <script>
        const ws = new WebSocket('ws://localhost:8080');
        const quotes = new Map();
        let messageCount = 0;
        
        ws.onopen = () => {
            document.getElementById('status').textContent = 'Connected';
            document.getElementById('status').style.color = 'green';
        };
        
        ws.onclose = () => {
            document.getElementById('status').textContent = 'Disconnected';
            document.getElementById('status').style.color = 'red';
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            messageCount++;
            
            if (data.type === 'quote') {
                updateQuote(data);
            } else if (data.type === 'snapshot') {
                data.data.forEach(quote => updateQuote(quote));
            }
            
            document.getElementById('stats').textContent = 
                \`Messages received: \${messageCount}\`;
        };
        
        function updateQuote(quote) {
            const prev = quotes.get(quote.symbol);
            quotes.set(quote.symbol, quote);
            
            let row = document.getElementById('quote-' + quote.symbol);
            if (!row) {
                row = document.createElement('tr');
                row.id = 'quote-' + quote.symbol;
                document.querySelector('#quotes tbody').appendChild(row);
            }
            
            const direction = prev ? 
                (quote.bid > prev.bid ? 'up' : quote.bid < prev.bid ? 'down' : '') : '';
            
            row.className = direction;
            setTimeout(() => row.className = '', 500);
            
            row.innerHTML = \`
                <td>\${quote.symbol}</td>
                <td class="bid">\${quote.bid}</td>
                <td class="ask">\${quote.ask}</td>
                <td>\${quote.spread}</td>
                <td>\${new Date(quote.timestamp * 1000).toLocaleTimeString()}</td>
            \`;
        }
        
        // Ping to keep connection alive
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    </script>
</body>
</html>
`;

// Main execution
if (require.main === module) {
    const args = process.argv.slice(2);
    
    if (args.includes('--serve-client')) {
        // Serve the HTML client
        const http = require('http');
        const port = 8081;
        
        http.createServer((req, res) => {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(htmlClient);
        }).listen(port);
        
        console.log(`Web client available at http://localhost:${port}`);
    }
    
    // Start the bridge
    const bridge = new MT4WebSocketBridge({
        mode: args.includes('--file') ? 'file' : 'pipe',
        wsPort: parseInt(args.find(a => a.startsWith('--port='))?.split('=')[1] || '8080')
    });
    
    bridge.start();
}

module.exports = MT4WebSocketBridge;