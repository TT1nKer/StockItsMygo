"""
数据库初始化脚本 - 阶段1：核心基础
创建核心3张表：stocks, price_history, data_metadata
"""

import sqlite3
import os


def init_database(db_path=None):
    """
    初始化数据库 - 核心表

    Args:
        db_path: 数据库文件路径（默认使用config/paths.py中的路径）
    """
    if db_path is None:
        from config.paths import paths
        db_path = paths.db_path
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)

    # 启用外键约束
    conn.execute('PRAGMA foreign_keys = ON')

    # 性能优化设置
    conn.execute('PRAGMA journal_mode = WAL')  # Write-Ahead Logging
    conn.execute('PRAGMA synchronous = NORMAL')
    conn.execute('PRAGMA cache_size = 10000')
    conn.execute('PRAGMA temp_store = MEMORY')

    cursor = conn.cursor()

    # ========== 1. 股票主表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            company_name TEXT,
            security_name TEXT,
            market_category TEXT,           -- NASDAQ 分类 (Q/G/S)
            exchange TEXT,                  -- 交易所
            sector TEXT,                    -- 行业
            industry TEXT,                  -- 子行业
            country TEXT,
            is_etf INTEGER DEFAULT 0,       -- 是否ETF
            is_active INTEGER DEFAULT 1,    -- 是否活跃
            first_added DATE,
            last_updated TIMESTAMP,

            -- 基础信息快照（常用字段）
            market_cap REAL,
            pe_ratio REAL,
            forward_pe REAL,
            price_to_book REAL,
            dividend_yield REAL,
            beta REAL,
            fifty_two_week_high REAL,
            fifty_two_week_low REAL,

            -- 扩展信息（JSON）
            info_json TEXT,

            UNIQUE(symbol)
        )
    ''')

    # 索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_sector ON stocks(sector)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_market_cap ON stocks(market_cap DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_active ON stocks(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_market_category ON stocks(market_category)')

    # ========== 2. 历史价格表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            dividends REAL DEFAULT 0,
            stock_splits REAL DEFAULT 0,

            PRIMARY KEY (symbol, date),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    # 索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_symbol ON price_history(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_date ON price_history(date DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_symbol_date ON price_history(symbol, date DESC)')

    # ========== 3. 数据更新元数据表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_metadata (
            symbol TEXT NOT NULL,
            data_type TEXT NOT NULL,        -- 'price_history' / 'dividends' / 'info' 等
            last_updated TIMESTAMP,
            last_success_date DATE,         -- 最后成功下载的数据日期
            update_frequency TEXT,          -- 'daily' / 'weekly' / 'monthly'
            status TEXT,                    -- 'success' / 'failed' / 'partial'
            error_message TEXT,
            record_count INTEGER,

            PRIMARY KEY (symbol, data_type),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    # 索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_type ON data_metadata(data_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_updated ON data_metadata(last_updated)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_status ON data_metadata(status)')

    # ========== 4. 股息历史表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dividends (
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            dividend REAL NOT NULL,

            PRIMARY KEY (symbol, date),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dividends_symbol ON dividends(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dividends_date ON dividends(date DESC)')

    # ========== 5. 股票分割表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_splits (
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            split_ratio REAL NOT NULL,

            PRIMARY KEY (symbol, date),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_splits_symbol ON stock_splits(symbol)')

    # ========== 6. 财务报表表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financials (
            symbol TEXT NOT NULL,
            report_date DATE NOT NULL,
            period_type TEXT NOT NULL,
            fiscal_year INTEGER,
            fiscal_quarter INTEGER,

            -- Income statement
            total_revenue REAL,
            gross_profit REAL,
            operating_income REAL,
            net_income REAL,
            ebitda REAL,
            eps REAL,

            -- Balance sheet
            total_assets REAL,
            total_liabilities REAL,
            stockholders_equity REAL,
            cash_and_equivalents REAL,
            total_debt REAL,

            -- Cash flow
            operating_cash_flow REAL,
            investing_cash_flow REAL,
            financing_cash_flow REAL,
            free_cash_flow REAL,

            -- Full data (JSON)
            income_stmt_json TEXT,
            balance_sheet_json TEXT,
            cash_flow_json TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (symbol, report_date, period_type),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_financials_symbol ON financials(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_financials_date ON financials(report_date DESC)')

    # ========== 7. 收益数据表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS earnings (
            symbol TEXT NOT NULL,
            earnings_date DATE NOT NULL,
            eps_estimate REAL,
            eps_actual REAL,
            revenue_estimate REAL,
            revenue_actual REAL,
            surprise_percent REAL,

            PRIMARY KEY (symbol, earnings_date),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_earnings_symbol ON earnings(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings(earnings_date DESC)')

    # ========== 8. 分析师评级表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyst_ratings (
            symbol TEXT NOT NULL,
            rating_date DATE NOT NULL,
            firm TEXT,
            from_rating TEXT,
            to_rating TEXT,
            action TEXT,

            PRIMARY KEY (symbol, rating_date, firm),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyst_ratings_symbol ON analyst_ratings(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyst_ratings_date ON analyst_ratings(rating_date DESC)')

    # ========== 9. 价格目标表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_targets (
            symbol TEXT NOT NULL,
            updated_date DATE NOT NULL,
            current_price REAL,
            target_high REAL,
            target_low REAL,
            target_mean REAL,
            target_median REAL,
            num_analysts INTEGER,

            PRIMARY KEY (symbol, updated_date),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_targets_symbol ON price_targets(symbol)')

    # ========== 10. 机构持股表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS institutional_holders (
            symbol TEXT NOT NULL,
            holder_name TEXT NOT NULL,
            date_reported DATE NOT NULL,
            shares REAL,
            value REAL,
            percent_out REAL,

            PRIMARY KEY (symbol, holder_name, date_reported),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_institutional_holders_symbol ON institutional_holders(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_institutional_holders_date ON institutional_holders(date_reported DESC)')

    # ========== 11. 内部人交易表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS insider_transactions (
            symbol TEXT NOT NULL,
            transaction_date DATE NOT NULL,
            insider_name TEXT NOT NULL,
            position TEXT,
            transaction_type TEXT,
            shares REAL,
            value REAL,

            PRIMARY KEY (symbol, transaction_date, insider_name),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_insider_transactions_symbol ON insider_transactions(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_insider_transactions_date ON insider_transactions(transaction_date DESC)')

    # ========== 12. 期权链表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS options_chain (
            symbol TEXT NOT NULL,
            expiration_date DATE NOT NULL,
            strike REAL NOT NULL,
            option_type TEXT NOT NULL,           -- 'call' or 'put'
            last_price REAL,
            bid REAL,
            ask REAL,
            volume INTEGER,
            open_interest INTEGER,
            implied_volatility REAL,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (symbol, expiration_date, strike, option_type),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_symbol ON options_chain(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_expiration ON options_chain(expiration_date)')

    # ========== 13. 技术指标表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS technical_indicators (
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            ma5 REAL,
            ma10 REAL,
            ma20 REAL,
            ma60 REAL,
            ma120 REAL,
            ma250 REAL,
            rsi REAL,
            macd REAL,
            macd_signal REAL,
            macd_histogram REAL,
            bollinger_upper REAL,
            bollinger_middle REAL,
            bollinger_lower REAL,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (symbol, date),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_technical_indicators_symbol ON technical_indicators(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_technical_indicators_date ON technical_indicators(date DESC)')

    # ========== 14. 分钟级数据表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intraday_price (
            symbol TEXT NOT NULL,
            datetime TIMESTAMP NOT NULL,
            interval TEXT NOT NULL,            -- '1m', '5m', '15m', '30m', '1h'
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (symbol, datetime, interval),
            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_intraday_symbol ON intraday_price(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_intraday_datetime ON intraday_price(datetime DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_intraday_interval ON intraday_price(interval)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_intraday_symbol_datetime ON intraday_price(symbol, datetime DESC)')

    # ========== 15. 观察列表表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            priority INTEGER DEFAULT 2,        -- 1=高, 2=中, 3=低
            source TEXT,                       -- 'manual', 'momentum_auto', 'custom'
            notes TEXT,
            target_price REAL,
            stop_loss REAL,
            is_active INTEGER DEFAULT 1,       -- 1=激活, 0=停用

            FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE,
            UNIQUE(symbol, is_active)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlist(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_priority ON watchlist(priority)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_source ON watchlist(source)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_added_date ON watchlist(added_date DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_active ON watchlist(is_active)')

    # ========== 16. 每日报告存档表 ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date DATE NOT NULL,
            report_type TEXT NOT NULL,         -- 'momentum', 'watchlist', 'comprehensive'
            symbols_analyzed INTEGER,
            signals_generated INTEGER,
            report_content TEXT,               -- Full report in Markdown format
            execution_time_seconds REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(report_date, report_type)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_reports(report_date DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_reports_type ON daily_reports(report_type)')

    conn.commit()
    conn.close()

    print(f"Database initialized: {db_path}")
    print("  Core tables: stocks, price_history, data_metadata")
    print("  Fundamental tables: dividends, stock_splits, financials, earnings")
    print("  Analyst tables: analyst_ratings, price_targets, institutional_holders, insider_transactions")
    print("  Options/Indicators tables: options_chain, technical_indicators")
    print("  Intraday/Watchlist tables: intraday_price, watchlist, daily_reports")
    print("  Total tables: 16")
    print("  Total indexes: 38")


if __name__ == "__main__":
    init_database()