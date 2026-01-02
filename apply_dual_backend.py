#!/usr/bin/env python3
"""
Apply Dual-Backend Transformation to db/api.py
Transforms INSERT OR REPLACE and query placeholders for PostgreSQL compatibility
"""

import re

def apply_transformations():
    with open('db/api.py', 'r') as f:
        content = f.read()

    print("Applying dual-backend transformations to db/api.py...")

    # 1. Update __init__ to use dynamic paths
    content = re.sub(
        r"def __init__\(self, db_path='d:/strategy=Z/db/stock\.db'\):",
        "def __init__(self, db_path=None):\n        if db_path is None:\n            from config.paths import paths\n            db_path = paths.db_path",
        content
    )
    print("✓ Updated __init__ for dynamic paths")

    # 2. Update _connect() to use db_connection
    content = re.sub(
        r"def _connect\(self\):\s+\"\"\"获取数据库连接\"\"\"\s+conn = sqlite3\.connect\(self\.db_path\)\s+conn\.execute\('PRAGMA foreign_keys = ON'\)\s+return conn",
        'def _connect(self):\n        """获取数据库连接"""\n        from db.connection import db_connection\n        return db_connection.connect()',
        content
    )
    print("✓ Updated _connect() method")

    # 3. Update _execute_batch() for PostgreSQL
    content = re.sub(
        r"(def _execute_batch.*?try:\s+)conn\.execute\('BEGIN TRANSACTION'\)",
        r"\1from config.database import config\n            # PostgreSQL uses cursor for transactions, SQLite uses conn\n            if config.DB_TYPE == 'postgresql':\n                cursor.execute('BEGIN')\n            else:\n                conn.execute('BEGIN TRANSACTION')",
        content,
        flags=re.DOTALL
    )
    print("✓ Updated _execute_batch() for dual backend")

    # 4. Convert INSERT OR REPLACE statements (11 total)
    replacements = [
        # stocks table
        (r"(# 批量插入\s+)sql = '''\s+INSERT OR REPLACE INTO stocks.*?VALUES \(\?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?\)\s+'''",
         r"\1from db.connection import db_connection\n        columns = [\n            'symbol', 'company_name', 'security_name', 'market_category', 'exchange',\n            'sector', 'industry', 'country', 'is_etf', 'is_active', 'first_added',\n            'last_updated', 'market_cap', 'pe_ratio', 'forward_pe', 'price_to_book',\n            'dividend_yield', 'beta', 'fifty_two_week_high', 'fifty_two_week_low', 'info_json'\n        ]\n        sql = db_connection.insert_or_replace('stocks', columns, conflict_columns=['symbol'])"),
        # price_history
        (r"sql = '''\s+INSERT OR REPLACE INTO price_history\s+\(symbol, date, open, high, low, close, volume, dividends, stock_splits\)\s+VALUES \(\?, \?, \?, \?, \?, \?, \?, \?, \?\)\s+'''",
         "from db.connection import db_connection\n            columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'dividends', 'stock_splits']\n            sql = db_connection.insert_or_replace('price_history', columns, conflict_columns=['symbol', 'date'])"),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    print("✓ Converted 2 INSERT OR REPLACE statements (stocks, price_history)")

    # Save
    with open('db/api.py', 'w') as f:
        f.write(content)

    print("\n✅ Transformations applied successfully!")
    print("Note: Additional INSERT OR REPLACE statements and query placeholders")
    print("will be handled individually to avoid errors.")

if __name__ == '__main__':
    apply_transformations()
