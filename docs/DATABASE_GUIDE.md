# 📊 数据库使用指南 / Database Usage Guide

> **简介**: 本指南介绍如何使用 StockItsMygo 的股票数据库（PostgreSQL + TimescaleDB）
>
> **Introduction**: This guide covers how to use the StockItsMygo stock database (PostgreSQL + TimescaleDB)

---

## 📈 数据库概况 / Database Overview

| 项目 / Item | 数值 / Value |
|-------------|-------------|
| **股票总数 / Total Stocks** | 2,156 NASDAQ stocks |
| **数据库大小 / Database Size** | ~1.7 GB |
| **价格数据覆盖率 / Coverage** | 99.2% (2,138/2,156) |
| **历史数据范围 / Time Range** | 完整历史（10-30年）/ Full history (10-30 years) |
| **数据粒度 / Granularity** | 日线级别 / Daily intervals |
| **总价格记录 / Total Records** | 9.4M+ historical price records |

---

## 🗄️ 数据库架构 / Database Architecture

### PostgreSQL + TimescaleDB

当前系统使用 **PostgreSQL 16** + **TimescaleDB 2.24**，提供：

Current system uses **PostgreSQL 16** + **TimescaleDB 2.24**, providing:

- ✅ **时序优化** / Time-series optimization
- ✅ **高性能查询** / High-performance queries
- ✅ **并发支持** / Concurrent access support
- ✅ **自动数据压缩** / Automatic data compression

### 连接信息 / Connection Info

```python
Host: localhost
Port: 5432
Database: stock_db
User: stock_user
Password: stock_password
```

---

## 🚀 快速开始 / Quick Start

### 1. 基础设置 / Basic Setup

```python
from config.database import config
from db.api import StockDB

# 切换到 PostgreSQL / Switch to PostgreSQL
config.switch_to_postgresql()

# 初始化数据库连接 / Initialize database
db = StockDB()
```

### 2. 获取股票列表 / Get Stock List

```python
# 获取所有股票 / Get all stocks
all_stocks = db.get_stock_list()
print(f"Total stocks: {len(all_stocks)}")  # 2,156

# 按市场类别筛选 / Filter by market category
nasdaq_global = db.get_stock_list(market_category='Q')  # NASDAQ Global Select
nasdaq_capital = db.get_stock_list(market_category='G')  # NASDAQ Capital Market
```

### 3. 查询价格历史 / Query Price History

```python
# 获取完整历史 / Get full history
df = db.get_price_history('AAPL')
print(df.head())
# Columns: date, open, high, low, close, volume, dividends, stock_splits

# 指定日期范围 / Specific date range
df = db.get_price_history('AAPL',
                          start_date='2024-01-01',
                          end_date='2024-12-31')

# 获取最新价格 / Get latest price
latest = db.get_latest_price('AAPL')
print(f"Latest close: ${latest['close']:.2f}")
print(f"Latest date: {latest['date']}")
```

---

## 📊 数据查询示例 / Query Examples

### 示例 1: 查找表现最好的股票 / Find Top Performers

```python
from db.api import StockDB
import pandas as pd

db = StockDB()
all_stocks = db.get_stock_list()

results = []
for symbol in all_stocks[:50]:  # 前50只 / First 50 stocks
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

# 按表现排序 / Sort by performance
results_df = pd.DataFrame(results)
top_10 = results_df.nlargest(10, 'change%')
print(top_10)
```

### 示例 2: 计算技术指标 / Calculate Technical Indicators

```python
from db.api import StockDB
import pandas as pd

db = StockDB()
df = db.get_price_history('AAPL', start_date='2023-01-01')

# 计算移动平均线 / Calculate moving averages
df['ma20'] = df['close'].rolling(window=20).mean()
df['ma50'] = df['close'].rolling(window=50).mean()

# 计算收益率 / Calculate returns
df['returns'] = df['close'].pct_change()

# 计算波动率 / Calculate volatility (30-day rolling std)
df['volatility'] = df['returns'].rolling(window=30).std()

print(df[['date', 'close', 'ma20', 'ma50', 'returns', 'volatility']].tail())
```

### 示例 3: 寻找突破股票 / Find Breakout Stocks

