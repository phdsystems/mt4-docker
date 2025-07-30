#!/usr/bin/env python3
"""
Arbitrage Monitor for Multi-broker MT4 System
Monitors and alerts on arbitrage opportunities
"""

import asyncio
import json
import time
import logging
import aiohttp
from typing import Dict, List, Optional, Set
from datetime import datetime
import statistics
import os

from broker_manager import BrokerManager, BrokerArbirtageDetector, create_example_brokers


class ArbitrageMonitor:
    """Advanced arbitrage monitoring with alerts and analytics"""
    
    def __init__(self, manager: BrokerManager):
        self.manager = manager
        self.detector = BrokerArbirtageDetector(manager)
        self.logger = logging.getLogger(__name__)
        
        # Alert configuration
        self.alert_webhook = os.environ.get('ALERT_WEBHOOK')
        self.min_profit_pips = float(os.environ.get('MIN_PROFIT_PIPS', '2'))
        self.alert_cooldown = 60  # seconds between alerts for same symbol
        self.last_alerts: Dict[str, float] = {}
        
        # Statistics
        self.opportunities_found = 0
        self.total_profit_pips = 0
        self.opportunities_by_symbol: Dict[str, int] = {}
        self.opportunities_by_broker_pair: Dict[str, int] = {}
        
        # Active monitoring
        self.monitored_symbols: Set[str] = set()
        self.monitoring = False
    
    def add_symbols(self, symbols: List[str]):
        """Add symbols to monitor"""
        self.monitored_symbols.update(symbols)
        self.logger.info(f"Monitoring symbols: {', '.join(self.monitored_symbols)}")
    
    async def start_monitoring(self):
        """Start monitoring for arbitrage opportunities"""
        self.monitoring = True
        self.logger.info("Started arbitrage monitoring")
        
        while self.monitoring:
            try:
                # Check each symbol
                for symbol in self.monitored_symbols:
                    opportunity = self.detector.check_arbitrage(symbol)
                    
                    if opportunity:
                        await self._handle_opportunity(opportunity)
                
                # Brief delay
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def _handle_opportunity(self, opportunity: Dict):
        """Handle detected arbitrage opportunity"""
        symbol = opportunity['symbol']
        profit_pips = opportunity['profit_pips']
        
        # Update statistics
        self.opportunities_found += 1
        self.total_profit_pips += profit_pips
        
        self.opportunities_by_symbol[symbol] = \
            self.opportunities_by_symbol.get(symbol, 0) + 1
        
        broker_pair = f"{opportunity['buy_broker']}-{opportunity['sell_broker']}"
        self.opportunities_by_broker_pair[broker_pair] = \
            self.opportunities_by_broker_pair.get(broker_pair, 0) + 1
        
        # Check if we should alert
        now = time.time()
        last_alert = self.last_alerts.get(symbol, 0)
        
        if profit_pips >= self.min_profit_pips and \
           now - last_alert > self.alert_cooldown:
            await self._send_alert(opportunity)
            self.last_alerts[symbol] = now
        
        # Log opportunity
        self.logger.info(
            f"Arbitrage: {symbol} - "
            f"Buy at {opportunity['buy_broker']} @ {opportunity['buy_price']}, "
            f"Sell at {opportunity['sell_broker']} @ {opportunity['sell_price']}, "
            f"Profit: {profit_pips:.1f} pips"
        )
    
    async def _send_alert(self, opportunity: Dict):
        """Send alert via webhook"""
        if not self.alert_webhook:
            return
        
        alert_data = {
            'type': 'arbitrage_opportunity',
            'timestamp': datetime.now().isoformat(),
            'symbol': opportunity['symbol'],
            'buy_broker': opportunity['buy_broker'],
            'buy_price': opportunity['buy_price'],
            'sell_broker': opportunity['sell_broker'],
            'sell_price': opportunity['sell_price'],
            'profit_pips': opportunity['profit_pips'],
            'profit_amount': opportunity['profit']
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.alert_webhook, json=alert_data) as resp:
                    if resp.status != 200:
                        self.logger.error(f"Alert webhook failed: {resp.status}")
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
    
    def get_statistics(self) -> Dict:
        """Get monitoring statistics"""
        avg_profit = self.total_profit_pips / self.opportunities_found \
            if self.opportunities_found > 0 else 0
        
        return {
            'monitoring': self.monitoring,
            'symbols_monitored': list(self.monitored_symbols),
            'opportunities_found': self.opportunities_found,
            'total_profit_pips': round(self.total_profit_pips, 1),
            'average_profit_pips': round(avg_profit, 2),
            'opportunities_by_symbol': self.opportunities_by_symbol,
            'opportunities_by_broker_pair': self.opportunities_by_broker_pair,
            'top_symbol': max(self.opportunities_by_symbol.items(), 
                            key=lambda x: x[1])[0] 
                        if self.opportunities_by_symbol else None,
            'top_broker_pair': max(self.opportunities_by_broker_pair.items(), 
                                 key=lambda x: x[1])[0] 
                            if self.opportunities_by_broker_pair else None
        }
    
    async def analyze_spreads(self) -> Dict[str, Dict]:
        """Analyze spread differences between brokers"""
        spread_analysis = {}
        
        for symbol in self.monitored_symbols:
            if symbol not in self.manager.market_data:
                continue
            
            spreads_by_broker = {}
            
            for broker_id, data in self.manager.market_data[symbol].items():
                if time.time() - data['received_at'] < 5:  # Fresh data only
                    spread = data.get('spread', 0)
                    if spread > 0:
                        spreads_by_broker[broker_id] = spread
            
            if len(spreads_by_broker) >= 2:
                spread_values = list(spreads_by_broker.values())
                
                spread_analysis[symbol] = {
                    'brokers': spreads_by_broker,
                    'min_spread': min(spread_values),
                    'max_spread': max(spread_values),
                    'avg_spread': statistics.mean(spread_values),
                    'spread_difference': max(spread_values) - min(spread_values),
                    'best_broker': min(spreads_by_broker.items(), 
                                     key=lambda x: x[1])[0]
                }
        
        return spread_analysis
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        self.logger.info("Stopped arbitrage monitoring")


