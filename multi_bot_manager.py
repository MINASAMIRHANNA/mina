# multi_bot_manager.py (hardened & improved)
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List
from binance.client import Client
from binance import ThreadedWebsocketManager
import pandas as pd
import numpy as np
import requests
import json
from decimal import Decimal

class BaseBot:
    def __init__(self, name, config, client):
        self.name = name
        self.config = config
        self.client = client
        self.orders = []
        self.positions = []
        self.running = False
        self.logger = logging.getLogger(name)
        # symbol info cache
        self._symbol_info_cache = {}
        self._symbol_info_cache_ts = {}

    def start(self):
        self.running = True
        self.logger.info(f"{self.name} started")

    def stop(self):
        self.running = False
        self.logger.info(f"{self.name} stopped")

    def safe_order(self, fn, *args, retries=3, backoff=1, **kwargs):
        """Retry wrapper for Binance order calls"""
        for i in range(retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Order call error attempt {i+1}/{retries}: {e}")
                time.sleep(backoff * (i+1))
        return None

    def get_symbol_info(self, symbol, force_refresh=False):
        now = time.time()
        cache = self._symbol_info_cache.get(symbol)
        ts = self._symbol_info_cache_ts.get(symbol, 0)
        if cache and not force_refresh and now - ts < 300:
            return cache
        try:
            info = self.client.get_symbol_info(symbol)
            if not info:
                return None
            filters = {f['filterType']: f for f in info.get('filters', [])}
            step_size = Decimal(filters['LOT_SIZE']['stepSize'])
            tick_size = Decimal(filters['PRICE_FILTER']['tickSize'])
            min_notional = Decimal(filters.get('MIN_NOTIONAL', {}).get('minNotional', '0'))
            res = {'stepSize': step_size, 'tickSize': tick_size, 'minNotional': min_notional}
            self._symbol_info_cache[symbol] = res
            self._symbol_info_cache_ts[symbol] = now
            return res
        except Exception as e:
            self.logger.error(f"Error fetching symbol info for {symbol}: {e}")
            return None

    def quantize_qty(self, qty: Decimal, step: Decimal):
        if step == 0:
            return float(qty)
        q = (qty // step) * step
        return float(q)

    def quantize_price(self, price: Decimal, tick: Decimal):
        if tick == 0:
            return float(price)
        p = (price // tick) * tick
        return float(p)

    def get_stats(self):
        filled_orders = [o for o in self.orders if o.get('status') == 'FILLED']
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
            'running': self.running
        }


class NewListingBot(BaseBot):
    def __init__(self, config, client):
        super().__init__("NewListingBot", config, client)
        self.monitored_symbols = set()
        self.new_listings_cache = {}

    def start(self):
        super().start()
        self._thread = threading.Thread(target=self.monitor_new_listings, daemon=True)
        self._thread.start()

    def monitor_new_listings(self):
        while self.running:
            try:
                exchange_info = self.client.get_exchange_info()
                current_symbols = {symbol['symbol'] for symbol in exchange_info.get('symbols', [])}

                new_symbols = current_symbols - self.monitored_symbols

                for symbol in new_symbols:
                    if symbol.endswith('USDT') and symbol not in self.new_listings_cache:
                        self.logger.info(f"New symbol detected: {symbol}")
                        # analyze in separate thread to avoid blocking
                        threading.Thread(target=self.analyze_new_listing, args=(symbol,), daemon=True).start()

                self.monitored_symbols = current_symbols

            except Exception as e:
                self.logger.error(f"Error monitoring new listings: {e}")

            time.sleep(60)

    def analyze_new_listing(self, symbol):
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            initial_price = float(ticker['price'])

            self.logger.info(f"New listing {symbol} at price: {initial_price}")

            account = self.client.get_account()
            usdt_balance = next((float(asset['free']) for asset in account.get('balances', [])
                                 if asset['asset'] == 'USDT'), 0)

            if usdt_balance > 10:
                # use max 2% of balance for new listing
                raw_qty = Decimal(str(usdt_balance)) * Decimal('0.02') / Decimal(str(initial_price))
                symbol_info = self.get_symbol_info(symbol)
                if symbol_info is None:
                    self.logger.warning(f"No symbol info for {symbol}, skipping trade")
                    return
                step = symbol_info['stepSize']
                qty = float((raw_qty // step) * step)
                if (Decimal(str(qty)) * Decimal(str(initial_price))) > Decimal('10'):
                    order = self.safe_order(self.client.order_market_buy, symbol=symbol, quantity=str(qty))
                    if not order:
                        self.logger.error(f"Buy order failed for {symbol}")
                        return

                    buy_price = float(order.get('fills', [])[0].get('price')) if order.get('fills') else initial_price

                    order_info = {
                        'order_id': order.get('orderId'),
                        'symbol': symbol,
                        'side': 'BUY',
                        'type': 'MARKET',
                        'quantity': qty,
                        'price': buy_price,
                        'status': order.get('status'),
                        'timestamp': datetime.now(),
                        'reason': 'New listing purchase',
                        'bot': self.name
                    }

                    self.orders.append(order_info)

                    self.positions.append({
                        'symbol': symbol,
                        'entry_price': buy_price,
                        'quantity': qty,
                        'entry_time': datetime.now(),
                        'take_profit': buy_price * (1 + self.config.NEW_LISTING_PROFIT_TARGET),
                        'stop_loss': buy_price * (1 - self.config.NEW_LISTING_STOP_LOSS)
                    })

                    self.new_listings_cache[symbol] = {'entry_price': buy_price, 'entry_time': datetime.now()}

                    self.logger.info(f"New listing purchase: {symbol} at {buy_price}")

        except Exception as e:
            self.logger.error(f"Error analyzing new listing {symbol}: {e}")

    def check_new_listing_positions(self):
        for position in self.positions[:]:
            try:
                current_price = float(self.client.get_symbol_ticker(symbol=position['symbol'])['price'])

                if current_price >= position['take_profit']:
                    self.place_sell_order(position, "New listing take profit")
                elif current_price <= position['stop_loss']:
                    self.place_sell_order(position, "New listing stop loss")

            except Exception as e:
                self.logger.error(f"Error checking position {position.get('symbol')}: {e}")

    def place_sell_order(self, position, reason):
        try:
            order = self.safe_order(self.client.order_market_sell,
                                    symbol=position['symbol'],
                                    quantity=str(position['quantity']))
            if not order:
                self.logger.error(f"Sell order failed for {position.get('symbol')}")
                return

            sell_price = float(order.get('fills', [])[0].get('price')) if order.get('fills') else 0
            profit = (sell_price - position['entry_price']) * position['quantity']

            order_info = {
                'order_id': order.get('orderId'),
                'symbol': position['symbol'],
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': position['quantity'],
                'price': sell_price,
                'status': order.get('status'),
                'timestamp': datetime.now(),
                'reason': reason,
                'profit': profit,
                'bot': self.name
            }

            self.orders.append(order_info)
            self.positions.remove(position)

            self.logger.info(f"New listing sale: {position['symbol']} at {sell_price}, Profit: {profit:.4f}")

        except Exception as e:
            self.logger.error(f"Error selling new listing position: {e}")


class HighVolumeBot(BaseBot):
    def __init__(self, config, client):
        super().__init__("HighVolumeBot", config, client)
        self.trading_symbols = set()
        self.volume_data = {}

    def start(self):
        super().start()
        self._thread = threading.Thread(target=self.analyze_high_volume_coins, daemon=True)
        self._thread.start()

    def analyze_high_volume_coins(self):
        while self.running:
            try:
                tickers_24hr = self.client.get_ticker()

                volume_scores = []
                for ticker in tickers_24hr:
                    if ticker['symbol'].endswith('USDT'):
                        symbol = ticker['symbol']
                        volume = float(ticker.get('volume', 0))
                        price_change = float(ticker.get('priceChangePercent', 0))

                        score = self.calculate_volume_score(symbol, volume, price_change)

                        if score > self.config.SCORE_THRESHOLD:
                            volume_scores.append({
                                'symbol': symbol,
                                'score': score,
                                'volume': volume,
                                'price_change': price_change
                            })

                volume_scores.sort(key=lambda x: x['score'], reverse=True)
                top_coins = volume_scores[:5]

                for coin in top_coins:
                    if coin['symbol'] not in self.trading_symbols:
                        threading.Thread(target=self.analyze_coin_for_trade, args=(coin,), daemon=True).start()

                self.check_high_volume_positions()

            except Exception as e:
                self.logger.error(f"Error in high volume analysis: {e}")

            time.sleep(300)

    def calculate_volume_score(self, symbol, volume, price_change):
        try:
            klines = self.client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, "1 week ago UTC")

            if len(klines) < 24:
                return 0

            volumes = [float(k[5]) for k in klines]
            avg_volume = np.mean(volumes[-168:]) if len(volumes) >= 168 else np.mean(volumes)

            if avg_volume == 0:
                return 0

            volume_ratio = volume / avg_volume

            volume_score = min(volume_ratio * 20, 50)
            momentum_score = abs(price_change) * 2
            consistency_score = min(np.std(volumes[-24:]) / avg_volume * 100, 30) if len(volumes) >= 24 else 15

            total_score = volume_score + momentum_score + (30 - consistency_score)

            return total_score

        except Exception as e:
            self.logger.error(f"Error calculating score for {symbol}: {e}")
            return 0

    def analyze_coin_for_trade(self, coin):
        try:
            symbol = coin['symbol']

            klines = self.client.get_historical_klines(symbol, Client.KLINE_INTERVAL_15MINUTE, "1 day ago UTC")

            if len(klines) < 20:
                return

            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            current_price = closes[-1]
            sma_20 = np.mean(closes[-20:])
            volume_sma = np.mean(volumes[-20:])

            if (current_price > sma_20 * 1.02 and volumes[-1] > volume_sma * self.config.VOLUME_SPIKE_THRESHOLD):
                self.place_high_volume_buy(symbol, current_price, coin['score'])

        except Exception as e:
            self.logger.error(f"Error analyzing coin {coin.get('symbol')}: {e}")

    def place_high_volume_buy(self, symbol, price, score):
        try:
            account = self.client.get_account()
            usdt_balance = next((float(asset['free']) for asset in account.get('balances', []) if asset['asset'] == 'USDT'), 0)

            if usdt_balance > 10:
                raw_qty = Decimal(str(usdt_balance)) * Decimal('0.03') / Decimal(str(price))
                symbol_info = self.get_symbol_info(symbol)
                if symbol_info is None:
                    self.logger.warning(f"No symbol info for {symbol}, skipping trade")
                    return
                step = symbol_info['stepSize']
                qty = float((raw_qty // step) * step)

                if (Decimal(str(qty)) * Decimal(str(price))) > Decimal('10'):
                    order = self.safe_order(self.client.order_market_buy, symbol=symbol, quantity=str(qty))
                    if not order:
                        self.logger.error(f"High volume buy failed for {symbol}")
                        return

                    buy_price = float(order.get('fills', [])[0].get('price')) if order.get('fills') else price

                    order_info = {
                        'order_id': order.get('orderId'),
                        'symbol': symbol,
                        'side': 'BUY',
                        'type': 'MARKET',
                        'quantity': qty,
                        'price': buy_price,
                        'status': order.get('status'),
                        'timestamp': datetime.now(),
                        'reason': f'High volume opportunity (Score: {score:.1f})',
                        'bot': self.name
                    }

                    self.orders.append(order_info)

                    self.positions.append({
                        'symbol': symbol,
                        'entry_price': buy_price,
                        'quantity': qty,
                        'entry_time': datetime.now(),
                        'take_profit': buy_price * (1 + self.config.PROFIT_TARGET * 2),
                        'stop_loss': buy_price * (1 - self.config.STOP_LOSS)
                    })

                    self.trading_symbols.add(symbol)

                    self.logger.info(f"High volume purchase: {symbol} at {buy_price}, Score: {score:.1f}")

        except Exception as e:
            self.logger.error(f"Error placing high volume buy: {e}")

    def check_high_volume_positions(self):
        for position in self.positions[:]:
            try:
                current_price = float(self.client.get_symbol_ticker(symbol=position['symbol'])['price'])

                if current_price >= position['take_profit']:
                    self.place_high_volume_sell(position, "Take profit")
                elif current_price <= position['stop_loss']:
                    self.place_high_volume_sell(position, "Take loss")

            except Exception as e:
                self.logger.error(f"Error checking high volume position: {e}")

    def place_high_volume_sell(self, position, reason):
        try:
            order = self.safe_order(self.client.order_market_sell, symbol=position['symbol'], quantity=str(position['quantity']))
            if not order:
                self.logger.error(f"High volume sell failed for {position.get('symbol')}")
                return

            sell_price = float(order.get('fills', [])[0].get('price')) if order.get('fills') else 0
            profit = (sell_price - position['entry_price']) * position['quantity']

            order_info = {
                'order_id': order.get('orderId'),
                'symbol': position['symbol'],
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': position['quantity'],
                'price': sell_price,
                'status': order.get('status'),
                'timestamp': datetime.now(),
                'reason': reason,
                'profit': profit,
                'bot': self.name
            }

            self.orders.append(order_info)
            self.positions.remove(position)
            self.trading_symbols.discard(position['symbol'])

            self.logger.info(f"High volume sale: {position['symbol']}, Profit: {profit:.4f}")

        except Exception as e:
            self.logger.error(f"Error selling high volume position: {e}")


class MultiBotManager:
    def __init__(self, config):
        self.config = config
        # create client for testnet and ensure API URL for python-binance compatibility
        self.client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=True)
        try:
            self.client.API_URL = getattr(config, 'TESTNET_API_URL', 'https://testnet.binance.vision/api')
        except Exception:
            pass
        self.bots = {}
        self.setup_logging()

    def setup_logging(self):
        # ensure logs folder exists
        import os
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/multi_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('MultiBotManager')

    def initialize_bots(self):
        try:
            from trading_bot import ScalpingTradingBot
            # ScalpingTradingBot handles its own client internally (ok to pass config only)
            self.bots['scalping'] = ScalpingTradingBot(self.config)
        except Exception as e:
            self.logger.error(f"Could not import ScalpingTradingBot: {e}")

        self.bots['new_listing'] = NewListingBot(self.config, self.client)
        self.bots['high_volume'] = HighVolumeBot(self.config, self.client)

        self.logger.info(f"Bots initialized: {list(self.bots.keys())}")

    def start_all_bots(self):
        for name, bot in self.bots.items():
            try:
                bot.start()
                self.logger.info(f"Started {name}")
            except Exception as e:
                self.logger.error(f"Error starting {name}: {e}")

    def stop_all_bots(self):
        for name, bot in self.bots.items():
            try:
                bot.stop()
                self.logger.info(f"Stopped {name}")
            except Exception as e:
                self.logger.error(f"Error stopping {name}: {e}")

    def get_all_stats(self):
        stats = {}
        for name, bot in self.bots.items():
            try:
                stats[name] = bot.get_stats()
            except Exception as e:
                self.logger.error(f"Error getting stats for {name}: {e}")
                stats[name] = {'name': name, 'error': str(e)}

        return stats

    def get_all_orders(self):
        all_orders = []
        for bot in self.bots.values():
            try:
                all_orders.extend(bot.orders)
            except Exception as e:
                self.logger.error(f"Error getting orders: {e}")

        all_orders.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        return all_orders
