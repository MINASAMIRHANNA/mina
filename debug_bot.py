# debug_bot.py
from binance.client import Client
from config import Config
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DebugBot')

def debug_binance_connection():
    """Debug Binance API connection"""
    try:
        config = Config()
        client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=True)
        
        # Test connection
        logger.info("🔌 Testing Binance connection...")
        server_time = client.get_server_time()
        logger.info(f"✅ Binance server time: {server_time['serverTime']}")
        
        # Test account info
        account = client.get_account()
        logger.info("💰 Account balances:")
        for balance in account['balances']:
            if float(balance['free']) > 0 or float(balance['locked']) > 0:
                logger.info(f"  {balance['asset']}: Free={balance['free']}, Locked={balance['locked']}")
        
        # Test symbol price
        symbol = config.SYMBOL
        ticker = client.get_symbol_ticker(symbol=symbol)
        logger.info(f"📈 {symbol} current price: {ticker['price']}")
        
        # Test order book
        depth = client.get_order_book(symbol=symbol)
        logger.info(f"📊 Order book - Bids: {len(depth['bids'])}, Asks: {len(depth['asks'])}")
        
        # Test historical data
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
        logger.info(f"📅 Historical klines: {len(klines)} candles")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Binance connection failed: {e}")
        return False

def test_order_placement():
    """Test placing a small order"""
    try:
        config = Config()
        client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=True)
        
        symbol = config.SYMBOL
        current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        
        logger.info(f"🔄 Testing order placement for {symbol}...")
        
        # Try to place a very small limit order (likely won't fill, but tests API)
        test_price = current_price * 0.5  # Very low price to avoid actual execution
        quantity = 0.001
        
        order = client.order_limit_buy(
            symbol=symbol,
            quantity=quantity,
            price=str(round(test_price, 2))
        )
        
        logger.info(f"✅ TEST ORDER PLACED: {order}")
        
        # Cancel the test order
        result = client.cancel_order(
            symbol=symbol,
            orderId=order['orderId']
        )
        logger.info(f"✅ TEST ORDER CANCELLED: {result}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Order placement test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Bot Debug...")
    
    if debug_binance_connection():
        logger.info("✅ Binance connection successful!")
    else:
        logger.error("❌ Binance connection failed!")
    
    if test_order_placement():
        logger.info("✅ Order placement test successful!")
    else:
        logger.error("❌ Order placement test failed!")