class ArbitrageSimulator:
    """Simulate arbitrage trading to estimate profits"""
    
    def __init__(self, monitor: ArbitrageMonitor):
        self.monitor = monitor
        self.simulated_trades = []
        self.balance = 10000  # Starting balance
        self.position_size = 0.1  # 0.1 lot
        self.transaction_cost = 2  # $2 per trade
        self.logger = logging.getLogger(__name__)
    
    def simulate_trade(self, opportunity: Dict):
        """Simulate an arbitrage trade"""
        # Calculate profit
        pip_value = 10 * self.position_size  # $10 per pip for 0.1 lot
        gross_profit = opportunity['profit_pips'] * pip_value
        net_profit = gross_profit - (2 * self.transaction_cost)  # Buy + sell
        
        # Update balance
        self.balance += net_profit
        
        # Record trade
        trade = {
            'timestamp': time.time(),
            'symbol': opportunity['symbol'],
            'buy_broker': opportunity['buy_broker'],
            'sell_broker': opportunity['sell_broker'],
            'profit_pips': opportunity['profit_pips'],
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'balance': self.balance
        }
        
        self.simulated_trades.append(trade)
        
        return trade
    
    def get_performance(self) -> Dict:
        """Get simulated trading performance"""
        if not self.simulated_trades:
            return {
                'total_trades': 0,
                'total_profit': 0,
                'win_rate': 0,
                'current_balance': self.balance
            }
        
        profits = [t['net_profit'] for t in self.simulated_trades]
        winning_trades = sum(1 for p in profits if p > 0)
        
        return {
            'total_trades': len(self.simulated_trades),
            'total_profit': sum(profits),
            'average_profit': statistics.mean(profits),
            'max_profit': max(profits),
            'min_profit': min(profits),
            'win_rate': winning_trades / len(self.simulated_trades) * 100,
            'current_balance': self.balance,
            'roi': (self.balance - 10000) / 10000 * 100  # ROI %
        }


async def main():
    """Main monitoring loop"""
    logging.basicConfig(level=logging.INFO)
    
    # Create broker manager
    manager = BrokerManager()
    
    # Add example brokers
    for broker_config in create_example_brokers():
        manager.add_broker(broker_config)
    
    # Create arbitrage monitor
    monitor = ArbitrageMonitor(manager)
    monitor.detector.min_profit_pips = 1  # Lower threshold for demo
    
    # Add symbols to monitor
    monitor.add_symbols(["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"])
    
    # Create simulator
    simulator = ArbitrageSimulator(monitor)
    
    try:
        # Start brokers
        await manager.start_all()
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        
        # Run for demonstration
        start_time = time.time()
        while time.time() - start_time < 300:  # 5 minutes
            await asyncio.sleep(30)
            
            # Print statistics
            stats = monitor.get_statistics()
            print(f"\n=== Arbitrage Statistics ===")
            print(f"Opportunities found: {stats['opportunities_found']}")
            print(f"Average profit: {stats['average_profit_pips']} pips")
            
            if stats['top_symbol']:
                print(f"Most opportunities: {stats['top_symbol']}")
            
            # Analyze spreads
            spread_analysis = await monitor.analyze_spreads()
            print("\n=== Spread Analysis ===")
            for symbol, analysis in spread_analysis.items():
                print(f"{symbol}: Best spread at {analysis['best_broker']} "
                      f"({analysis['min_spread']} pips)")
            
            # Simulate some trades
            if monitor.detector.opportunities:
                for opp in monitor.detector.opportunities[-5:]:  # Last 5
                    simulator.simulate_trade(opp)
            
            # Show performance
            performance = simulator.get_performance()
            if performance['total_trades'] > 0:
                print(f"\n=== Simulated Performance ===")
                print(f"Total trades: {performance['total_trades']}")
                print(f"Total profit: ${performance['total_profit']:.2f}")
                print(f"Win rate: {performance['win_rate']:.1f}%")
                print(f"ROI: {performance['roi']:.2f}%")
        
        # Stop monitoring
        monitor.stop_monitoring()
        await monitor_task
        
    finally:
        # Cleanup
        await manager.stop_all()


if __name__ == "__main__":
    asyncio.run(main())