# Stock Database Usage Guide

## Database Summary

- **Total Stocks**: 2,156 NASDAQ stocks
- **Database Size**: 1.47 GB
- **Price History Coverage**: 100% (2,156/2,156 stocks)
- **Time Range**: Full historical data (typically 10-30 years per stock)
- **Data Granularity**: Daily intervals
- **Database Location**: `d:/strategy=Z/db/stock.db`

## Available Data Types

### 1. Price History (All 2,156 stocks)
- Daily OHLCV data (Open, High, Low, Close, Volume)
- Full historical range (max available from Yahoo Finance)
- Dividends and stock splits included

### 2. Analyst Data (3 stocks: AAPL, GOOGL, MSFT)
- Analyst ratings (upgrades/downgrades)
- Price targets (consensus data)
- Institutional holdings
- Insider transactions

### 3. Technical Indicators (3 stocks: AAPL, MSFT, NVDA)
- Moving averages (MA5, MA20, MA60)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands

### 4. Options Data (2 stocks: AAPL, MSFT)
- Options chains (calls/puts)
- Greeks (delta, gamma, theta, vega)
- Implied volatility

---

## How to Use the Database

### Basic Setup

```python
from db.api import StockDB

# Initialize database connection
db = StockDB()
```

### 1. Get Stock List

```python
# Get all stocks
all_stocks = db.get_stock_list()
print(f"Total stocks: {len(all_stocks)}")  # 2156

# Filter by market category
nasdaq_global = db.get_stock_list(market_category='Q')  # NASDAQ Global Select
nasdaq_capital = db.get_stock_list(market_category='G')  # NASDAQ Capital Market
```

### 2. Query Price History

```python
# Get full price history for a stock
df = db.get_price_history('AAPL')
print(df.head())
# Columns: date, open, high, low, close, volume, dividends, stock_splits

# Get price history for specific date range
df = db.get_price_history('AAPL',
                           start_date='2024-01-01',
                           end_date='2024-12-31')

# Get latest price
latest = db.get_latest_price('AAPL')
print(f"Latest close: {latest['close']}")
print(f"Latest date: {latest['date']}")
```

### 3. Query Dividends and Splits

```python
# Get dividend history
dividends = db.get_dividends('AAPL')
print(dividends)

# Get stock split history
splits = db.get_splits('AAPL')
print(splits)
```

### 4. Query Technical Indicators

```python
# Get technical indicators (only available for AAPL, MSFT, NVDA)
indicators = db.get_technical_indicators('AAPL')
print(indicators.head())
# Columns: date, ma5, ma20, ma60, rsi, macd, macd_signal, macd_hist,
#          bb_upper, bb_middle, bb_lower

# Get indicators for specific date range
indicators = db.get_technical_indicators('AAPL',
                                          start_date='2024-01-01',
                                          end_date='2024-12-31')
```

### 5. Query Analyst Data (AAPL, GOOGL, MSFT only)

```python
# Get analyst ratings
ratings = db.get_analyst_ratings('AAPL')
print(ratings)

# Get price targets
targets = db.get_price_targets('AAPL')
print(f"Target price: {targets['target_price'].iloc[0]}")
print(f"Number of analysts: {targets['number_of_analysts'].iloc[0]}")

# Get institutional holdings
institutions = db.get_institutional_holders('AAPL')
print(institutions)

# Get insider transactions
insider = db.get_insider_transactions('AAPL')
print(insider)
```

### 6. Query Options Data (AAPL, MSFT only)

```python
# Get all options for a stock
options = db.get_options('AAPL')
print(options)

# Get options for specific expiration date
options = db.get_options('AAPL', expiration_date='2024-12-20')
```

---

## Download New Data

### Update Price History

```python
# Update single stock
db.download_price_history('AAPL', period='max')

# Batch update (concurrent download)
stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
db.batch_download_prices(stocks, workers=5)

# Force re-download (ignore incremental update)
db.download_price_history('AAPL', force_update=True)
```

