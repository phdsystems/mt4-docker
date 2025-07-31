#!/usr/bin/env python3
"""
Simple MT4 Data Web Server
Runs locally without Docker
"""

import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import json
import csv
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Paths
PROJECT_ROOT = Path("/workspace/mt4-docker")
WEB_DIR = PROJECT_ROOT / "web"

@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory(str(WEB_DIR), 'data-viewer.html')

@app.route('/api/files')
def get_files():
    """Mock file list"""
    return jsonify([
        {'name': 'market_data.csv', 'size': '2.3 KB', 'modified': datetime.now().isoformat()},
        {'name': 'EURUSD_H1.csv', 'size': '15.2 KB', 'modified': datetime.now().isoformat()},
        {'name': 'export_data.csv', 'size': '8.7 KB', 'modified': datetime.now().isoformat()}
    ])

@app.route('/api/latest')
def get_latest_data():
    """Mock latest data"""
    prices = {
        'EURUSD': {'bid': 1.08765, 'ask': 1.08785, 'spread': 2.0},
        'GBPUSD': {'bid': 1.26543, 'ask': 1.26563, 'spread': 2.0},
        'USDJPY': {'bid': 149.875, 'ask': 149.895, 'spread': 2.0},
        'AUDUSD': {'bid': 0.65432, 'ask': 0.65452, 'spread': 2.0}
    }
    
    history = []
    import random
    symbols = list(prices.keys())
    
    for i in range(20):
        symbol = random.choice(symbols)
        base = prices[symbol]['bid']
        bid = base + (random.random() - 0.5) * 0.001
        ask = bid + 0.0002
        
        history.append({
            'time': datetime.now().isoformat(),
            'symbol': symbol,
            'bid': f"{bid:.5f}",
            'ask': f"{ask:.5f}",
            'spread': f"{(ask - bid) * 10000:.1f}"
        })
    
    return jsonify({'prices': prices, 'history': history})

@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'time': datetime.now().isoformat()})

if __name__ == '__main__':
    print("Starting Simple MT4 Web Server...")
    print("Access at: http://localhost:8081")
    print("\nAPI Endpoints:")
    print("  http://localhost:8081/api/files     - List CSV files")
    print("  http://localhost:8081/api/latest    - Get latest data")
    print("  http://localhost:8081/health        - Health check")
    print("\nPress Ctrl+C to stop")
    
    app.run(host='0.0.0.0', port=8081, debug=True)