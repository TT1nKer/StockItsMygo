"""
数据库功能测试脚本
验证阶段1的核心功能
"""

import sys
sys.path.append('d:/strategy=Z')

from db.init_db import init_database
from db.api import StockDB
from script.judgeV0 import judge

def test_phase1():
    """Test Phase 1: Core Functionality"""

    print("="*60)
    print("Phase 1 Test: Core Functionality")
    print("="*60)

    # Step 1: Initialize database
    print("\n[1/5] Initializing database...")
    init_database()

    # Step 2: Import stock list
    print("\n[2/5] Importing stock list...")
    db = StockDB()
    count = db.import_stock_list('d:/strategy=Z/DATA/nasdaq-listed-symbols.csv')
    print(f"Imported: {count} stocks")

    # Step 3: View stock categories
    print("\n[3/5] Checking stock categories...")
    q_stocks = db.get_stock_list(market_category='Q')
    g_stocks = db.get_stock_list(market_category='G')
    s_stocks = db.get_stock_list(market_category='S')
    print(f"Q-Category: {len(q_stocks)} stocks")
    print(f"G-Category: {len(g_stocks)} stocks")
    print(f"S-Category: {len(s_stocks)} stocks")
    print(f"Total: {len(q_stocks) + len(g_stocks) + len(s_stocks)} stocks")

    # Step 4: Download test stock data
    print("\n[4/5] Downloading test stock data...")
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']

    for symbol in test_symbols:
        success = db.download_price_history(symbol, period='1y')
        if success:
            # Query data
            df = db.get_price_history(symbol)
            latest_price = db.get_latest_price(symbol)
            print(f"  {symbol}: {len(df)} records, latest price: ${latest_price:.2f}")

    # Step 5: Test judgment script
    print("\n[5/5] Testing judgment script...")
    for symbol in test_symbols:
        # Use database mode
        result = judge(symbol, use_db=True)
        if result:
            print(f"  {result['symbol']}: {result['action']} (score={result['score']}, reasons={result['reasons']})")

    print("\n"+"="*60)
    print("Phase 1 Test Completed!")
    print("="*60)

    print("\nNext steps:")
    print("1. Batch download more stocks: db.batch_download_prices(stocks, workers=5)")
    print("2. Check update status: db.get_update_status()")
    print("3. Use judgeV0.py for analysis")

if __name__ == "__main__":
    test_phase1()