#!/usr/bin/env python3
"""
Stock Analysis Dashboard
Web-based interface for viewing stock data and analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request
from config.database import config
from db.api import StockDB
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json

app = Flask(__name__)

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
    """Main dashboard page"""
    return render_template('dashboard.html')

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
def get_user_watchlist():
    """Get user's personal watchlist"""
    try:
        import psycopg2

        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        # Get watchlist stocks
        cursor.execute("""
            SELECT symbol, added_date, target_date, notes
            FROM user_watchlist
            WHERE is_active = true
            ORDER BY added_date DESC
        """)

        watchlist = []
        for row in cursor.fetchall():
            symbol, added_date, target_date, notes = row

            # Get latest price
            history = db.get_price_history(symbol)
            if len(history) >= 2:
                latest = history.iloc[-1]
                previous = history.iloc[-2]
                added_price = None

                # Get price at add date
                added_row = history[history['date'] == str(added_date)]
                if len(added_row) > 0:
                    added_price = float(added_row.iloc[0]['close'])

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
                    'volume': int(latest['volume']),
                    'links': get_stock_links(symbol)
                })

        conn.close()
        return jsonify(watchlist)
    except Exception as e:
        return jsonify({'error': str(e), 'watchlist': []}), 500

@app.route('/api/watchlist/add', methods=['POST'])
def add_to_watchlist():
    """Add stock to watchlist"""
    try:
        import psycopg2
        from datetime import datetime, timedelta

        data = request.json
        symbol = data.get('symbol')
        notes = data.get('notes', '')
        days = data.get('days', 14)

        if not symbol:
            return jsonify({'error': 'Symbol required'}), 400

        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                added_date DATE DEFAULT CURRENT_DATE,
                target_date DATE,
                notes TEXT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol)
            )
        """)

        # Add to watchlist
        today = datetime.now().date()
        target = today + timedelta(days=days)

        cursor.execute("""
            INSERT INTO user_watchlist (symbol, added_date, target_date, notes, is_active)
            VALUES (%s, %s, %s, %s, true)
            ON CONFLICT (symbol) DO UPDATE SET
                is_active = true,
                target_date = EXCLUDED.target_date,
                notes = EXCLUDED.notes
        """, (symbol, today, target, notes))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'{symbol} added to watchlist'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlist/remove/<symbol>', methods=['DELETE'])
def remove_from_watchlist(symbol):
    """Remove stock from watchlist"""
    try:
        import psycopg2

        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_watchlist
            SET is_active = false
            WHERE symbol = %s
        """, (symbol,))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'{symbol} removed from watchlist'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_data():
    """Trigger data update and recommendation generation"""
    try:
        import subprocess

        # Run update script
        result = subprocess.run(
            ['python', 'tools/update_recent_data.py', '--days', '5'],
            capture_output=True,
            text=True,
            timeout=600
        )

        # Run recommendation generation
        rec_result = subprocess.run(
            ['python', 'strategy_recommender.py'],
            capture_output=True,
            text=True,
            timeout=600
        )

        return jsonify({
            'success': True,
            'message': 'Data updated and recommendations generated',
            'update_output': result.stdout[:500],
            'rec_output': rec_result.stdout[:500]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print('=' * 70)
    print('Stock Analysis Dashboard')
    print('=' * 70)
    print('\nStarting web server...')
    print('Dashboard URL: http://localhost:8080')
    print('\nPress Ctrl+C to stop')
    print('=' * 70)

    app.run(debug=True, host='0.0.0.0', port=8080)
