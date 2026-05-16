#!/usr/bin/env python3
"""
Backfill historical A-share daily OHLCV into stock_db_cn.

Concurrent via multiprocessing (baostock is NOT thread-safe — shared sockets
cause zlib decompression failures under threading. Multi-process gives each
worker its own baostock login + socket).

Each worker process:
  - logs into Baostock once at startup (BaostockSession)
  - holds its own psycopg2 connection
  - tries AKShare first, falls back to Baostock on error

Resumable: per-symbol incremental. Re-running on an up-to-date DB is fast.

Rate-limit guard: aborts on
  (a) Baostock returning a known rate-limit error code, OR
  (b) server-side push-back phrases in error messages (频率 / 请稍后 / 接收数据异常), OR
  (c) rolling failure rate > 30% over last 50 results.

— per user request 2026-05-16 "如果被限制了提醒我".

Usage:
    STOCK_DB_TYPE=postgresql STOCK_PG_PORT=5433 STOCK_PG_DATABASE=stock_db_cn \\
        python tools/cn_backfill.py [--workers 4] [--start ...] [--end ...] [--limit N]
"""
import argparse
import multiprocessing as mp
import os
import sys
import time
from collections import deque
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

from config.database import config
from ingest.cn_data import (
    BaostockSession,
    BaostockRateLimitError,
    _akshare_fetch,
    _bs_query,
    normalize_symbol,
    write_price_history,
)


DEFAULT_YEARS_BACK = 5
DEFAULT_WORKERS = 4

FAILURE_WINDOW = 50
FAILURE_RATE_ABORT = 0.30

# Phrases that mean Baostock SERVER pushed back (vs client-side protocol bug).
_SERVER_PUSHBACK_PHRASES = ('频率', '请稍后', '接收数据异常')


# ============================================================================
# Worker-process state (re-initialized once per forked worker)
# ============================================================================

_W = {'pg_conn': None, 'bs_ctx': None}


def _init_worker():
    """Runs once per worker process: log into baostock + open PG connection."""
    _W['pg_conn'] = psycopg2.connect(config.get_connection_string())
    _W['bs_ctx'] = BaostockSession()
    _W['bs_ctx'].__enter__()


def _process_one(args) -> tuple:
    """Fetch one symbol's history, write to DB.
    Returns (symbol, n_rows, status_str, fatal_bool)."""
    sym, fetch_start, end = args
    canonical = normalize_symbol(sym)
    used = None
    df = None

    try:
        try:
            df = _akshare_fetch(canonical, fetch_start, end, adjust='')
            used = 'ak'
        except Exception:
            df = _bs_query(canonical, fetch_start, end)
            used = 'bs'
    except BaostockRateLimitError as e:
        return (sym, 0, f'RATE-LIMIT: {e}', True)
    except Exception as e:
        msg = str(e)
        if any(p in msg for p in _SERVER_PUSHBACK_PHRASES):
            return (sym, 0, f'SERVER-PUSHBACK: {msg[:80]}', True)
        return (sym, 0, f'FAIL: {type(e).__name__}: {msg[:60]}', False)

    if df.empty:
        return (sym, 0, f'empty({used})', False)

    df = df.copy()
    df['symbol'] = canonical
    df['adj_factor'] = 1.0
    try:
        n = write_price_history(
            df[['symbol', 'date', 'open', 'high', 'low', 'close',
                'volume', 'adj_factor']],
            _W['pg_conn'],
        )
        return (sym, n, f'+{n}({used})', False)
    except Exception as e:
        return (sym, 0, f'WRITE-FAIL: {type(e).__name__}: {str(e)[:60]}', False)


# ============================================================================
# Main process: planning, progress, abort detection
# ============================================================================

def _coverage_per_symbol(conn) -> dict:
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


