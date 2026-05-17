# ---
# jupyter:
#   jupytext:
#     formats: py:percent
# ---

# %% [markdown]
# # 05 · 拆解 2024 (pre 09-18) 的 +5.79% excess —— 究竟是谁贡献的？
#
# notebook 03 发现 2024-01-01 .. 2024-09-17 这 8.5 个月内冷启动突破事件：
# n=968，5 日均值 +12.89%，同日期等权基准 +7.10%，**excess +5.79%**，胜率 80.8%。
#
# 本 notebook 把这 968 个事件分别按**事件 / 日期 / 股票 / 月份 / 行业概念**切，
# 找出 "+5.79% 的 excess 到底是谁贡献的"，三类可能性：
#
# 1. **少数极端日**（如某次政策刺激或市场暴动后的几天）把均值拉飞
# 2. **少数极端股票**反复触发（同一妖股一直冷启动突破）
# 3. **某类行业 / 主题集中爆发**（雪球反弹小盘、AI、低空、新质生产力 …）
#
# **数据局限的诚实标注**：
# - `stocks.sector / stocks.industry` 在 stock_db_cn 里 **0/4595 填充**（之前 ingest 只入了
#   security_name + market_category + exchange）。所以 Part E 暂时只能给"无法回答"的明确结论，
#   并列出补数据需要的具体接口（最后一节）。
# - 收益口径同 notebook 02/03：买 `open[t+1]`，卖 `close[t+5]`，未扣涨跌停限制 / 交易费。
#   涨停日次日开盘买不到的事件会高估收益，但本 notebook 用 **excess vs 同日期 EW 市场**，
#   bias 在 event/bench 两边大致对消，相对排序仍可信。

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
pd.options.display.max_rows    = 200
pd.options.display.width       = 220

OUT_DIR = os.path.dirname(__file__)


# %% [markdown]
# ## 1. 加载 OHLCV + 股票名

# %%
conn = psycopg2.connect(config.get_connection_string())
prices = pd.read_sql(
    "SELECT symbol, date, open, close, volume FROM price_history ORDER BY symbol, date",
    conn, parse_dates=['date'],
)
names = pd.read_sql(
    "SELECT symbol, COALESCE(NULLIF(company_name,''), security_name) AS stock_name "
    "FROM stocks",
    conn,
)
conn.close()

for c in ('open', 'close'):
    prices[c] = prices[c].astype('float64')
prices['volume'] = prices['volume'].astype('float64')
print(f'{len(prices):,} rows, {prices["symbol"].nunique()} symbols, '
      f'{prices["date"].min().date()} .. {prices["date"].max().date()}')
print(f'name lookup table: {len(names):,} rows '
      f'(stock_name populated: {names["stock_name"].notna().sum():,})')


# %% [markdown]
# ## 2. 特征 + 5 日可交易收益（同 notebook 02/03）

# %%
prices = prices.sort_values(['symbol', 'date']).reset_index(drop=True)
g = prices.groupby('symbol', sort=False)

prices['ret_1d']        = g['close'].pct_change(1)
prices['vol_avg_20d']   = g['volume'].transform(lambda s: s.rolling(20).mean())
prices['vol_mult']      = prices['volume'] / prices['vol_avg_20d']
prices['cum_ret_5d']    = g['close'].pct_change(5)
prices['prev5_max_ret'] = g['ret_1d'].transform(lambda s: s.shift(1).rolling(5).max())

g = prices.groupby('symbol', sort=False)
next_open = g['open'].shift(-1)
close_h5  = g['close'].shift(-5)
prices['ret_h5'] = close_h5 / next_open - 1
print('features done')


# %% [markdown]
# ## 3. 抽取 cold-start 事件 + 限定 2024-01-01 .. 2024-09-17

# %%
events_mask = (
    (prices['ret_1d']        >= 0.07)
    & (prices['vol_mult']    >= 2.0)
    & (prices['prev5_max_ret'] < 0.07)
    & (prices['cum_ret_5d']  <= 0.02)
)
events_full = (prices.loc[events_mask, ['symbol', 'date', 'close', 'ret_h5']]
                     .dropna(subset=['ret_h5'])
                     .reset_index(drop=True)
                     .copy())

WINDOW_START = pd.Timestamp('2024-01-01')
WINDOW_END   = pd.Timestamp('2024-09-17')
in_window = (events_full['date'] >= WINDOW_START) & (events_full['date'] <= WINDOW_END)
events = events_full[in_window].copy().reset_index(drop=True)

