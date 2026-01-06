# Watchlist 功能完整指南

## 功能概览

Watchlist 让你可以监控感兴趣的股票，追踪它们的表现。

### 核心功能
- ✅ 添加股票到 14 天监控列表
- ✅ 4 种仓位类型（Long/Short/Watch/Wishlist）
- ✅ 自动计算收益
- ✅ 按仓位类型过滤
- ✅ 每个用户独立的 watchlist

---

## 仓位类型

### 📈 Long（做多）
- **用途**: 看涨的股票
- **场景**: 你认为价格会上涨
- **颜色**: 绿色
- **示例**: "我觉得 AAPL 会涨"

### 📉 Short（做空）
- **用途**: 看跌的股票
- **场景**: 你认为价格会下跌
- **颜色**: 红色
- **示例**: "我觉得 XYZ 会跌"

### 👁️ Watch（观察）
- **用途**: 只是观察，没有明确方向
- **场景**: 研究阶段，等待信号
- **颜色**: 蓝色
- **示例**: "我在研究这只股票"

### ⭐ Wishlist（愿望清单）
- **用途**: 想买但还没买
- **场景**: 等待更好的入场价格
- **颜色**: 橙色
- **示例**: "等价格低一点再买"

---

## 如何使用

### 添加股票

1. **从每日推荐添加**：
   - 进入 "📊 Daily Picks" 标签页
   - 找到感兴趣的股票
   - 点击 "👁️ Watch" 按钮
   - **弹出窗口选择仓位类型**：
     - 📈 Long - 看涨
     - 📉 Short - 看跌
     - 👁️ Watch - 观察
     - ⭐ Wishlist - 愿望清单
   - 确认后添加成功

2. **系统会记录**：
   - 添加日期
   - 添加时的价格
   - 14 天目标日期
   - 仓位类型

### 查看 Watchlist

1. 进入 "👁️ My Watchlist" 标签页
2. 看到你的所有股票：
   - **Symbol**: 股票代码
   - **Position**: 仓位类型（带颜色徽章）
   - **Current Price**: 当前价格
   - **Added Price**: 添加时价格
   - **Change Since Add**: 添加后的涨跌幅
   - **Days Left**: 距离目标日期还有几天
   - **Notes**: 备注
   - **Actions**: 删除按钮 + Yahoo 链接

### 过滤 Watchlist

使用顶部的过滤按钮：
- **All Positions** - 显示所有
- **📈 Long Only** - 只显示做多
- **📉 Short Only** - 只显示做空
- **👁️ Watch Only** - 只显示观察
- **⭐ Wishlist Only** - 只显示愿望清单

**过滤是即时的，无需刷新页面！**

### 删除股票

1. 在 watchlist 表格中找到股票
2. 点击 "Remove" 按钮
3. 确认删除
4. Watchlist 自动刷新

---

## 使用场景

### 场景 1：日内交易者
```
上午 9:30:
- 看到 AAPL 在推荐列表（分数 65）
- 添加为 📈 Long（看涨）
- 看到 TSLA 也在列表
- 添加为 📉 Short（看跌）

查看 Watchlist:
- 点击 "📈 Long Only" → 只看做多仓位
- 点击 "📉 Short Only" → 只看做空仓位
```

### 场景 2：长期投资者
```
第 1 天:
- 发现 20 只有潜力的股票
- 全部添加为 ⭐ Wishlist

接下来 2 周:
- 每天查看 wishlist
- 研究每只股票
- 决定方向后改为 📈 Long 或 📉 Short

查看进度:
- 点击 "⭐ Wishlist Only" → 看哪些还在研究
- 点击 "📈 Long Only" → 看哪些已经决定买入
```

### 场景 3：研究阶段
```
发现有趣的股票:
- 添加为 👁️ Watch（观察模式）
- 监控 14 天
- 根据表现决定方向

决策后:
- 重新添加为 📈 Long 或 📉 Short
- 或者删除（不感兴趣了）
```

---

## 技术细节

### 数据计算

**Change Since Add（添加后涨跌）**:
```
Change % = ((Current Price - Added Price) / Added Price) × 100
```

例如：
- Added Price: $100
- Current Price: $105
- Change: +5.0%

**Days Remaining（剩余天数）**:
```
Days = Target Date - Today
```

颜色编码：
- **绿色**: > 7 天
- **橙色**: 4-7 天
- **红色**: ≤ 3 天（即将到期）

### 数据库结构

```sql
user_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,           -- 用户 ID
    symbol VARCHAR(20) NOT NULL,        -- 股票代码
    added_date DATE NOT NULL,           -- 添加日期
    target_date DATE,                   -- 目标日期（14 天后）
    notes TEXT,                         -- 备注
    position_type VARCHAR(20) NOT NULL, -- 仓位类型 ✨ NEW
    is_active BOOLEAN DEFAULT true,     -- 是否活跃
    UNIQUE (user_id, symbol)            -- 每个用户每只股票只能添加一次
)
```

---

## 常见问题

### Q: 可以添加同一只股票多次吗？
A: 不可以。每个用户每只股票只能添加一次。如果想改变仓位类型，需要先删除再重新添加。

### Q: 14 天后会自动删除吗？
A: 不会。14 天只是一个提醒期限，过期后仍然保留在 watchlist 中。你可以手动删除。

### Q: 如何改变仓位类型？
A: 目前需要先删除，然后重新添加并选择新的仓位类型。

### Q: Long 和 Short 只是标记，不会真的交易吧？
A: 对！这只是帮你记录你的观点，系统不会执行任何交易。

### Q: 其他用户能看到我的 watchlist 吗？
A: 不能。每个用户的 watchlist 是完全独立和私密的。

### Q: 可以添加多少只股票？
A: 没有限制。但建议不要超过 50 只，否则难以管理。

### Q: 数据多久更新一次？
A: 每次打开 watchlist 标签页时自动加载最新价格。价格数据来自数据库，更新频率取决于你运行 "Update Data" 的频率。

---

## 未来功能（计划中）

### 批量编辑
- 选择多只股票
- 批量更改仓位类型
- 批量删除

### 仓位分析
- "你有 5 Long, 2 Short, 3 Watch, 1 Wishlist"
- Long 仓位平均收益: +5.2%
- Short 仓位平均收益: -2.1%

### 快速操作
- 右键点击股票 → 更改仓位类型
- 拖拽股票到不同仓位分类

### 导出功能
- 导出所有 watchlist
- 只导出 Long 仓位
- 生成 Excel 报表

---

*功能上线日期：2026-01-06*
*仓位类型是 watchlist 的核心功能，充分利用它来管理你的股票！*
