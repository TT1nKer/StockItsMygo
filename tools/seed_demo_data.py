#!/usr/bin/env python3
"""Create a small deterministic dataset for screenshots and local demos.

The seed is deliberately offline: it never calls a market-data provider and it
is safe to run repeatedly because all writes use upserts.
"""

import math
import os
import random
import sys
from datetime import date, timedelta

import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import config
from db.init_db_postgres import init_database


DEMO_STOCKS = [
    ("AAPL", "Apple Inc.", "Technology", 190.0),
    ("MSFT", "Microsoft Corporation", "Technology", 420.0),
    ("NVDA", "NVIDIA Corporation", "Technology", 125.0),
    ("AMZN", "Amazon.com, Inc.", "Consumer Cyclical", 185.0),
    ("GOOGL", "Alphabet Inc.", "Communication Services", 175.0),
    ("META", "Meta Platforms, Inc.", "Communication Services", 510.0),
    ("JPM", "JPMorgan Chase & Co.", "Financial Services", 220.0),
    ("TSLA", "Tesla, Inc.", "Consumer Cyclical", 245.0),
]


def business_days(end: date, count: int):
    days = []
    current = end
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return list(reversed(days))


def main():
    config.switch_to_postgresql()
    init_database()

    rng = random.Random(20260107)
    dates = business_days(date.today(), 260)
    price_rows = []

    conn = psycopg2.connect(config.get_connection_string())
    cursor = conn.cursor()

    stock_rows = [
        (symbol, company, company, "Q", "NASDAQ", sector, "United States", 0, 1, dates[0])
        for symbol, company, sector, _ in DEMO_STOCKS
    ]
    execute_values(cursor, """
        INSERT INTO stocks
            (symbol, company_name, security_name, market_category, exchange,
             sector, country, is_etf, is_active, first_added)
        VALUES %s
        ON CONFLICT (symbol) DO UPDATE SET
            company_name = EXCLUDED.company_name,
            security_name = EXCLUDED.security_name,
            sector = EXCLUDED.sector,
            is_active = EXCLUDED.is_active
    """, stock_rows)

    latest = {}
    for stock_index, (symbol, _, _, starting_price) in enumerate(DEMO_STOCKS):
        price = starting_price * 0.82
        for day_index, trading_day in enumerate(dates):
            trend = 0.0008 + stock_index * 0.00003
            cycle = math.sin(day_index / 15 + stock_index) * 0.006
            shock = rng.gauss(0, 0.009)
            open_price = price * (1 + rng.gauss(0, 0.003))
            close = max(5, price * (1 + trend + cycle + shock))
            high = max(open_price, close) * (1 + rng.uniform(0.002, 0.015))
            low = min(open_price, close) * (1 - rng.uniform(0.002, 0.015))
            volume = int((18_000_000 + stock_index * 2_000_000) * rng.uniform(0.65, 1.55))
            price_rows.append((
                symbol, trading_day, round(open_price, 4), round(high, 4),
                round(low, 4), round(close, 4), volume, 1.0, 0, 0,
            ))
            price = close
        latest[symbol] = price

    execute_values(cursor, """
        INSERT INTO price_history
            (symbol, date, open, high, low, close, volume, adj_factor, dividends, stock_splits)
        VALUES %s
        ON CONFLICT (symbol, date) DO UPDATE SET
            open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
            close = EXCLUDED.close, volume = EXCLUDED.volume
    """, price_rows, page_size=1000)

    recommendation_rows = []
    for index, (symbol, _, _, _) in enumerate(DEMO_STOCKS):
        score = 82 - index * 6
        recommendation_rows.append((
            symbol, date.today(), round(latest[symbol], 4), score,
            ["Positive momentum", "Above 20-day average"],
            48 + index * 2, 4.5 - index * 0.3, 8.0 - index * 0.45,
            1.1 + index * 0.08, index < 2, index in (0, 2),
        ))
    execute_values(cursor, """
        INSERT INTO daily_recommendations
            (symbol, recommendation_date, price, score, signals, rsi,
             momentum_10d, momentum_20d, volume_trend, is_breakout, has_volume_surge)
        VALUES %s
        ON CONFLICT (symbol, recommendation_date) DO UPDATE SET
            price = EXCLUDED.price, score = EXCLUDED.score, signals = EXCLUDED.signals,
            rsi = EXCLUDED.rsi, momentum_10d = EXCLUDED.momentum_10d,
            momentum_20d = EXCLUDED.momentum_20d, volume_trend = EXCLUDED.volume_trend,
            is_breakout = EXCLUDED.is_breakout,
            has_volume_surge = EXCLUDED.has_volume_surge
    """, recommendation_rows)

    conn.commit()
    conn.close()
    print(f"Demo ready: {len(DEMO_STOCKS)} stocks, {len(price_rows):,} OHLCV rows, "
          f"{len(recommendation_rows)} recommendations")


if __name__ == "__main__":
    main()