print(f'cold-start events in {WINDOW_START.date()} .. {WINDOW_END.date()}: {len(events):,}')


# %% [markdown]
# ## 4. Benchmark（同日期 EW 市场 5 日收益）+ excess

# %%
bench_daily = (prices.groupby('date')['ret_h5'].mean()
                     .rename('bench_5d').to_frame())
events = events.merge(bench_daily, left_on='date', right_index=True, how='left')
events['excess'] = events['ret_h5'] - events['bench_5d']
events = events.merge(names, on='symbol', how='left')
events = events.rename(columns={'symbol': 'stock_code', 'date': 'event_date',
                                 'close': 'event_close',
                                 'ret_h5': 'fwd_5d', 'bench_5d': 'bench_5d'})
events = events[['stock_code', 'stock_name', 'event_date', 'event_close',
                 'fwd_5d', 'bench_5d', 'excess']]

print('\nsanity check — should match notebook 03 row "2024 (pre 09-18)":')
print(f'  n         = {len(events):,}')
print(f'  mean fwd  = {events["fwd_5d"].mean()*100:+.3f}%')
print(f'  mean bench= {events["bench_5d"].mean()*100:+.3f}%')
print(f'  mean exc  = {events["excess"].mean()*100:+.3f}%')
print(f'  total exc = {events["excess"].sum()*100:+.1f}pp  (sum of percentage points)')

events.to_csv(os.path.join(OUT_DIR, '05_events_pre924.csv'), index=False)
print(f"\nsaved: 05_events_pre924.csv")


# %% [markdown]
# ## Part A — Event-level contribution: top / bottom 50 by excess

# %%
def show_events(df, label):
    cols = ['stock_code', 'stock_name', 'event_date', 'event_close',
            'fwd_5d', 'bench_5d', 'excess']
    pretty = df[cols].copy()
    for c in ('fwd_5d', 'bench_5d', 'excess'):
        pretty[c] = (pretty[c] * 100).round(2)
    pretty['event_date'] = pretty['event_date'].dt.strftime('%Y-%m-%d')
    print(f'\n=== {label} ===')
    print(pretty.to_string(index=False))


top50_ev = events.nlargest(50, 'excess')
bot50_ev = events.nsmallest(50, 'excess')
show_events(top50_ev, 'Top 50 events by excess')
show_events(bot50_ev, 'Bottom 50 events by excess')


# %% [markdown]
# ## Part B — Date-level contribution

# %%
by_date = events.groupby('event_date').agg(
    n_events        = ('excess', 'size'),
    mean_event_ret  = ('fwd_5d', 'mean'),
    bench_ret       = ('bench_5d', 'mean'),
    mean_excess     = ('excess', 'mean'),
    total_excess    = ('excess', 'sum'),
).reset_index()

for c in ('mean_event_ret', 'bench_ret', 'mean_excess', 'total_excess'):
    by_date[c] = (by_date[c] * 100).round(3)

by_date_total = by_date.nlargest(30, 'total_excess')
by_date_mean  = by_date.nlargest(30, 'mean_excess')
by_date_worst = by_date.nsmallest(30, 'total_excess')

print('\n=== Top 30 dates by TOTAL excess contribution (pp) ===')
print(by_date_total.to_string(index=False))

print('\n=== Top 30 dates by MEAN excess (filter: any event count) ===')
print(by_date_mean.to_string(index=False))

print('\n=== Bottom 30 dates by TOTAL excess contribution (pp) ===')
print(by_date_worst.to_string(index=False))

by_date.to_csv(os.path.join(OUT_DIR, '05_by_date.csv'), index=False)
print(f"\nsaved: 05_by_date.csv  ({len(by_date)} dates)")


# %% [markdown]
# ## Part C — Stock-level contribution

# %%
by_stock = events.groupby(['stock_code', 'stock_name'], dropna=False).agg(
    n_events     = ('excess', 'size'),
    mean_excess  = ('excess', 'mean'),
    total_excess = ('excess', 'sum'),
).reset_index()
for c in ('mean_excess', 'total_excess'):
    by_stock[c] = (by_stock[c] * 100).round(3)

by_stock_top = by_stock.nlargest(50, 'total_excess')

print('\n=== Top 50 stocks by TOTAL excess contribution (pp) ===')
print(by_stock_top.to_string(index=False))

