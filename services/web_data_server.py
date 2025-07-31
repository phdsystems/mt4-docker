#!/usr/bin/env python3
"""
MT4 Data Web Server
Serves the web interface and provides API endpoints for MT4 data
"""

import os
import json
import csv
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, Response
from flask_cors import CORS
import glob

app = Flask(__name__)
CORS(app)

# Configuration
MT4_BASE = Path("/mt4")
DATA_DIR = MT4_BASE / "MQL4/Files"
WEB_DIR = Path("/web")

class MT4DataProvider:
    def __init__(self):
        self.data_dir = DATA_DIR
        
    def get_csv_files(self):
        """Get list of available CSV files"""
        files = []
        for csv_file in self.data_dir.glob("*.csv"):
            stat = csv_file.stat()
            files.append({
                'name': csv_file.name,
                'size': self._format_size(stat.st_size),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return sorted(files, key=lambda x: x['modified'], reverse=True)
    
    def _format_size(self, size):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def read_latest_data(self):
        """Read the most recent data from CSV files"""
        prices = {}
        history = []
        
        # Try to find and read CSV files
        csv_files = list(self.data_dir.glob("*.csv"))
        
        for csv_file in csv_files[:5]:  # Read up to 5 most recent files
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Try different column name formats
                        time_col = row.get('Time') or row.get('DateTime') or row.get('timestamp')
                        symbol_col = row.get('Symbol') or row.get('symbol')
                        bid_col = row.get('Bid') or row.get('bid')
                        ask_col = row.get('Ask') or row.get('ask')
                        
                        if all([time_col, symbol_col, bid_col, ask_col]):
                            # Update current prices
                            if symbol_col not in prices:
                                spread = float(ask_col) - float(bid_col)
                                prices[symbol_col] = {
                                    'bid': float(bid_col),
                                    'ask': float(ask_col),
                                    'spread': round(spread * 10000, 1)  # Convert to points
                                }
                            
                            # Add to history
                            history.append({
                                'time': time_col,
                                'symbol': symbol_col,
                                'bid': bid_col,
                                'ask': ask_col,
                                'spread': round((float(ask_col) - float(bid_col)) * 10000, 1)
                            })
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")
        
        # If no data found, generate demo data
        if not prices:
            prices = self._generate_demo_prices()
            history = self._generate_demo_history()
        
        return {'prices': prices, 'history': history[:50]}  # Limit history to 50 entries
    
    def _generate_demo_prices(self):
        """Generate demo price data"""
        return {
            'EURUSD': {'bid': 1.08765, 'ask': 1.08785, 'spread': 2.0},
            'GBPUSD': {'bid': 1.26543, 'ask': 1.26563, 'spread': 2.0},
            'USDJPY': {'bid': 149.875, 'ask': 149.895, 'spread': 2.0},
            'AUDUSD': {'bid': 0.65432, 'ask': 0.65452, 'spread': 2.0}
        }
    
    def _generate_demo_history(self):
        """Generate demo history data"""
        import random
        history = []
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
        
        for i in range(20):
            symbol = random.choice(symbols)
            base_price = 1.1 if symbol != 'USDJPY' else 150.0
            bid = base_price + (random.random() - 0.5) * 0.01
            ask = bid + 0.0002
            
            history.append({
                'time': datetime.now().isoformat(),
                'symbol': symbol,
                'bid': f"{bid:.5f}",
                'ask': f"{ask:.5f}",
                'spread': f"{(ask - bid) * 10000:.1f}"
            })
        
        return history

# Initialize data provider
data_provider = MT4DataProvider()

# API Routes
@app.route('/api/files')
def get_files():
    """Get list of available CSV files"""
    return jsonify(data_provider.get_csv_files())

@app.route('/api/latest')
def get_latest_data():
    """Get latest market data"""
    return jsonify(data_provider.read_latest_data())

@app.route('/api/file/<filename>')
def get_file_content(filename):
    """Get content of specific CSV file"""
    file_path = DATA_DIR / filename
    if file_path.exists() and file_path.suffix == '.csv':
        with open(file_path, 'r') as f:
            content = f.read()
        return Response(content, mimetype='text/csv')
    return jsonify({'error': 'File not found'}), 404

# Web Routes
@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory(WEB_DIR, 'data-viewer.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(WEB_DIR, path)

# Health check
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'data_dir': str(DATA_DIR),
        'files_found': len(list(DATA_DIR.glob('*.csv')))
    })

if __name__ == '__main__':
    print(f"MT4 Data Web Server starting...")
    print(f"Data directory: {DATA_DIR}")
    print(f"Web directory: {WEB_DIR}")
    
    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Start server
    app.run(host='0.0.0.0', port=8080, debug=True)