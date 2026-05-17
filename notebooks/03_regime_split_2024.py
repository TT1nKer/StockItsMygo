# ---
# jupyter:
#   jupytext:
#     formats: py:percent
# ---

# %% [markdown]
# # 03 · 2024 反常表现到底是全年均匀的，还是集中在 924 行情之后？
#
# **背景**：notebook 02 发现冷启动突破事件的 5 日均值收益在 2024 年达到 +12% 量级，
# 单年把 5 年均值 (+6.27%) 拉得很高；剔除 2024 后 ≈ +1.5%，跟用户在聚宽上的 6 个月窗口
# (+1.34%) 对得上。问题是：2024 这个超常表现到底是全年的、还是只在某段时间里发生？
#
# 已知 2024-09-24 央行/财政推出宽松组合拳，触发"924 行情"，A 股 9 月底到 10 月初出现急涨。
# 本 notebook 按 2024-09-18 切分（用户指定边界），把 2024 拆成两段，
# 跟 2021-2025 其它年份并排比较：
#
# - n（事件数）
# - 5 日均值 / 中位数 / 胜率 / p25 / p75
# - 同一批事件日期上的"等权市场 5 日收益"作基准
# - 超额收益 = 事件均值 − 同日期基准均值
#
# 事件定义沿用 notebook 02 的 **cold-start breakout**：
# `ret_1d ≥ 7%` AND `vol_mult ≥ 2.0` AND `prev5_max_ret < 7%` AND `cum_ret_5d ≤ 2%`，
# 收益口径同样是"次日开盘买、第 5 个交易日收盘卖"。

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
pd.options.display.width = 200

# %% [markdown]
# ## 1. 加载 OHLCV、计算特征 + 可交易 5 日收益

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

prices = prices.sort_values(['symbol', 'date']).reset_index(drop=True)
g = prices.groupby('symbol', sort=False)

prices['ret_1d']        = g['close'].pct_change(1)
prices['vol_avg_20d']   = g['volume'].transform(lambda s: s.rolling(20).mean())
prices['vol_mult']      = prices['volume'] / prices['vol_avg_20d']
prices['cum_ret_5d']    = g['close'].pct_change(5)
prices['prev5_max_ret'] = g['ret_1d'].transform(lambda s: s.shift(1).rolling(5).max())

# Tradable forward return: buy open[t+1], sell close[t+5]
g = prices.groupby('symbol', sort=False)
next_open = g['open'].shift(-1)
close_h5  = g['close'].shift(-5)
prices['ret_h5'] = close_h5 / next_open - 1

print('features done')


# %% [markdown]
# ## 2. 事件抽取（cold-start breakout）+ per-event 5 日收益

# %%
events_mask = (
    (prices['ret_1d']        >= 0.07)
    & (prices['vol_mult']    >= 2.0)
    & (prices['prev5_max_ret'] < 0.07)
    & (prices['cum_ret_5d']  <= 0.02)
)
events = (prices.loc[events_mask, ['symbol', 'date', 'ret_h5']]
                .dropna(subset=['ret_h5'])
                .reset_index(drop=True)
                .copy())
print(f'total cold-start events with realised 5d return: {len(events):,}')
print(f'date range: {events["date"].min().date()} .. {events["date"].max().date()}')


# %% [markdown]
# ## 3. 等权市场 5 日基准 — 每个交易日一个数
#
# 对每个日期 `t`，取**所有在 `t` 当天有报价的股票**的 `ret_h5` 求平均，
# 得到"如果你在 `t+1` 开盘等权买入全市场、`t+5` 收盘卖出"的收益。
# 然后把这个基准 join 回事件表，按事件加权聚合。
# （每个事件日权重 = 当天事件数，所以基准是"事件密集日"加权的市场表现。）

# %%
bench_daily = (prices.groupby('date')['ret_h5']
                     .mean()
                     .rename('bench_5d')
                     .to_frame())
print(f'benchmark series: {len(bench_daily):,} trading days')
print(f'  full-period bench mean: {bench_daily["bench_5d"].mean()*100:+.3f}%')

events = events.merge(bench_daily, left_on='date', right_index=True, how='left')
print(f'events with bench attached: {events["bench_5d"].notna().sum():,} / {len(events):,}')


