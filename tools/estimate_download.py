"""Estimate download requirements for all stocks"""
from db.api import StockDB

db = StockDB()

# Get stock counts by category
all_stocks = db.get_stock_list()
q_stocks = db.get_stock_list(market_category='Q')
g_stocks = db.get_stock_list(market_category='G')
s_stocks = db.get_stock_list(market_category='S')

print("="*70)
print("DOWNLOAD ESTIMATION FOR ALL NASDAQ STOCKS")
print("="*70)

print("\n[Stock Count by Category]")
print(f"  Q-Category (NASDAQ Global Select): {len(q_stocks)} stocks")
print(f"  G-Category (NASDAQ Global Market): {len(g_stocks)} stocks")
print(f"  S-Category (NASDAQ Capital Market): {len(s_stocks)} stocks")
print(f"  Total: {len(all_stocks)} stocks")

print("\n[Data Granularity - Time Intervals]")
print("  Daily price data (OHLCV):")
print("    - Period: 'max' (all available history)")
print("    - Interval: 1 day (default)")
print("    - Typical history: 10-30 years depending on stock age")
print("    - NVDA example: 6775 days = ~27 years of data")
print("\n  Alternative intervals available (if needed later):")
print("    - 1 minute: Only last 7 days")
print("    - 5 minutes: Only last 60 days")
print("    - 1 hour: Only last 730 days")
print("    - 1 day: Full history (recommended)")
print("    - 1 week: Full history")
print("    - 1 month: Full history")

print("\n[Storage Estimation]")

# Based on actual data
# NVDA: 6775 price records
# AAPL: 250 price records (1 year)
# Estimate: average stock has ~5000 days of history (20 years)
avg_price_records = 5000
price_record_size = 80  # bytes per record (rough estimate)

# Price history only
price_storage_mb = (len(all_stocks) * avg_price_records * price_record_size) / (1024 * 1024)

# With all data types
# Based on actual sample: AAPL has 246 indicators, 89 dividends, 5 splits, 388 options
avg_indicators = 5000  # same as price history
avg_dividends = 50
avg_splits = 5
avg_options = 400  # 3 expiration dates
avg_analyst = 10
avg_holders = 10
avg_insiders = 50

total_records = avg_price_records + avg_indicators + avg_dividends + avg_splits + avg_options + avg_analyst + avg_holders + avg_insiders
total_storage_mb = (len(all_stocks) * total_records * price_record_size) / (1024 * 1024)

print(f"  Price history only:")
print(f"    - Estimated records: {len(all_stocks):,} stocks × {avg_price_records:,} days = {len(all_stocks) * avg_price_records:,} records")
print(f"    - Estimated size: ~{price_storage_mb:.0f} MB (~{price_storage_mb/1024:.1f} GB)")
print(f"\n  With all data types (price + indicators + dividends + options + analyst data):")
print(f"    - Estimated records: {len(all_stocks):,} stocks × {total_records:,} avg records = {len(all_stocks) * total_records:,} records")
print(f"    - Estimated size: ~{total_storage_mb:.0f} MB (~{total_storage_mb/1024:.1f} GB)")
print(f"\n  Conservative estimate with overhead: 2-3 GB")

print("\n[Download Time Estimation]")
print("  Factors:")
print("    - yfinance API speed: ~1-2 seconds per stock")
print("    - Threading workers: 5 (recommended to avoid rate limiting)")
print("    - Network speed: variable")
print("\n  Time estimates:")

stocks_per_worker_sec = 1.5  # average seconds per stock
total_time_sec = (len(all_stocks) * stocks_per_worker_sec) / 5  # 5 workers
total_time_min = total_time_sec / 60
total_time_hour = total_time_min / 60

print(f"    - With 5 workers: ~{total_time_min:.0f} minutes (~{total_time_hour:.1f} hours)")
print(f"    - With 10 workers: ~{total_time_min/2:.0f} minutes (higher risk of rate limiting)")
print(f"\n  Recommended approach:")
print(f"    - Download in batches of 100-200 stocks")
print(f"    - Use 5 workers to avoid Yahoo Finance throttling")
print(f"    - Monitor for failures and retry")

print("\n[Recommended Download Strategy]")
print("""
  1. Start with Q-category stocks (highest quality):
     stocks = db.get_stock_list(market_category='Q')
     db.batch_download_prices(stocks, period='max', workers=5)

  2. Then G-category:
     stocks = db.get_stock_list(market_category='G')
     db.batch_download_prices(stocks, period='max', workers=5)

  3. Finally S-category:
     stocks = db.get_stock_list(market_category='S')
     db.batch_download_prices(stocks, period='max', workers=5)

  4. Or download in batches:
     all_stocks = db.get_stock_list()
     for i in range(0, len(all_stocks), 100):
         batch = all_stocks[i:i+100]
         print(f"Downloading batch {i//100 + 1}/{len(all_stocks)//100 + 1}")
         db.batch_download_prices(batch, period='max', workers=5)
""")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"Total stocks to download: {len(all_stocks):,}")
print(f"Estimated storage: 2-3 GB")
print(f"Estimated time: {total_time_hour:.1f} hours (with 5 workers)")
print(f"Data granularity: Daily (1 day interval)")
print(f"History depth: Full history (typically 10-30 years per stock)")
print("="*70)
