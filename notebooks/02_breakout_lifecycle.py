# ---
# jupyter:
#   jupytext:
#     formats: py:percent
# ---

# %% [markdown]
# # 02 · 放量大涨生命周期 — 在 5 年数据上 replicate + sensitivity
#
# 用户在 JoinQuant 上做了 2025-11 → 2026-05 共 118 个交易日的实证，发现：
# - 朴素 "≥7% + 2x volume" 追涨：weak（5日 +0.11%，胜率 44%）
# - **首次爆发 vs 重复爆发**：首次显著好（5日 +0.74% vs -0.94%）
# - **冷启动首次爆发**（前 5 日累计涨幅 ≤2%）：5日 +1.34%，胜率 50.6%
# - 但相对中证 1000 超额只 +0.12%
#
# **本 notebook 目的**：
# 1. 在我们的 5 年 stock_db_cn 数据上 replicate 同样逻辑（量级一致吗？方向一致吗？）
# 2. **Threshold sensitivity**：换阈值（涨幅 / 量比 / 冷启动定义）效应是否仍在 — 检测是不是窄峰
# 3. **Regime sensitivity**：按日历年切，每年单独看 — 是不是 2025-26 特有
#
# **诚实标注的近似**：
# - 用户用 `money` (成交额)，我们 schema 只存了 `volume` (股数)。`volume[t]/mean(volume[20])` 跟
#   `money[t]/mean(money[20])` 的比值差一个 ~5-10% 的偏离，对粗粒度阈值（2x / 1.5x）影响不大
#   但应注意完全数值不可比。

# %%
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['STOCK_DB_TYPE']     = 'postgresql'
os.environ['STOCK_PG_PORT']     = '5433'
os.environ['STOCK_PG_DATABASE'] = 'stock_db_cn'

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2

from config.database import config

pd.options.display.max_columns = 50
pd.options.display.width = 180

# %% [markdown]
# ## 1. 加载 OHLCV

# %%
conn = psycopg2.connect(config.get_connection_string())
prices = pd.read_sql(
    "SELECT symbol, date, open, close, volume FROM price_history ORDER BY symbol, date",
    conn, parse_dates=['date'],
)
conn.close()
for c in ('open', 'close'):
    prices[c] = prices[c].astype('float64')
prices['volume'] = prices['volume'].astype('float64')
print(f'{len(prices):,} rows, {prices["symbol"].nunique()} symbols, '
      f'{prices["date"].min().date()} .. {prices["date"].max().date()}')


# %% [markdown]
# ## 2. 特征（per-symbol）— 日内涨幅 / 量倍数 / 5日累计涨幅 / 5日内是否已爆发

# %%
prices = prices.sort_values(['symbol', 'date']).reset_index(drop=True)
g = prices.groupby('symbol', sort=False)

prices['ret_1d']     = g['close'].pct_change(1)
prices['vol_avg_20d'] = g['volume'].transform(lambda s: s.rolling(20).mean())
prices['vol_mult']    = prices['volume'] / prices['vol_avg_20d']

# Cumulative return over past 5 trading days (close-to-close)
prices['cum_ret_5d']  = g['close'].pct_change(5)

# Was there any >=7% day in the past 5 trading days BEFORE today?
# rolling(5) of ret_1d.shift(1) → last 5 days excluding today
prev5_max = g['ret_1d'].transform(lambda s: s.shift(1).rolling(5).max())
prices['prev5_max_ret'] = prev5_max

print('features done')
prices[['symbol','date','close','ret_1d','vol_mult','cum_ret_5d','prev5_max_ret']].tail(5)


# %% [markdown]
# ## 3. 计算"次日开盘买入 → N日收盘卖出"的可交易收益
# 用户的口径：避免 lookahead，event 当日不交易，开盘信号确认是次日。

