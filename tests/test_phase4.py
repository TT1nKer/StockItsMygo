"""
Test Phase 4: Options and Technical Indicators
Test options chain data and technical indicator calculations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.init_db import init_database
from db.api import StockDB


def test_phase4():
    """Test Phase 4: Options and Technical Indicators"""

    print("="*60)
    print("Phase 4 Test: Options and Technical Indicators")
    print("="*60)

    # Initialize database (will add Phase 4 tables if not exist)
    print("\n[1/4] Re-initializing database with Phase 4 tables...")
    init_database()

    db = StockDB()

    # Use stocks that are already in the database
    print("\n[2/4] Using stocks from database...")
    test_symbols = ['AAPL', 'MSFT']  # Test with 2 stocks to avoid too much data

    # Test 1: Download options data
    print("\n[3/4] Testing options chain download...")
    for symbol in test_symbols:
        db.download_options(symbol)

    # Test 2: Calculate technical indicators
    print("\n[4/4] Testing technical indicators calculation...")
    for symbol in test_symbols:
        db.calculate_technical_indicators(symbol)

    # Query and display
    print("\n" + "="*60)
    print("Querying and displaying results...")
    print("="*60)

    for symbol in test_symbols:
        print(f"\n--- {symbol} ---")

        # Options
        options = db.get_options(symbol)
        if not options.empty:
            print(f"Options: {len(options)} records")
            print(f"Expiration dates: {options['expiration_date'].unique()}")
            print("\nSample options data:")
            print(options.head(10))
        else:
            print("No options data")

        # Technical Indicators
        indicators = db.get_technical_indicators(symbol)
        if not indicators.empty:
            print(f"\nTechnical Indicators: {len(indicators)} records")
            print("\nLatest indicators:")
            print(indicators.tail(5))
        else:
            print("\nNo technical indicator data")

    # Test comprehensive data with technical indicators
    print("\n" + "="*60)
    print("Testing comprehensive download with technical indicators...")
    print("="*60)

    test_symbol = 'NVDA'
    print(f"\nDownloading all data for {test_symbol}...")

    # Download price history first (if not already downloaded)
    db.download_price_history(test_symbol, period='max')

    # Calculate technical indicators
    db.calculate_technical_indicators(test_symbol)

    # Verify data
    print(f"\nVerifying {test_symbol} data:")
    price_df = db.get_price_history(test_symbol)
    indicators_df = db.get_technical_indicators(test_symbol)

    print(f"  Price history: {len(price_df)} records")
    print(f"  Technical indicators: {len(indicators_df)} records")

    if not indicators_df.empty:
        print(f"\nLatest technical indicators for {test_symbol}:")
        latest = indicators_df.iloc[-1]
        print(f"  Date: {latest['date']}")
        print(f"  MA5: {latest['ma5']:.2f}")
        print(f"  MA20: {latest['ma20']:.2f}")
        print(f"  MA60: {latest['ma60']:.2f}")
        print(f"  RSI: {latest['rsi']:.2f}")
        print(f"  MACD: {latest['macd']:.2f}")

    print("\n" + "="*60)
    print("Phase 4 Test Completed!")
    print("="*60)

    print("\nDatabase now supports:")
    print("- Price history (OHLCV)")
    print("- Dividend history")
    print("- Stock split history")
    print("- Analyst ratings")
    print("- Price targets")
    print("- Institutional holders")
    print("- Insider transactions")
    print("- Options chain data")
    print("- Technical indicators (MA, RSI, MACD, Bollinger Bands)")


if __name__ == "__main__":
    test_phase4()