# %% [markdown]
# ## 4. 按 period 聚合
#
# Period 划分：
# - 2021 / 2022 / 2023 / 2024 (full) / 2025 各算一行
# - 2024 (pre 09-18)：`2024-01-01 .. 2024-09-17`
# - 2024 (post 09-18)：`2024-09-18 .. 2024-12-31`

# %%
def period_stats(sub: pd.DataFrame) -> pd.Series:
    r = sub['ret_h5']
    b = sub['bench_5d']
    return pd.Series({
        'n':         len(r),
        'mean_%':    r.mean()      * 100,
        'median_%':  r.median()    * 100,
        'winrate_%': (r > 0).mean() * 100,
        'p25_%':     r.quantile(0.25) * 100,
        'p75_%':     r.quantile(0.75) * 100,
        'bench_%':   b.mean()      * 100,
        'excess_%':  (r.mean() - b.mean()) * 100,
    })


periods = [
    ('2021',              ('2021-01-01', '2021-12-31')),
    ('2022',              ('2022-01-01', '2022-12-31')),
    ('2023',              ('2023-01-01', '2023-12-31')),
    ('2024',              ('2024-01-01', '2024-12-31')),
    ('2024 (pre 09-18)',  ('2024-01-01', '2024-09-17')),
    ('2024 (post 09-18)', ('2024-09-18', '2024-12-31')),
    ('2025',              ('2025-01-01', '2025-12-31')),
]

rows = []
for label, (start, end) in periods:
    sub = events[(events['date'] >= start) & (events['date'] <= end)]
    if len(sub) == 0:
        continue
    rows.append(period_stats(sub).rename(label))

table = pd.DataFrame(rows)
print('\nPER-PERIOD COMPARISON:')
print(table.round(3).to_string())


# %% [markdown]
# ## 5. 可视化

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Highlight the two 2024 subperiods
colors = []
for label in table.index:
    if 'pre 09-18' in label:
        colors.append('#d97706')   # amber for pre-rally
    elif 'post 09-18' in label:
        colors.append('#dc2626')   # red for post-rally
    elif label == '2024':
        colors.append('#9ca3af')   # gray for full-year (combines the two)
    else:
        colors.append('#2563eb')   # blue for other years

# Left: mean return
axes[0].bar(range(len(table)), table['mean_%'].values, color=colors,
            edgecolor='black', linewidth=0.6)
axes[0].axhline(0, color='k', linewidth=0.5)
axes[0].set_xticks(range(len(table)))
axes[0].set_xticklabels(table.index, rotation=30, ha='right')
axes[0].set_ylabel('mean 5-day return %')
axes[0].set_title('Cold-start breakout — mean 5d return by period')
for i, v in enumerate(table['mean_%'].values):
    axes[0].text(i, v + (0.2 if v >= 0 else -0.6), f'{v:+.2f}',
                 ha='center', fontsize=9)

# Right: excess return over benchmark
axes[1].bar(range(len(table)), table['excess_%'].values, color=colors,
            edgecolor='black', linewidth=0.6)
axes[1].axhline(0, color='k', linewidth=0.5)
axes[1].set_xticks(range(len(table)))
axes[1].set_xticklabels(table.index, rotation=30, ha='right')
axes[1].set_ylabel('excess 5d return % (event − benchmark)')
axes[1].set_title('Excess over equal-weight market benchmark')
for i, v in enumerate(table['excess_%'].values):
    axes[1].text(i, v + (0.1 if v >= 0 else -0.3), f'{v:+.2f}',
                 ha='center', fontsize=9)

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), '03_regime_split_2024.png')
plt.savefig(out, dpi=110, bbox_inches='tight')
print(f'saved: {out}')


# %% [markdown]
# ## 6. 数据驱动的判读
#
# 把 pre / post / 2024 全年三行的关键数字提出来，自动生成结论文字。

# %%
def fmt(x): return f'{x:+.2f}%'

t_pre  = table.loc['2024 (pre 09-18)']
t_post = table.loc['2024 (post 09-18)']
t_full = table.loc['2024']

print(f'2024 全年      :  n={int(t_full["n"]):>6,d}   mean={fmt(t_full["mean_%"])}   '
      f'bench={fmt(t_full["bench_%"])}   excess={fmt(t_full["excess_%"])}   '
      f'winrate={t_full["winrate_%"]:.1f}%')
print(f'2024 (pre 924) :  n={int(t_pre["n"]):>6,d}   mean={fmt(t_pre["mean_%"])}   '
      f'bench={fmt(t_pre["bench_%"])}   excess={fmt(t_pre["excess_%"])}   '
      f'winrate={t_pre["winrate_%"]:.1f}%')
