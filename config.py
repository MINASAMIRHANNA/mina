import os
from decimal import Decimal

class Config:
    # Binance API Configuration
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

    # Environment toggles
    LIVE = os.getenv('LIVE', 'false').lower() in ('1', 'true', 'yes')  # true => production
    DRY_RUN = os.getenv('DRY_RUN', 'true').lower() in ('1', 'true', 'yes')  # if true, do not place real orders

    # API URLs
    TESTNET_API_URL = os.getenv('TESTNET_API_URL', 'https://testnet.binance.vision/api')
    PROD_API_URL = os.getenv('PROD_API_URL', 'https://api.binance.com')

    # Trading Configuration
    SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
    BASE_ASSET = SYMBOL.replace('USDT', '')
    QUOTE_ASSET = 'USDT'

    # Trading Parameters
    QUANTITY = float(os.getenv('QUANTITY', '0.001'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.01'))
    STOP_LOSS = float(os.getenv('STOP_LOSS', '0.01'))
    PROFIT_TARGET = float(os.getenv('PROFIT_TARGET', '0.02'))

    # Strategy indicators
    EMA_SHORT = int(os.getenv('EMA_SHORT', '9'))
    EMA_LONG = int(os.getenv('EMA_LONG', '21'))
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
    MACD_FAST = int(os.getenv('MACD_FAST', '12'))
    MACD_SLOW = int(os.getenv('MACD_SLOW', '26'))
    MACD_SIGNAL = int(os.getenv('MACD_SIGNAL', '9'))

    # Risk controls
    MAX_DRAWDOWN = float(os.getenv('MAX_DRAWDOWN', '0.05'))
    DAILY_LOSS_LIMIT = float(os.getenv('DAILY_LOSS_LIMIT', '0.02'))

    # New Listings & High volume
    NEW_LISTING_PROFIT_TARGET = float(os.getenv('NEW_LISTING_PROFIT_TARGET', '0.05'))
    NEW_LISTING_STOP_LOSS = float(os.getenv('NEW_LISTING_STOP_LOSS', '0.03'))
    VOLUME_SPIKE_THRESHOLD = float(os.getenv('VOLUME_SPIKE_THRESHOLD', '3.0'))
    SCORE_THRESHOLD = float(os.getenv('SCORE_THRESHOLD', '80'))

    # Telegram Alerts (optional)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
