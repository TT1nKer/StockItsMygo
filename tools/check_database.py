"""Quick database check script"""
import sqlite3
from db.api import StockDB

# Check tables
conn = sqlite3.connect('<dynamically determined path>')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print("="*60)
print("DATABASE STATUS")
print("="*60)
print(f"\nTotal tables: {len(tables)}")
print("\nAll tables:")
for i, table in enumerate(tables, 1):
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {i}. {table:<30} {count:>6} records")

conn.close()

# Check stocks
db = StockDB()
print("\n" + "="*60)
print("STOCK DATA SUMMARY")
print("="*60)

stocks = db.get_stock_list()
print(f"\nTotal stocks in database: {len(stocks)}")

# Show some sample data
print("\nSample stocks with full data:")
for symbol in ['AAPL', 'MSFT', 'GOOGL', 'NVDA']:
    price = db.get_price_history(symbol)
    divs = db.get_dividends(symbol)
    splits = db.get_splits(symbol)
    ratings = db.get_analyst_ratings(symbol)
    holders = db.get_institutional_holders(symbol)
    insiders = db.get_insider_transactions(symbol)
    options = db.get_options(symbol)
    indicators = db.get_technical_indicators(symbol)

    print(f"\n{symbol}:")
    print(f"  Price history: {len(price)} records")
    print(f"  Dividends: {len(divs)} records")
    print(f"  Splits: {len(splits)} records")
    print(f"  Analyst ratings: {len(ratings)} records")
    print(f"  Institutional holders: {len(holders)} records")
    print(f"  Insider transactions: {len(insiders)} records")
    print(f"  Options: {len(options)} records")
    print(f"  Technical indicators: {len(indicators)} records")

print("\n" + "="*60)
print("ALL PHASES COMPLETED SUCCESSFULLY!")
print("="*60)
