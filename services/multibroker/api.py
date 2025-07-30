#!/usr/bin/env python3
"""
Multi-broker API for MT4 System
Provides REST API for managing multiple brokers and accessing aggregated data
"""

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import redis
import json
import time
import logging
from typing import Dict, List, Optional
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.multibroker.broker_manager import BrokerManager, BrokerConfig, BrokerStatus


app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global broker manager instance
broker_manager = BrokerManager()

# Redis for caching
try:
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Connected to Redis")
except:
    redis_client = None
    logger.warning("Redis not available, running without cache")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'brokers_loaded': len(broker_manager.brokers)
    })


@app.route('/api/v1/brokers', methods=['GET'])
def list_brokers():
    """List all configured brokers"""
    brokers = []
    
    for broker_id, broker in broker_manager.brokers.items():
        brokers.append({
            'id': broker_id,
            'name': broker.config.name,
            'server': broker.config.server,
            'status': broker.status.value,
            'enabled': broker.config.enabled,
            'symbols': broker.config.symbols,
            'priority': broker.config.priority,
            'error_count': broker.error_count,
            'last_tick': broker.last_tick
        })
    
    return jsonify({
        'brokers': brokers,
        'total': len(brokers)
    })


@app.route('/api/v1/brokers', methods=['POST'])
def add_broker():
    """Add a new broker"""
    data = request.json
    
    # Validate required fields
    required = ['id', 'name', 'server', 'login', 'password', 'symbols', 'zmq_port', 'vnc_port']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Create broker config
    config = BrokerConfig(
        id=data['id'],
        name=data['name'],
        server=data['server'],
        login=data['login'],
        password=data['password'],
        symbols=data['symbols'],
        zmq_port=data['zmq_port'],
        vnc_port=data['vnc_port'],
        container_name=f"mt4_{data['id']}",
        enabled=data.get('enabled', True),
        priority=data.get('priority', 1),
        max_spread=data.get('max_spread'),
        trading_hours=data.get('trading_hours')
    )
    
    # Add broker
    if broker_manager.add_broker(config):
        return jsonify({
            'message': f'Broker {config.id} added successfully',
            'broker_id': config.id
        }), 201
    else:
        return jsonify({'error': 'Broker already exists'}), 409


@app.route('/api/v1/brokers/<broker_id>', methods=['GET'])
def get_broker(broker_id):
    """Get specific broker details"""
    if broker_id not in broker_manager.brokers:
        return jsonify({'error': 'Broker not found'}), 404
    
    broker = broker_manager.brokers[broker_id]
    
    return jsonify({
        'id': broker_id,
        'name': broker.config.name,
        'server': broker.config.server,
        'status': broker.status.value,
        'enabled': broker.config.enabled,
        'symbols': broker.config.symbols,
        'priority': broker.config.priority,
        'max_spread': broker.config.max_spread,
        'trading_hours': broker.config.trading_hours,
        'connected_at': broker.connected_at,
        'last_tick': broker.last_tick,
        'error_count': broker.error_count
    })


@app.route('/api/v1/brokers/<broker_id>/start', methods=['POST'])
async def start_broker(broker_id):
    """Start a specific broker"""
    if broker_id not in broker_manager.brokers:
        return jsonify({'error': 'Broker not found'}), 404
    
    success = await broker_manager.start_broker(broker_id)
    
    if success:
        return jsonify({'message': f'Broker {broker_id} started successfully'})
    else:
        return jsonify({'error': 'Failed to start broker'}), 500


@app.route('/api/v1/brokers/<broker_id>/stop', methods=['POST'])
async def stop_broker(broker_id):
    """Stop a specific broker"""
    if broker_id not in broker_manager.brokers:
        return jsonify({'error': 'Broker not found'}), 404
    
    success = await broker_manager.stop_broker(broker_id)
    
    if success:
        return jsonify({'message': f'Broker {broker_id} stopped successfully'})
    else:
        return jsonify({'error': 'Failed to stop broker'}), 500


@app.route('/api/v1/brokers/<broker_id>', methods=['DELETE'])
async def remove_broker(broker_id):
    """Remove a broker"""
    if broker_id not in broker_manager.brokers:
        return jsonify({'error': 'Broker not found'}), 404
    
    # Stop broker first
    await broker_manager.stop_broker(broker_id)
    
    # Remove from manager
    del broker_manager.brokers[broker_id]
    
    return jsonify({'message': f'Broker {broker_id} removed successfully'})


@app.route('/api/v1/market/quotes', methods=['GET'])
def get_quotes():
    """Get aggregated market quotes"""
    symbols = request.args.get('symbols', '').split(',')
    
    if not symbols or symbols == ['']:
        # Return all available symbols
        symbols = list(broker_manager.symbol_brokers.keys())
    
    quotes = {}
    
    for symbol in symbols:
        symbol = symbol.strip().upper()
        quote = broker_manager.get_best_quote(symbol)
        if quote:
            quotes[symbol] = quote
    
    return jsonify({
        'quotes': quotes,
        'timestamp': time.time()
    })


