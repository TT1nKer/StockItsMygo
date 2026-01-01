"""
Incremental Data Update - Only update recent days

This script:
1. Checks the latest date in database
2. Downloads only missing days (not full history)
3. Much faster than full download (minutes vs hours)

Usage:
    python tools/update_recent_data.py          # Update all stocks
    python tools/update_recent_data.py --days 5 # Update last 5 days
"""

import sys
sys.path.insert(0, 'd:/strategy=Z')

from db.api import StockDB
from script.trading_calendar import TradingCalendar
from datetime import datetime, timedelta
import time
import argparse


def update_recent_data(days_back=10, batch_size=200, workers=10):
    """
    Incrementally update recent price data

    Args:
        days_back: How many days to look back (default 10)
        batch_size: Stocks per batch
        workers: Concurrent downloads
    """
    db = StockDB()

    print("=" * 80)
    print("INCREMENTAL DATA UPDATE")
    print("=" * 80)
    print()

    # Check what we need to update
    expected_date = TradingCalendar.get_expected_data_date()
    print(f"Today: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Expected data date: {expected_date.strftime('%Y-%m-%d')}")
    print()

    # Get all stocks
    all_stocks = db.get_stock_list()
    print(f"Total stocks: {len(all_stocks)}")

    # Sample check: find latest date in database
    sample_symbol = all_stocks[0]
    sample_data = db.get_price_history(sample_symbol)
    if sample_data is not None and len(sample_data) > 0:
        sample_data = sample_data.sort_values('date', ascending=False)
        latest_db_date = sample_data.iloc[0]['date']
        if isinstance(latest_db_date, str):
            latest_db_date = datetime.strptime(latest_db_date, '%Y-%m-%d').date()

        days_behind = (expected_date - latest_db_date).days
        print(f"Latest data in DB: {latest_db_date.strftime('%Y-%m-%d')}")
        print(f"Days behind: {days_behind}")
        print()

        if days_behind <= 0:
            print("✓ Data is already up-to-date!")
            print("  No update needed.")
            return

        if days_behind > days_back:
            print(f"⚠ Data is {days_behind} days behind (> {days_back} day threshold)")
            print(f"  Updating last {days_back} days...")
            print()

    # Calculate period for download
    # Use a short period to only get recent data
    period = f"{days_back}d"

    print(f"Download period: {period} (last {days_back} days)")
    print(f"Batch size: {batch_size} stocks")
    print(f"Workers: {workers}")
    print()

    # Confirm
    response = input("Start incremental update? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Update cancelled.")
        return

    print()
    print("=" * 80)
    print("STARTING UPDATE")
    print("=" * 80)
    print()

    start_time = time.time()
    overall_success = 0
    overall_failed = 0

    # Process in batches
    total_batches = (len(all_stocks) + batch_size - 1) // batch_size

    for i in range(0, len(all_stocks), batch_size):
        batch_num = (i // batch_size) + 1
        batch = all_stocks[i:i+batch_size]

        print(f"[Batch {batch_num}/{total_batches}] Updating {len(batch)} stocks...")

        # Download batch with short period (only recent days)
        results = db.batch_download_prices(
            symbols=batch,
            period=period,
            workers=workers
        )

        overall_success += results['success']
        overall_failed += results['failed']

        # Progress
        stocks_done = i + len(batch)
        pct_done = stocks_done / len(all_stocks) * 100
        print(f"  Progress: {stocks_done}/{len(all_stocks)} ({pct_done:.1f}%)")
        print(f"  Success: {results['success']}/{len(batch)}")

        if batch_num < total_batches:
            time.sleep(1)  # Brief pause between batches

    # Summary
    total_time = time.time() - start_time

    print()
    print("=" * 80)
    print("UPDATE COMPLETED")
    print("=" * 80)
    print()
    print(f"Total stocks: {len(all_stocks)}")
    print(f"Success: {overall_success} ({overall_success/len(all_stocks)*100:.1f}%)")
    print(f"Failed: {overall_failed}")
    print(f"Time: {total_time/60:.1f} minutes")
    print()

    # Verify update
    print("Verifying update...")
    sample_data = db.get_price_history(sample_symbol)
    if sample_data is not None and len(sample_data) > 0:
        sample_data = sample_data.sort_values('date', ascending=False)
        latest_db_date = sample_data.iloc[0]['date']
        if isinstance(latest_db_date, str):
            latest_db_date = datetime.strptime(latest_db_date, '%Y-%m-%d').date()

        print(f"Latest data after update: {latest_db_date.strftime('%Y-%m-%d')}")

        if latest_db_date >= expected_date:
            print("✓ Data is now up-to-date!")
        else:
            days_still_behind = (expected_date - latest_db_date).days
            print(f"⚠ Still {days_still_behind} days behind")
            print("  (This might be normal if market hasn't closed yet)")


def main():
    parser = argparse.ArgumentParser(description='Incrementally update recent stock data')
    parser.add_argument('--days', type=int, default=10,
                       help='How many days to look back (default: 10)')
    parser.add_argument('--batch', type=int, default=200,
                       help='Batch size (default: 200)')
    parser.add_argument('--workers', type=int, default=10,
                       help='Concurrent workers (default: 10)')

    args = parser.parse_args()

    update_recent_data(
        days_back=args.days,
        batch_size=args.batch,
        workers=args.workers
    )


if __name__ == '__main__':
    main()
