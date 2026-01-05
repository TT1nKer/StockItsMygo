#!/usr/bin/env python3
"""
Daily Stock Recommendation System
Analyzes stocks and generates daily picks based on technical and fundamental criteria
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import config
from db.api import StockDB
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

config.switch_to_postgresql()
db = StockDB()

class StockRecommender:
    """Generate daily stock recommendations based on multiple criteria"""

    def __init__(self):
        self.db = db

    def calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period

        if down == 0:
            return 100

        rs = up / down
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_momentum(self, prices, period=10):
        """Calculate price momentum"""
        if len(prices) < period + 1:
            return 0
        return ((prices[-1] - prices[-period-1]) / prices[-period-1]) * 100

    def calculate_volume_trend(self, volumes, period=10):
        """Calculate volume trend"""
        if len(volumes) < period:
            return 0
        recent_avg = np.mean(volumes[-5:])
        historical_avg = np.mean(volumes[-period:])
        return ((recent_avg - historical_avg) / historical_avg) * 100

    def is_breakout(self, history, period=20):
        """Check if stock is breaking out"""
        if len(history) < period + 1:
            return False

        recent = history.tail(period + 1)
        high_20 = recent['high'].iloc[:-1].max()
        latest_close = recent['close'].iloc[-1]

        # Breakout if close is above 20-day high
        return latest_close > high_20

    def has_volume_surge(self, history, threshold=1.5):
        """Check for volume surge"""
        if len(history) < 20:
            return False

        avg_volume = history['volume'].iloc[-20:-1].mean()
        latest_volume = history['volume'].iloc[-1]

        return latest_volume > (avg_volume * threshold)

    def analyze_stock(self, symbol):
        """Comprehensive stock analysis"""
        try:
            history = self.db.get_price_history(symbol)

            if len(history) < 30:  # Need at least 30 days of data
                return None

            # Get latest data
            latest = history.iloc[-1]
            prices = history['close'].values
            volumes = history['volume'].values

            # Calculate indicators
            rsi = self.calculate_rsi(prices)
            momentum_10d = self.calculate_momentum(prices, 10)
            momentum_20d = self.calculate_momentum(prices, 20)
            volume_trend = self.calculate_volume_trend(volumes)

            # Get 52-week high/low
            year_data = history.tail(252)
            high_52w = year_data['high'].max()
            low_52w = year_data['low'].min()

            # Calculate distance from 52-week high
            distance_from_high = ((latest['close'] - high_52w) / high_52w) * 100

            # Check patterns
            is_breakout = self.is_breakout(history)
            has_volume = self.has_volume_surge(history)

            # Calculate score (0-100)
            score = 0
            signals = []

            # RSI scoring (oversold/overbought)
            if 30 <= rsi <= 40:
                score += 20
                signals.append('Oversold (RSI)')
            elif 60 <= rsi <= 70:
                score += 10
                signals.append('Strong momentum')

            # Momentum scoring
            if momentum_10d > 5:
                score += 15
                signals.append('Positive 10-day momentum')
            if momentum_20d > 10:
                score += 15
                signals.append('Strong 20-day trend')

            # Volume scoring
            if volume_trend > 20:
                score += 15
                signals.append('Increasing volume')
            if has_volume:
                score += 10
                signals.append('Volume surge')

            # Breakout scoring
            if is_breakout:
                score += 15
                signals.append('Breakout pattern')

            # Near 52-week high
            if distance_from_high > -5:
                score += 10
                signals.append('Near 52-week high')

            return {
                'symbol': symbol,
                'price': float(latest['close']),
                'volume': int(latest['volume']),
                'rsi': round(rsi, 2),
                'momentum_10d': round(momentum_10d, 2),
                'momentum_20d': round(momentum_20d, 2),
                'volume_trend': round(volume_trend, 2),
                'high_52w': float(high_52w),
                'low_52w': float(low_52w),
                'distance_from_high': round(distance_from_high, 2),
                'is_breakout': bool(is_breakout),
                'has_volume_surge': bool(has_volume),
                'score': score,
                'signals': signals,
                'date': str(latest['date'])
            }
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None

    def get_daily_recommendations(self, min_score=30):
        """Get all daily recommendations above minimum score threshold - FAST VERSION"""
        print("Analyzing stocks for daily recommendations...", flush=True)

        stocks = self.db.get_stock_list()
        print(f"Total stocks to analyze: {len(stocks)}", flush=True)

        results = []
        progress_interval = 100  # Show progress every 100 stocks

        # Process stocks one by one but with better progress reporting
        print("Starting analysis (this will take 3-5 minutes)...", flush=True)

        for i, symbol in enumerate(stocks):
            # Show progress more frequently at start, then every 100
            should_print = (i < 500 and (i + 1) % 100 == 0) or ((i + 1) % 200 == 0)
            if should_print:
                elapsed_pct = ((i + 1) / len(stocks)) * 100
                print(f"Progress: {i+1}/{len(stocks)} ({elapsed_pct:.1f}%) - {len(results)} candidates found", flush=True)

            try:
                analysis = self.analyze_stock(symbol)
                if analysis and analysis['score'] >= min_score:
                    results.append(analysis)
            except Exception as e:
                # Silently skip errors to speed up
                continue

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        print(f"\nCompleted! Found {len(results)} stocks with score >= {min_score}", flush=True)

        return results

    def save_recommendations(self, recommendations):
        """Save daily recommendations to database"""
        import psycopg2
        from psycopg2.extras import execute_values

        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()

        # Create recommendations table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_recommendations (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                recommendation_date DATE,
                price NUMERIC(12, 2),
                score INTEGER,
                signals TEXT[],
                rsi NUMERIC(6, 2),
                momentum_10d NUMERIC(8, 2),
                momentum_20d NUMERIC(8, 2),
                volume_trend NUMERIC(8, 2),
                is_breakout BOOLEAN,
                has_volume_surge BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, recommendation_date)
            )
        """)

        # Insert recommendations (convert all numpy types to Python types)
        today = datetime.now().date()
        values = [
            (
                str(r['symbol']),
                today,
                float(r['price']),
                int(r['score']),
                r['signals'],
                float(r['rsi']) if r['rsi'] is not None else None,
                float(r['momentum_10d']) if r['momentum_10d'] is not None else None,
                float(r['momentum_20d']) if r['momentum_20d'] is not None else None,
                float(r['volume_trend']) if r['volume_trend'] is not None else None,
                bool(r['is_breakout']),
                bool(r['has_volume_surge'])
            )
            for r in recommendations
        ]

        execute_values(
            cursor,
            """
            INSERT INTO daily_recommendations
            (symbol, recommendation_date, price, score, signals, rsi, momentum_10d,
             momentum_20d, volume_trend, is_breakout, has_volume_surge)
            VALUES %s
            ON CONFLICT (symbol, recommendation_date) DO UPDATE SET
                price = EXCLUDED.price,
                score = EXCLUDED.score,
                signals = EXCLUDED.signals,
                rsi = EXCLUDED.rsi,
                momentum_10d = EXCLUDED.momentum_10d,
                momentum_20d = EXCLUDED.momentum_20d,
                volume_trend = EXCLUDED.volume_trend,
                is_breakout = EXCLUDED.is_breakout,
                has_volume_surge = EXCLUDED.has_volume_surge,
                created_at = CURRENT_TIMESTAMP
            """,
            values
        )

        conn.commit()
        conn.close()

        print(f"✓ Saved {len(recommendations)} recommendations to database", flush=True)

if __name__ == '__main__':
    recommender = StockRecommender()

    print("="*70)
    print("DAILY STOCK RECOMMENDATION SYSTEM")
    print("="*70)

    # Generate ALL recommendations (score >= 30)
    recommendations = recommender.get_daily_recommendations(min_score=30)

    # Save ALL to database (for web dashboard filtering)
    recommender.save_recommendations(recommendations)

    # Display top 10
    print("\n" + "="*70)
    print("TOP 10 RECOMMENDATIONS")
    print("="*70)

    for i, rec in enumerate(recommendations[:10], 1):
        print(f"\n{i}. {rec['symbol']} - Score: {rec['score']}")
        print(f"   Price: ${rec['price']:.2f}")
        print(f"   Signals: {', '.join(rec['signals'][:3])}")
        print(f"   RSI: {rec['rsi']} | 10D Momentum: {rec['momentum_10d']:.1f}%")
