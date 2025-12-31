"""
Quick Start Example
Demonstrates basic usage of the stock database
"""

from db.api import StockDB
from script.judgeV0 import judge

def main():
    print("=" * 70)
    print("Stock Database Quick Start")
    print("=" * 70)
    print()

    # Initialize database
    db = StockDB()
    print("Database initialized")
    print()

    # Example 1: Get stock list
    print("1. Getting stock list")
    print("-" * 70)
    all_stocks = db.get_stock_list()
    print(f"Total stocks: {len(all_stocks)}")
    print(f"First 10 stocks: {all_stocks[:10]}")
    print()

    # Example 2: Query price history
    print("2. Query price history")
    print("-" * 70)
    symbol = 'AAPL'
    df = db.get_price_history(symbol, start_date='2024-01-01')
    print(f"{symbol} price data (latest 5 days):")
    print(df[['date', 'open', 'high', 'low', 'close', 'volume']].tail())
    print()

    # Example 3: Get latest price
    print("3. Get latest price")
    print("-" * 70)
    latest = db.get_latest_price(symbol)
    print(f"{symbol} latest price:")
    print(f"  Date: {latest['date']}")
    print(f"  Close: ${latest['close']:.2f}")
    print(f"  Volume: {latest['volume']:,}")
    print()

    # Example 4: Use judge function
    print("4. Use judge function")
    print("-" * 70)
    result = judge(symbol, use_db=True)
    print(f"{symbol} judgment: {result}")
    print()

    # Example 5: Batch query
    print("5. Batch query")
    print("-" * 70)
    stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    print(f"{'Symbol':<10} {'Latest Price':<15} {'Change %':<10}")
    print("-" * 40)

    for sym in stocks:
        df = db.get_price_history(sym, start_date='2024-01-01')
        if len(df) > 0:
            latest_price = df.iloc[-1]['close']
            start_price = df.iloc[0]['close']
            change_pct = ((latest_price - start_price) / start_price) * 100
            print(f"{sym:<10} ${latest_price:<14.2f} {change_pct:>8.2f}%")
    print()

    # Example 6: Query dividends
    print("6. Query dividends")
    print("-" * 70)
    dividends = db.get_dividends('AAPL')
    if len(dividends) > 0:
        print(f"AAPL dividends (latest 5):")
        print(dividends.tail())
    else:
        print("No dividend data available")
    print()

    print("=" * 70)
    print("Quick start completed!")
    print()
    print("Next steps:")
    print("  1. Read docs/README.md for detailed documentation")
    print("  2. Check tools/ folder for utility scripts")
    print("  3. Write your own analysis strategies")
    print("=" * 70)

if __name__ == '__main__':
    main()
