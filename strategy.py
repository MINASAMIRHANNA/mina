import pandas as pd
import numpy as np
from typing import Dict
import talib

class IntelligentScalpingStrategy:
    def __init__(self, config):
        self.config = config
        self.position = None
        self.trend = 'NEUTRAL'
        self.price_data = []  # list of {'timestamp': ts, 'close': price}

    def calculate_indicators(self, prices: list) -> Dict:
        """Calculate technical indicators for intelligent decision making"""
        if len(prices) < self.config.EMA_LONG:
            return {}

        closes = pd.Series(prices).astype(float).values

        try:
            ema_short = talib.EMA(closes, timeperiod=self.config.EMA_SHORT)[-1]
            ema_long = talib.EMA(closes, timeperiod=self.config.EMA_LONG)[-1]
            rsi = talib.RSI(closes, timeperiod=self.config.RSI_PERIOD)[-1]
            macd, macd_signal, macd_hist = talib.MACD(
                closes,
                fastperiod=self.config.MACD_FAST,
                slowperiod=self.config.MACD_SLOW,
                signalperiod=self.config.MACD_SIGNAL
            )
            macd_val = macd[-1] if macd.size > 0 else 0
            macd_signal_val = macd_signal[-1] if macd_signal.size > 0 else 0
            macd_hist_val = macd_hist[-1] if macd_hist.size > 0 else 0
            bb_upper, bb_middle, bb_lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)

            return {
                'ema_short': float(ema_short),
                'ema_long': float(ema_long),
                'rsi': float(rsi),
                'macd': float(macd_val),
                'macd_signal': float(macd_signal_val),
                'macd_hist': float(macd_hist_val),
                'bb_upper': float(bb_upper[-1]),
                'bb_middle': float(bb_middle[-1]),
                'bb_lower': float(bb_lower[-1])
            }
        except Exception as e:
            print(f"[Indicator Error] {e}")
            return {}

    def determine_trend(self, indicators: Dict) -> str:
        if not indicators:
            return 'NEUTRAL'
        trend_score = 0
        if indicators['ema_short'] > indicators['ema_long']:
            trend_score += 1
        else:
            trend_score -= 1
        if indicators['macd'] > indicators['macd_signal']:
            trend_score += 1
        else:
            trend_score -= 1
        if indicators['rsi'] > 50:
            trend_score += 0.5
        else:
            trend_score -= 0.5
        if trend_score >= 1.5:
            return 'UPTREND'
        elif trend_score <= -1.5:
            return 'DOWNTREND'
        else:
            return 'NEUTRAL'

    def generate_signal(self, current_price: float, indicators: Dict) -> Dict:
        signal = {'action': 'HOLD', 'confidence': 0, 'reason': '', 'price': current_price}
        if not indicators:
            return signal
        trend = self.determine_trend(indicators)
        self.trend = trend
        if trend == 'UPTREND':
            if current_price <= indicators['bb_lower'] and indicators['rsi'] < 35:
                signal.update({'action': 'BUY', 'confidence': 0.8, 'reason': 'Uptrend buy dip'})
            elif current_price >= indicators['bb_upper'] and indicators['rsi'] > 70:
                signal.update({'action': 'SELL', 'confidence': 0.7, 'reason': 'Uptrend take profit'})
        elif trend == 'DOWNTREND':
            if current_price >= indicators['bb_upper'] and indicators['rsi'] > 65:
                signal.update({'action': 'SELL', 'confidence': 0.75, 'reason': 'Downtrend sell rally'})
            elif current_price <= indicators['bb_lower'] and indicators['rsi'] < 30:
                signal.update({'action': 'BUY', 'confidence': 0.6, 'reason': 'Downtrend cautious buy'})
        else:
            if current_price <= indicators['bb_lower'] and indicators['rsi'] < 30:
                signal.update({'action': 'BUY', 'confidence': 0.7, 'reason': 'Range buy'})
            elif current_price >= indicators['bb_upper'] and indicators['rsi'] > 70:
                signal.update({'action': 'SELL', 'confidence': 0.7, 'reason': 'Range sell'})
        return signal

    def update_price_data(self, price: float, timestamp: int):
        self.price_data.append({'timestamp': timestamp, 'close': price})
        if len(self.price_data) > 100:
            self.price_data = self.price_data[-50:]
