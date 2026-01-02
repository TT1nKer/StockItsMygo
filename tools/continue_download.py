#!/usr/bin/env python3
"""
Continue downloading stocks that don't have price data yet
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import config
from db.api import StockDB
import time

def continue_download():
    """Continue downloading remaining stocks"""

    # Use PostgreSQL
    print("Switching to PostgreSQL backend...")
    config.switch_to_postgresql()

    db = StockDB()

    print("="*70)
    print("CONTINUING NASDAQ STOCK DOWNLOAD TO POSTGRESQL")
    print("="*70)

    # Get all stocks
    all_stocks = db.get_stock_list()
    print(f"\nTotal stocks in database: {len(all_stocks)}")

    # Get stocks that already have data
    status = db.get_update_status(data_type='price_history')
    symbols_with_data = set(status['symbol'].unique())

    # Find stocks without data
    stocks_to_download = [s for s in all_stocks if s not in symbols_with_data]

    print(f"Stocks with data: {len(symbols_with_data)}")
    print(f"Stocks to download: {len(stocks_to_download)}")

    if len(stocks_to_download) == 0:
        print("\n✓ All stocks already have data!")
        return

    # Download in batches of 200
    batch_size = 200
    total_batches = (len(stocks_to_download) + batch_size - 1) // batch_size

    print(f"\nBatch size: {batch_size}")
    print(f"Total batches: {total_batches}")
    print(f"Workers per batch: 5 (to avoid rate limiting)")

    overall_success = 0
    overall_failed = 0

    start_time = time.time()

    for i in range(0, len(stocks_to_download), batch_size):
        batch_num = (i // batch_size) + 1
        batch = stocks_to_download[i:i+batch_size]

        print(f"\n{'='*70}")
        print(f"BATCH {batch_num}/{total_batches}")
        print(f"Stocks {i+1} to {min(i+batch_size, len(stocks_to_download))}")
        print(f"{'='*70}")

        # Download batch
        results = db.batch_download_prices(batch, period='max', workers=5)

        overall_success += results['success']
        overall_failed += results['failed']

        # Progress summary
        elapsed = time.time() - start_time
        elapsed_min = elapsed / 60
        stocks_done = i + len(batch)
        stocks_remaining = len(stocks_to_download) - stocks_done

        if stocks_done > 0:
            rate = stocks_done / elapsed_min  # stocks per minute
            eta_min = stocks_remaining / rate if rate > 0 else 0

            print(f"\n--- Overall Progress ---")
            print(f"Completed: {stocks_done}/{len(stocks_to_download)} stocks ({stocks_done/len(stocks_to_download)*100:.1f}%)")
            print(f"Success: {overall_success} | Failed: {overall_failed}")
            print(f"Elapsed time: {elapsed_min:.1f} minutes")
            print(f"Rate: {rate:.1f} stocks/minute")
            print(f"ETA: {eta_min:.1f} minutes remaining")

        # Brief pause between batches
        if batch_num < total_batches:
            print("\nPausing 2 seconds before next batch...")
            time.sleep(2)

    # Final summary
    total_time = time.time() - start_time
    total_time_min = total_time / 60

    print("\n" + "="*70)
    print("DOWNLOAD COMPLETED!")
    print("="*70)
    print(f"\nTotal stocks processed: {len(stocks_to_download)}")
    print(f"Successful: {overall_success} ({overall_success/len(stocks_to_download)*100:.1f}%)")
    print(f"Failed: {overall_failed} ({overall_failed/len(stocks_to_download)*100:.1f}%)")
    print(f"Total time: {total_time_min:.1f} minutes ({total_time/3600:.2f} hours)")
    print(f"Average rate: {len(stocks_to_download)/total_time_min:.1f} stocks/minute")

    # Check PostgreSQL database size
    import psycopg2
    try:
        conn = psycopg2.connect('host=localhost port=5432 dbname=stock_db user=stock_user password=stock_password')
        cursor = conn.cursor()
        cursor.execute("SELECT pg_size_pretty(pg_database_size('stock_db'))")
        db_size = cursor.fetchone()[0]
        print(f"\nPostgreSQL database size: {db_size}")
        conn.close()
    except Exception as e:
        print(f"\nCould not check database size: {e}")

    # Show final status
    print("\n" + "="*70)
    print("Checking final status...")
    print("="*70)

    status = db.get_update_status()
    symbols_with_data = status[status['data_type']=='price_history']['symbol'].unique()

    all_stocks = db.get_stock_list()
    print(f"\nStocks with price data: {len(symbols_with_data)}/{len(all_stocks)}")
    print(f"Coverage: {len(symbols_with_data)/len(all_stocks)*100:.1f}%")

    if overall_failed > 0:
        print(f"\nNote: {overall_failed} stocks failed to download.")
        print("You can retry failed downloads later if needed.")

if __name__ == "__main__":
    continue_download()
