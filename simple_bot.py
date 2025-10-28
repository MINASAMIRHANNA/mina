# simple_bot.py
import logging
import time
from datetime import datetime
from binance.client import Client
from binance import ThreadedWebsocketManager

class SimpleTestBot:
    def __init__(self, config):
        self.config = config
        self.client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=True)
        self.orders = []
        self.running = False
        self.logger = logging.getLogger('SimpleBot')
        
    def start(self):
        self.logger.info("🚀 Starting Simple Test Bot...")
        self.running = True
        
        # Test connection
        self.test_connection()
        
        # Start monitoring
        self.start_monitoring()
        
    def test_connection(self):
        """Test Binance connection and show account info"""
        try:
            # Test server time
            server_time = self.client.get_server_time()
            self.logger.info(f"✅ Binance connection successful - Server time: {server_time['serverTime']}")
            
            # Show account balance
            account = self.client.get_account()
            usdt_balance = next((float(asset['free']) for asset in account['balances'] 
                               if asset['asset'] == 'USDT'), 0)
            self.logger.info(f"💰 USDT Balance: {usdt_balance}")
            
            # Show current price
            ticker = self.client.get_symbol_ticker(symbol=self.config.SYMBOL)
            self.logger.info(f"📈 {self.config.SYMBOL} price: ${ticker['price']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def start_monitoring(self):
        """Start monitoring market and place test orders"""
        import threading
        
        def monitor():
            order_placed = False
            
            while self.running:
                try:
                    # Get current price
                    ticker = self.client.get_symbol_ticker(symbol=self.config.SYMBOL)
                    current_price = float(ticker['price'])
                    
                    self.logger.info(f"📊 Monitoring {self.config.SYMBOL}: ${current_price:.2f}")
                    
                    # Place a test order (only once)
                    if not order_placed and self.running:
                        self.place_test_order(current_price)
                        order_placed = True
                    
                except Exception as e:
                    self.logger.error(f"Monitoring error: {e}")
                
                time.sleep(10)
        
        thread = threading.Thread(target=monitor)
        thread.daemon = True
        thread.start()
    
    def place_test_order(self, current_price):
        """Place a test order"""
        try:
            # Check balance
            account = self.client.get_account()
            usdt_balance = next((float(asset['free']) for asset in account['balances'] 
                               if asset['asset'] == 'USDT'), 0)
            
            if usdt_balance < 11:
                self.logger.warning(f"❌ Insufficient balance: {usdt_balance} USDT (need at least 11)")
                return
            
            # Calculate quantity for $10 order
            quantity = 10 / current_price
            quantity = round(quantity, 6)  # Round to 6 decimal places
            
            self.logger.info(f"🔄 Placing test buy order: {quantity} {self.config.SYMBOL} at ${current_price:.2f}")
            
            # Place market buy order
            order = self.client.order_market_buy(
                symbol=self.config.SYMBOL,
                quantity=quantity
            )
            
            order_info = {
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'quantity': float(order['executedQty']),
                'price': current_price,
                'status': order['status'],
                'timestamp': datetime.now(),
                'reason': 'Test order',
                'bot': 'SimpleBot'
            }
            
            self.orders.append(order_info)
            self.logger.info(f"✅ TEST ORDER SUCCESSFUL: {order_info}")
            
            # Immediately place sell order
            self.place_test_sell_order(quantity, current_price)
            
        except Exception as e:
            self.logger.error(f"❌ Test order failed: {e}")
    
    def place_test_sell_order(self, quantity, buy_price):
        """Place test sell order"""
        try:
            # Wait a moment
            time.sleep(2)
            
            # Get current price
            ticker = self.client.get_symbol_ticker(symbol=self.config.SYMBOL)
            current_price = float(ticker['price'])
            
            # Place market sell order
            order = self.client.order_market_sell(
                symbol=self.config.SYMBOL,
                quantity=quantity
            )
            
            profit = (current_price - buy_price) * quantity
            
            order_info = {
                'order_id': order['orderId'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'quantity': float(order['executedQty']),
                'price': current_price,
                'status': order['status'],
                'timestamp': datetime.now(),
                'reason': 'Test sell',
                'profit': profit,
                'bot': 'SimpleBot'
            }
            
            self.orders.append(order_info)
            self.logger.info(f"✅ TEST SELL SUCCESSFUL: Profit: ${profit:.4f}")
            
        except Exception as e:
            self.logger.error(f"❌ Test sell failed: {e}")
    
    def stop(self):
        self.running = False
        self.logger.info("🛑 Simple Test Bot stopped")
    
    def get_stats(self):
        return {
            'name': 'SimpleBot',
            'total_trades': len(self.orders),
            'running': self.running
        }
    