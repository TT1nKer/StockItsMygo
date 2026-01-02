"""
Retry failed stock downloads using single-threaded approach to avoid database locking.
"""

import sys
import time
from db.api import StockDB

def retry_failed_downloads():
    """Retry downloading stocks that failed or were not attempted."""
    db = StockDB()

    print("=" * 70)
    print("RETRYING FAILED STOCK DOWNLOADS")
    print("=" * 70)
    print()

    # Get all stocks
    all_stocks = db.get_stock_list()
    print(f"Total stocks in database: {len(all_stocks)}")

    # Get stocks that already have price data
    status = db.get_update_status()
    successful_symbols = set(
        status[status['data_type'] == 'price_history']['symbol'].unique()
    )

    # Find stocks that need downloading
    pending_stocks = [s for s in all_stocks if s not in successful_symbols]
    print(f"Stocks already downloaded: {len(successful_symbols)}")
    print(f"Stocks pending download: {len(pending_stocks)}")
    print()

    if not pending_stocks:
        print("All stocks already downloaded!")
        return

    print("Starting single-threaded download (no database locking issues)...")
    print()

    success_count = 0
    fail_count = 0
    start_time = time.time()

    for i, symbol in enumerate(pending_stocks, 1):
        try:
            # Download one stock at a time (returns True/False)
            result = db.download_price_history(symbol, period='max')

            if result:
                success_count += 1
            else:
                fail_count += 1

        except Exception as e:
            fail_count += 1
            print(f"ERROR {i}/{len(pending_stocks)} - {symbol}: {str(e)}")

        # Progress update every 50 stocks
        if i % 50 == 0:
            elapsed = time.time() - start_time
            rate = i / (elapsed / 60)  # stocks per minute
            remaining = len(pending_stocks) - i
            eta = remaining / rate if rate > 0 else 0

            print()
            print(f"--- Progress Update ---")
            print(f"Completed: {i}/{len(pending_stocks)} ({i/len(pending_stocks)*100:.1f}%)")
            print(f"Success: {success_count} | Failed: {fail_count}")
            print(f"Rate: {rate:.1f} stocks/minute")
            print(f"ETA: {eta:.1f} minutes")
            print()

    elapsed = time.time() - start_time

    print()
    print("=" * 70)
    print("DOWNLOAD COMPLETED")
    print("=" * 70)
    print(f"Total processed: {len(pending_stocks)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Success rate: {success_count/len(pending_stocks)*100:.1f}%")
    print(f"Total time: {elapsed/60:.1f} minutes")
    print()

    # Final database stats
    import os
    db_size = os.path.getsize('<dynamically determined path>') / (1024 * 1024)
    print(f"Final database size: {db_size:.1f} MB")
    print()

if __name__ == '__main__':
    retry_failed_downloads()
