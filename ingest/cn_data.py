"""
A-share daily OHLCV ingestion.

Primary source:  AKShare (wraps EastMoney / Sina / Tencent).
Fallback source: Baostock (when EastMoney throttles; see akfamily/akshare#6100).

Canonical symbol format in our DB: 'sh600519' / 'sz000001'.
price_history stores RAW (unadjusted) prices + an adj_factor column.
Query qfq-adjusted close as `close * adj_factor`.
"""
import contextlib
import io
import re
import pandas as pd
import akshare as ak
import baostock as bs


@contextlib.contextmanager
def _suppress_stdout():
    """Swallow baostock's chatty 'login success!' / 'logout success!' prints."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        yield


# ============================================================================
# Symbol format conversion
# ============================================================================

_RAW_RE    = re.compile(r'^(\d{6})$')
_OURS_RE   = re.compile(r'^(sh|sz)(\d{6})$')
_DOTTED_RE = re.compile(r'^(sh|sz)\.(\d{6})$')
_YAHOO_RE  = re.compile(r'^(\d{6})\.(ss|sz)$')


def _infer_exchange(six_digit: str) -> str:
    """SSE (sh) for codes starting 6/9, SZSE (sz) for 0/3."""
    first = six_digit[0]
    if first in ('6', '9'):
        return 'sh'
    if first in ('0', '3'):
        return 'sz'
    raise ValueError(f'Cannot infer exchange for code {six_digit!r}')


def normalize_symbol(s: str) -> str:
    """Convert any common A-share symbol format to canonical 'sh600519'."""
    s = s.strip().lower()
    if _OURS_RE.match(s):
        return s
    if m := _DOTTED_RE.match(s):
        return f'{m.group(1)}{m.group(2)}'
    if _RAW_RE.match(s):
        return f'{_infer_exchange(s)}{s}'
    if m := _YAHOO_RE.match(s):
        code = m.group(1)
        ex = 'sh' if m.group(2) == 'ss' else 'sz'
        return f'{ex}{code}'
    raise ValueError(f'Unrecognized symbol format: {s!r}')


def to_akshare(s: str) -> str:
    """Our 'sh600519' → AKShare's '600519'."""
    return normalize_symbol(s)[2:]


def to_baostock(s: str) -> str:
    """Our 'sh600519' → Baostock's 'sh.600519'."""
    canonical = normalize_symbol(s)
    return f'{canonical[:2]}.{canonical[2:]}'


# ============================================================================
# Source-specific fetchers (lower-level, raise on empty/error)
# ============================================================================

_AKSHARE_COL_MAP = {
    '日期': 'date',
    '开盘': 'open',
    '收盘': 'close',
    '最高': 'high',
    '最低': 'low',
    '成交量': 'volume',
}


def _akshare_fetch(symbol: str, start: str, end: str, adjust: str) -> pd.DataFrame:
    """
    Fetch daily OHLCV from AKShare. adjust: '' (raw) | 'qfq' | 'hfq'.
    Returns df with columns: date, open, high, low, close, volume.
    """
    df = ak.stock_zh_a_hist(
        symbol=to_akshare(symbol),
        period='daily',
        start_date=start.replace('-', ''),
        end_date=end.replace('-', ''),
        adjust=adjust,
    )
    if df is None or len(df) == 0:
        # Legitimate empty (no trading days in range), not an error.
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df = df.rename(columns=_AKSHARE_COL_MAP)[
        ['date', 'open', 'high', 'low', 'close', 'volume']
    ].copy()
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df


class BaostockRateLimitError(RuntimeError):
    """Raised when Baostock returns a code that smells like account-level
    throttling — caller (e.g. backfill driver) should stop and surface."""


# Baostock error codes that mean "back off, you're being rate-limited"
_BS_RATE_LIMIT_CODES = {'10001003', '10001005', '10001007', '10001008'}


