"""
Check Database Data Summary
检查数据库数据摘要
"""

import sqlite3
from datetime import datetime
from config.paths import paths

db_path = paths.db_path

print("=" * 80)
print("DATABASE DATA SUMMARY")
print("=" * 80)
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Basic stock info
print("1. STOCK INFORMATION")
print("-" * 80)
total_stocks = cursor.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
print(f"Total stocks in database: {total_stocks}")

# Stocks with data
stocks_with_daily = cursor.execute("SELECT COUNT(DISTINCT symbol) FROM price_history").fetchone()[0]
print(f"Stocks with daily price data: {stocks_with_daily}")

stocks_with_intraday = cursor.execute("SELECT COUNT(DISTINCT symbol) FROM intraday_price").fetchone()[0]
print(f"Stocks with intraday data: {stocks_with_intraday}")
print()

# 2. Daily price data
print("2. DAILY PRICE DATA")
print("-" * 80)
total_daily_records = cursor.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
print(f"Total daily price records: {total_daily_records:,}")

if total_daily_records > 0:
    # Date range
    date_range = cursor.execute("""
        SELECT MIN(date), MAX(date), COUNT(DISTINCT date)
        FROM price_history
    """).fetchone()
    print(f"Date range: {date_range[0]} to {date_range[1]}")
    print(f"Trading days covered: {date_range[2]}")

    # Latest data date
    latest_date = cursor.execute("SELECT MAX(date) FROM price_history").fetchone()[0]
    print(f"Latest data: {latest_date}")

    # Stocks updated on latest date
    latest_count = cursor.execute("""
        SELECT COUNT(DISTINCT symbol)
        FROM price_history
        WHERE date = ?
    """, (latest_date,)).fetchone()[0]
    print(f"Stocks updated on latest date: {latest_count}")
print()

# 3. Intraday data
print("3. INTRADAY DATA (5-minute)")
print("-" * 80)
total_intraday = cursor.execute("SELECT COUNT(*) FROM intraday_price").fetchone()[0]
print(f"Total intraday records: {total_intraday:,}")

if total_intraday > 0:
    # Symbols with intraday data
    intraday_symbols = cursor.execute("""
        SELECT symbol, COUNT(*) as records,
               MIN(datetime) as first_dt,
               MAX(datetime) as last_dt
        FROM intraday_price
        GROUP BY symbol
        ORDER BY records DESC
        LIMIT 10
    """).fetchall()

    print(f"\nTop 10 stocks with intraday data:")
    for sym, count, first, last in intraday_symbols:
        print(f"  {sym}: {count:,} records ({first[:10]} to {last[:10]})")
print()

# 4. Watchlist
print("4. WATCHLIST")
print("-" * 80)
watchlist_count = cursor.execute("SELECT COUNT(*) FROM watchlist WHERE is_active=1").fetchone()[0]
print(f"Active watchlist stocks: {watchlist_count}")

if watchlist_count > 0:
    watchlist = cursor.execute("""
        SELECT symbol, priority, source, added_date, notes
        FROM watchlist
        WHERE is_active = 1
        ORDER BY priority, added_date DESC
    """).fetchall()

    priority_names = {1: 'High', 2: 'Medium', 3: 'Low'}

    print("\nWatchlist stocks:")
    for sym, priority, source, added, notes in watchlist:
        pri_name = priority_names.get(priority, 'Unknown')
        print(f"  [{sym}] Priority: {pri_name} | Source: {source} | Added: {added[:10]}")
        if notes:
            print(f"         Notes: {notes[:60]}")
print()

# 5. Technical indicators
print("5. TECHNICAL INDICATORS")
print("-" * 80)
stocks_with_indicators = cursor.execute("SELECT COUNT(DISTINCT symbol) FROM technical_indicators").fetchone()[0]
print(f"Stocks with calculated indicators: {stocks_with_indicators}")

if stocks_with_indicators > 0:
    latest_indicator_date = cursor.execute("SELECT MAX(date) FROM technical_indicators").fetchone()[0]
    print(f"Latest indicators date: {latest_indicator_date}")

    latest_count = cursor.execute("""
        SELECT COUNT(DISTINCT symbol)
        FROM technical_indicators
        WHERE date = ?
    """, (latest_indicator_date,)).fetchone()[0]
    print(f"Stocks with latest indicators: {latest_count}")
print()

# 6. Daily reports
print("6. DAILY REPORTS")
print("-" * 80)
report_count = cursor.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0]
print(f"Total reports archived: {report_count}")

if report_count > 0:
    recent_reports = cursor.execute("""
        SELECT report_date, report_type, symbols_analyzed, signals_generated
        FROM daily_reports
        ORDER BY report_date DESC
        LIMIT 5
    """).fetchall()

    print("\nRecent reports:")
    for date, rtype, symbols, signals in recent_reports:
        print(f"  {date} | Type: {rtype} | Analyzed: {symbols} | Signals: {signals}")
print()

# 7. Database size
print("7. DATABASE SIZE")
print("-" * 80)
import os
if os.path.exists(db_path):
    size_bytes = os.path.getsize(db_path)
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_bytes / (1024 * 1024 * 1024)

    if size_gb >= 1:
        print(f"Database size: {size_gb:.2f} GB ({size_bytes:,} bytes)")
    else:
        print(f"Database size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
print()

# 8. Data freshness
print("8. DATA FRESHNESS")
print("-" * 80)
today = datetime.now().strftime('%Y-%m-%d')
print(f"Today's date: {today}")

if total_daily_records > 0:
    latest_date = cursor.execute("SELECT MAX(date) FROM price_history").fetchone()[0]
    days_old = (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(latest_date, '%Y-%m-%d')).days

    if days_old == 0:
        print(f"Daily data: UP TO DATE (last update: {latest_date})")
    elif days_old <= 3:
        print(f"Daily data: RECENT (last update: {latest_date}, {days_old} days ago)")
    else:
        print(f"Daily data: OUTDATED (last update: {latest_date}, {days_old} days ago)")
        print("  -> Run: python tools/daily_update.py")

print()
print("=" * 80)
print("SUMMARY COMPLETE")
print("=" * 80)

conn.close()