```python
from db.api import StockDB

db = StockDB()
all_stocks = db.get_stock_list()

breakout_stocks = []

for symbol in all_stocks[:100]:  # 检查前100只 / Check first 100
    df = db.get_price_history(symbol, start_date='2024-11-01')
    if len(df) > 20:
        # 计算20日均线 / Calculate 20-day MA
        df['ma20'] = df['close'].rolling(window=20).mean()

        # 检查突破 / Check for breakout
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        if prev['close'] < prev['ma20'] and latest['close'] > latest['ma20']:
            breakout_stocks.append({
                'symbol': symbol,
                'price': latest['close'],
                'ma20': latest['ma20'],
                'volume': latest['volume']
            })

print(f"找到 {len(breakout_stocks)} 只突破股票 / Found {len(breakout_stocks)} breakout stocks")
for stock in breakout_stocks[:10]:
    print(f"{stock['symbol']}: ${stock['price']:.2f} (MA20: ${stock['ma20']:.2f})")
```

### 示例 4: 投资组合分析 / Portfolio Analysis

```python
from db.api import StockDB
import pandas as pd

db = StockDB()

# 定义投资组合 / Define portfolio
portfolio = {
    'AAPL': 10,   # 10 shares
    'MSFT': 15,   # 15 shares
    'GOOGL': 5,   # 5 shares
    'AMZN': 8,    # 8 shares
    'NVDA': 12    # 12 shares
}

# 计算投资组合价值 / Calculate portfolio value
start_date = '2024-01-01'
end_date = '2024-12-31'

portfolio_value = []

for symbol, shares in portfolio.items():
    df = db.get_price_history(symbol, start_date=start_date, end_date=end_date)
    df['value'] = df['close'] * shares
    df['symbol'] = symbol
    portfolio_value.append(df[['date', 'symbol', 'value']])

# 合并所有股票 / Combine all stocks
all_data = pd.concat(portfolio_value)

# 按日期计算总价值 / Calculate daily total value
daily_total = all_data.groupby('date')['value'].sum().reset_index()
daily_total.columns = ['date', 'total_value']

# 计算总收益 / Calculate total return
initial_value = daily_total.iloc[0]['total_value']
final_value = daily_total.iloc[-1]['total_value']
total_return = ((final_value - initial_value) / initial_value) * 100

print(f"初始价值 / Initial: ${initial_value:,.2f}")
print(f"最终价值 / Final: ${final_value:,.2f}")
print(f"总收益率 / Total Return: {total_return:.2f}%")
```

---

## 🔄 数据更新 / Data Updates

### 更新单只股票 / Update Single Stock

```python
from db.api import StockDB

db = StockDB()

# 更新价格历史 / Update price history
db.download_price_history('AAPL', period='max')

# 强制重新下载 / Force re-download
db.download_price_history('AAPL', force_update=True)
```

### 批量更新 / Batch Update

```python
# 批量下载（并发） / Batch download (concurrent)
stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
db.batch_download_prices(stocks, workers=5)
```

### 检查更新状态 / Check Update Status

```python
# 查看需要更新的股票 / Check what needs updating
status = db.get_update_status()
print(status)

# 检查单只股票是否需要更新 / Check if stock needs update
needs_update = db.needs_update('AAPL', 'price_history', frequency='daily')
print(f"Needs update: {needs_update}")
```

---

## 🔧 数据库管理 / Database Administration

### Docker 命令 / Docker Commands

```bash
# 启动 PostgreSQL / Start PostgreSQL
docker-compose up -d

# 停止 / Stop
docker-compose down

# 查看日志 / View logs
docker-compose logs -f timescaledb

# 检查状态 / Check status
docker-compose ps

# 访问数据库 shell / Access database shell
docker exec -it strategy-z-pg psql -U stock_user -d stock_db
```

### 常用 SQL 查询 / Common SQL Queries

```sql
-- 列出所有表 / List all tables
\dt

-- 查看表结构 / Describe table
\d price_history

-- 统计股票数量 / Count stocks
SELECT COUNT(*) FROM stocks;

-- 统计价格记录 / Count price records
SELECT COUNT(*) FROM price_history;

-- 查看数据库大小 / Check database size
SELECT pg_size_pretty(pg_database_size('stock_db'));

-- 查看 TimescaleDB hypertables
SELECT * FROM timescaledb_information.hypertables;

-- 查看某只股票的最新价格 / Get latest price for a stock
SELECT * FROM price_history
WHERE symbol = 'AAPL'
ORDER BY date DESC
LIMIT 1;

-- 查看数据覆盖率 / Check data coverage
SELECT
    COUNT(DISTINCT symbol) as stocks_with_data,
    MIN(date) as earliest_date,
    MAX(date) as latest_date,
    COUNT(*) as total_records
FROM price_history;
```

---

## ⚡ 性能优化建议 / Performance Tips

### 1. 使用日期过滤 / Use Date Filters

只查询需要的日期范围，避免加载全部数据：

Query only the date range you need to avoid loading all data:

