#!/usr/bin/env python3
"""
FAST Stock Recommendation System
Uses batch SQL queries and caching for 10x+ speed improvement
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import config
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime

config.switch_to_postgresql()

class FastStockRecommender:
    def __init__(self):
        self.conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        self.price_cache = {}  # Cache all price data in memory

    def load_all_price_data(self):
        """Load ALL price data in one massive query - MUCH faster than 2000+ queries"""
        print("Loading all price data (this may take 30-60 seconds)...", flush=True)

        # Single query to get last 252 days (1 year) of data for ALL stocks
        query = """
            SELECT symbol, date, open, high, low, close, volume
            FROM price_history
            WHERE date >= CURRENT_DATE - INTERVAL '252 days'
            ORDER BY symbol, date
        """

        df = pd.read_sql(query, self.conn)
        print(f"Loaded {len(df):,} price records for analysis", flush=True)

        # Group by symbol and cache
        print("Organizing data by symbol...", flush=True)
        for symbol, group in df.groupby('symbol'):
            self.price_cache[symbol] = group.sort_values('date').reset_index(drop=True)

        print(f"✓ Cached data for {len(self.price_cache)} stocks", flush=True)
        return self.price_cache

    def calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:]) if len(gains) >= period else 0
        avg_loss = np.mean(losses[-period:]) if len(losses) >= period else 0

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def calculate_momentum(self, prices, days):
        """Calculate price momentum"""
        if len(prices) < days + 1:
            return 0
        return ((prices[-1] - prices[-(days+1)]) / prices[-(days+1)]) * 100

    def calculate_volume_trend(self, volumes):
        """Calculate volume trend"""
        if len(volumes) < 20:
            return 0
        recent_avg = np.mean(volumes[-5:])
        historical_avg = np.mean(volumes[-20:-5])
        if historical_avg == 0:
            return 0
        return ((recent_avg - historical_avg) / historical_avg) * 100

    def analyze_stock_fast(self, symbol):
        """Analyze stock using cached data"""
        history = self.price_cache.get(symbol)

        if history is None or len(history) < 30:
            return None

        try:
            latest = history.iloc[-1]
            prices = history['close'].values
            volumes = history['volume'].values

            # Calculate indicators
            rsi = self.calculate_rsi(prices)
            momentum_10d = self.calculate_momentum(prices, 10)
            momentum_20d = self.calculate_momentum(prices, 20)
            volume_trend = self.calculate_volume_trend(volumes)

            # 52-week high/low
            high_52w = history['high'].max()
            low_52w = history['low'].min()
            distance_from_high = ((latest['close'] - high_52w) / high_52w) * 100

            # Patterns
            is_breakout = latest['close'] > history['high'].iloc[-20:-1].max() if len(history) >= 20 else False
            has_volume = latest['volume'] > (np.mean(volumes[-20:]) * 1.5) if len(volumes) >= 20 else False

            # Calculate score
            score = 0
            signals = []

            if 30 <= rsi <= 40:
                score += 20
                signals.append('Oversold (RSI)')
            elif 60 <= rsi <= 70:
                score += 10
                signals.append('Strong momentum')

            if momentum_10d > 5:
                score += 15
                signals.append('Positive 10-day momentum')
            if momentum_20d > 10:
                score += 15
                signals.append('Strong 20-day trend')

            if volume_trend > 20:
                score += 15
                signals.append('Increasing volume')
            if has_volume:
                score += 10
                signals.append('Volume surge')

            if is_breakout:
                score += 15
                signals.append('Breakout pattern')

            if distance_from_high > -5:
                score += 10
                signals.append('Near 52-week high')

            return {
                'symbol': symbol,
                'price': float(latest['close']),
                'score': score,
                'signals': signals,
                'rsi': round(float(rsi), 2),
                'momentum_10d': round(float(momentum_10d), 2),
                'momentum_20d': round(float(momentum_20d), 2),
                'volume_trend': round(float(volume_trend), 2),
                'is_breakout': bool(is_breakout),
                'has_volume_surge': bool(has_volume),
                'date': str(latest['date'])
            }
        except Exception as e:
            return None

    def generate_recommendations(self, min_score=30):
        """Generate recommendations using fast batch processing"""
        print("="*70, flush=True)
        print("FAST STOCK RECOMMENDATION SYSTEM", flush=True)
        print("="*70, flush=True)

        # Step 1: Load all data at once (30-60 seconds)
        self.load_all_price_data()

        # Step 2: Analyze all stocks (now very fast - just calculations)
        print(f"\nAnalyzing {len(self.price_cache)} stocks...", flush=True)

        results = []
        symbols = list(self.price_cache.keys())

        for i, symbol in enumerate(symbols):
            if (i + 1) % 500 == 0:
                print(f"Progress: {i+1}/{len(symbols)} ({len(results)} candidates)", flush=True)

            analysis = self.analyze_stock_fast(symbol)
            if analysis and analysis['score'] >= min_score:
                results.append(analysis)

        results.sort(key=lambda x: x['score'], reverse=True)

        print(f"\n✓ Found {len(results)} stocks with score >= {min_score}", flush=True)

        # Step 3: Save to database
        self.save_recommendations(results)

        return results

    def save_recommendations(self, recommendations):
        """Save recommendations to database"""
        from psycopg2.extras import execute_values

        cursor = self.conn.cursor()

        # Create table if needed
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

        today = datetime.now().date()
        values = [
            (
                str(r['symbol']),
                today,
                float(r['price']),
                int(r['score']),
                r['signals'],
                float(r['rsi']),
                float(r['momentum_10d']),
                float(r['momentum_20d']),
                float(r['volume_trend']),
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
                has_volume_surge = EXCLUDED.has_volume_surge
            """,
            values
        )

        self.conn.commit()
        print(f"✓ Saved {len(recommendations)} recommendations to database", flush=True)

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()


if __name__ == '__main__':
    import time
    start_time = time.time()

    recommender = FastStockRecommender()
    recommendations = recommender.generate_recommendations(min_score=30)

    elapsed = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"TOTAL TIME: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"{'='*70}")

    # Show top 10
    print("\nTOP 10 RECOMMENDATIONS:")
    print("="*70)
    for i, rec in enumerate(recommendations[:10], 1):
        print(f"\n{i}. {rec['symbol']} - Score: {rec['score']}")
        print(f"   Price: ${rec['price']:.2f}")
        print(f"   Signals: {', '.join(rec['signals'][:3])}")