class BaostockSession:
    """Hold one baostock login for many queries.

    Baostock stores the session token at module level, so DON'T nest these
    or use multiple instances concurrently across processes. Multiple
    THREADS sharing one session are fine (each query opens its own socket).
    """

    def __enter__(self):
        with _suppress_stdout():
            lg = bs.login()
        if lg.error_code != '0':
            raise RuntimeError(f'baostock login failed: {lg.error_code} {lg.error_msg}')
        return self

    def __exit__(self, *args):
        with _suppress_stdout():
            bs.logout()


def _bs_query(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Query Baostock — caller must hold an active BaostockSession.
    Returns date/open/high/low/close/volume; empty df if no trading days."""
    rs = bs.query_history_k_data_plus(
        to_baostock(symbol),
        'date,open,high,low,close,volume',
        start_date=start,
        end_date=end,
        frequency='d',
        adjustflag='3',  # 3 = 不复权 raw
    )
    if rs.error_code != '0':
        if rs.error_code in _BS_RATE_LIMIT_CODES:
            raise BaostockRateLimitError(
                f'Baostock rate-limit signal {rs.error_code}: {rs.error_msg}'
            )
        raise RuntimeError(f'Baostock error {rs.error_code}: {rs.error_msg}')
    df = rs.get_data()
    if len(df) == 0:
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    for col in ('open', 'high', 'low', 'close'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').astype('Int64')
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df[['date', 'open', 'high', 'low', 'close', 'volume']]


def _baostock_fetch(symbol: str, start: str, end: str) -> pd.DataFrame:
    """One-off Baostock fetch with its own login/logout (slow)."""
    with BaostockSession():
        return _bs_query(symbol, start, end)


# ============================================================================
# Public API
# ============================================================================

def fetch_daily(
    symbol: str,
    start: str = '2020-01-01',
    end: str | None = None,
    with_adjustment: bool = False,
) -> pd.DataFrame:
    """
    Fetch daily OHLCV for one A-share symbol.

    Returns DataFrame ready to insert into price_history:
      symbol, date, open, high, low, close, volume, adj_factor

    Always RAW prices. adj_factor defaults to 1.0.
    with_adjustment=True makes a second AKShare call (qfq) to compute the
    factor as qfq_close / raw_close. Falls back silently to 1.0 on failure.

    Tries AKShare first; falls back to Baostock on error or empty result.
    """
    if end is None:
        end = pd.Timestamp.today().strftime('%Y-%m-%d')
    canonical = normalize_symbol(symbol)

    used_source: str
    ak_err: Exception | None = None
    try:
        df = _akshare_fetch(canonical, start, end, adjust='')
        used_source = 'akshare'
    except Exception as e:
        ak_err = e
        try:
            df = _baostock_fetch(canonical, start, end)
            used_source = 'baostock'
        except Exception as bs_err:
            raise RuntimeError(
                f'Both sources failed for {symbol}: '
                f'akshare={ak_err!r}, baostock={bs_err!r}'
            ) from bs_err

    if df.empty:
        # No trading days in range (e.g., incremental fetch over a weekend).
        return pd.DataFrame(columns=['symbol', 'date', 'open', 'high', 'low',
                                      'close', 'volume', 'adj_factor'])

    df['symbol'] = canonical
    df['adj_factor'] = 1.0

    if with_adjustment and used_source == 'akshare':
        try:
            qfq = _akshare_fetch(canonical, start, end, adjust='qfq')
            merged = df.merge(
                qfq[['date', 'close']].rename(columns={'close': 'close_qfq'}),
                on='date',
                how='left',
            )
            df['adj_factor'] = (merged['close_qfq'] / merged['close']).values
        except Exception:
            pass  # leave adj_factor = 1.0

    return df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_factor']]


# ============================================================================
# Database writers (idempotent)
# ============================================================================

def ensure_stock(symbol: str, conn, name: str | None = None) -> None:
    """Insert minimal stock row if missing. No-op if symbol already present.
    first_added left NULL — populate_stocks() fills it from the real listing date.
    """
    canonical = normalize_symbol(symbol)
    exchange = 'SSE' if canonical.startswith('sh') else 'SZSE'
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO stocks (symbol, security_name, exchange, country, is_active)
            VALUES (%s, %s, %s, %s, 1)
            ON CONFLICT (symbol) DO NOTHING
            """,
            (canonical, name, exchange, 'CN'),
        )
    conn.commit()