```python
# 好 / Good
df = db.get_price_history('AAPL', start_date='2024-01-01')

# 不推荐 / Not recommended (loads all historical data)
df = db.get_price_history('AAPL')
df = df[df['date'] >= '2024-01-01']
```

### 2. 批量处理 / Batch Operations

处理多只股票时使用循环：

Use loops when processing multiple stocks:

```python
for symbol in stock_list:
    df = db.get_price_history(symbol, start_date='2024-01-01')
    # Your analysis code
```

### 3. 利用索引 / Leverage Indexes

TimescaleDB 已对以下字段建立索引：

TimescaleDB has indexes on:
- `symbol` - 快速股票查找 / Fast stock lookup
- `date` - 时间范围查询优化 / Optimized time range queries

### 4. 增量更新 / Incremental Updates

数据库自动跟踪上次更新时间，只下载新数据：

Database automatically tracks last update, only downloads new data:

```python
db.download_price_history('AAPL')  # 只下载新数据 / Only new data
```

---

## 🆘 故障排除 / Troubleshooting

### PostgreSQL 连接失败 / Connection Failed

```bash
# 检查 Docker 是否运行 / Check if Docker is running
docker ps

# 查看日志 / View logs
docker-compose logs timescaledb

# 重启容器 / Restart container
docker-compose restart
```

### 切换回 SQLite / Switch Back to SQLite

如果 PostgreSQL 出现问题，可以切换到 SQLite 备份：

If PostgreSQL has issues, switch to SQLite backup:

```python
from config.database import config
config.switch_to_sqlite()
```

### 数据库锁定错误 / Database Locked Errors

PostgreSQL 支持并发，不会出现锁定错误。如果使用 SQLite：

PostgreSQL supports concurrency, no lock errors. If using SQLite:

```python
# SQLite 只支持单个写入 / SQLite only supports single writer
# 切换到 PostgreSQL 解决 / Switch to PostgreSQL to resolve
config.switch_to_postgresql()
```

---

## 📝 常见问题 / FAQ

### Q: 如何查看某只股票有多少历史数据？

**How to check how much historical data a stock has?**

```python
df = db.get_price_history('AAPL')
print(f"Records: {len(df)}")
print(f"Start: {df.iloc[0]['date']}")
print(f"End: {df.iloc[-1]['date']}")
```

### Q: 如何导出数据到 CSV？

**How to export data to CSV?**

```python
df = db.get_price_history('AAPL')
df.to_csv('AAPL_history.csv', index=False)
```

### Q: 数据库占用空间太大怎么办？

**What if database takes too much space?**

当前 1.7 GB 包含 2,156 只股票的完整历史。如需缩减：

Current 1.7 GB contains full history for 2,156 stocks. To reduce:

1. 只保留需要的股票 / Keep only needed stocks
2. 只保留最近几年的数据 / Keep only recent years
3. 使用 TimescaleDB 压缩 / Use TimescaleDB compression

### Q: 如何添加自己计算的指标？

**How to add custom calculated indicators?**

```python
# 在 Python 中计算后保存 / Calculate in Python and save
df = db.get_price_history('AAPL')
df['my_indicator'] = df['close'].rolling(window=10).mean()

# 或添加到数据库 schema / Or add to database schema
# See db/init_db_postgres.py for schema modifications
```

---

## 📚 相关文件 / Related Files

| 文件 / File | 用途 / Purpose |
|------------|---------------|
| `config/database.py` | 数据库配置 / Database configuration |
| `db/api.py` | StockDB API 接口 / StockDB API interface |
| `db/connection.py` | 数据库连接管理 / Connection management |
| `db/init_db_postgres.py` | PostgreSQL 初始化 / PostgreSQL initialization |
| `docker-compose.yml` | Docker 容器配置 / Docker container config |
| `tools/update_recent_data.py` | 数据更新工具 / Data update tool |

---

## 🎯 下一步 / Next Steps

1. ✅ 查询任何股票的历史数据 / Query historical data for any stock
2. ✅ 编写自己的量化策略 / Write your own quantitative strategies
3. ✅ 回测交易策略 / Backtest trading strategies
4. ✅ 寻找投资机会 / Find investment opportunities
5. ✅ 构建投资组合 / Build portfolios

需要帮助？查看其他文档：

Need help? Check other docs:
- [MASTER_README.md](MASTER_README.md) - 文档导航 / Documentation index
- [部署指南 / Deployment Guide](deployment/DEPLOYMENT.md)
- [常见问题 / FAQ](setup/FAQ.md)

---

*Happy Trading! 📈*
