"""
数据库 API - 阶段1：核心功能
提供股票数据的下载、存储和查询接口
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import json


class StockDB:
    """股票数据库 API"""

    def __init__(self, db_path='d:/strategy=Z/db/stock.db'):
        self.db_path = db_path

    # ============ Level 1: 基础操作 ============

    def _connect(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def _execute_batch(self, sql, data, batch_size=1000):
        """
        批量执行SQL

        Args:
            sql: SQL语句
            data: 数据列表
            batch_size: 每批数量
        """
        conn = self._connect()
        cursor = conn.cursor()

        try:
            conn.execute('BEGIN TRANSACTION')

            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                cursor.executemany(sql, batch)

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # ============ Level 2: 数据下载 ============

    def import_stock_list(self, csv_path, exchange='NASDAQ'):
        """
        从CSV导入股票列表（仅导入高质量股票）

        Args:
            csv_path: CSV文件路径
            exchange: 交易所名称

        Returns:
            int: 导入的股票数量
        """
        df = pd.read_csv(csv_path)

        # 过滤高质量股票
        df_filtered = df[
            (df['ETF'] == 'N') &
            (df['Financial Status'] == 'N') &
            (df['Test Issue'] == 'N') &
            (df['Security Name'].str.contains('Common Stock', na=False))
        ].copy()

        # 准备数据
        df_filtered['exchange'] = exchange
        df_filtered['is_etf'] = 0
        df_filtered['is_active'] = 1
        df_filtered['first_added'] = datetime.now().date()

        # 字段映射
        data = []
        for _, row in df_filtered.iterrows():
            data.append((
                row['Symbol'],
                row.get('Company Name', ''),
                row.get('Security Name', ''),
                row.get('Market Category', ''),
                exchange,
                None,  # sector
                None,  # industry
                None,  # country
                0,     # is_etf
                1,     # is_active
                datetime.now().date(),  # first_added
                None,  # last_updated
                None,  # market_cap
                None,  # pe_ratio
                None,  # forward_pe
                None,  # price_to_book
                None,  # dividend_yield
                None,  # beta
                None,  # fifty_two_week_high
                None,  # fifty_two_week_low
                None   # info_json
            ))

        # 批量插入
        sql = '''
            INSERT OR REPLACE INTO stocks (
                symbol, company_name, security_name, market_category, exchange,
                sector, industry, country, is_etf, is_active, first_added,
                last_updated, market_cap, pe_ratio, forward_pe, price_to_book,
                dividend_yield, beta, fifty_two_week_high, fifty_two_week_low, info_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        self._execute_batch(sql, data)

        print(f"Imported {len(data)} stocks to database")
        return len(data)

    def download_price_history(self, symbol, period='max', force_update=False):
        """
        下载股票历史价格（支持增量更新）

        Args:
            symbol: 股票代码
            period: 时间周期
            force_update: 是否强制全量更新

        Returns:
            bool: 是否成功
        """
        try:
            # 检查是否需要更新
            if not force_update:
                metadata = self._get_metadata(symbol, 'price_history')
                if metadata and metadata['last_success_date']:
                    # 计算开始日期（从最后成功日期的下一天开始）
                    last_date = datetime.strptime(metadata['last_success_date'], '%Y-%m-%d').date()
                    start_date = last_date + timedelta(days=1)

                    # 如果最后更新是今天，跳过
                    if start_date > datetime.now().date():
                        print(f"{symbol} data is up to date")
                        return True

                    # 增量下载
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(start=start_date.isoformat(), end=datetime.now().date().isoformat())

                    if df.empty:
                        print(f"{symbol} no new data")
                        return True
                else:
                    # 首次下载
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(period=period)
            else:
                # 强制全量下载
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period)

            if df.empty:
                print(f"WARNING: {symbol} no data available")
                self._update_metadata(symbol, 'price_history', status='failed',
                                     error_message='No data available')
                return False

            # 准备数据
            df.reset_index(inplace=True)
            df['symbol'] = symbol

            # 重命名列
            df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Dividends': 'dividends',
                'Stock Splits': 'stock_splits'
            }, inplace=True)

            # 转换日期格式
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 插入数据
            data = []
            for _, row in df.iterrows():
                data.append((
                    symbol,
                    row['date'],
                    float(row['open']) if pd.notna(row['open']) else None,
                    float(row['high']) if pd.notna(row['high']) else None,
                    float(row['low']) if pd.notna(row['low']) else None,
                    float(row['close']) if pd.notna(row['close']) else None,
                    int(row['volume']) if pd.notna(row['volume']) else None,
                    float(row.get('dividends', 0)) if pd.notna(row.get('dividends')) else 0,
                    float(row.get('stock_splits', 0)) if pd.notna(row.get('stock_splits')) else 0
                ))

            sql = '''
                INSERT OR REPLACE INTO price_history
                (symbol, date, open, high, low, close, volume, dividends, stock_splits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

            self._execute_batch(sql, data)

            # 更新元数据
            last_date = df['date'].max()
            self._update_metadata(
                symbol, 'price_history',
                status='success',
                last_success_date=last_date,
                record_count=len(data)
            )

            print(f"SUCCESS: {symbol} downloaded {len(data)} records (latest: {last_date})")
            return True

        except Exception as e:
            print(f"ERROR: {symbol} download failed: {e}")
            self._update_metadata(symbol, 'price_history', status='failed', error_message=str(e))
            return False

    def batch_download_prices(self, symbols, period='max', workers=5):
        """
        批量下载股票价格（并发）

        Args:
            symbols: 股票代码列表
            period: 时间周期
            workers: 并发线程数

        Returns:
            dict: {'success': int, 'failed': int, 'skipped': int}
        """
        results = {'success': 0, 'failed': 0, 'skipped': 0}

        print(f"\nBatch downloading {len(symbols)} stocks...")
        print(f"Workers: {workers}\n")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.download_price_history, sym, period): sym
                      for sym in symbols}

            for i, future in enumerate(as_completed(futures), 1):
                symbol = futures[future]
                try:
                    success = future.result()
                    if success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    print(f"ERROR: {symbol} exception: {e}")
                    results['failed'] += 1

                # 进度提示
                if i % 10 == 0:
                    print(f"Progress: {i}/{len(symbols)}")

        print(f"\nCompleted: success={results['success']}, failed={results['failed']}")
        return results

    def download_dividends(self, symbol):
        """
        Download dividend history

        Args:
            symbol: Stock symbol

        Returns:
            bool: Success status
        """
        try:
            ticker = yf.Ticker(symbol)
            dividends = ticker.dividends

            if dividends.empty:
                print(f"{symbol} no dividend data")
                return True

            # Prepare data
            data = []
            for date, dividend in dividends.items():
                data.append((
                    symbol,
                    date.date(),
                    float(dividend)
                ))

            sql = '''
                INSERT OR REPLACE INTO dividends (symbol, date, dividend)
                VALUES (?, ?, ?)
            '''

            self._execute_batch(sql, data)
            self._update_metadata(symbol, 'dividends', status='success', record_count=len(data))

            print(f"SUCCESS: {symbol} downloaded {len(data)} dividend records")
            return True

        except Exception as e:
            print(f"ERROR: {symbol} dividend download failed: {e}")
            self._update_metadata(symbol, 'dividends', status='failed', error_message=str(e))
            return False

    def download_splits(self, symbol):
        """
        Download stock split history

        Args:
            symbol: Stock symbol

        Returns:
            bool: Success status
        """
        try:
            ticker = yf.Ticker(symbol)
            splits = ticker.splits

            if splits.empty:
                print(f"{symbol} no split data")
                return True

            # Prepare data
            data = []
            for date, ratio in splits.items():
                data.append((
                    symbol,
                    date.date(),
                    float(ratio)
                ))

            sql = '''
                INSERT OR REPLACE INTO stock_splits (symbol, date, split_ratio)
                VALUES (?, ?, ?)
            '''

            self._execute_batch(sql, data)
            self._update_metadata(symbol, 'stock_splits', status='success', record_count=len(data))

            print(f"SUCCESS: {symbol} downloaded {len(data)} split records")
            return True

        except Exception as e:
            print(f"ERROR: {symbol} split download failed: {e}")
            self._update_metadata(symbol, 'stock_splits', status='failed', error_message=str(e))
            return False

    def download_all_data(self, symbol):
        """
        Download all available data for a stock

        Args:
            symbol: Stock symbol

        Returns:
            dict: Results summary
        """
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }

        print(f"\nDownloading all data for {symbol}...")

        # Price history
        if self.download_price_history(symbol, period='max'):
            results['success'].append('price_history')
        else:
            results['failed'].append('price_history')

        # Dividends
        if self.download_dividends(symbol):
            results['success'].append('dividends')
        else:
            results['failed'].append('dividends')

        # Splits
        if self.download_splits(symbol):
            results['success'].append('splits')
        else:
            results['failed'].append('splits')

        print(f"\nCompleted {symbol}: success={len(results['success'])}, failed={len(results['failed'])}")
        return results

    # ============ Phase 3: Analyst & Holdings Data ============

    def download_analyst_ratings(self, symbol):
        """
        Download analyst ratings/recommendations

        Args:
            symbol: Stock symbol

        Returns:
            bool: Success status
        """
        try:
            ticker = yf.Ticker(symbol)
            recommendations = ticker.recommendations

            if recommendations is None or recommendations.empty:
                print(f"{symbol} no analyst rating data")
                return True

            # Prepare data
            data = []
            for idx, row in recommendations.iterrows():
                data.append((
                    symbol,
                    idx.date() if hasattr(idx, 'date') else idx,
                    row.get('Firm', ''),
                    row.get('From Grade', ''),
                    row.get('To Grade', ''),
                    row.get('Action', '')
                ))

            sql = '''
                INSERT OR REPLACE INTO analyst_ratings
                (symbol, rating_date, firm, from_rating, to_rating, action)
                VALUES (?, ?, ?, ?, ?, ?)
            '''

            self._execute_batch(sql, data)
            self._update_metadata(symbol, 'analyst_ratings', status='success', record_count=len(data))

            print(f"SUCCESS: {symbol} downloaded {len(data)} analyst rating records")
            return True

        except Exception as e:
            print(f"ERROR: {symbol} analyst rating download failed: {e}")
            self._update_metadata(symbol, 'analyst_ratings', status='failed', error_message=str(e))
            return False

    def download_price_targets(self, symbol):
        """
        Download analyst price targets

        Args:
            symbol: Stock symbol

        Returns:
            bool: Success status
        """
        try:
            ticker = yf.Ticker(symbol)

            # Try to get analyst price targets
            try:
                info = ticker.info
                target_data = {
                    'current': info.get('currentPrice'),
                    'target_high': info.get('targetHighPrice'),
                    'target_low': info.get('targetLowPrice'),
                    'target_mean': info.get('targetMeanPrice'),
                    'target_median': info.get('targetMedianPrice'),
                    'num_analysts': info.get('numberOfAnalystOpinions')
                }

                if not any(target_data.values()):
                    print(f"{symbol} no price target data")
                    return True

                data = [(
                    symbol,
                    datetime.now().date(),
                    target_data['current'],
                    target_data['target_high'],
                    target_data['target_low'],
                    target_data['target_mean'],
                    target_data['target_median'],
                    target_data['num_analysts']
                )]

                sql = '''
                    INSERT OR REPLACE INTO price_targets
                    (symbol, updated_date, current_price, target_high, target_low,
                     target_mean, target_median, num_analysts)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''

                self._execute_batch(sql, data)
                self._update_metadata(symbol, 'price_targets', status='success', record_count=len(data))

                print(f"SUCCESS: {symbol} downloaded price target data")
                return True

            except Exception as inner_e:
                print(f"{symbol} no price target data available: {inner_e}")
                return True

        except Exception as e:
            print(f"ERROR: {symbol} price target download failed: {e}")
            self._update_metadata(symbol, 'price_targets', status='failed', error_message=str(e))
            return False

    def download_institutional_holders(self, symbol):
        """
        Download institutional holders data

        Args:
            symbol: Stock symbol

        Returns:
            bool: Success status
        """
        try:
            ticker = yf.Ticker(symbol)
            holders = ticker.institutional_holders

            if holders is None or holders.empty:
                print(f"{symbol} no institutional holder data")
                return True

            # Prepare data
            data = []
            for _, row in holders.iterrows():
                data.append((
                    symbol,
                    row.get('Holder', ''),
                    pd.to_datetime(row.get('Date Reported')).date() if pd.notna(row.get('Date Reported')) else None,
                    float(row.get('Shares', 0)) if pd.notna(row.get('Shares')) else None,
                    float(row.get('Value', 0)) if pd.notna(row.get('Value')) else None,
                    float(row.get('% Out', 0)) if pd.notna(row.get('% Out')) else None
                ))

            sql = '''
                INSERT OR REPLACE INTO institutional_holders
                (symbol, holder_name, date_reported, shares, value, percent_out)
                VALUES (?, ?, ?, ?, ?, ?)
            '''

            self._execute_batch(sql, data)
            self._update_metadata(symbol, 'institutional_holders', status='success', record_count=len(data))

            print(f"SUCCESS: {symbol} downloaded {len(data)} institutional holder records")
            return True

        except Exception as e:
            print(f"ERROR: {symbol} institutional holder download failed: {e}")
            self._update_metadata(symbol, 'institutional_holders', status='failed', error_message=str(e))
            return False

    def download_insider_transactions(self, symbol):
        """
        Download insider transactions data

        Args:
            symbol: Stock symbol

        Returns:
            bool: Success status
        """
        try:
            ticker = yf.Ticker(symbol)
            insiders = ticker.insider_transactions

            if insiders is None or insiders.empty:
                print(f"{symbol} no insider transaction data")
                return True

            # Prepare data
            data = []
            for _, row in insiders.iterrows():
                data.append((
                    symbol,
                    pd.to_datetime(row.get('Start Date')).date() if pd.notna(row.get('Start Date')) else None,
                    row.get('Insider', ''),
                    row.get('Position', ''),
                    row.get('Transaction', ''),
                    float(row.get('Shares', 0)) if pd.notna(row.get('Shares')) else None,
                    float(row.get('Value', 0)) if pd.notna(row.get('Value')) else None
                ))

            sql = '''
                INSERT OR REPLACE INTO insider_transactions
                (symbol, transaction_date, insider_name, position, transaction_type, shares, value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            '''

            self._execute_batch(sql, data)
            self._update_metadata(symbol, 'insider_transactions', status='success', record_count=len(data))

            print(f"SUCCESS: {symbol} downloaded {len(data)} insider transaction records")
            return True

        except Exception as e:
            print(f"ERROR: {symbol} insider transaction download failed: {e}")
            self._update_metadata(symbol, 'insider_transactions', status='failed', error_message=str(e))
            return False

    # ============ Phase 4: Options & Technical Indicators ============

    def download_options(self, symbol, expiration_date=None):
        """
        Download options chain data

        Args:
            symbol: Stock symbol
            expiration_date: Specific expiration date (optional, downloads all if None)

        Returns:
            bool: Success status
        """
        try:
            ticker = yf.Ticker(symbol)

            # Get available expiration dates
            expirations = ticker.options

            if not expirations:
                print(f"{symbol} no options data available")
                return True

            # If specific date provided, use it; otherwise get first available
            if expiration_date:
                if expiration_date not in expirations:
                    print(f"{symbol} no options for expiration date {expiration_date}")
                    return False
                expirations_to_download = [expiration_date]
            else:
                # Download first 3 expiration dates to avoid too much data
                expirations_to_download = expirations[:3]

            total_records = 0
            for exp_date in expirations_to_download:
                opt = ticker.option_chain(exp_date)

                # Process calls
                data = []
                for _, row in opt.calls.iterrows():
                    data.append((
                        symbol,
                        exp_date,
                        float(row.get('strike', 0)),
                        'call',
                        float(row.get('lastPrice', 0)) if pd.notna(row.get('lastPrice')) else None,
                        float(row.get('bid', 0)) if pd.notna(row.get('bid')) else None,
                        float(row.get('ask', 0)) if pd.notna(row.get('ask')) else None,
                        int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
                        int(row.get('openInterest', 0)) if pd.notna(row.get('openInterest')) else None,
                        float(row.get('impliedVolatility', 0)) if pd.notna(row.get('impliedVolatility')) else None,
                        datetime.now()
                    ))

                # Process puts
                for _, row in opt.puts.iterrows():
                    data.append((
                        symbol,
                        exp_date,
                        float(row.get('strike', 0)),
                        'put',
                        float(row.get('lastPrice', 0)) if pd.notna(row.get('lastPrice')) else None,
                        float(row.get('bid', 0)) if pd.notna(row.get('bid')) else None,
                        float(row.get('ask', 0)) if pd.notna(row.get('ask')) else None,
                        int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
                        int(row.get('openInterest', 0)) if pd.notna(row.get('openInterest')) else None,
                        float(row.get('impliedVolatility', 0)) if pd.notna(row.get('impliedVolatility')) else None,
                        datetime.now()
                    ))

                sql = '''
                    INSERT OR REPLACE INTO options_chain
                    (symbol, expiration_date, strike, option_type, last_price, bid, ask,
                     volume, open_interest, implied_volatility, downloaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''

                self._execute_batch(sql, data)
                total_records += len(data)

            self._update_metadata(symbol, 'options_chain', status='success', record_count=total_records)
            print(f"SUCCESS: {symbol} downloaded {total_records} option records for {len(expirations_to_download)} expiration dates")
            return True

        except Exception as e:
            print(f"ERROR: {symbol} options download failed: {e}")
            self._update_metadata(symbol, 'options_chain', status='failed', error_message=str(e))
            return False

    def calculate_technical_indicators(self, symbol):
        """
        Calculate technical indicators from price history

        Args:
            symbol: Stock symbol

        Returns:
            bool: Success status
        """
        try:
            # Get price history
            df = self.get_price_history(symbol)

            if df.empty:
                print(f"{symbol} no price data for calculating indicators")
                return False

            df = df.sort_values('date')
            df['close'] = df['close'].astype(float)

            # Calculate moving averages
            df['ma5'] = df['close'].rolling(window=5).mean()
            df['ma10'] = df['close'].rolling(window=10).mean()
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma60'] = df['close'].rolling(window=60).mean()
            df['ma120'] = df['close'].rolling(window=120).mean()
            df['ma250'] = df['close'].rolling(window=250).mean()

            # Calculate RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            # Calculate MACD
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema12 - ema26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']

            # Calculate Bollinger Bands
            df['bollinger_middle'] = df['close'].rolling(window=20).mean()
            std = df['close'].rolling(window=20).std()
            df['bollinger_upper'] = df['bollinger_middle'] + (std * 2)
            df['bollinger_lower'] = df['bollinger_middle'] - (std * 2)

            # Prepare data for insertion
            data = []
            for _, row in df.iterrows():
                if pd.notna(row['ma5']):  # Only insert rows where indicators are calculated
                    data.append((
                        symbol,
                        row['date'],
                        float(row['ma5']) if pd.notna(row['ma5']) else None,
                        float(row['ma10']) if pd.notna(row['ma10']) else None,
                        float(row['ma20']) if pd.notna(row['ma20']) else None,
                        float(row['ma60']) if pd.notna(row['ma60']) else None,
                        float(row['ma120']) if pd.notna(row['ma120']) else None,
                        float(row['ma250']) if pd.notna(row['ma250']) else None,
                        float(row['rsi']) if pd.notna(row['rsi']) else None,
                        float(row['macd']) if pd.notna(row['macd']) else None,
                        float(row['macd_signal']) if pd.notna(row['macd_signal']) else None,
                        float(row['macd_histogram']) if pd.notna(row['macd_histogram']) else None,
                        float(row['bollinger_upper']) if pd.notna(row['bollinger_upper']) else None,
                        float(row['bollinger_middle']) if pd.notna(row['bollinger_middle']) else None,
                        float(row['bollinger_lower']) if pd.notna(row['bollinger_lower']) else None,
                        datetime.now()
                    ))

            if not data:
                print(f"{symbol} insufficient data for indicators")
                return False

            sql = '''
                INSERT OR REPLACE INTO technical_indicators
                (symbol, date, ma5, ma10, ma20, ma60, ma120, ma250, rsi, macd, macd_signal,
                 macd_histogram, bollinger_upper, bollinger_middle, bollinger_lower, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''

            self._execute_batch(sql, data)
            self._update_metadata(symbol, 'technical_indicators', status='success', record_count=len(data))

            print(f"SUCCESS: {symbol} calculated {len(data)} technical indicator records")
            return True

        except Exception as e:
            print(f"ERROR: {symbol} technical indicator calculation failed: {e}")
            self._update_metadata(symbol, 'technical_indicators', status='failed', error_message=str(e))
            return False

    # ============ Level 3: 数据查询 ============

    def get_stock_list(self, market_category=None, sector=None, is_active=True):
        """
        获取股票列表

        Args:
            market_category: 市场分类 ('Q', 'G', 'S')
            sector: 行业
            is_active: 是否活跃

        Returns:
            list: 股票代码列表
        """
        conn = self._connect()

        query = "SELECT symbol FROM stocks WHERE 1=1"
        params = []

        if market_category:
            query += " AND market_category = ?"
            params.append(market_category)

        if sector:
            query += " AND sector = ?"
            params.append(sector)

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)

        df = pd.read_sql(query, conn, params=params if params else None)
        conn.close()

        return df['symbol'].tolist()

    def get_price_history(self, symbol, start_date=None, end_date=None, columns=None):
        """
        查询股票历史价格

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            columns: 返回的列（默认全部）

        Returns:
            DataFrame: 历史价格数据
        """
        conn = self._connect()

        if columns:
            cols = ', '.join(columns)
        else:
            cols = '*'

        query = f"SELECT {cols} FROM price_history WHERE symbol = ?"
        params = [symbol]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date"

        df = pd.read_sql(query, conn, params=params)
        conn.close()

        return df

    def get_latest_price(self, symbol):
        """
        获取最新价格

        Args:
            symbol: 股票代码

        Returns:
            float: 最新收盘价
        """
        conn = self._connect()
        query = "SELECT close FROM price_history WHERE symbol = ? ORDER BY date DESC LIMIT 1"
        result = pd.read_sql(query, conn, params=(symbol,))
        conn.close()

        return float(result['close'].iloc[0]) if not result.empty else None

    def get_stock_info(self, symbol):
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            dict: 股票信息
        """
        conn = self._connect()
        query = "SELECT * FROM stocks WHERE symbol = ?"
        result = pd.read_sql(query, conn, params=(symbol,))
        conn.close()

        if result.empty:
            return None

        info = result.iloc[0].to_dict()

        # 解析JSON字段
        if info.get('info_json'):
            try:
                info['info_full'] = json.loads(info['info_json'])
            except:
                pass

        return info

    # ============ Level 4: 元数据管理 ============

    def _get_metadata(self, symbol, data_type):
        """获取元数据"""
        conn = self._connect()
        query = "SELECT * FROM data_metadata WHERE symbol = ? AND data_type = ?"
        result = pd.read_sql(query, conn, params=(symbol, data_type))
        conn.close()

        return result.iloc[0].to_dict() if not result.empty else None

    def _update_metadata(self, symbol, data_type, status='success',
                        last_success_date=None, error_message=None, record_count=None):
        """更新元数据"""
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO data_metadata
            (symbol, data_type, last_updated, last_success_date, status, error_message, record_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol,
            data_type,
            datetime.now(),
            last_success_date,
            status,
            error_message,
            record_count
        ))

        conn.commit()
        conn.close()

    def needs_update(self, symbol, data_type, frequency='daily'):
        """
        判断是否需要更新

        Args:
            symbol: 股票代码
            data_type: 数据类型
            frequency: 更新频率 ('daily', 'weekly', 'monthly')

        Returns:
            bool: 是否需要更新
        """
        metadata = self._get_metadata(symbol, data_type)

        if not metadata:
            return True  # 没有记录，需要下载

        if metadata['status'] == 'failed':
            return True  # 上次失败，需要重试

        last_updated = metadata.get('last_updated')
        if not last_updated:
            return True

        # 转换为datetime
        last_updated = datetime.fromisoformat(last_updated)
        now = datetime.now()

        # 根据频率判断
        if frequency == 'daily':
            return (now - last_updated).days >= 1
        elif frequency == 'weekly':
            return (now - last_updated).days >= 7
        elif frequency == 'monthly':
            return (now - last_updated).days >= 30
        else:
            return False

    def get_update_status(self, symbol=None, data_type=None):
        """
        查询更新状态

        Args:
            symbol: 股票代码（可选）
            data_type: 数据类型（可选）

        Returns:
            DataFrame: 元数据记录
        """
        conn = self._connect()

        query = "SELECT * FROM data_metadata WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if data_type:
            query += " AND data_type = ?"
            params.append(data_type)

        query += " ORDER BY last_updated DESC"

        df = pd.read_sql(query, conn, params=params if params else None)
        conn.close()

        return df

    def get_dividends(self, symbol):
        """
        Query dividend history

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame: Dividend data
        """
        conn = self._connect()
        query = "SELECT * FROM dividends WHERE symbol = ? ORDER BY date DESC"
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()

        return df

    def get_splits(self, symbol):
        """
        Query stock split history

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame: Split data
        """
        conn = self._connect()
        query = "SELECT * FROM stock_splits WHERE symbol = ? ORDER BY date DESC"
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()

        return df

    def get_analyst_ratings(self, symbol):
        """
        Query analyst ratings

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame: Analyst rating data
        """
        conn = self._connect()
        query = "SELECT * FROM analyst_ratings WHERE symbol = ? ORDER BY rating_date DESC"
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()

        return df

    def get_price_targets(self, symbol):
        """
        Query price targets

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame: Price target data
        """
        conn = self._connect()
        query = "SELECT * FROM price_targets WHERE symbol = ? ORDER BY updated_date DESC"
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()

        return df

    def get_institutional_holders(self, symbol):
        """
        Query institutional holders

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame: Institutional holder data
        """
        conn = self._connect()
        query = "SELECT * FROM institutional_holders WHERE symbol = ? ORDER BY date_reported DESC"
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()

        return df

    def get_insider_transactions(self, symbol):
        """
        Query insider transactions

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame: Insider transaction data
        """
        conn = self._connect()
        query = "SELECT * FROM insider_transactions WHERE symbol = ? ORDER BY transaction_date DESC"
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()

        return df

    def get_options(self, symbol, expiration_date=None):
        """
        Query options chain data

        Args:
            symbol: Stock symbol
            expiration_date: Specific expiration date (optional)

        Returns:
            DataFrame: Options data
        """
        conn = self._connect()

        if expiration_date:
            query = "SELECT * FROM options_chain WHERE symbol = ? AND expiration_date = ? ORDER BY strike"
            df = pd.read_sql(query, conn, params=(symbol, expiration_date))
        else:
            query = "SELECT * FROM options_chain WHERE symbol = ? ORDER BY expiration_date, strike"
            df = pd.read_sql(query, conn, params=(symbol,))

        conn.close()
        return df

    def get_technical_indicators(self, symbol, start_date=None, end_date=None):
        """
        Query technical indicators

        Args:
            symbol: Stock symbol
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            DataFrame: Technical indicator data
        """
        conn = self._connect()

        query = "SELECT * FROM technical_indicators WHERE symbol = ?"
        params = [symbol]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date"

        df = pd.read_sql(query, conn, params=params)
        conn.close()

        return df

    # ============ Level 7: 分钟级数据 (Intraday Data) ============

    def download_intraday_data(self, symbol, interval='5m', period='7d'):
        """
        下载股票分钟级数据

        Args:
            symbol: 股票代码
            interval: 时间间隔 ('1m', '5m', '15m', '30m', '1h')
            period: 时间周期 ('1d', '5d', '7d', '30d', '60d')
                    注意：1m数据最多7天，5m数据最多60天

        Returns:
            bool: 是否成功
        """
        try:
            # 下载数据
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if len(df) == 0:
                print(f"{symbol}: No intraday data available")
                return False

            # 准备数据
            df = df.reset_index()
            df['symbol'] = symbol
            df['interval'] = interval
            df['datetime'] = df['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

            # 转换列名
            df = df.rename(columns={
                'Datetime': 'datetime',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # 选择需要的列
            df = df[['symbol', 'datetime', 'interval', 'open', 'high', 'low', 'close', 'volume']]

            # 批量插入
            conn = self._connect()
            df.to_sql('intraday_price', conn, if_exists='append', index=False)
            conn.close()

            print(f"{symbol}: Downloaded {len(df)} {interval} records")
            return True

        except Exception as e:
            print(f"{symbol}: Failed to download intraday data - {str(e)}")
            return False

    def get_intraday_data(self, symbol, interval='5m', start_datetime=None, end_datetime=None):
        """
        查询分钟级数据

        Args:
            symbol: 股票代码
            interval: 时间间隔
            start_datetime: 开始时间 (YYYY-MM-DD HH:MM:SS)
            end_datetime: 结束时间 (YYYY-MM-DD HH:MM:SS)

        Returns:
            pd.DataFrame: 分钟级价格数据
        """
        query = '''
            SELECT * FROM intraday_price
            WHERE symbol = ? AND interval = ?
        '''
        params = [symbol, interval]

        if start_datetime:
            query += ' AND datetime >= ?'
            params.append(start_datetime)

        if end_datetime:
            query += ' AND datetime <= ?'
            params.append(end_datetime)

        query += ' ORDER BY datetime ASC'

        conn = self._connect()
        df = pd.read_sql(query, conn, params=params)
        conn.close()

        return df

    def cleanup_old_intraday_data(self, days_to_keep=30):
        """
        清理旧的分钟级数据 (保留最近N天)

        Args:
            days_to_keep: 保留天数

        Returns:
            int: 删除的记录数
        """
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d %H:%M:%S')

        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM intraday_price
            WHERE datetime < ?
        ''', (cutoff_date,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"Cleaned up {deleted_count} old intraday records (kept {days_to_keep} days)")
        return deleted_count

    def batch_download_intraday(self, symbols, interval='5m', period='7d', workers=3):
        """
        批量下载分钟级数据（使用3个workers避免限流）

        Args:
            symbols: 股票代码列表
            interval: 时间间隔
            period: 时间周期
            workers: 并发数（建议3个，避免API限制）

        Returns:
            dict: {'success': int, 'failed': int}
        """
        results = {'success': 0, 'failed': 0}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self.download_intraday_data, symbol, interval, period): symbol
                for symbol in symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    success = future.result()
                    if success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    print(f"{symbol}: Error - {str(e)}")
                    results['failed'] += 1

        print(f"\nBatch intraday download complete:")
        print(f"  Success: {results['success']}")
        print(f"  Failed: {results['failed']}")

        return results

    # ============ Level 8: 观察列表 (Watchlist) ============

    def add_to_watchlist(self, symbol, priority=2, source='manual', notes='', target_price=None, stop_loss=None):
        """
        添加股票到观察列表

        Args:
            symbol: 股票代码
            priority: 优先级 (1=高, 2=中, 3=低)
            source: 来源 ('manual', 'momentum_auto', 'custom')
            notes: 备注
            target_price: 目标价
            stop_loss: 止损价

        Returns:
            bool: 是否成功
        """
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # 检查是否已存在活跃记录
            cursor.execute('''
                SELECT id FROM watchlist
                WHERE symbol = ? AND is_active = 1
            ''', (symbol,))

            existing = cursor.fetchone()

            if existing:
                # 更新现有记录
                cursor.execute('''
                    UPDATE watchlist
                    SET priority = ?, source = ?, notes = ?,
                        target_price = ?, stop_loss = ?, added_date = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (priority, source, notes, target_price, stop_loss, existing[0]))
                print(f"{symbol}: Updated in watchlist")
            else:
                # 插入新记录
                cursor.execute('''
                    INSERT INTO watchlist (symbol, priority, source, notes, target_price, stop_loss)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (symbol, priority, source, notes, target_price, stop_loss))
                print(f"{symbol}: Added to watchlist")

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"{symbol}: Failed to add to watchlist - {str(e)}")
            return False

    def remove_from_watchlist(self, symbol):
        """
        从观察列表移除股票 (设置为不活跃)

        Args:
            symbol: 股票代码

        Returns:
            bool: 是否成功
        """
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE watchlist
                SET is_active = 0
                WHERE symbol = ? AND is_active = 1
            ''', (symbol,))

            if cursor.rowcount > 0:
                print(f"{symbol}: Removed from watchlist")
            else:
                print(f"{symbol}: Not found in active watchlist")

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"{symbol}: Failed to remove from watchlist - {str(e)}")
            return False

    def get_watchlist(self, priority=None, source=None):
        """
        获取观察列表

        Args:
            priority: 优先级筛选 (1/2/3)
            source: 来源筛选 ('manual', 'momentum_auto', etc.)

        Returns:
            pd.DataFrame: 观察列表
        """
        query = '''
            SELECT * FROM watchlist
            WHERE is_active = 1
        '''
        params = []

        if priority:
            query += ' AND priority = ?'
            params.append(priority)

        if source:
            query += ' AND source = ?'
            params.append(source)

        query += ' ORDER BY priority ASC, added_date DESC'

        conn = self._connect()
        df = pd.read_sql(query, conn, params=params)
        conn.close()

        return df

    def update_watchlist_prices(self, symbol, target_price=None, stop_loss=None):
        """
        更新观察列表中的目标价和止损价

        Args:
            symbol: 股票代码
            target_price: 目标价
            stop_loss: 止损价

        Returns:
            bool: 是否成功
        """
        try:
            conn = self._connect()
            cursor = conn.cursor()

            updates = []
            params = []

            if target_price is not None:
                updates.append('target_price = ?')
                params.append(target_price)

            if stop_loss is not None:
                updates.append('stop_loss = ?')
                params.append(stop_loss)

            if not updates:
                return False

            params.append(symbol)

            cursor.execute(f'''
                UPDATE watchlist
                SET {', '.join(updates)}
                WHERE symbol = ? AND is_active = 1
            ''', params)

            conn.commit()
            conn.close()

            print(f"{symbol}: Prices updated in watchlist")
            return True

        except Exception as e:
            print(f"{symbol}: Failed to update prices - {str(e)}")
            return False

    def export_watchlist(self, filepath):
        """
        导出观察列表到CSV

        Args:
            filepath: CSV文件路径

        Returns:
            bool: 是否成功
        """
        try:
            df = self.get_watchlist()
            df.to_csv(filepath, index=False)
            print(f"Watchlist exported to {filepath} ({len(df)} stocks)")
            return True
        except Exception as e:
            print(f"Failed to export watchlist - {str(e)}")
            return False

    def import_watchlist(self, filepath):
        """
        从CSV导入观察列表

        Args:
            filepath: CSV文件路径

        Returns:
            int: 导入数量
        """
        try:
            df = pd.read_csv(filepath)
            count = 0

            for _, row in df.iterrows():
                success = self.add_to_watchlist(
                    symbol=row['symbol'],
                    priority=row.get('priority', 2),
                    source=row.get('source', 'manual'),
                    notes=row.get('notes', ''),
                    target_price=row.get('target_price'),
                    stop_loss=row.get('stop_loss')
                )
                if success:
                    count += 1

            print(f"Imported {count} stocks to watchlist")
            return count

        except Exception as e:
            print(f"Failed to import watchlist - {str(e)}")
            return 0


# 使用示例
if __name__ == "__main__":
    db = StockDB()

    # 示例1: 导入股票列表
    # count = db.import_stock_list('d:/strategy=Z/DATA/nasdaq-listed-symbols.csv')

    # 示例2: 下载单只股票
    # db.download_price_history('AAPL', period='1y')

    # 示例3: 批量下载
    # stocks = db.get_stock_list(market_category='Q')[:10]
    # db.batch_download_prices(stocks, period='1y', workers=5)

    # 示例4: 查询数据
    # df = db.get_price_history('AAPL', start_date='2024-01-01')
    # print(df.head())

    print("StockDB API 已加载")