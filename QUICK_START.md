# Quick Start Guide - Dual-Backend System

## Using the System

### Switch Between Databases

```python
from config.database import config
from db.api import StockDB

# Use PostgreSQL (recommended)
config.switch_to_postgresql()
db = StockDB()

# Or use SQLite (backup)
config.switch_to_sqlite()
db = StockDB()
```

### Download Stock Data

```python
from config.database import config
from db.api import StockDB

config.switch_to_postgresql()
db = StockDB()

# Download price history for a stock
db.download_price_history('AAPL', period='1y')

# Download all data types
db.download_all_data('AAPL')
```

### Query Data

```python
# Get stock list
stocks = db.get_stock_list()
print(f"Total stocks: {len(stocks)}")

# Get stock information
info = db.get_stock_info('AAPL')
print(info['company_name'])

# Get price history
history = db.get_price_history('AAPL', start_date='2024-01-01')
print(f"Records: {len(history)}")

# Get latest price
price = db.get_latest_price('AAPL')
print(f"Latest price: ${price:.2f}")
```

### Bulk Download (Multiple Stocks)

```python
from config.database import config
from db.api import StockDB

config.switch_to_postgresql()
db = StockDB()

# Get list of stocks to download
stocks = db.get_stock_list()[:100]  # First 100 stocks

# Download price history for each
for symbol in stocks:
    try:
        print(f"Downloading {symbol}...")
        db.download_price_history(symbol, period='2y')
    except Exception as e:
        print(f"Failed {symbol}: {e}")
```

## Docker Commands

```bash
# Start PostgreSQL
docker-compose up -d

# Stop PostgreSQL
docker-compose down

# View logs
docker-compose logs -f timescaledb

# Check container status
docker-compose ps

# Access PostgreSQL shell
docker exec -it strategy-z-pg psql -U stock_user -d stock_db

# Restart container
docker-compose restart
```

## Database Administration

### PostgreSQL Queries

```bash
# Connect to database
docker exec -it strategy-z-pg psql -U stock_user -d stock_db

# In psql:
\dt                    # List tables
\d stocks              # Describe stocks table
SELECT COUNT(*) FROM stocks;
SELECT COUNT(*) FROM price_history;

# Check hypertables
SELECT * FROM timescaledb_information.hypertables;

# Check database size
SELECT pg_size_pretty(pg_database_size('stock_db'));
```

### SQLite Queries

```bash
sqlite3 db/stock.db

# In sqlite:
.tables                # List tables
.schema stocks         # Show table structure
SELECT COUNT(*) FROM stocks;
SELECT COUNT(*) FROM price_history;
```

## Troubleshooting

### PostgreSQL Container Not Starting

```bash
# Check Docker is running
docker ps

# View container logs
docker-compose logs timescaledb

# Remove and recreate
docker-compose down
rm -rf pg-data
docker-compose up -d
```

### Connection Errors

```python
# Test connection
from config.database import config
from db.connection import db_connection

config.switch_to_postgresql()
conn = db_connection.connect()
print("✓ Connected successfully")
conn.close()
```

### Switch Back to SQLite

```python
# Edit config/database.py line 8
DB_TYPE = 'sqlite'  # Change from 'postgresql'

# Or use runtime switching
from config.database import config
config.switch_to_sqlite()
```

## Performance Tips

### For Large Downloads
- Use PostgreSQL (no "database locked" errors)
- Download during off-peak hours
- Use batch size of 1000 (default)

### For Queries
- Both backends perform similarly for small datasets
- PostgreSQL better for concurrent access
- SQLite better for single-user, simple queries

### For Storage
- PostgreSQL: Data in `pg-data/` directory
- SQLite: Data in `db/stock.db` file

## Next Steps

1. **Import Full Dataset**:
   ```bash
   source venv/bin/activate
   python tools/download_all_stocks.py
   ```

2. **Verify Data**:
   ```bash
   python check_data_summary.py
   ```

3. **Run Analysis**:
   ```bash
   python daily_observation.py
   ```

4. **Switch to PostgreSQL Permanently**:
   ```python
   # Edit config/database.py
   DB_TYPE = 'postgresql'
   ```

## Important Notes

- Pandas shows SQLAlchemy warnings - these are **informational only**
- Keep both databases for first week as backup
- SQLite file remains available even when using PostgreSQL
- Docker container auto-starts on system boot
