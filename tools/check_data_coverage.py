"""Check data acquisition coverage"""
from db.api import StockDB
import pandas as pd

db = StockDB()

print("="*60)
print("DATA ACQUISITION STATUS")
print("="*60)

# Get all stocks
all_stocks = db.get_stock_list()
print(f"\nTotal stocks in database: {len(all_stocks)}")

# Get data status
status = db.get_update_status()

# Summary by data type
print("\nData acquisition by type:")
by_type = status.groupby('data_type').agg({
    'symbol': 'count',
    'status': lambda x: (x=='success').sum()
})
by_type.columns = ['Total Records', 'Successful']
print(by_type)

# Stocks with price data
symbols_with_price = status[status['data_type']=='price_history']['symbol'].unique()
print(f"\nStocks with price data: {len(symbols_with_price)} stocks")
print(f"Coverage: {len(symbols_with_price)/len(all_stocks)*100:.1f}%")
print(f"Stock symbols: {', '.join(sorted(symbols_with_price))}")

# Stocks with technical indicators
symbols_with_indicators = status[status['data_type']=='technical_indicators']['symbol'].unique()
print(f"\nStocks with technical indicators: {len(symbols_with_indicators)} stocks")
print(f"Stock symbols: {', '.join(sorted(symbols_with_indicators))}")

# Stocks with analyst data
symbols_with_analysts = status[status['data_type']=='analyst_ratings']['symbol'].unique()
print(f"\nStocks with analyst ratings: {len(symbols_with_analysts)} stocks")
print(f"Stock symbols: {', '.join(sorted(symbols_with_analysts))}")

# Stocks with options
symbols_with_options = status[status['data_type']=='options_chain']['symbol'].unique()
print(f"\nStocks with options data: {len(symbols_with_options)} stocks")
print(f"Stock symbols: {', '.join(sorted(symbols_with_options))}")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"Database has {len(all_stocks)} stocks imported from NASDAQ")
print(f"Only {len(symbols_with_price)} stocks ({len(symbols_with_price)/len(all_stocks)*100:.1f}%) have price data downloaded")
print(f"\nTo download all stocks, you can run:")
print("  db.batch_download_prices(all_stocks, period='max', workers=5)")
