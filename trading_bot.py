# trading_bot.py (updated for multi-bot compatibility)
import logging
from binance.client import Client
from binance import ThreadedWebsocketManager
import json
import time
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from strategy import IntelligentScalpingStrategy
from config import Config
from multi_bot_manager import BaseBot

class ScalpingTradingBot(BaseBot):
    def __init__(self, config: Config):
        super().__init__("ScalpingBot", config, None)
        self.client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=True)
        self.twm = None
        self.strategy = IntelligentScalpingStrategy(config)
        
    def start_trading(self):
        """Start the trading bot"""
        self.logger.info("Starting trading bot...")
        self.running = True
        
        # Initialize ThreadedWebsocketManager
        self.twm = ThreadedWebsocketManager()
        self.twm.start()
        
        # Start kline socket
        self.twm.start_kline_socket(
            symbol=self.config.SYMBOL,
            callback=self.handle_socket_message,
            interval=Client.KLINE_INTERVAL_1MINUTE
        )
        
        self.logger.info("Trading bot started successfully")
    
    def stop_trading(self):
        """Stop the trading bot"""
        self.logger.info("Stopping trading bot...")
        self.running = False
        if self.twm:
            self.twm.stop()
    
    def start(self):
        """Start bot (BaseBot compatibility)"""
        self.start_trading()
    
    def stop(self):
        """Stop bot (BaseBot compatibility)"""
        self.stop_trading()
    
    def get_current_price(self) -> float:
        """Get current price from Binance"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=self.config.SYMBOL)
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"Error getting current price: {e}")
            return 0.0
    
    def get_account_balance(self):
        """Get current account balance"""
        try:
            account = self.client.get_account()
            self.balance = {
                asset['asset']: {
                    'free': float(asset['free']),
                    'locked': float(asset['locked'])
                }
                for asset in account['balances']
                if asset['asset'] in [self.config.BASE_ASSET, self.config.QUOTE_ASSET]
            }
            return self.balance
        except Exception as e:
            self.logger.error(f"Error getting account balance: {e}")
            return {}
    
    def calculate_quantity(self, price: float) -> float:
        """Calculate quantity based on available balance and risk management"""
        balance = self.get_account_balance()
        quote_balance = balance.get(self.config.QUOTE_ASSET, {}).get('free', 0)
        
        # Use fixed quantity or calculate based on balance
        if quote_balance > 0:
            max_investment = quote_balance * 0.1
            calculated_quantity = min(
                max_investment / price,
                self.config.MAX_POSITION_SIZE
            )
            return float(Decimal(str(calculated_quantity)).quantize(
                Decimal('0.00001'), rounding=ROUND_DOWN
            ))
        
        return self.config.QUANTITY
    
    def place_buy_order(self, price: float, reason: str) -> bool:
        """Place a buy order"""
        try:
            quantity = self.calculate_quantity(price)
            
            if quantity <= 0:
                self.logger.warning("Insufficient balance for buy order")
                return False
            
            # Place limit order slightly above current price
            buy_price = round(price * 1.001, 2)
            
            order = self.client.order_limit_buy(
                symbol=self.config.SYMBOL,
                quantity=quantity,
                price=str(buy_price)
            )
            
            order_info = {
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'quantity': float(order['origQty']),
                'price': float(order['price']),
                'status': order['status'],
                'timestamp': datetime.now(),
                'reason': reason,
                'bot': self.name
            }
            
            self.orders.append(order_info)
            self.logger.info(f"BUY order placed: {order_info}")
            
            # Store position information
            self.positions.append({
                'symbol': self.config.SYMBOL,
                'entry_price': buy_price,
                'quantity': quantity,
                'entry_time': datetime.now(),
                'stop_loss': buy_price * (1 - self.config.STOP_LOSS),
                'take_profit': buy_price * (1 + self.config.PROFIT_TARGET)
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error placing buy order: {e}")
            return False
    
    def place_sell_order(self, price: float, reason: str) -> bool:
        """Place a sell order"""
        try:
            if not self.positions:
                self.logger.warning("No positions to sell")
                return False
            
            current_position = self.positions[-1]
            quantity = current_position['quantity']
            
            # Place limit order slightly below current price
            sell_price = round(price * 0.999, 2)
            
            order = self.client.order_limit_sell(
                symbol=self.config.SYMBOL,
                quantity=quantity,
                price=str(sell_price)
            )
            
            profit = (sell_price - current_position['entry_price']) * quantity
            
            order_info = {
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'quantity': float(order['origQty']),
                'price': float(order['price']),
                'status': order['status'],
                'timestamp': datetime.now(),
                'reason': reason,
                'profit': profit,
                'bot': self.name
            }
            
            self.orders.append(order_info)
            self.logger.info(f"SELL order placed: {order_info}")
            
            # Remove position
            self.positions.pop()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error placing sell order: {e}")
            return False
    
    def handle_socket_message(self, msg):
        """Handle WebSocket messages for real-time trading"""
        try:
            if msg['e'] == 'error':
                self.logger.error(f"WebSocket error: {msg}")
                return
                
            if msg['e'] == 'kline':
                kline = msg['k']
                if kline['x']:  # Kline closed
                    current_price = float(kline['c'])
                    timestamp = msg['E']
                    
                    # Update strategy with new price
                    self.strategy.update_price_data(current_price, timestamp)
                    
                    # Calculate indicators
                    prices = [p['close'] for p in self.strategy.price_data]
                    indicators = self.strategy.calculate_indicators(prices)
                    
                    if indicators:
                        # Generate trading signal
                        signal = self.strategy.generate_signal(current_price, indicators)
                        
                        self.logger.info(f"Signal: {signal}")
                        
                        # Execute trading logic
                        if signal['action'] == 'BUY' and signal['confidence'] > 0.6 and not self.positions:
                            self.place_buy_order(current_price, signal['reason'])
                        
                        elif signal['action'] == 'SELL' and signal['confidence'] > 0.6 and self.positions:
                            self.place_sell_order(current_price, signal['reason'])
                        
                        # Check for stop loss and take profit
                        self.check_position_management(current_price)
                    
        except Exception as e:
            self.logger.error(f"Error handling socket message: {e}")
    
    def check_position_management(self, current_price: float):
        """Check stop loss and take profit for current position"""
        if not self.positions:
            return
        
        position = self.positions[-1]
        
        # Check stop loss
        if current_price <= position['stop_loss']:
            self.logger.warning(f"Stop loss triggered at {current_price}")
            self.place_sell_order(current_price, "Stop loss triggered")
        
        # Check take profit
        elif current_price >= position['take_profit']:
            self.logger.info(f"Take profit triggered at {current_price}")
            self.place_sell_order(current_price, "Take profit triggered")
    
    def get_stats(self):
        """Get trading statistics"""
        filled_orders = [o for o in self.orders if o['status'] == 'FILLED']
        total_trades = len(filled_orders)
        winning_trades = len([o for o in filled_orders if o.get('profit', 0) > 0])
        total_profit = sum([o.get('profit', 0) for o in filled_orders])
        
        return {
            'name': self.name,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'total_profit': total_profit,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'current_positions': len(self.positions),
            'running': self.running,
            'symbol': self.config.SYMBOL
        }
