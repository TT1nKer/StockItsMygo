"""
数据库初始化脚本 - 双后端支持版本
支持 SQLite 和 PostgreSQL + TimescaleDB
"""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import config
from db.connection import db_connection


def init_database(db_path=None):
    """
    初始化数据库 - 支持双后端

    Args:
        db_path: 数据库文件路径（仅SQLite使用，PostgreSQL忽略此参数）
    """
    # 只在SQLite模式下处理路径
    if config.DB_TYPE == 'sqlite':
        if db_path is None:
            from config.paths import paths
            db_path = paths.db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = db_connection.connect()
    cursor = conn.cursor()

    # PostgreSQL特定：禁用外键约束检查（导入数据时）
    if config.DB_TYPE == 'postgresql':
        cursor.execute("SET session_replication_role = 'replica';")
    else:
        # SQLite性能优化
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.execute('PRAGMA cache_size = 10000')
        conn.execute('PRAGMA temp_store = MEMORY')

    # ========== 1. 股票主表 ==========
    if config.DB_TYPE == 'sqlite':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                company_name TEXT,
                security_name TEXT,
                market_category TEXT,
                exchange TEXT,
                sector TEXT,
                industry TEXT,
                country TEXT,
                is_etf INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                first_added DATE,
                last_updated TIMESTAMP,
                market_cap REAL,
                pe_ratio REAL,
                forward_pe REAL,
                price_to_book REAL,
                dividend_yield REAL,
                beta REAL,
                fifty_two_week_high REAL,
                fifty_two_week_low REAL,
                info_json TEXT,
                UNIQUE(symbol)
            )
        ''')
    else:  # PostgreSQL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol VARCHAR(20) PRIMARY KEY,
                company_name VARCHAR(500),
                security_name VARCHAR(500),
                market_category VARCHAR(10),
                exchange VARCHAR(50),
                sector VARCHAR(200),
                industry VARCHAR(200),
                country VARCHAR(100),
                is_etf INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                first_added DATE,
                last_updated TIMESTAMP,
                market_cap NUMERIC(20, 2),
                pe_ratio NUMERIC(10, 2),
                forward_pe NUMERIC(10, 2),
                price_to_book NUMERIC(10, 2),
                dividend_yield NUMERIC(10, 6),
                beta NUMERIC(10, 4),
                fifty_two_week_high NUMERIC(12, 4),
                fifty_two_week_low NUMERIC(12, 4),
                info_json TEXT
            )
        ''')

    cursor.execute(db_connection.create_index('idx_stocks_sector', 'stocks', ['sector']))
    cursor.execute(db_connection.create_index('idx_stocks_market_cap', 'stocks', ['market_cap']))
    cursor.execute(db_connection.create_index('idx_stocks_active', 'stocks', ['is_active']))
    cursor.execute(db_connection.create_index('idx_stocks_market_category', 'stocks', ['market_category']))

    # ========== 2. 历史价格表 (Hypertable for PostgreSQL) ==========
    if config.DB_TYPE == 'sqlite':
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
    else:  # PostgreSQL + TimescaleDB
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                symbol VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                open NUMERIC(12, 4),
                high NUMERIC(12, 4),
                low NUMERIC(12, 4),
                close NUMERIC(12, 4),
                volume BIGINT,
                dividends NUMERIC(10, 6) DEFAULT 0,
                stock_splits NUMERIC(10, 6) DEFAULT 0,
                PRIMARY KEY (symbol, date)
            )
        ''')

        # Convert to TimescaleDB Hypertable
        try:
            cursor.execute("""
                SELECT create_hypertable('price_history', 'date',
                                         chunk_time_interval => INTERVAL '1 month',
                                         if_not_exists => TRUE)
            """)
        except Exception as e:
            print(f"  Note: Hypertable creation skipped ({e})")

    cursor.execute(db_connection.create_index('idx_price_symbol', 'price_history', ['symbol']))
    cursor.execute(db_connection.create_index('idx_price_date', 'price_history', ['date']))
    cursor.execute(db_connection.create_index('idx_price_symbol_date', 'price_history', ['symbol', 'date']))

    # ========== 3-13. 其他表 (使用相同模式) ==========
    # 为简洁起见,这里展示一个通用函数来创建其他表

    _create_metadata_table(cursor)
    _create_dividends_table(cursor)
    _create_splits_table(cursor)
    _create_financials_table(cursor)
    _create_earnings_table(cursor)
    _create_analyst_ratings_table(cursor)
    _create_price_targets_table(cursor)
    _create_institutional_holders_table(cursor)
    _create_insider_transactions_table(cursor)
    _create_options_chain_table(cursor)
    _create_technical_indicators_table(cursor)
    _create_intraday_price_table(cursor)
    _create_watchlist_table(cursor)
    _create_daily_reports_table(cursor)

    # 恢复外键约束
    if config.DB_TYPE == 'postgresql':
        cursor.execute("SET session_replication_role = 'origin';")

    conn.commit()
    conn.close()

    db_location = db_path if config.DB_TYPE == 'sqlite' else f"PostgreSQL ({config.PG_HOST}:{config.PG_PORT}/{config.PG_DATABASE})"
    print(f"Database initialized: {db_location}")
    print(f"  Backend: {config.DB_TYPE.upper()}")
    print("  Core tables: stocks, price_history, data_metadata")
    print("  Fundamental tables: dividends, stock_splits, financials, earnings")
    print("  Analyst tables: analyst_ratings, price_targets, institutional_holders, insider_transactions")
    print("  Options/Indicators tables: options_chain, technical_indicators")
    print("  Intraday/Watchlist tables: intraday_price, watchlist, daily_reports")
    print("  Total tables: 16")
    print("  Total indexes: 38")

    if config.DB_TYPE == 'postgresql':
        print("  ✓ TimescaleDB Hypertable: price_history")


def _create_metadata_table(cursor):
    """创建数据更新元数据表"""
    if config.DB_TYPE == 'sqlite':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_metadata (
                symbol TEXT NOT NULL,
                data_type TEXT NOT NULL,
                last_updated TIMESTAMP,
                last_success_date DATE,
                update_frequency TEXT,
                status TEXT,
                error_message TEXT,
                record_count INTEGER,
                PRIMARY KEY (symbol, data_type),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_metadata (
                symbol VARCHAR(20) NOT NULL,
                data_type VARCHAR(50) NOT NULL,
                last_updated TIMESTAMP,
                last_success_date DATE,
                update_frequency VARCHAR(20),
                status VARCHAR(20),
                error_message TEXT,
                record_count INTEGER,
                PRIMARY KEY (symbol, data_type)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_metadata_type', 'data_metadata', ['data_type']))
    cursor.execute(db_connection.create_index('idx_metadata_updated', 'data_metadata', ['last_updated']))
    cursor.execute(db_connection.create_index('idx_metadata_status', 'data_metadata', ['status']))


def _create_dividends_table(cursor):
    """创建股息历史表"""
    if config.DB_TYPE == 'sqlite':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dividends (
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                dividend REAL NOT NULL,
                PRIMARY KEY (symbol, date),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dividends (
                symbol VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                dividend NUMERIC(10, 6) NOT NULL,
                PRIMARY KEY (symbol, date)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_dividends_symbol', 'dividends', ['symbol']))
    cursor.execute(db_connection.create_index('idx_dividends_date', 'dividends', ['date']))


def _create_splits_table(cursor):
    """创建股票分割表"""
    if config.DB_TYPE == 'sqlite':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_splits (
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                split_ratio REAL NOT NULL,
                PRIMARY KEY (symbol, date),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_splits (
                symbol VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                split_ratio NUMERIC(10, 6) NOT NULL,
                PRIMARY KEY (symbol, date)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_splits_symbol', 'stock_splits', ['symbol']))


def _create_financials_table(cursor):
    """创建财务报表表"""
    if config.DB_TYPE == 'sqlite':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financials (
                symbol TEXT NOT NULL,
                report_date DATE NOT NULL,
                period_type TEXT NOT NULL,
                fiscal_year INTEGER,
                fiscal_quarter INTEGER,
                total_revenue REAL,
                gross_profit REAL,
                operating_income REAL,
                net_income REAL,
                ebitda REAL,
                eps REAL,
                total_assets REAL,
                total_liabilities REAL,
                stockholders_equity REAL,
                cash_and_equivalents REAL,
                total_debt REAL,
                operating_cash_flow REAL,
                investing_cash_flow REAL,
                financing_cash_flow REAL,
                free_cash_flow REAL,
                income_stmt_json TEXT,
                balance_sheet_json TEXT,
                cash_flow_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, report_date, period_type),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financials (
                symbol VARCHAR(20) NOT NULL,
                report_date DATE NOT NULL,
                period_type VARCHAR(20) NOT NULL,
                fiscal_year INTEGER,
                fiscal_quarter INTEGER,
                total_revenue NUMERIC(20, 2),
                gross_profit NUMERIC(20, 2),
                operating_income NUMERIC(20, 2),
                net_income NUMERIC(20, 2),
                ebitda NUMERIC(20, 2),
                eps NUMERIC(10, 4),
                total_assets NUMERIC(20, 2),
                total_liabilities NUMERIC(20, 2),
                stockholders_equity NUMERIC(20, 2),
                cash_and_equivalents NUMERIC(20, 2),
                total_debt NUMERIC(20, 2),
                operating_cash_flow NUMERIC(20, 2),
                investing_cash_flow NUMERIC(20, 2),
                financing_cash_flow NUMERIC(20, 2),
                free_cash_flow NUMERIC(20, 2),
                income_stmt_json TEXT,
                balance_sheet_json TEXT,
                cash_flow_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, report_date, period_type)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_financials_symbol', 'financials', ['symbol']))
    cursor.execute(db_connection.create_index('idx_financials_date', 'financials', ['report_date']))


def _create_earnings_table(cursor):
    """创建收益数据表"""
    if config.DB_TYPE == 'sqlite':
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
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS earnings (
                symbol VARCHAR(20) NOT NULL,
                earnings_date DATE NOT NULL,
                eps_estimate NUMERIC(10, 4),
                eps_actual NUMERIC(10, 4),
                revenue_estimate NUMERIC(20, 2),
                revenue_actual NUMERIC(20, 2),
                surprise_percent NUMERIC(10, 2),
                PRIMARY KEY (symbol, earnings_date)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_earnings_symbol', 'earnings', ['symbol']))
    cursor.execute(db_connection.create_index('idx_earnings_date', 'earnings', ['earnings_date']))


def _create_analyst_ratings_table(cursor):
    """创建分析师评级表"""
    if config.DB_TYPE == 'sqlite':
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
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analyst_ratings (
                symbol VARCHAR(20) NOT NULL,
                rating_date DATE NOT NULL,
                firm VARCHAR(200),
                from_rating VARCHAR(50),
                to_rating VARCHAR(50),
                action VARCHAR(50),
                PRIMARY KEY (symbol, rating_date, firm)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_analyst_ratings_symbol', 'analyst_ratings', ['symbol']))
    cursor.execute(db_connection.create_index('idx_analyst_ratings_date', 'analyst_ratings', ['rating_date']))


def _create_price_targets_table(cursor):
    """创建价格目标表"""
    if config.DB_TYPE == 'sqlite':
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
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_targets (
                symbol VARCHAR(20) NOT NULL,
                updated_date DATE NOT NULL,
                current_price NUMERIC(12, 4),
                target_high NUMERIC(12, 4),
                target_low NUMERIC(12, 4),
                target_mean NUMERIC(12, 4),
                target_median NUMERIC(12, 4),
                num_analysts INTEGER,
                PRIMARY KEY (symbol, updated_date)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_price_targets_symbol', 'price_targets', ['symbol']))


def _create_institutional_holders_table(cursor):
    """创建机构持股表"""
    if config.DB_TYPE == 'sqlite':
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
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS institutional_holders (
                symbol VARCHAR(20) NOT NULL,
                holder_name VARCHAR(200) NOT NULL,
                date_reported DATE NOT NULL,
                shares NUMERIC(20, 2),
                value NUMERIC(20, 2),
                percent_out NUMERIC(10, 4),
                PRIMARY KEY (symbol, holder_name, date_reported)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_institutional_holders_symbol', 'institutional_holders', ['symbol']))
    cursor.execute(db_connection.create_index('idx_institutional_holders_date', 'institutional_holders', ['date_reported']))


def _create_insider_transactions_table(cursor):
    """创建内部人交易表"""
    if config.DB_TYPE == 'sqlite':
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
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insider_transactions (
                symbol VARCHAR(20) NOT NULL,
                transaction_date DATE NOT NULL,
                insider_name VARCHAR(200) NOT NULL,
                position VARCHAR(100),
                transaction_type VARCHAR(50),
                shares NUMERIC(20, 2),
                value NUMERIC(20, 2),
                PRIMARY KEY (symbol, transaction_date, insider_name)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_insider_transactions_symbol', 'insider_transactions', ['symbol']))
    cursor.execute(db_connection.create_index('idx_insider_transactions_date', 'insider_transactions', ['transaction_date']))


def _create_options_chain_table(cursor):
    """创建期权链表"""
    if config.DB_TYPE == 'sqlite':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options_chain (
                symbol TEXT NOT NULL,
                expiration_date DATE NOT NULL,
                strike REAL NOT NULL,
                option_type TEXT NOT NULL,
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
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options_chain (
                symbol VARCHAR(20) NOT NULL,
                expiration_date DATE NOT NULL,
                strike NUMERIC(12, 4) NOT NULL,
                option_type VARCHAR(10) NOT NULL,
                last_price NUMERIC(12, 4),
                bid NUMERIC(12, 4),
                ask NUMERIC(12, 4),
                volume INTEGER,
                open_interest INTEGER,
                implied_volatility NUMERIC(10, 6),
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, expiration_date, strike, option_type)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_options_symbol', 'options_chain', ['symbol']))
    cursor.execute(db_connection.create_index('idx_options_expiration', 'options_chain', ['expiration_date']))


def _create_technical_indicators_table(cursor):
    """创建技术指标表"""
    if config.DB_TYPE == 'sqlite':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS technical_indicators (
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                ma5 REAL, ma10 REAL, ma20 REAL, ma60 REAL, ma120 REAL, ma250 REAL,
                rsi REAL,
                macd REAL, macd_signal REAL, macd_histogram REAL,
                bollinger_upper REAL, bollinger_middle REAL, bollinger_lower REAL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS technical_indicators (
                symbol VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                ma5 NUMERIC(12, 4), ma10 NUMERIC(12, 4), ma20 NUMERIC(12, 4),
                ma60 NUMERIC(12, 4), ma120 NUMERIC(12, 4), ma250 NUMERIC(12, 4),
                rsi NUMERIC(10, 4),
                macd NUMERIC(12, 6), macd_signal NUMERIC(12, 6), macd_histogram NUMERIC(12, 6),
                bollinger_upper NUMERIC(12, 4), bollinger_middle NUMERIC(12, 4), bollinger_lower NUMERIC(12, 4),
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_technical_indicators_symbol', 'technical_indicators', ['symbol']))
    cursor.execute(db_connection.create_index('idx_technical_indicators_date', 'technical_indicators', ['date']))


def _create_intraday_price_table(cursor):
    """创建分钟级数据表 (Hypertable for PostgreSQL)"""
    if config.DB_TYPE == 'sqlite':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intraday_price (
                symbol TEXT NOT NULL,
                datetime TIMESTAMP NOT NULL,
                interval TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL,
                volume INTEGER,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, datetime, interval),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intraday_price (
                symbol VARCHAR(20) NOT NULL,
                datetime TIMESTAMP NOT NULL,
                interval VARCHAR(10) NOT NULL,
                open NUMERIC(12, 4), high NUMERIC(12, 4), low NUMERIC(12, 4), close NUMERIC(12, 4),
                volume BIGINT,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, datetime, interval)
            )
        ''')

        # Convert to TimescaleDB Hypertable with compression
        try:
            cursor.execute("""
                SELECT create_hypertable('intraday_price', 'datetime',
                                         chunk_time_interval => INTERVAL '1 day',
                                         if_not_exists => TRUE)
            """)
            cursor.execute("""
                ALTER TABLE intraday_price SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'symbol'
                )
            """)
        except Exception as e:
            print(f"  Note: Intraday hypertable setup skipped ({e})")

    cursor.execute(db_connection.create_index('idx_intraday_symbol', 'intraday_price', ['symbol']))
    cursor.execute(db_connection.create_index('idx_intraday_datetime', 'intraday_price', ['datetime']))
    cursor.execute(db_connection.create_index('idx_intraday_interval', 'intraday_price', ['interval']))


