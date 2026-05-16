#!/usr/bin/env python3
"""
Stock Analysis Dashboard
Web-based interface for viewing stock data and analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from config.database import config
from db.api import StockDB
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
import threading

# Authentication imports
from auth import (
    login_required, get_current_user_id, get_current_username,
    authenticate_user, register_user, is_logged_in
)

app = Flask(__name__)

# Configure session (secret key for session encryption)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-key-CHANGE-IN-PRODUCTION-b8f3d2e1a9c4')

# Global variable to track update progress
update_status = {
    'running': False,
    'progress': [],
    'current_step': '',
    'error': None
}

# Use PostgreSQL backend
config.switch_to_postgresql()
db = StockDB()

def get_stock_links(symbol):
    """Generate links to popular financial websites"""
    return {
        'yahoo': f'https://finance.yahoo.com/quote/{symbol}',
        'finviz': f'https://finviz.com/quote.ashx?t={symbol}',
        'marketwatch': f'https://www.marketwatch.com/investing/stock/{symbol}',
        'seeking_alpha': f'https://seekingalpha.com/symbol/{symbol}',
        'tradingview': f'https://www.tradingview.com/symbols/{symbol}/',
        'google': f'https://www.google.com/finance/quote/{symbol}:NASDAQ'
    }

@app.route('/')
def index():
    """Main dashboard page - requires login"""
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=get_current_username())


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication handler"""
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')

        success, message, user_id = authenticate_user(username, password)

        if success:
            # Create session
            session['user_id'] = user_id
            session['username'] = username
            return jsonify({'success': True, 'redirect': '/'})
        else:
            return jsonify({'success': False, 'error': message}), 401

    # GET request - show login page
    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    invitation_code = data.get('invitation_code')

    success, message, user_id = register_user(username, password, invitation_code)

    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('login'))


# ============================================================================
# Public API Routes (no login required)
# ============================================================================

@app.route('/api/stats')
def get_stats():
    """Get overall database statistics"""
    try:
        import psycopg2
        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        # Get counts
        cursor.execute('SELECT COUNT(*) FROM stocks')
        total_stocks = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(DISTINCT symbol) FROM price_history')
        stocks_with_data = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM price_history')
        total_records = cursor.fetchone()[0]

        cursor.execute("SELECT pg_size_pretty(pg_database_size('stock_db'))")
        db_size = cursor.fetchone()[0]

        cursor.execute('SELECT MAX(date) FROM price_history')
        latest_date = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'total_stocks': total_stocks,
            'stocks_with_data': stocks_with_data,
            'coverage': round(stocks_with_data / total_stocks * 100, 1),
            'total_records': total_records,
            'db_size': db_size,
            'latest_date': str(latest_date) if latest_date else 'N/A'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/top_movers')
