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
        raise ValueError(f'AKShare empty for {symbol} (adjust={adjust!r})')
    df = df.rename(columns=_AKSHARE_COL_MAP)[
        ['date', 'open', 'high', 'low', 'close', 'volume']
    ].copy()
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df


def _baostock_fetch(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Fetch daily raw OHLCV from Baostock. Returns same shape as _akshare_fetch."""
    with _suppress_stdout():
        bs.login()
    try:
        rs = bs.query_history_k_data_plus(
            to_baostock(symbol),
            'date,open,high,low,close,volume',
            start_date=start,
            end_date=end,
            frequency='d',
            adjustflag='3',  # 3 = 不复权 raw
        )
        if rs.error_code != '0':
            raise RuntimeError(f'Baostock error {rs.error_code}: {rs.error_msg}')
        df = rs.get_data()
        if len(df) == 0:
            raise ValueError(f'Baostock empty for {symbol}')
        for col in ('open', 'high', 'low', 'close'):
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').astype('Int64')
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df[['date', 'open', 'high', 'low', 'close', 'volume']]
    finally:
        with _suppress_stdout():
            bs.logout()


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
    """Insert minimal stock row if missing. No-op if symbol already present."""
    canonical = normalize_symbol(symbol)
    exchange = 'SSE' if canonical.startswith('sh') else 'SZSE'
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO stocks (symbol, security_name, exchange, country, is_active, first_added)
            VALUES (%s, %s, %s, %s, 1, CURRENT_DATE)
            ON CONFLICT (symbol) DO NOTHING
            """,
            (canonical, name, exchange, 'CN'),
        )
    conn.commit()


def write_price_history(df: pd.DataFrame, conn) -> int:
    """
    Bulk-upsert price_history rows. Returns number of rows written.
    DataFrame must have columns: symbol, date, open, high, low, close, volume, adj_factor.
    """
    from psycopg2.extras import execute_values
    if df.empty:
        return 0
    # Convert numpy scalars to Python natives — psycopg2 can't adapt numpy.int64.
    rows = [
        (str(r.symbol), r.date,
         float(r.open), float(r.high), float(r.low), float(r.close),
         int(r.volume), float(r.adj_factor))
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
