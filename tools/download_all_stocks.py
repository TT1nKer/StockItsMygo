"""
Download all stocks price data
Downloads in batches with progress tracking
"""

import sys
sys.path.append('d:/strategy=Z')

from db.api import StockDB
import time

def download_all_stocks():
    """Download all stocks in batches"""

    db = StockDB()

    print("="*70)
    print("DOWNLOADING ALL NASDAQ STOCKS")
    print("="*70)

    # Get all stocks
    all_stocks = db.get_stock_list()
    print(f"\nTotal stocks to download: {len(all_stocks)}")

    # Download in batches of 200
    batch_size = 200
    total_batches = (len(all_stocks) + batch_size - 1) // batch_size

    print(f"Batch size: {batch_size}")
    print(f"Total batches: {total_batches}")
    print(f"Workers per batch: 5 (to avoid rate limiting)")

    overall_success = 0
    overall_failed = 0

    start_time = time.time()

    for i in range(0, len(all_stocks), batch_size):
        batch_num = (i // batch_size) + 1
        batch = all_stocks[i:i+batch_size]

        print(f"\n{'='*70}")
        print(f"BATCH {batch_num}/{total_batches}")
        print(f"Stocks {i+1} to {min(i+batch_size, len(all_stocks))}")
        print(f"{'='*70}")

        # Download batch
        results = db.batch_download_prices(batch, period='max', workers=5)

        overall_success += results['success']
        overall_failed += results['failed']

        # Progress summary
        elapsed = time.time() - start_time
        elapsed_min = elapsed / 60
        stocks_done = i + len(batch)
        stocks_remaining = len(all_stocks) - stocks_done

        if stocks_done > 0:
            rate = stocks_done / elapsed_min  # stocks per minute
            eta_min = stocks_remaining / rate if rate > 0 else 0

            print(f"\n--- Overall Progress ---")
            print(f"Completed: {stocks_done}/{len(all_stocks)} stocks ({stocks_done/len(all_stocks)*100:.1f}%)")
            print(f"Success: {overall_success} | Failed: {overall_failed}")
            print(f"Elapsed time: {elapsed_min:.1f} minutes")
            print(f"Rate: {rate:.1f} stocks/minute")
            print(f"ETA: {eta_min:.1f} minutes remaining")

        # Brief pause between batches to avoid overwhelming the API
        if batch_num < total_batches:
            print("\nPausing 2 seconds before next batch...")
            time.sleep(2)

    # Final summary
    total_time = time.time() - start_time
    total_time_min = total_time / 60

    print("\n" + "="*70)
    print("DOWNLOAD COMPLETED!")
    print("="*70)
    print(f"\nTotal stocks processed: {len(all_stocks)}")
    print(f"Successful: {overall_success} ({overall_success/len(all_stocks)*100:.1f}%)")
    print(f"Failed: {overall_failed} ({overall_failed/len(all_stocks)*100:.1f}%)")
    print(f"Total time: {total_time_min:.1f} minutes ({total_time/3600:.2f} hours)")
    print(f"Average rate: {len(all_stocks)/total_time_min:.1f} stocks/minute")

    # Check database size
    import os
    db_size = os.path.getsize('d:/strategy=Z/db/stock.db') / (1024 * 1024)
    print(f"\nDatabase size: {db_size:.1f} MB ({db_size/1024:.2f} GB)")

    # Show download status
    print("\n" + "="*70)
    print("Checking final status...")
    print("="*70)

    status = db.get_update_status()
    symbols_with_data = status[status['data_type']=='price_history']['symbol'].unique()

    print(f"\nStocks with price data: {len(symbols_with_data)}/{len(all_stocks)}")
    print(f"Coverage: {len(symbols_with_data)/len(all_stocks)*100:.1f}%")

    if overall_failed > 0:
        print(f"\nNote: {overall_failed} stocks failed to download.")
        print("You can retry failed downloads later if needed.")

if __name__ == "__main__":
    download_all_stocks()
