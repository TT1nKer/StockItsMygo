"""
Test Phase 2: Fundamental Data
Test dividends, splits, and comprehensive data download
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.init_db import init_database
from db.api import StockDB


def test_phase2():
    """Test Phase 2: Fundamental Data"""

    print("="*60)
    print("Phase 2 Test: Fundamental Data")
    print("="*60)

    # Initialize database (will add new tables if not exist)
    print("\n[1/4] Re-initializing database with new tables...")
    init_database()

    db = StockDB()

    # Use stocks that are already in the database
    print("\n[1.5/4] Using stocks from database...")
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']  # These were added in Phase 1

    # Test 1: Download dividends
    print("\n[2/4] Testing dividend download...")
    for symbol in test_symbols:
        db.download_dividends(symbol)

    # Test 2: Download splits
    print("\n[3/4] Testing split download...")
    for symbol in test_symbols:
        db.download_splits(symbol)

    # Test 3: Query and display
    print("\n[4/4] Querying and displaying results...")
    for symbol in test_symbols:
        print(f"\n--- {symbol} ---")

        # Dividends
        dividends = db.get_dividends(symbol)
        if not dividends.empty:
            print(f"Dividends: {len(dividends)} records")
            print(dividends.head())
        else:
            print("No dividend data")

        # Splits
        splits = db.get_splits(symbol)
        if not splits.empty:
            print(f"Splits: {len(splits)} records")
            print(splits)
        else:
            print("No split data")

    # Test 4: Comprehensive download
    print("\n" + "="*60)
    print("Testing comprehensive download...")
    print("="*60)

    test_symbol = 'NVDA'
    results = db.download_all_data(test_symbol)
    print(f"\nResults for {test_symbol}:")
    print(f"  Success: {results['success']}")
    print(f"  Failed: {results['failed']}")

    # Verify data
    print(f"\nVerifying {test_symbol} data:")
    price_df = db.get_price_history(test_symbol)
    dividends_df = db.get_dividends(test_symbol)
    splits_df = db.get_splits(test_symbol)

    print(f"  Price history: {len(price_df)} records")
    print(f"  Dividends: {len(dividends_df)} records")
    print(f"  Splits: {len(splits_df)} records")

    print("\n" + "="*60)
    print("Phase 2 Test Completed!")
    print("="*60)

    print("\nDatabase now supports:")
    print("- Price history (OHLCV)")
    print("- Dividend history")
    print("- Stock split history")
    print("- Comprehensive download (download_all_data)")


if __name__ == "__main__":
    test_phase2()
