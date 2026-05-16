# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       format_name: percent
# ---

# %% [markdown]
# # Event Study: 低波动 + 放量 + 价格未突破
#
# **假设**：一只 A 股出现以下三个条件时，可能预示资金在低位吸筹：
#
# 1. 20 日收益波动率排在全市场底 30%（"低波动"）
# 2. 5 日均量 / 20 日均量 > 1.8（"放量"）
# 3. 5 日价格变化 |Δ| < 3%（"价格没突破"）
#
# 用 `stock_db_cn` 全市场 5 年数据扫一遍，看：
# - 这种模式历史上触发了多少次
# - 触发后 3/5/10/20 日收益分布跟"随便挑一天"比有没有差别
#
# **已知缺陷**（第一版，知道但不修）：
# - 波动率阈值用全数据集 quantile → 有 look-ahead bias，正经研究要用 rolling/expanding
# - 没扣 benchmark（沪深 300）, "超额收益"还不算
# - 没做样本外验证 / FDR 校正
#
# 这一版的目标只是：**把 pipeline 跑通，看 effect size 大概是什么 order of magnitude**。

# %%
import os
import sys

# Make project root importable + point at the CN DB
sys.path.insert(0, os.path.abspath('..'))
os.environ['STOCK_DB_TYPE']     = 'postgresql'
os.environ['STOCK_PG_PORT']     = '5433'
os.environ['STOCK_PG_DATABASE'] = 'stock_db_cn'

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2

from config.database import config

pd.options.display.max_columns = 50
pd.options.display.width = 160

print('connection:', config.get_connection_string())


# %% [markdown]
# ## 1. 加载全市场 OHLCV

# %%
conn = psycopg2.connect(config.get_connection_string())
prices = pd.read_sql(
    """
    SELECT symbol, date, open, high, low, close, volume
    FROM price_history
    ORDER BY symbol, date
    """,
    conn,
    parse_dates=['date'],
)
conn.close()

print(f'{len(prices):>10,d} rows')
print(f'{prices["symbol"].nunique():>10,d} symbols')
print(f'{prices["date"].min().date()} .. {prices["date"].max().date()}')


# %% [markdown]
# ## 2. 特征工程（per-symbol rolling）

# %%
prices = prices.sort_values(['symbol', 'date']).reset_index(drop=True)

# Convert NUMERIC → float so rolling works fast
for c in ('open', 'high', 'low', 'close'):
    prices[c] = prices[c].astype('float64')
prices['volume'] = prices['volume'].astype('float64')   # NaN-friendly

g = prices.groupby('symbol', sort=False)

prices['ret_1d']      = g['close'].pct_change(1)
prices['vol_20d']     = g['ret_1d'].transform(lambda s: s.rolling(20).std())
prices['vol_avg_5d']  = g['volume'].transform(lambda s: s.rolling(5).mean())
prices['vol_avg_20d'] = g['volume'].transform(lambda s: s.rolling(20).mean())
prices['vol_ratio']   = prices['vol_avg_5d'] / prices['vol_avg_20d']
prices['price_5d_chg'] = g['close'].pct_change(5)

print('features computed')
prices[['symbol', 'date', 'close', 'vol_20d', 'vol_ratio', 'price_5d_chg']].head(10)


# %% [markdown]
# ## 3. Detector → hits

# %%
vol_thresh = prices['vol_20d'].quantile(0.30)
print(f'低波动阈值 (vol_20d <): {vol_thresh:.5f}')

mask = (
    (prices['vol_20d']  < vol_thresh)
    & (prices['vol_ratio'] > 1.8)
    & (prices['price_5d_chg'].abs() < 0.03)
)
hits = prices.loc[mask].copy()

print(f'触发事件: {len(hits):,} ({len(hits)/len(prices.dropna(subset=["vol_20d"]))*100:.2f}% of valid days)')
print(f'涉及股票: {hits["symbol"].nunique()}')
print(f'日期范围: {hits["date"].min().date()} .. {hits["date"].max().date()}')
hits[['symbol', 'date', 'close', 'vol_20d', 'vol_ratio', 'price_5d_chg']].head()


