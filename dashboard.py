# dashboard.py (updated for multi-bot)
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import threading
import time
import os
from config import Config
from multi_bot_manager import MultiBotManager

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize multi-bot manager
config = Config()
bot_manager = MultiBotManager(config)
bot_manager.initialize_bots()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/orders')
def get_orders():
    return jsonify(bot_manager.get_all_orders()[-50:])  # Last 50 orders

@app.route('/api/stats')
def get_stats():
    return jsonify(bot_manager.get_all_stats())

@app.route('/api/balance')
def get_balance():
    # Get balance from first bot (they all share the same account)
    for bot_name, bot in bot_manager.bots.items():
        if hasattr(bot, 'get_account_balance'):
            return jsonify(bot.get_account_balance())
    return jsonify({})

@app.route('/api/start', methods=['POST'])
def start_trading():
    bot_manager.start_all_bots()
    return jsonify({'status': 'started', 'message': 'All trading bots started successfully'})

@app.route('/api/stop', methods=['POST'])
def stop_trading():
    bot_manager.stop_all_bots()
    return jsonify({'status': 'stopped', 'message': 'All trading bots stopped'})

@app.route('/api/start-bot/<bot_name>', methods=['POST'])
def start_single_bot(bot_name):
    if bot_name in bot_manager.bots:
        bot_manager.bots[bot_name].start()
        return jsonify({'status': 'started', 'message': f'{bot_name} started successfully'})
    return jsonify({'status': 'error', 'message': 'Bot not found'})

@app.route('/api/stop-bot/<bot_name>', methods=['POST'])
def stop_single_bot(bot_name):
    if bot_name in bot_manager.bots:
        bot_manager.bots[bot_name].stop()
        return jsonify({'status': 'stopped', 'message': f'{bot_name} stopped successfully'})
    return jsonify({'status': 'error', 'message': 'Bot not found'})

@app.route('/api/health')
def health_check():
    stats = bot_manager.get_all_stats()
    running_bots = sum(1 for bot_stats in stats.values() if bot_stats.get('running', False))
    
    return jsonify({
        'status': 'healthy',
        'total_bots': len(bot_manager.bots),
        'running_bots': running_bots,
        'service': 'multi-bot-trading-dashboard'
    })

@app.route('/api/config')
def get_config():
    return jsonify({
        'symbol': config.SYMBOL,
        'quantity': config.QUANTITY,
        'profit_target': config.PROFIT_TARGET,
        'stop_loss': config.STOP_LOSS,
        'new_listing_profit_target': config.NEW_LISTING_PROFIT_TARGET,
        'new_listing_stop_loss': config.NEW_LISTING_STOP_LOSS
    })

@socketio.on('connect')
def handle_connect():
    print('Client connected to dashboard')
    socketio.emit('status_update', {
        'status': 'connected', 
        'total_bots': len(bot_manager.bots)
    })

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from dashboard')

def background_data_updater():
    """Background thread to update data periodically"""
    while True:
        try:
            socketio.emit('orders_update', bot_manager.get_all_orders()[-20:])
            socketio.emit('stats_update', bot_manager.get_all_stats())
            
            # Get balance from any bot
            for bot_name, bot in bot_manager.bots.items():
                if hasattr(bot, 'get_account_balance'):
                    socketio.emit('balance_update', bot.get_account_balance())
                    break
                    
        except Exception as e:
            print(f"Error in background updater: {e}")
        
        time.sleep(3)

if __name__ == '__main__':
    host = config.DASHBOARD_HOST
    port = config.DASHBOARD_PORT
    
    print(f"Starting Multi-Bot Trading Dashboard on http://{host}:{port}")
    print(f"Available Bots: {list(bot_manager.bots.keys())}")
    print(f"Main Trading Symbol: {config.SYMBOL}")
    
    # Start background updater
    updater_thread = threading.Thread(target=background_data_updater)
    updater_thread.daemon = True
    updater_thread.start()
    
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    @app.route('/api/force-trade', methods=['POST'])
def force_trade():
    """Force a test trade to verify everything works"""
    try:
        from binance.client import Client
        client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=True)
        
        # Get current price
        symbol = 'BTCUSDT'
        ticker = client.get_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
        
        # Place a limit order that likely won't execute
        test_price = current_price * 0.9  # 10% below current price
        quantity = 0.001
        
        order = client.order_limit_buy(
            symbol=symbol,
            quantity=quantity,
            price=str(round(test_price, 2))
        )
        
        return jsonify({
            'status': 'success', 
            'message': f'Test order placed at ${test_price:.2f}',
            'order': order
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})