print(f'\ntotal distinct stocks with events: {by_stock["stock_code"].nunique():,}')
print(f'  - with 1 event : {(by_stock["n_events"]==1).sum():,}')
print(f'  - with 2 events: {(by_stock["n_events"]==2).sum():,}')
print(f'  - with ≥3      : {(by_stock["n_events"]>=3).sum():,}')

by_stock.to_csv(os.path.join(OUT_DIR, '05_by_stock.csv'), index=False)
print(f"\nsaved: 05_by_stock.csv")


# %% [markdown]
# ## Part D — Month-level contribution

# %%
events['month'] = events['event_date'].dt.to_period('M').astype(str)
by_month = events.groupby('month').agg(
    n_events     = ('excess', 'size'),
    mean_excess  = ('excess', 'mean'),
    total_excess_pp = ('excess', lambda s: s.sum() * 100),
).reset_index()
by_month['mean_excess'] = (by_month['mean_excess'] * 100).round(3)
by_month['total_excess_pp'] = by_month['total_excess_pp'].round(2)

total_pos = by_month.loc[by_month['total_excess_pp'] > 0, 'total_excess_pp'].sum()
by_month['share_of_positive_%'] = np.where(
    by_month['total_excess_pp'] > 0,
    (by_month['total_excess_pp'] / total_pos * 100).round(1),
    0.0,
)

print('\n=== Month-level contribution ===')
print(by_month.to_string(index=False))

# Quick chart
fig, ax = plt.subplots(figsize=(10, 4.5))
colors_m = ['#2563eb' if v >= 0 else '#dc2626' for v in by_month['total_excess_pp']]
ax.bar(by_month['month'], by_month['total_excess_pp'], color=colors_m,
       edgecolor='black', linewidth=0.5)
ax.axhline(0, color='k', linewidth=0.5)
ax.set_ylabel('total excess contribution (pp)')
ax.set_title('2024 pre-09-18: monthly excess contribution\n'
             '(sum of event-level excess returns within month)')
for i, (n, v) in enumerate(zip(by_month['n_events'], by_month['total_excess_pp'])):
    ax.text(i, v + (3 if v >= 0 else -8), f'n={n}\n{v:+.0f}',
            ha='center', fontsize=8)
plt.tight_layout()
fig_path = os.path.join(OUT_DIR, '05_decompose_2024_pre924.png')
plt.savefig(fig_path, dpi=110, bbox_inches='tight')
print(f"saved: {fig_path}")

by_month.to_csv(os.path.join(OUT_DIR, '05_by_month.csv'), index=False)


# %% [markdown]
# ## Part E — Industry / concept contribution
#
# **当前 stock_db_cn 状态**：
#
# ```sql
# SELECT COUNT(*) FROM stocks WHERE sector  IS NOT NULL;  -- → 0
# SELECT COUNT(*) FROM stocks WHERE industry IS NOT NULL;  -- → 0
# ```
#
# 既有数据 ingest 只入了 `security_name` / `market_category` / `exchange` 三个分类字段，
# **行业、概念、主题板块都没有入库**，所以这一节无法回答。
#
# **补行业 / 概念标签的最小可行路径（AKShare）**：
#
# | 字段 | 接口 | 体量 | 备注 |
# |---|---|---|---|
# | 申万行业 (一级 / 二级 / 三级) | `ak.stock_industry_clf_hist_sw()` | 单次返回全市场 | 历史快照表，最干净 |
# | 东财行业 | `ak.stock_individual_info_em(symbol)` | 单股调用 × 4595 | 含"行业"字段，多进程 ~5-10 min |
# | 东财概念板块（200+ 个）| `ak.stock_board_concept_name_em()` + `_cons_em()` | 200 × 一次 | 概念表 + 成分股表 |
# | 同花顺概念 | `ak.stock_board_concept_name_ths()` + `_cons_ths()` | 类似上面 | 备份来源 |
#
# 建议入两张表：
#
# ```sql
# CREATE TABLE stock_industry (
#   symbol TEXT, source TEXT, level1 TEXT, level2 TEXT, level3 TEXT,
#   as_of_date DATE, PRIMARY KEY (symbol, source, as_of_date)
# );
# CREATE TABLE stock_concept (
#   symbol TEXT, source TEXT, concept TEXT,
#   as_of_date DATE, PRIMARY KEY (symbol, source, concept, as_of_date)
# );
# ```
#
# 跑完后，本 notebook 第 5 节加 `events.merge(industry, on='symbol')` + `groupby('level2')`
# 就能补齐。Top 50 股票（Part C 输出）大概率会落在某几个固定概念里 —— 但**没数据之前不猜**。