def fetch_universe() -> pd.DataFrame:
    """
    Fetch the A-share symbol universe (上交所主板 + 深交所主板/中小板/创业板).
    Excludes STAR Market (科创板) and BSE (北交所) — see project_goal_evolution
    memory for the scoping decision.

    Returns DataFrame columns: symbol, name, listing_date, exchange, market_category.
    """
    sh = ak.stock_info_sh_name_code(symbol='主板A股')
    sh_df = pd.DataFrame({
        'code': sh['证券代码'].astype(str),
        'name': sh['证券简称'].str.strip(),
        'listing_date': pd.to_datetime(sh['上市日期'], errors='coerce'),
        'exchange': 'SSE',
        'market_category': '主板',
    })

    sz = ak.stock_info_sz_name_code(symbol='A股列表')
    sz_df = pd.DataFrame({
        'code': sz['A股代码'].astype(str),
        'name': sz['A股简称'].astype(str).str.replace(r'\s+', '', regex=True),
        'listing_date': pd.to_datetime(sz['A股上市日期'], errors='coerce'),
        'exchange': 'SZSE',
        # 板块 values are typically '主板' / '中小企业板' / '创业板'
        'market_category': sz['板块'].astype(str).str.replace('中小企业板', '中小板'),
    })

    combined = pd.concat([sh_df, sz_df], ignore_index=True)
    combined['symbol'] = combined['code'].apply(normalize_symbol)
    return combined[['symbol', 'name', 'listing_date', 'exchange', 'market_category']]


def populate_stocks(conn) -> int:
    """Bulk-upsert the full A-share universe into stocks. Returns rows written."""
    from psycopg2.extras import execute_values
    df = fetch_universe()
    rows = [
        (r.symbol, r.name, r.exchange, 'CN', r.market_category,
         r.listing_date.date() if pd.notna(r.listing_date) else None)
        for r in df.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO stocks
                (symbol, security_name, exchange, country, market_category, first_added)
            VALUES %s
            ON CONFLICT (symbol) DO UPDATE SET
                security_name   = EXCLUDED.security_name,
                exchange        = EXCLUDED.exchange,
                market_category = EXCLUDED.market_category,
                -- Prefer the real listing date from the universe API; fall back
                -- to whatever was already there (typically NULL).
                first_added     = COALESCE(EXCLUDED.first_added, stocks.first_added)
            """,
            rows,
            page_size=1000,
        )
    conn.commit()
    return len(rows)


def write_price_history(df: pd.DataFrame, conn) -> int:
    """
    Bulk-upsert price_history rows. Returns number of rows written.
    DataFrame must have columns: symbol, date, open, high, low, close, volume, adj_factor.
    """
    from psycopg2.extras import execute_values
    if df.empty:
        return 0
    # Convert numpy scalars to Python natives — psycopg2 can't adapt numpy.int64.
    # NA / NaN values (typical on 停牌 days) become Python None → PG NULL.
    def _f(x):  # float-or-null
        return None if pd.isna(x) else float(x)

    def _i(x):  # int-or-null
        return None if pd.isna(x) else int(x)

    rows = [
        (str(r.symbol), r.date,
         _f(r.open), _f(r.high), _f(r.low), _f(r.close),
         _i(r.volume), _f(r.adj_factor))
        for r in df[['symbol', 'date', 'open', 'high', 'low', 'close',
                      'volume', 'adj_factor']].itertuples(index=False)
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO price_history
                (symbol, date, open, high, low, close, volume, adj_factor)
            VALUES %s
            ON CONFLICT (symbol, date) DO UPDATE SET
                open       = EXCLUDED.open,
                high       = EXCLUDED.high,
                low        = EXCLUDED.low,
                close      = EXCLUDED.close,
                volume     = EXCLUDED.volume,
                adj_factor = EXCLUDED.adj_factor
            """,
            rows,
            page_size=1000,
        )
    conn.commit()
    return len(rows)