@app.route('/api/v1/market/quotes/<symbol>', methods=['GET'])
def get_symbol_quotes(symbol):
    """Get quotes for a specific symbol from all brokers"""
    symbol = symbol.upper()
    
    if symbol not in broker_manager.market_data:
        return jsonify({'error': f'No data available for {symbol}'}), 404
    
    broker_quotes = []
    
    for broker_id, data in broker_manager.market_data[symbol].items():
        if broker_id in broker_manager.brokers:
            broker = broker_manager.brokers[broker_id]
            
            quote = {
                'broker_id': broker_id,
                'broker_name': broker.config.name,
                'bid': data.get('bid'),
                'ask': data.get('ask'),
                'spread': data.get('spread'),
                'timestamp': data.get('timestamp'),
                'received_at': data.get('received_at'),
                'age': time.time() - data.get('received_at', 0)
            }
            
            broker_quotes.append(quote)
    
    # Sort by best bid
    broker_quotes.sort(key=lambda x: x.get('bid', 0), reverse=True)
    
    return jsonify({
        'symbol': symbol,
        'quotes': broker_quotes,
        'best_bid': max((q['bid'] for q in broker_quotes if q['bid']), default=None),
        'best_ask': min((q['ask'] for q in broker_quotes if q['ask']), default=None)
    })


@app.route('/api/v1/status', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    status = broker_manager.get_broker_status()
    
    # Add market data summary
    market_summary = {}
    for symbol, brokers_data in broker_manager.market_data.items():
        active_brokers = sum(1 for b, d in brokers_data.items() 
                           if time.time() - d.get('received_at', 0) < 5)
        market_summary[symbol] = {
            'active_brokers': active_brokers,
            'total_brokers': len(brokers_data)
        }
    
    status['market_summary'] = market_summary
    
    return jsonify(status)


@app.route('/api/v1/spreads', methods=['GET'])
def get_spread_analysis():
    """Get spread analysis across brokers"""
    spreads = {}
    
    for symbol, brokers_data in broker_manager.market_data.items():
        symbol_spreads = []
        
        for broker_id, data in brokers_data.items():
            if time.time() - data.get('received_at', 0) < 5:  # Fresh data only
                spread = data.get('spread', 0)
                if spread > 0:
                    symbol_spreads.append({
                        'broker_id': broker_id,
                        'broker_name': broker_manager.brokers[broker_id].config.name,
                        'spread': spread
                    })
        
        if symbol_spreads:
            symbol_spreads.sort(key=lambda x: x['spread'])
            
            spreads[symbol] = {
                'best': symbol_spreads[0],
                'worst': symbol_spreads[-1],
                'all': symbol_spreads
            }
    
    return jsonify({
        'spreads': spreads,
        'timestamp': time.time()
    })


@app.route('/api/v1/arbitrage/opportunities', methods=['GET'])
def get_arbitrage_opportunities():
    """Get current arbitrage opportunities"""
    # This would integrate with ArbitrageMonitor
    # For now, return mock data
    
    opportunities = []
    
    # Check for arbitrage in current market data
    for symbol in broker_manager.market_data:
        brokers_data = []
        
        for broker_id, data in broker_manager.market_data[symbol].items():
            if time.time() - data.get('received_at', 0) < 1:
                brokers_data.append({
                    'broker_id': broker_id,
                    'bid': data.get('bid', 0),
                    'ask': data.get('ask', 0)
                })
        
        if len(brokers_data) >= 2:
            # Find best bid and ask
            best_bid = max(brokers_data, key=lambda x: x['bid'])
            best_ask = min(brokers_data, key=lambda x: x['ask'])
            
            if best_bid['broker_id'] != best_ask['broker_id']:
                profit = best_bid['bid'] - best_ask['ask']
                profit_pips = profit * 10000 if symbol != 'USDJPY' else profit * 100
                
                if profit_pips > 0:
                    opportunities.append({
                        'symbol': symbol,
                        'buy_broker': best_ask['broker_id'],
                        'buy_price': best_ask['ask'],
                        'sell_broker': best_bid['broker_id'],
                        'sell_price': best_bid['bid'],
                        'profit': profit,
                        'profit_pips': round(profit_pips, 1),
                        'timestamp': time.time()
                    })
    
    # Sort by profit
    opportunities.sort(key=lambda x: x['profit_pips'], reverse=True)
    
    return jsonify({
        'opportunities': opportunities[:10],  # Top 10
        'total': len(opportunities)
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({'error': 'Internal server error'}), 500


# Initialize with example brokers on startup
def init_brokers():
    """Initialize example brokers"""
    from services.multibroker.broker_manager import create_example_brokers
    
    for config in create_example_brokers():
        broker_manager.add_broker(config)
    
    logger.info(f"Initialized {len(broker_manager.brokers)} brokers")


if __name__ == '__main__':
    init_brokers()
    app.run(host='0.0.0.0', port=5001, debug=True)