# %%
HORIZONS = [1, 2, 3, 5]
g = prices.groupby('symbol', sort=False)
next_open = g['open'].shift(-1)              # 次日开盘价（buy）
for h in HORIZONS:
    close_n = g['close'].shift(-h)           # 第 h 日收盘价（sell at close of t+h）
    # 用户的"持有期 N 日"= 次日开盘买，第 1/2/3/5 日 close 卖。
    # 即买入价 = open[t+1], 卖出价 = close[t+h] 其中 h 是持有 trade days 后
    # h=1 → buy open[t+1], sell close[t+1] (持有1日)
    # h=5 → buy open[t+1], sell close[t+5] (持有5日)
    prices[f'ret_h{h}'] = close_n / next_open - 1


# %% [markdown]
# ## 4. Detector 基线（用户的朴素版）：≥7% + 2x volume

# %%
def define_events(df, ret_th=0.07, vol_th=2.0, cold_th=0.02):
    """Returns three masks at the event-day grain.

    Note: prev5_max_ret = max single-day return in the 5 trading days
    BEFORE today (excluding today). So:
      - first_breakout: prev5_max_ret < ret_th
      - repeat_breakout: prev5_max_ret >= ret_th
      - cold_start: first_breakout AND cum_ret_5d <= cold_th
    """
    base = (df['ret_1d'] >= ret_th) & (df['vol_mult'] >= vol_th)
    first = base & (df['prev5_max_ret'] < ret_th)
    repeat = base & (df['prev5_max_ret'] >= ret_th)
    cold = first & (df['cum_ret_5d'] <= cold_th)
    warm = first & (df['cum_ret_5d'] > cold_th) & (df['cum_ret_5d'] <= 0.10)
    hot  = first & (df['cum_ret_5d'] > 0.10)
    return {'base': base, 'first': first, 'repeat': repeat,
            'cold': cold, 'warm': warm, 'hot': hot}


def stats(mask, label):
    """Return DataFrame of (horizon, n, mean, median, winrate) for a mask."""
    out = []
    for h in HORIZONS:
        r = prices.loc[mask, f'ret_h{h}'].dropna()
        out.append({'group': label, 'horizon': h, 'n': len(r),
                    'mean_%': r.mean() * 100,
                    'median_%': r.median() * 100,
                    'winrate_%': (r > 0).mean() * 100})
    return pd.DataFrame(out)


events = define_events(prices)

print('event counts:')
for k, m in events.items():
    print(f'  {k:<8s}: {m.sum():,}')


# %% [markdown]
# ## 5. 全 5 年数据：基线 / 首次 / 重复 / 冷启动 / 温和 / 已热

# %%
all_groups = pd.concat([
    stats(events['base'],   'all naive (≥7% +2x vol)'),
    stats(events['first'],  'first breakout'),
    stats(events['repeat'], 'repeat breakout'),
    stats(events['cold'],   'cold start (first + cum5d ≤2%)'),
    stats(events['warm'],   'warm start (first + cum5d 2-10%)'),
    stats(events['hot'],    'hot start  (first + cum5d >10%)'),
], ignore_index=True)

# Pivot for legibility: rows=group, cols=horizon, value=mean%
piv = all_groups.pivot(index='group', columns='horizon',
                       values=['mean_%', 'winrate_%', 'n'])
print('5-YEAR replication (mean % return | win rate % | N):')
print(piv.round(3))


# %% [markdown]
# ## 6. Regime stability — 按日历年拆

# %%
prices['year'] = prices['date'].dt.year
years = sorted(prices['year'].unique())
print('\nCOLD-START group, per-year 5-day return:\n')
print(f'{"year":>6s}  {"N":>6s}  {"mean %":>8s}  {"median %":>9s}  {"winrate %":>10s}')
print('-' * 50)
cold_mask = events['cold']
for y in years:
    sub = prices[cold_mask & (prices['year'] == y)]['ret_h5'].dropna()
    if len(sub):
        print(f'{y:>6d}  {len(sub):>6,d}  {sub.mean()*100:>7.3f}%  '
              f'{sub.median()*100:>8.3f}%  {(sub > 0).mean()*100:>9.2f}%')


# %% [markdown]
# ## 7. Threshold sensitivity — 冷启动 5 日均值收益作为效应衡量

# %%
ret_grid  = [0.05, 0.07, 0.09]   # 单日涨幅阈值
vol_grid  = [1.5, 2.0, 2.5]      # 量倍数
cold_grid = [0.00, 0.02, 0.05]   # 冷启动累计涨幅上限

