#!/usr/bin/env python3
"""
Backfill historical A-share daily OHLCV into stock_db_cn.

Reads the universe from `stocks` (populated by ingest.cn_data.populate_stocks),
fetches each symbol's history via ingest.cn_data.fetch_daily (AKShare → Baostock
fallback), and bulk-upserts into price_history.

Resumability: per-symbol incremental — if a symbol already has rows in
price_history, only the gap [max(date)+1 .. END] is re-fetched. Re-running
on a finished DB is fast (does nothing per symbol that's up to date).

Usage:
    STOCK_DB_TYPE=postgresql STOCK_PG_PORT=5433 STOCK_PG_DATABASE=stock_db_cn \\
        python tools/cn_backfill.py [--start 2021-05-16] [--end YYYY-MM-DD] [--limit N]
"""
import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta

# Path setup so this runs from anywhere
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

from config.database import config
from ingest.cn_data import fetch_daily, write_price_history


DEFAULT_YEARS_BACK = 5


def coverage_per_symbol(conn) -> dict:
    """Returns {symbol: max_date_or_None} for every symbol in stocks."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT s.symbol, MAX(ph.date)
            FROM stocks s
            LEFT JOIN price_history ph ON s.symbol = ph.symbol
            WHERE s.country = 'CN'
            GROUP BY s.symbol
            ORDER BY s.symbol
        """)
        return dict(cur.fetchall())


def backfill(start: str, end: str, limit: int | None = None) -> None:
    conn = psycopg2.connect(config.get_connection_string())
    coverage = coverage_per_symbol(conn)
    symbols = list(coverage.keys())
    if limit is not None:
        symbols = symbols[:limit]

    print(f'[{datetime.now():%H:%M:%S}] backfill: '
          f'{len(symbols)} symbols, window {start}..{end}')
    end_date = datetime.strptime(end, '%Y-%m-%d').date()

    n_ok, n_skip, failed = 0, 0, []
    t0 = time.time()

    for i, sym in enumerate(symbols, 1):
        already = coverage.get(sym)
        # Skip if already covers (or nearly covers) the requested end —
        # avoids no-op fetches over weekends/holidays.
        if already and (end_date - already).days <= 3:
            n_skip += 1
            continue

        # Pick range: full window for new symbols, incremental for partial ones
        fetch_start = (already + timedelta(days=1)).isoformat() if already else start

        try:
            df = fetch_daily(sym, start=fetch_start, end=end)
            n = write_price_history(df, conn)
            n_ok += 1
            status = f'+{n} rows'
        except Exception as e:
            failed.append((sym, type(e).__name__, str(e)[:120]))
            status = f'FAIL: {type(e).__name__}'

        if i % 25 == 0 or i == len(symbols):
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed else 0
            eta_min = (len(symbols) - i) / rate / 60 if rate else 0
            print(f'[{datetime.now():%H:%M:%S}] [{i:4d}/{len(symbols)}] '
                  f'{sym} {status}  '
                  f'(rate {rate:.2f}/s, ETA {eta_min:.0f}min, '
                  f'ok={n_ok} skip={n_skip} fail={len(failed)})',
                  flush=True)

    elapsed = time.time() - t0
    print(f'\n[{datetime.now():%H:%M:%S}] done in {elapsed/60:.1f}min: '
          f'{n_ok} fetched, {n_skip} skipped (already current), {len(failed)} failed')

    if failed:
        print('\nFailures:')
        for sym, exc_type, msg in failed[:30]:
            print(f'  {sym}: {exc_type}: {msg}')
        if len(failed) > 30:
            print(f'  ... and {len(failed) - 30} more')

    conn.close()


def main() -> None:
    default_start = (date.today() - timedelta(days=DEFAULT_YEARS_BACK * 365)).isoformat()
    default_end = date.today().isoformat()

    p = argparse.ArgumentParser(description='Backfill A-share OHLCV')
    p.add_argument('--start', default=default_start, help=f'YYYY-MM-DD (default: {default_start})')
    p.add_argument('--end',   default=default_end,   help=f'YYYY-MM-DD (default: {default_end})')
    p.add_argument('--limit', type=int, default=None, help='Only process the first N symbols')
    args = p.parse_args()

    backfill(args.start, args.end, limit=args.limit)


if __name__ == '__main__':
    main()