def get_top_movers():
    """Get top gaining and losing stocks"""
    try:
        # Get stocks with recent data
        stocks = db.get_stock_list()

        movers = []
        for symbol in stocks[:200]:  # Check first 200 for speed
            history = db.get_price_history(symbol)
            if len(history) >= 2:
                latest = history.iloc[-1]
                previous = history.iloc[-2]
                change_pct = ((latest['close'] - previous['close']) / previous['close']) * 100

                movers.append({
                    'symbol': symbol,
                    'price': round(latest['close'], 2),
                    'change': round(change_pct, 2),
                    'volume': int(latest['volume']),
                    'links': get_stock_links(symbol)
                })

        # Sort by change percentage
        movers.sort(key=lambda x: x['change'], reverse=True)

        return jsonify({
            'gainers': movers[:10],
            'losers': movers[-10:][::-1]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/<symbol>')
def get_stock_data(symbol):
    """Get detailed data for a specific stock"""
    try:
        # Get stock info
        stock_info = db.get_stock_info(symbol)

        # Get price history
        history = db.get_price_history(symbol)

        if len(history) == 0:
            return jsonify({'error': f'No data found for {symbol}'}), 404

        # Calculate statistics
        latest = history.iloc[-1]

        # Get 52-week high/low
        last_year = history.tail(252)  # ~252 trading days in a year
        high_52w = last_year['high'].max()
        low_52w = last_year['low'].min()

        # Calculate returns
        if len(history) >= 2:
            change_1d = ((latest['close'] - history.iloc[-2]['close']) / history.iloc[-2]['close']) * 100
        else:
            change_1d = 0

        if len(history) >= 5:
            change_5d = ((latest['close'] - history.iloc[-5]['close']) / history.iloc[-5]['close']) * 100
        else:
            change_5d = 0

        if len(history) >= 20:
            change_1m = ((latest['close'] - history.iloc[-20]['close']) / history.iloc[-20]['close']) * 100
        else:
            change_1m = 0

        # Prepare chart data (last 6 months)
        recent = history.tail(126)

        return jsonify({
            'symbol': symbol,
            'info': stock_info if stock_info else {},
            'latest_price': round(latest['close'], 2),
            'latest_date': str(latest['date']),
            'change_1d': round(change_1d, 2),
            'change_5d': round(change_5d, 2),
            'change_1m': round(change_1m, 2),
            'volume': int(latest['volume']),
            'high_52w': round(high_52w, 2),
            'low_52w': round(low_52w, 2),
            'total_records': len(history),
            'chart_data': {
                'dates': recent['date'].astype(str).tolist(),
                'open': recent['open'].tolist(),
                'high': recent['high'].tolist(),
                'low': recent['low'].tolist(),
                'close': recent['close'].tolist(),
                'volume': recent['volume'].tolist()
            },
            'links': get_stock_links(symbol)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search_stocks():
    """Search for stocks by symbol or name"""
    query = request.args.get('q', '').upper()

    if not query:
        return jsonify([])

    try:
        stocks = db.get_stock_list()

        # Filter stocks that match the query
        matches = []
        for symbol in stocks:
            if query in symbol:
                stock_info = db.get_stock_info(symbol)
                matches.append({
                    'symbol': symbol,
                    'name': stock_info.get('company_name', '') if stock_info else '',
                    'sector': stock_info.get('sector', '') if stock_info else ''
                })

                if len(matches) >= 10:
                    break

        return jsonify(matches)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations')
def get_daily_recommendations():
    """Get today's stock recommendations with optional filtering"""
    try:
        import psycopg2
        from datetime import datetime

        # Get filter parameters
        min_score = request.args.get('min_score', 30, type=int)
        max_results = request.args.get('limit', 200, type=int)  # Default: show up to 200

        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        # Get today's recommendations with score filter
        today = datetime.now().date()
        cursor.execute("""
            SELECT symbol, price, score, signals, rsi, momentum_10d,
                   is_breakout, has_volume_surge, recommendation_date
            FROM daily_recommendations
            WHERE recommendation_date = %s AND score >= %s
            ORDER BY score DESC
            LIMIT %s
        """, (today, min_score, max_results))

        recommendations = []
        for row in cursor.fetchall():
            symbol, price, score, signals, rsi, momentum, is_breakout, has_volume, rec_date = row
            recommendations.append({
                'symbol': symbol,
                'price': float(price) if price else 0,
                'score': score,
                'signals': signals if signals else [],
                'rsi': float(rsi) if rsi else 0,
                'momentum': float(momentum) if momentum else 0,
                'is_breakout': is_breakout,
                'has_volume_surge': has_volume,
                'date': str(rec_date),
                'links': get_stock_links(symbol)
            })

        # Get counts by score range (before closing connection)
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN score >= 60 THEN 1 END) as high_score,
                COUNT(CASE WHEN score >= 40 AND score < 60 THEN 1 END) as medium_score,
                COUNT(CASE WHEN score >= 30 AND score < 40 THEN 1 END) as low_score,
                COUNT(*) as total
            FROM daily_recommendations
            WHERE recommendation_date = %s
        """, (today,))

        counts = cursor.fetchone()
        conn.close()

        return jsonify({
            'recommendations': recommendations,
            'counts': {
                'high': counts[0] if counts else 0,
                'medium': counts[1] if counts else 0,
                'low': counts[2] if counts else 0,
                'total': counts[3] if counts else 0
            }
        })
    except Exception as e:
        return jsonify({'error': str(e), 'recommendations': [], 'counts': {}}), 500

@app.route('/api/watchlist')
@login_required
def get_user_watchlist():
    """Get user's personal watchlist"""
    try:
        import psycopg2
        from datetime import datetime

        user_id = get_current_user_id()
        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        # Get watchlist stocks for current user only
        cursor.execute("""
            SELECT symbol, added_date, target_date, notes, position_type
            FROM user_watchlist
            WHERE is_active = true AND user_id = %s
            ORDER BY added_date DESC
        """, (user_id,))

        watchlist = []
        for row in cursor.fetchall():
            symbol, added_date, target_date, notes, position_type = row

            # Get latest price
            history = db.get_price_history(symbol)
            if len(history) >= 2:
                latest = history.iloc[-1]
                previous = history.iloc[-2]
                added_price = None

                # Get price at add date (convert both to string for comparison)
                history['date_str'] = history['date'].astype(str)
                added_row = history[history['date_str'] == str(added_date)]
                if len(added_row) > 0:
                    added_price = float(added_row.iloc[0]['close'])
                else:
                    # If exact date not found, use latest price as fallback
                    added_price = float(latest['close'])

                change_pct = ((latest['close'] - previous['close']) / previous['close']) * 100
                change_since_add = ((latest['close'] - added_price) / added_price * 100) if added_price else 0

                watchlist.append({
                    'symbol': symbol,
                    'price': round(latest['close'], 2),
                    'change': round(change_pct, 2),
                    'added_price': round(added_price, 2) if added_price else None,
                    'change_since_add': round(change_since_add, 2) if added_price else None,
                    'added_date': str(added_date),
                    'target_date': str(target_date) if target_date else None,
                    'days_remaining': (target_date - datetime.now().date()).days if target_date else None,
                    'notes': notes,
                    'position_type': position_type,
                    'volume': int(latest['volume']),
                    'links': get_stock_links(symbol)
                })

        conn.close()
        return jsonify(watchlist)
    except Exception as e:
        return jsonify({'error': str(e), 'watchlist': []}), 500

@app.route('/api/watchlist/add', methods=['POST'])
@login_required
def add_to_watchlist():
    """Add stock to watchlist"""
    try:
        import psycopg2
        from datetime import datetime, timedelta

        user_id = get_current_user_id()
        data = request.json
        symbol = data.get('symbol')
        notes = data.get('notes', '')
        days = data.get('days', 14)
        position_type = data.get('position_type', 'watch')

        # Validate position_type
        valid_types = ['long', 'short', 'watch', 'wishlist']
        if position_type not in valid_types:
            position_type = 'watch'

        if not symbol:
            return jsonify({'error': 'Symbol required'}), 400

        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        # Note: table structure now includes user_id (added by migration)
        # No longer creating table here - should already exist from migration

        # Add to watchlist for current user
        today = datetime.now().date()
        target = today + timedelta(days=days)

        cursor.execute("""
            INSERT INTO user_watchlist (user_id, symbol, added_date, target_date, notes, position_type, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, true)
            ON CONFLICT (user_id, symbol) DO UPDATE SET
                is_active = true,
                target_date = EXCLUDED.target_date,
                notes = EXCLUDED.notes,
                position_type = EXCLUDED.position_type
        """, (user_id, symbol, today, target, notes, position_type))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'{symbol} added to watchlist'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlist/remove/<symbol>', methods=['DELETE'])
@login_required
def remove_from_watchlist(symbol):
    """Remove stock from watchlist"""
    try:
        import psycopg2

        user_id = get_current_user_id()
        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_watchlist
            SET is_active = false
            WHERE symbol = %s AND user_id = %s
        """, (symbol, user_id))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'{symbol} removed from watchlist'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_update_background():
    """Background thread function to run update"""
    global update_status
    import subprocess

    try:
        venv_python = os.path.join(os.getcwd(), 'venv', 'bin', 'python')

        # Step 1: Update price data
        update_status['current_step'] = 'Downloading latest price data (last 5 days)...'
        update_status['progress'].append(update_status['current_step'])

        result = subprocess.Popen(
            [venv_python, '-u', 'tools/update_recent_data.py', '--days', '5', '--yes'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            cwd=os.getcwd()
        )

        # Read output line by line
        for line in result.stdout:
            line = line.strip()
            if line and not line.startswith('/'):  # Filter out file paths and warnings
                if 'Batch' in line or 'SUCCESS' in line or 'Progress:' in line or 'stocks' in line or 'Total' in line:
                    update_status['progress'].append(line)

        result.wait()

        if result.returncode != 0:
            update_status['error'] = 'Data update failed'
            update_status['running'] = False
            return

        update_status['progress'].append('✓ Price data updated successfully')

        # Step 2: Generate recommendations (use FAST version)
        update_status['current_step'] = 'Analyzing 2,138 stocks (fast mode - 2-3 minutes)...'
        update_status['progress'].append(update_status['current_step'])

        rec_result = subprocess.Popen(
            [venv_python, '-u', 'strategy_recommender_fast.py'],  # Use fast version!
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            cwd=os.getcwd()
        )

        # Read recommender output
        for line in rec_result.stdout:
            line = line.strip()
            if line and not line.startswith('/'):
                if 'Progress:' in line or 'Found' in line or 'Saved' in line or '===' in line or 'Analyzing' in line or 'Total stocks' in line:
                    update_status['progress'].append(line)

        rec_result.wait()

        if rec_result.returncode != 0:
            update_status['error'] = 'Recommendation generation failed'
            update_status['running'] = False
            return

        update_status['progress'].append('✓ Recommendations generated successfully')
        update_status['current_step'] = 'Complete!'
        update_status['running'] = False

    except Exception as e:
        update_status['error'] = str(e)
        update_status['running'] = False

@app.route('/api/update', methods=['POST'])
def update_data():
    """Start data update in background"""
    global update_status

    if update_status['running']:
        return jsonify({
            'success': False,
            'error': 'Update already in progress'
        }), 400

    # Reset status
    update_status = {
        'running': True,
        'progress': ['Starting update...'],
        'current_step': 'Initializing...',
        'error': None
    }

    # Start background thread
    thread = threading.Thread(target=run_update_background)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Update started in background'
    })

@app.route('/api/update/status', methods=['GET'])
def update_progress():
    """Get current update progress"""
    global update_status
    return jsonify({
        'running': update_status['running'],
        'progress': update_status['progress'][-50:],  # Last 50 lines
        'current_step': update_status['current_step'],
        'error': update_status['error']
    })

if __name__ == '__main__':
    print('=' * 70)
    print('Stock Analysis Dashboard')
    print('=' * 70)
    print('\nStarting web server...')
    port = int(os.environ.get('DASHBOARD_PORT', 8090))
    print(f'Dashboard URL: http://localhost:{port}')
    print('\nPress Ctrl+C to stop')
    print('=' * 70)

    app.run(debug=True, host='0.0.0.0', port=port)
