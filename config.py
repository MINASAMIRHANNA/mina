import os
from decimal import Decimal

class Config:
    # Binance API Configuration
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    
    # Trading Configuration
    SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
    BASE_ASSET = SYMBOL.replace('USDT', '')
    QUOTE_ASSET = 'USDT'

    # Optional testnet API URL (for python-binance compatibility)
    TESTNET_API_URL = os.getenv('TESTNET_API_URL', 'https://testnet.binance.vision/api')

    
    # Trading Parameters
    QUANTITY = float(os.getenv('QUANTITY', '0.001'))
    PROFIT_TARGET = float(os.getenv('PROFIT_TARGET', '0.003'))
    STOP_LOSS = float(os.getenv('STOP_LOSS', '0.002'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.01'))
    
    # Strategy Parameters
    RSI_PERIOD = 14
    EMA_SHORT = 9
    EMA_LONG = 21
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Risk Management
    MAX_DRAWDOWN = float(os.getenv('MAX_DRAWDOWN', '0.05'))
    DAILY_LOSS_LIMIT = float(os.getenv('DAILY_LOSS_LIMIT', '0.02'))
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    
    # Dashboard Configuration
    DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
    DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '5002'))
    
    # New Bots Configuration
    NEW_LISTING_PROFIT_TARGET = float(os.getenv('NEW_LISTING_PROFIT_TARGET', '0.05'))  # 5%
    NEW_LISTING_STOP_LOSS = float(os.getenv('NEW_LISTING_STOP_LOSS', '0.03'))  # 3%
    VOLUME_SPIKE_THRESHOLD = float(os.getenv('VOLUME_SPIKE_THRESHOLD', '3.0'))  # 3x average volume
    SCORE_THRESHOLD = float(os.getenv('SCORE_THRESHOLD', '80'))  # Minimum score to trade