# %% [markdown]
# ## 4. 计算未来 N 日收益（3 / 5 / 10 / 20）

# %%
HORIZONS = [3, 5, 10, 20]
g = prices.groupby('symbol', sort=False)

for h in HORIZONS:
    prices[f'fwd_{h}d_ret'] = g['close'].shift(-h) / prices['close'] - 1

# Join forward returns onto hits
fwd_cols = [f'fwd_{h}d_ret' for h in HORIZONS]
hits = hits.merge(prices[['symbol', 'date'] + fwd_cols], on=['symbol', 'date'], how='left')

print(hits[['symbol', 'date', 'close'] + fwd_cols].head(10))


# %% [markdown]
# ## 5. 收益分布 vs 基准（"随便选一天"的同周期收益）

# %%
print(f'{"horizon":>8s}  {"N hits":>8s}  '
      f'{"hit mean":>10s}  {"hit median":>11s}  {"hit win%":>9s}  {"hit std":>9s}  '
      f'{"base mean":>10s}  {"base median":>11s}  {"diff (mean)":>11s}')
print('-' * 110)

results = []
for h in HORIZONS:
    hit  = hits[f'fwd_{h}d_ret'].dropna()
    base = prices[f'fwd_{h}d_ret'].dropna()
    diff = hit.mean() - base.mean()
    results.append({
        'horizon': h,
        'n_hits': len(hit),
        'hit_mean': hit.mean(),
        'hit_median': hit.median(),
        'hit_winrate': (hit > 0).mean(),
        'hit_std': hit.std(),
        'base_mean': base.mean(),
        'base_median': base.median(),
        'diff_mean': diff,
    })
    print(f'{h:>8d}  {len(hit):>8,d}  '
          f'{hit.mean()*100:>9.3f}%  {hit.median()*100:>10.3f}%  {(hit > 0).mean()*100:>8.2f}%  '
          f'{hit.std()*100:>8.2f}%  '
          f'{base.mean()*100:>9.3f}%  {base.median()*100:>10.3f}%  '
          f'{diff*100:>+10.3f}%')

results_df = pd.DataFrame(results)


# %% [markdown]
# ## 6. 直方图：hits 收益分布 vs 基准

# %%
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
for ax, h in zip(axes.flat, HORIZONS):
    hit  = hits[f'fwd_{h}d_ret'].dropna() * 100
    base = prices[f'fwd_{h}d_ret'].dropna() * 100
    bins = np.linspace(-15, 15, 60)
    ax.hist(base.clip(-15, 15), bins=bins, alpha=0.35,
            label=f'baseline (n={len(base):,})', density=True, color='gray')
    ax.hist(hit.clip(-15, 15), bins=bins, alpha=0.65,
            label=f'hits (n={len(hit):,})', density=True, color='steelblue')
    ax.axvline(0, color='k', linewidth=0.5)
    ax.axvline(hit.mean(), color='steelblue', linestyle='--', linewidth=1,
               label=f'hit mean={hit.mean():+.2f}%')
    ax.axvline(base.mean(), color='gray', linestyle='--', linewidth=1,
               label=f'base mean={base.mean():+.2f}%')
    ax.set_title(f'{h}-day forward return')
    ax.set_xlabel('return %')
    ax.legend(fontsize=8)
plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), '01_low_vol_volume_spike_distribution.png')
plt.savefig(out, dpi=110, bbox_inches='tight')
print(f'saved: {out}')


# %% [markdown]
# ## 7. 抽样检查：表现最好 / 最差的 10 个 hits（10 日窗口）

# %%
print('--- top 10 by 10-day forward return ---')
print(hits.nlargest(10, 'fwd_10d_ret')[
    ['symbol', 'date', 'close', 'vol_20d', 'vol_ratio', 'price_5d_chg', 'fwd_10d_ret']
].to_string(index=False))

print('\n--- bottom 10 by 10-day forward return ---')
print(hits.nsmallest(10, 'fwd_10d_ret')[
    ['symbol', 'date', 'close', 'vol_20d', 'vol_ratio', 'price_5d_chg', 'fwd_10d_ret']
].to_string(index=False))