def backfill(start: str, end: str, limit: int | None, workers: int) -> int:
    conn = psycopg2.connect(config.get_connection_string())
    coverage = _coverage_per_symbol(conn)
    conn.close()

    end_date = datetime.strptime(end, '%Y-%m-%d').date()

    work_items, n_skipped = [], 0
    for sym, already in coverage.items():
        if already and (end_date - already).days <= 3:
            n_skipped += 1
            continue
        fetch_start = ((already + timedelta(days=1)).isoformat()
                       if already else start)
        work_items.append((sym, fetch_start, end))

    if limit is not None:
        work_items = work_items[:limit]

    print(f'[{datetime.now():%H:%M:%S}] backfill: '
          f'{len(work_items)} to fetch ({n_skipped} skipped), '
          f'{workers} processes, window {start}..{end}', flush=True)

    if not work_items:
        return 0

    recent = deque(maxlen=FAILURE_WINDOW)
    n_ok = n_fail = 0
    failures: list[tuple] = []
    abort_reason: str | None = None
    t0 = time.time()

    # multiprocessing pool — each worker has its own baostock login + PG conn.
    ctx = mp.get_context('fork')  # cheaper than spawn on Linux
    with ctx.Pool(processes=workers, initializer=_init_worker) as pool:
        try:
            for i, (sym, n, status, fatal) in enumerate(
                pool.imap_unordered(_process_one, work_items, chunksize=1), 1
            ):
                if 'FAIL' in status or 'RATE-LIMIT' in status or 'PUSHBACK' in status:
                    n_fail += 1
                    recent.append(1)
                    failures.append((sym, status))
                else:
                    n_ok += 1
                    recent.append(0)

                if fatal and not abort_reason:
                    abort_reason = f'{sym}: {status}'

                if (not abort_reason
                    and len(recent) >= FAILURE_WINDOW
                    and sum(recent) / len(recent) > FAILURE_RATE_ABORT):
                    abort_reason = (f'failure rate {sum(recent)}/{len(recent)} '
                                    f'exceeded {FAILURE_RATE_ABORT:.0%}')

                if i % 25 == 0 or i == len(work_items) or abort_reason:
                    elapsed = time.time() - t0
                    rate = i / elapsed if elapsed else 0
                    eta = (len(work_items) - i) / rate / 60 if rate else 0
                    print(f'[{datetime.now():%H:%M:%S}] '
                          f'[{i:4d}/{len(work_items)}] '
                          f'{sym} {status}  '
                          f'(rate {rate:.2f}/s, ETA {eta:.0f}min, '
                          f'ok={n_ok} fail={n_fail})', flush=True)

                if abort_reason:
                    pool.terminate()
                    break
        finally:
            pool.close()
            pool.join()

    elapsed = time.time() - t0
    print(f'\n[{datetime.now():%H:%M:%S}] done in {elapsed/60:.1f}min — '
          f'ok={n_ok}, fail={n_fail}, skipped={n_skipped}', flush=True)

    if abort_reason:
        print(f'\n!!! ABORTED: {abort_reason}', flush=True)
        print('!!! Re-run later; partial progress is in DB (resumable).', flush=True)

    if failures:
        print(f'\nFirst {min(30, len(failures))} failures:', flush=True)
        for sym, status in failures[:30]:
            print(f'  {sym}: {status}')
        if len(failures) > 30:
            print(f'  ... and {len(failures) - 30} more')

    return 1 if abort_reason else 0


def main() -> None:
    default_start = (date.today() - timedelta(days=DEFAULT_YEARS_BACK * 365)).isoformat()
    default_end = date.today().isoformat()

    p = argparse.ArgumentParser(description='Backfill A-share OHLCV (multi-process)')
    p.add_argument('--start',   default=default_start)
    p.add_argument('--end',     default=default_end)
    p.add_argument('--limit',   type=int, default=None)
    p.add_argument('--workers', type=int, default=DEFAULT_WORKERS)
    args = p.parse_args()

    sys.exit(backfill(args.start, args.end, args.limit, args.workers))


if __name__ == '__main__':
    main()