print(f'2024 (post 924):  n={int(t_post["n"]):>6,d}   mean={fmt(t_post["mean_%"])}   '
      f'bench={fmt(t_post["bench_%"])}   excess={fmt(t_post["excess_%"])}   '
      f'winrate={t_post["winrate_%"]:.1f}%')

pre_share  = t_pre['n']  / t_full['n']
post_share = t_post['n'] / t_full['n']
print(f'\n事件数占比：pre = {pre_share*100:.1f}%, post = {post_share*100:.1f}%')
print(f'pre 与 post 的 mean 差：{(t_post["mean_%"] - t_pre["mean_%"]):+.2f} pp')
print(f'pre 与 post 的 excess 差：{(t_post["excess_%"] - t_pre["excess_%"]):+.2f} pp')


# %% [markdown]
# ## 7. 结论（根据本机实际数据）
#
# **问题**："2024 的反常表现是全年均匀的，还是集中在 2024-09-18 之后？"
#
# **答：跟最初猜想相反 — 2024 的异常表现几乎完全集中在 924 行情*之前*（2024-01-01 .. 2024-09-17），
# 而不是行情期间或之后。**
#
# 关键数字：
#
# | 时段 | n | mean 5d | bench 5d | excess | winrate |
# |---|---:|---:|---:|---:|---:|
# | 2024 (pre 09-18)  |  968 | +12.89% | +7.10% | **+5.79%** | 80.8% |
# | 2024 (post 09-18) |   73 |  +3.10% | +2.96% |   +0.13%   | 54.8% |
# | 2024 全年        | 1041 | +12.20% | +6.81% | **+5.40%** | 79.0% |
#
# 看到的三个关键事实：
#
# 1. **事件数严重失衡**：2024 全年 1041 个冷启动事件里，**93% 在 924 之前**（968 个），
#    924 之后 8.5 个交易月的 3.5 个月里只有 73 个。说明 924 行情之后，市场进入了高动量状态，
#    "冷启动"（前 5 日累计涨幅 ≤2%）的前提条件在大多数股票上都不成立 — 啥都在涨。
#
# 2. **回报差距巨大**：pre-924 mean +12.89% vs post-924 mean +3.10%，差 9.8pp。
#    pre-924 段冷启动突破后 5 日平均涨 13%、胜率 81%；post-924 段平均只赚 3%、胜率 55%（基本是随机）。
#
# 3. **超额收益也差很多**：pre-924 excess +5.79%（事件 +12.89% − 同期等权市场 +7.10%），
#    post-924 excess 只有 +0.13%。post-924 段冷启动突破完全没有 alpha，
#    跟普通市场没区别 — 涨的是 beta，不是事件信号。
#
# **隐含的含义**：
#
# - notebook 02 看到的 2024 +12.2% 不是来自 924 行情顺风，而是来自**整个 2024 上半年到 9 月中旬这 8 个多月**。
#   这段时间 A 股小盘股有多个连续主题轮动（AI/Sora、低空经济、新质生产力、雪球敲入后的小盘反弹等），
#   冷启动突破刚好在这种"题材频繁切换 + 单股票快速发动"的环境里高效命中。
#
# - 924 之后整个市场进入"beta 行情"，所有股票一起涨，单股事件信号被淹没。
#   这反过来印证：冷启动突破策略**只在题材轮动型市场里有效**，beta 单边行情里失效。
#
# - **进一步要查的事**（下一个 notebook 候选）：
#   把 2024 pre-924 再细拆 — Q1（Jan-Mar，雪球+AI）、Q2（Apr-Jun，红利+低空）、Q3-前（Jul-Sep 17，新质生产力轮动）
#   看是某一个题材潮把均值拉飞，还是真的全季节都给力。
#   如果是单一题材主导，那 2024 的 "+12%" 就只是 "**那个题材碰巧落在我们的事件窗口里**"，
#   不是策略本身的可重复优势。
#
# - 对未来调用：**不要**把 2024 cold-start 的 +12% 当作策略基线 expectation。
#   2021 / 2022 / 2023 / 2025 的事件均值都在 +1% 到 +2% 区间，
#   2024 pre-924 是 outlier；除非市场再次进入类似的密集题材轮动期，否则均值回归到 +1-2% 是更合理的先验。