def _create_watchlist_table(cursor):
    """创建观察列表表"""
    autoincrement = db_connection.get_autoincrement_type()

    if config.DB_TYPE == 'sqlite':
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS watchlist (
                id {autoincrement},
                symbol TEXT NOT NULL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                priority INTEGER DEFAULT 2,
                source TEXT,
                notes TEXT,
                target_price REAL,
                stop_loss REAL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE,
                UNIQUE(symbol, is_active)
            )
        ''')
    else:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS watchlist (
                id {autoincrement},
                symbol VARCHAR(20) NOT NULL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                priority INTEGER DEFAULT 2,
                source VARCHAR(50),
                notes TEXT,
                target_price NUMERIC(12, 4),
                stop_loss NUMERIC(12, 4),
                is_active INTEGER DEFAULT 1,
                UNIQUE(symbol, is_active)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_watchlist_symbol', 'watchlist', ['symbol']))
    cursor.execute(db_connection.create_index('idx_watchlist_priority', 'watchlist', ['priority']))
    cursor.execute(db_connection.create_index('idx_watchlist_source', 'watchlist', ['source']))
    cursor.execute(db_connection.create_index('idx_watchlist_added_date', 'watchlist', ['added_date']))
    cursor.execute(db_connection.create_index('idx_watchlist_active', 'watchlist', ['is_active']))


def _create_daily_reports_table(cursor):
    """创建每日报告存档表"""
    autoincrement = db_connection.get_autoincrement_type()

    if config.DB_TYPE == 'sqlite':
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS daily_reports (
                id {autoincrement},
                report_date DATE NOT NULL,
                report_type TEXT NOT NULL,
                symbols_analyzed INTEGER,
                signals_generated INTEGER,
                report_content TEXT,
                execution_time_seconds REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(report_date, report_type)
            )
        ''')
    else:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS daily_reports (
                id {autoincrement},
                report_date DATE NOT NULL,
                report_type VARCHAR(50) NOT NULL,
                symbols_analyzed INTEGER,
                signals_generated INTEGER,
                report_content TEXT,
                execution_time_seconds NUMERIC(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(report_date, report_type)
            )
        ''')

    cursor.execute(db_connection.create_index('idx_daily_reports_date', 'daily_reports', ['report_date']))
    cursor.execute(db_connection.create_index('idx_daily_reports_type', 'daily_reports', ['report_type']))


if __name__ == "__main__":
    init_database()