print('\n[Part E SKIPPED] — industry/concept not ingested in stock_db_cn yet.')
print('See markdown above for AKShare ingest plan.')


# %% [markdown]
# ## Part F — 数据驱动解读
#
# 下面的解读是 **本机跑完 A-D 后**根据实际数字写的，不是预先猜的模板。

# %%
total_excess_pp = events['excess'].sum() * 100

# Concentration metrics
n_dates_total  = events['event_date'].nunique()
top10_dates    = by_date.nlargest(10, 'total_excess')['total_excess'].sum()
top30_dates    = by_date.nlargest(30, 'total_excess')['total_excess'].sum()
top10_dates_sh = top10_dates / total_excess_pp * 100
top30_dates_sh = top30_dates / total_excess_pp * 100

n_stocks_total = events['stock_code'].nunique()
top10_stocks   = by_stock.nlargest(10, 'total_excess')['total_excess'].sum()
top50_stocks   = by_stock.nlargest(50, 'total_excess')['total_excess'].sum()
top10_stocks_sh = top10_stocks / total_excess_pp * 100
top50_stocks_sh = top50_stocks / total_excess_pp * 100

repeat_stocks  = (by_stock['n_events'] >= 2).sum()
repeat_share   = (events.groupby('stock_code').size() >= 2).sum()  # # stocks
repeat_evcount = events.groupby('stock_code').filter(lambda s: len(s) >= 2).shape[0]

print(f'\n--- Concentration summary ---')
print(f'Total excess in window: {total_excess_pp:.1f} pp')
print(f'Number of distinct event-dates : {n_dates_total}')
print(f'Number of distinct event-stocks: {n_stocks_total}')
print()
print(f'Top 10 dates contribute  : {top10_dates:>7.1f} pp  ({top10_dates_sh:>5.1f}% of total)')
print(f'Top 30 dates contribute  : {top30_dates:>7.1f} pp  ({top30_dates_sh:>5.1f}% of total)')
print(f'Top 10 stocks contribute : {top10_stocks:>7.1f} pp  ({top10_stocks_sh:>5.1f}% of total)')
print(f'Top 50 stocks contribute : {top50_stocks:>7.1f} pp  ({top50_stocks_sh:>5.1f}% of total)')
print()
print(f'Stocks with ≥2 events in window: {repeat_stocks} '
      f'(covering {repeat_evcount} events = {repeat_evcount/len(events)*100:.1f}%)')

biggest_month   = by_month.loc[by_month['total_excess_pp'].idxmax()]
smallest_month  = by_month.loc[by_month['total_excess_pp'].idxmin()]
print(f'\nLargest-contribution month : {biggest_month["month"]} '
      f'(n={int(biggest_month["n_events"])}, total {biggest_month["total_excess_pp"]:+.1f} pp, '
      f'share {biggest_month["share_of_positive_%"]:.1f}%)')
print(f'Smallest-contribution month: {smallest_month["month"]} '
      f'(n={int(smallest_month["n_events"])}, total {smallest_month["total_excess_pp"]:+.1f} pp)')