rows = []
for r in ret_grid:
    for v in vol_grid:
        for c in cold_grid:
            ev = define_events(prices, ret_th=r, vol_th=v, cold_th=c)
            cold_5d = prices.loc[ev['cold'], 'ret_h5'].dropna()
            rows.append({
                'ret_th': r, 'vol_th': v, 'cold_th': c,
                'n': len(cold_5d),
                'mean_5d_%':   cold_5d.mean() * 100   if len(cold_5d) else np.nan,
                'median_5d_%': cold_5d.median() * 100 if len(cold_5d) else np.nan,
                'winrate_%':   (cold_5d > 0).mean() * 100 if len(cold_5d) else np.nan,
            })
sens = pd.DataFrame(rows)
print('THRESHOLD SENSITIVITY (cold-start 5-day return):')
print(sens.pivot_table(index=['ret_th','vol_th'], columns='cold_th',
                        values='mean_5d_%').round(3))
print()
print('(N events per cell):')
print(sens.pivot_table(index=['ret_th','vol_th'], columns='cold_th',
                       values='n').astype(int))


# %% [markdown]
# ## 8. 焦点期 vs 全期 — 跟用户的 6 个月窗口对照

# %%
user_window = (prices['date'] >= '2025-11-17') & (prices['date'] <= '2026-05-15')
print('\nCOLD-START in USER WINDOW (2025-11-17 .. 2026-05-15):')
for h in HORIZONS:
    sub = prices.loc[events['cold'] & user_window, f'ret_h{h}'].dropna()
    print(f'  h{h}: n={len(sub):,}  mean={sub.mean()*100:+.3f}%  '
          f'median={sub.median()*100:+.3f}%  win={((sub>0).mean()*100):.2f}%')

print('\nCOLD-START in FULL 5-YEAR (for comparison):')
for h in HORIZONS:
    sub = prices.loc[events['cold'], f'ret_h{h}'].dropna()
    print(f'  h{h}: n={len(sub):,}  mean={sub.mean()*100:+.3f}%  '
          f'median={sub.median()*100:+.3f}%  win={((sub>0).mean()*100):.2f}%')


# %% [markdown]
# ## 9. 可视化：每年 cold-start 5d 收益分布 + threshold grid heatmap

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Left: per-year boxplot of cold-start 5-day return
yearly = []
for y in years:
    sub = prices.loc[events['cold'] & (prices['year'] == y), 'ret_h5'].dropna() * 100
    if len(sub) > 20:
        yearly.append((y, sub))
axes[0].boxplot([s for _, s in yearly], labels=[str(y) for y, _ in yearly],
                showfliers=False)
axes[0].axhline(0, color='k', linewidth=0.5)
axes[0].set_title('Cold-start 5-day return by calendar year')
axes[0].set_ylabel('return %')
axes[0].set_ylim(-15, 20)

# Right: heatmap of sensitivity (avg over cold_th, indexed by ret_th × vol_th)
heat = sens.pivot_table(index='ret_th', columns='vol_th', values='mean_5d_%')
im = axes[1].imshow(heat.values, cmap='RdBu_r', vmin=-2, vmax=2, aspect='auto')
axes[1].set_xticks(range(len(vol_grid))); axes[1].set_xticklabels(vol_grid)
axes[1].set_yticks(range(len(ret_grid))); axes[1].set_yticklabels(ret_grid)
axes[1].set_xlabel('vol multiplier threshold')
axes[1].set_ylabel('daily return threshold')
axes[1].set_title('Cold-start 5d mean return % (averaged over cold_th)')
for i in range(len(ret_grid)):
    for j in range(len(vol_grid)):
        axes[1].text(j, i, f'{heat.values[i,j]:+.2f}', ha='center', va='center',
                     color='white' if abs(heat.values[i,j]) > 1 else 'black')
plt.colorbar(im, ax=axes[1])

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), '02_breakout_lifecycle.png')
plt.savefig(out, dpi=110, bbox_inches='tight')
print(f'saved: {out}')
