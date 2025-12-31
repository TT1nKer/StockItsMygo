"""
Test Phase 3: Analyst and Holdings Data
Test analyst ratings, price targets, institutional holders, and insider transactions
"""

import sys
sys.path.append('d:/strategy=Z')

from db.init_db import init_database
from db.api import StockDB


def test_phase3():
    """Test Phase 3: Analyst and Holdings Data"""

    print("="*60)
    print("Phase 3 Test: Analyst and Holdings Data")
    print("="*60)

    # Initialize database (will add Phase 3 tables if not exist)
    print("\n[1/5] Re-initializing database with Phase 3 tables...")
    init_database()

    db = StockDB()

    # Use stocks that are already in the database
    print("\n[2/5] Using stocks from database...")
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']  # These were added in Phase 1

    # Test 1: Download analyst ratings
    print("\n[3/5] Testing analyst ratings download...")
    for symbol in test_symbols:
        db.download_analyst_ratings(symbol)

    # Test 2: Download price targets
    print("\n[4/5] Testing price targets download...")
    for symbol in test_symbols:
        db.download_price_targets(symbol)

    # Test 3: Download institutional holders
    print("\n[5/5] Testing institutional holders download...")
    for symbol in test_symbols:
        db.download_institutional_holders(symbol)

    # Test 4: Download insider transactions
    print("\n[6/6] Testing insider transactions download...")
    for symbol in test_symbols:
        db.download_insider_transactions(symbol)

    # Query and display
    print("\n" + "="*60)
    print("Querying and displaying results...")
    print("="*60)

    for symbol in test_symbols:
        print(f"\n--- {symbol} ---")

        # Analyst ratings
        ratings = db.get_analyst_ratings(symbol)
        if not ratings.empty:
            print(f"Analyst Ratings: {len(ratings)} records")
            print(ratings.head())
        else:
            print("No analyst rating data")

        # Price targets
        targets = db.get_price_targets(symbol)
        if not targets.empty:
            print(f"\nPrice Targets: {len(targets)} records")
            print(targets)
        else:
            print("\nNo price target data")

        # Institutional holders
        holders = db.get_institutional_holders(symbol)
        if not holders.empty:
            print(f"\nInstitutional Holders: {len(holders)} records")
            print(holders.head())
        else:
            print("\nNo institutional holder data")

        # Insider transactions
        insiders = db.get_insider_transactions(symbol)
        if not insiders.empty:
            print(f"\nInsider Transactions: {len(insiders)} records")
            print(insiders.head())
        else:
            print("\nNo insider transaction data")

    print("\n" + "="*60)
    print("Phase 3 Test Completed!")
    print("="*60)

    print("\nDatabase now supports:")
    print("- Price history (OHLCV)")
    print("- Dividend history")
    print("- Stock split history")
    print("- Analyst ratings")
    print("- Price targets")
    print("- Institutional holders")
    print("- Insider transactions")


if __name__ == "__main__":
    test_phase3()