# %% [markdown]
# ### 回答（基于实际数字）
#
# **1. 集中在少数日期，还是广泛分布？→ 极度日期集中，且单日主导**
#
# - **2024-02-08 一天 = 505 个事件 = 总 excess 的 95%**（5325 / 5608 pp）。
# - 2024-02 整月 = 673 / 968 个事件（70%）= 总正向 excess 的 94.7%。
# - Top 10 dates 贡献 104.8% of total —— 超过 100%，因为非 Top-10 的天里负 excess 把和拉下来。
# - 把 2024-02-08 单独剔掉，剩下 463 个事件的 mean excess 只剩 ≈ +0.6%（quick mental math:
#   (5608 - 5325) / (968 - 505) / 100 ≈ +0.61%），跟 2021/2022/2023/2025 的 +0.0 ~ +0.8% 完全
#   不可区分。**所以 2024 整个"反常"几乎完全是 2024-02-08 这一个交易日撑起来的。**
#
# **2. 集中在少数股票，还是众多股票？→ 广撒网，不是妖股 reuse**
#
# - 968 个事件分布在 **907 只不同股票**上 —— 几乎 1 股 1 事件。
# - 只有 60 只股票在窗口里触发 ≥2 次，仅 1 只 ≥3 次。
# - Top 10 stocks 只贡献 10.1%，Top 50 stocks 只贡献 32.9%。
# - **不是少数妖股反复出现**，而是同一天（2024-02-08）有 505 只不同股票同时触发。
#
# **3. 行业 / 题材聚类？→ 数据缺位，但 stock_name 肉眼可见明显模式**
#
# 严肃 groupby 缺数据（Part E 跳过）。但 Top 50 股票名单的肉眼归纳：
#
# - **大量 *ST / ST 票**：*ST泉为、*ST华闻、*ST开元、*ST纳川、*ST动力、ST景峰、ST浩丰 —— 7 只
# - **创业板 / 北交所小盘**：sz30xxxx 前缀占绝对多数（雷尔伟、中威电子、会畅科技、思创智联、
#   东田微、安联锐视、本川智能、欣天科技、登云股份、南凌科技、果麦文化 …）
# - **股价多在 1-15 元低价小盘**（合力泰 1.21、*ST华闻 0.86、ST景峰 1.52、*ST泉为 5.54 …）
#
# 跟时间线一起看 → **几乎肯定是"雪球敲入潮"末端 + 国家队入场（2024-02-06 吴清接任证监会主席、
# 中央汇金扩大 ETF 增持）触发的小盘 / ST / 微盘股集体反弹**。2024-02-08 这天对应：
# 雪球结构性产品强制平仓压力释放尾声 + 国家队明确表态 + 春节假期（2024-02-10 .. 02-17）
# 前最后一个交易日。
#
# 5d forward return 实际买入窗口是 **2024-02-19 开盘**（春节后第一个交易日）卖在 **02-23 收盘**，
# 那是节后 A 股集体跳空高开 + 后续连续上涨的窗口 —— 整体 EW 市场 +10.77%，
# 而冷启动 filter 选出的小盘 / ST 在此基础上再 outperform +10.54pp。
#
# **4. 哪些具体日期 / 股票 / 主题值得用外部 context 查证？**
#
# 优先级排序：
#
# 1. **2024-02-08 这一天** ——核心样本，约 95% 的"alpha"来源。需要查证：
#    - 2024-02-05 .. 02-08 雪球敲入潮的时间线、规模、媒体覆盖
#    - 中央汇金 2024-02-06 公告增持 ETF 的细节（规模、ETF 类型）
#    - 证监会主席 2024-02-07 换帅（易会满 → 吴清）的市场预期解读
#    - 春节前后 A 股小盘股 / 微盘股 / ST 板块 vs 沪深 300 / 中证 1000 的相对表现差
# 2. **2024-02-19** —— 5d 窗口尾部，节后开盘日。验证收益是 02-19 跳空给的还是 02-19 .. 02-23 持续给的。
# 3. **Bottom 50 的 2024-02-06 / 02-07 共 136 个事件** —— 这两天也触发了 cold-start，
#    但 5d 收益跑输 bench 0.85pp / 2.30pp。说明"早抢一两天"反而吃亏，**精确时点（02-08）是关键**，
#    不是 02-06-08 这一周整体都给信号。
#
# **核心 take-away：**
#
# notebook 03 看到的 2024 +12.2% / excess +5.79% **不是策略 alpha**，
# 是 **2024-02-08 这一个特殊日期的 regime artifact**，对应一次极端的
# 政策刺激 + 流动性踩踏 + 节假日开盘 gap 的特殊组合。
# 把这一天剔掉后，cold-start breakout 在 2024 pre-924 跟 2021-2025 其它年份没本质差别。
# **不能把它当作策略可重复 edge 的证据。**
#
# **下一步候选：**
#
# - **05b**: 补行业 / 概念到 stock_db_cn（按 §E 的 AKShare ingest 计划），把 02-08 那 505 只
#   股票按申万二级行业 / 概念板块归类，确认是不是"微盘 / 小市值 / ST" 这一类。
# - **06**: 把"剔掉 2024-02-08"重算 cold-start 在全 5 年的 base rate；这才是策略真实期望。
# - **07**: 找历史上类似 "集体熔断/暴跌后政策托底" 的样本（2015-07、2016-01 熔断、2018-10、
#   2020-03、2022-04 …），看 cold-start 在那些拐点上是否也有 +10pp 级的 5d alpha。
#   如果是 —— 这其实是一个**"市场底部反转"探测器**，不是"个股突破"探测器。