### Download All Data Types for a Stock

```python
# Download everything available for a stock
db.download_all_data('AAPL')

# This includes:
# - Price history
# - Dividends
# - Stock splits
# - Analyst ratings
# - Price targets
# - Institutional holdings
# - Insider transactions
# - Options data
# - Technical indicators
```

### Check Update Status

```python
# Check what needs updating
status = db.get_update_status()
print(status)

# Check if a stock needs update (based on frequency)
needs_update = db.needs_update('AAPL', 'price_history', frequency='daily')
print(f"Needs update: {needs_update}")
```

---

## Example: Stock Analysis

### Example 1: Find Top Performers

```python
from db.api import StockDB
import pandas as pd

db = StockDB()
all_stocks = db.get_stock_list()

results = []
for symbol in all_stocks[:50]:  # First 50 stocks
    df = db.get_price_history(symbol, start_date='2024-01-01')
    if len(df) > 0:
        start_price = df.iloc[0]['close']
        end_price = df.iloc[-1]['close']
        pct_change = ((end_price - start_price) / start_price) * 100
        results.append({
            'symbol': symbol,
            'start': start_price,
            'end': end_price,
            'change%': pct_change
        })

# Sort by performance
results_df = pd.DataFrame(results)
top_10 = results_df.nlargest(10, 'change%')
print(top_10)
```

### Example 2: Use Existing Judge Function

```python
from script.judgeV0 import judge

# Use database mode (faster, no API calls)
result = judge('AAPL', use_db=True)
print(result)  # BUY, SELL, or HOLD

# Traditional mode (live API call)
result = judge('AAPL', use_db=False)
```

### Example 3: Calculate Custom Indicators

```python
from db.api import StockDB
import pandas as pd

db = StockDB()
df = db.get_price_history('AAPL', start_date='2023-01-01')

# Calculate 20-day moving average
df['ma20'] = df['close'].rolling(window=20).mean()

# Calculate daily returns
df['returns'] = df['close'].pct_change()

# Calculate volatility (30-day rolling std)
df['volatility'] = df['returns'].rolling(window=30).std()

print(df[['date', 'close', 'ma20', 'returns', 'volatility']].tail())
```

---

## Database Statistics

```python
# Run the coverage check
import subprocess
subprocess.run(['python', 'check_data_coverage.py'])

# Or in Python
from db.api import StockDB
status = db.get_update_status()
print(status.groupby('data_type').size())
```

---

## Performance Tips

1. **Use Date Filters**: Query only the date range you need
   ```python
   df = db.get_price_history('AAPL', start_date='2024-01-01')
   ```

2. **Batch Operations**: Process multiple stocks in loops
   ```python
   for symbol in stock_list:
       df = db.get_price_history(symbol)
       # your analysis
   ```

3. **Incremental Updates**: Database automatically tracks last update date
   ```python
   db.download_price_history('AAPL')  # Only downloads new data
   ```

4. **Close Connection**: Not required (auto-managed), but you can:
   ```python
   # Connections are automatically closed after each query
   ```

---

## Data Freshness

- **Last Updated**: 2025-12-26
- **Update Frequency**: Run download scripts as needed
- **Incremental Updates**: Supported (only downloads new data)

---

## Files

- **Database**: `d:/strategy=Z/db/stock.db` (1.47 GB)
- **API**: `d:/strategy=Z/db/api.py` (StockDB class)
- **Schema**: `d:/strategy=Z/db/init_db.py` (database structure)
- **Judge**: `d:/strategy=Z/script/judgeV0.py` (stock judgment)
- **Coverage Check**: `d:/strategy=Z/check_data_coverage.py`
- **Download All**: `d:/strategy=Z/download_all_stocks.py`
- **Retry Failed**: `d:/strategy=Z/retry_failed_downloads.py`
