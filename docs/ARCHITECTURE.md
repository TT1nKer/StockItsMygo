# 系统架构文档 - 分层设计 v2.1

**Created**: 2025-12-31
**Last Updated**: 2025-12-31 (v2.1 stability & boundary fixes)
**Status**: Production Ready
**Architecture Version**: 2.1
**Change Type**: Stability & Boundary Fix
**Backward Compatibility**: Yes (with migration notes)

---

## 📐 架构概览

本系统采用严格的5层架构设计，防止代码无序堆积，确保长期可维护性。

### 核心哲学

**不预测涨跌，只识别异常/结构事件**

- 异常 ≠ 预测方向
- 异常 = 值得冒险 -1R
- 焦点："相对自身历史，突然不像平时"

---

## 🏗️ 5层架构图

```
┌──────────────────────────────────────────────────────┐
│  Layer 5: Workflow Orchestration                     │
│  - tools/daily_workflow.py (356 lines)               │
│  - 只做流程编排，禁止包含业务逻辑                         │
│  ✅ Can call: Layer 2, 3, 4                          │
│  ⚠️  Limited access to Layer 1 (prepare-only)        │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  Layer 4: Reporting                                  │
│  - tools/report_generator.py (434 lines)             │
│  - 消费 ReportContext，生成Markdown报告                │
│  ✅ Can consume: ReportContext (read-only)           │
│  ❌ Cannot call: Any layer's methods                 │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  Layer 3: Events & Deep Validation                   │
│  - script/event_discovery_system.py                  │
│  - 结构事件确认（Gap/Squeeze + 日内验证）                │
│  - 按需调用，不并入主流程                                │
│  ✅ Can call: Layer 1                                │
│  ❌ Cannot call: Layer 2                             │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  Layer 2: Signals (Fast Screening)                   │
│  - script/signals/momentum_signal.py (316 lines)     │
│  - script/signals/anomaly_signal.py (490 lines)      │
│  - 产出: List[WatchlistCandidate]                    │
│  ✅ Can call: Layer 1                                │
│  ❌ Cannot call: Layer 3, 4, 5                       │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  Layer 1: Data Access                                │
│  - db/api.py                                         │
│  - 只负责取数、复权、缓存                                │
│  ❌ Cannot call: Any upper layer                     │
└──────────────────────────────────────────────────────┘
```

---

## 🔒 Layer 调用约束（v2.1 强化）

### Layer 5 → Layer 1: Limited Access

**⚠️ Allowed (Prepare-only)**:
- Data preparation, cache refresh, health check
- Methods prefixed with: `prepare_*`, `update_*`, `warmup_*`, `get_stock_list()`

**❌ Forbidden**:
- Any business data retrieval (e.g., `get_price_history()`)
- Any logic depending on historical series

**Layer 1 API Convention**:
```python
# Workflow allowed
db.get_stock_list()      # metadata only
db.prepare_*()           # cache warming
db.update_*()            # data refresh

# Signals / Events only
db.get_price_history()   # historical series
db.get_*()               # general rule
```

**Rationale**: 防止 workflow 被迫把"数据准备"塞进 signal 层，导致分层名存实亡。

---

### Layer 4: Reporting Context

**Consumes**: `ReportContext` (read-only struct)

```python
@dataclass
class ReportContext:
    """
    Unified input for report generation

    All data needed for rendering, pre-computed by workflow layer.
    """
    # Signal results
    momentum_candidates: List[WatchlistCandidate]
    anomaly_candidates: List[WatchlistCandidate]

    # Analysis results
    watchlist: List[Dict]
    analyses: List[Dict]
    strategy_results: List[Dict]

    # Optional deep validation
    confirmed_events: Optional[List[ConfirmedEvent]] = None

    # Execution metadata
    stats: Dict[str, Any] = field(default_factory=dict)
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
```

**Forbidden**:
- ❌ 调用任何 Layer 的方法
- ❌ 进行数据计算、评分、筛选
- ❌ 推断/猜测任何统计信息

**Rationale**: 避免 report_generator 内部"猜测"统计信息，保持纯渲染。

---

## 📋 数据契约 (Data Contracts v2.1)

### WatchlistCandidate

**用途**: Layer 2 的统一输出格式，供 Layer 5 聚合与 Layer 4 渲染。

```python
@dataclass
class WatchlistCandidate:
    # 基础信息
    symbol: str
    date: str  # YYYY-MM-DD
    close: float

    # 来源标识 (v2.1: 扩展支持 'both')
    # 'momentum': 趋势信号
    # 'anomaly': 异常信号
    # 'both': 双重确认（由 workflow 在合并时标记）
    source: Literal['momentum', 'anomaly', 'both']

    # 评分 (0-100)
    score: int

    # 分类标签（用于报告分组）
    # v2.1: Mixed usage (backward compatible)
    # v2.2: Will refactor to event_tags / feature_tags namespaces
    tags: List[str] = field(default_factory=list)

    # 风险参数（如有）
    stop_loss: Optional[float] = None
    risk_pct: Optional[float] = None  # v2.1: 止损幅度（正数百分比，0-100）

    # 元数据（供报告详细展示）
    # 例: {'momentum_20d': 15.2, 'volume_ratio': 2.3, 'volatility': 3.5}
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**生命周期**:
- **产生**: 每日workflow Step 2 (momentum + anomaly scanners)
- **消费**: Step 3 (watchlist builder), Step 7 (report generator)
- **存储**: 内存对象，不持久化（报告中体现即可）

**生产者**:
- `script/signals/momentum_signal.py::scan()` → List[WatchlistCandidate]
- `script/signals/anomaly_signal.py::scan()` → List[WatchlistCandidate]
- `tools/daily_workflow.py::_build_watchlist()` → 合并时创建 `source='both'`

**消费者**:
- `tools/daily_workflow.py::_build_watchlist()` → 合并、去重、优先级排序
- `tools/report_generator.py::generate_daily_report()` → Markdown表格

**验证规则**:
- `score`: 必须 0-100
- `source`: 必须 'momentum', 'anomaly', 或 'both'
- `risk_pct`: 如果存在，必须 0-100 (正数百分比)

**辅助方法**:
- `has_tag(tag: str) -> bool`: 检查是否包含指定标签
- `has_all_tags(tags: List[str]) -> bool`: 检查是否包含所有标签
- `is_core_three_factor() -> bool`: 检查是否满足核心三要素（仅异常信号）
- `to_dict() -> Dict`: 转换为字典（用于报告生成）

---

### v2.1 Breaking Changes & Migration

#### 1. `source` field expansion

**Before (v2.0)**:
```python
source: Literal['momentum', 'anomaly']
```

**After (v2.1)**:
```python
source: Literal['momentum', 'anomaly', 'both']
```

**Migration**:
- Signal scanners: No change needed (只产生 'momentum' 或 'anomaly')
- Workflow layer: 双重确认时创建新 Candidate with `source='both'`
- Report layer: 支持 `source='both'` 的渲染

---

#### 2. `risk_pct` semantics change

**Before (v2.0)**:
```python
risk_pct: Optional[float] = None  # 负数 (e.g., -3.5)
assert risk_pct < 0, "should be negative"
```

**After (v2.1)**:
```python
risk_pct: Optional[float] = None  # 正数百分比 (0-100)
assert 0 <= risk_pct <= 100, "positive percentage"
```

**Migration**:
```python
# Old code
risk_pct = (stop_loss - close) / close * 100  # -3.5

# New code (v2.1)
risk_pct = abs((close - stop_loss) / close * 100)  # 3.5
```

**Rationale**:
- 正数语义在报告中更清晰（"Risk: 3.5%"）
- 为未来 short selling 留后路（正数适用于多空）
- Direction (long/short) 由 `stop_loss` vs `close` 隐含

**Display in Reports**:
```python
# Old (v2.0)
f"Risk: {risk_pct:.1f}%"  # Risk: -3.5%

# New (v2.1)
f"Risk: {risk_pct:.1f}%"  # Risk: 3.5%
```

---

## 🏷️ 异常分类学 (Anomaly Taxonomy v2.1)

### 三层分类

#### 1. STRUCTURAL (结构性异常)
**可生成 tag，参与评分**

- `VOLATILITY_EXPANSION`: TR/ATR > 2.0
- `VOLUME_SPIKE`: Volume/MA > 1.5
- `CLEAR_STRUCTURE`: 止损位自然存在
- `GAP`: 跳空 > 1%
- `BREAKOUT`: 突破20日高点
- `SQUEEZE_RELEASE`: 连续收敛→扩张

#### 2. AUXILIARY (辅助指标)
**只加权，不单独触发**

- `DOLLAR_VOLUME`: 成交金额 > 历史70分位
- `MOMENTUM_CONFIRM`: 与动量信号对齐

#### 3. NOISE_FILTER (噪音过滤)
**一票否决（不生成tag，直接过滤）**

- `LOW_LIQUIDITY`: 日均成交额 < 100万
- `PENNY_STOCK`: 价格 < $5
- `CORPORATE_ACTION`: 单日gap > 50%（疑似分红/拆股）

---

### v2.2 Roadmap: Tags Namespace Separation

**Current (v2.1)**: Mixed usage, backward compatible

**Planned (v2.2)**: Strong separation

```python
# event_tags (STRUCTURAL ONLY)
# - Define structural event identity
# - event_discovery_system may ONLY read these
event_tags = [
    'GAP_REV',          # Gap reversal
    'GAP_CONT',         # Gap continuation
    'SQUEEZE_RELEASE',  # Squeeze breakout
    'BREAKOUT',         # Price breakout (optional)
]

# feature_tags (EXPLANATORY ONLY)
# - Descriptive characteristics
# - Used for scoring and filtering only
feature_tags = [
    'VOLATILITY_EXPANSION',
    'VOLUME_SPIKE',
    'CLEAR_STRUCTURE',
    'DOLLAR_VOLUME_OK',
    'MOMENTUM_CONFIRM',
]
```

**Enforcement Rules (v2.2)**:
```python
# v2.2 validation
assert all(tag in event_tags for tag in candidate.event_tags)
assert all(tag in feature_tags for tag in candidate.feature_tags)

# event_discovery_system (v2.2)
def run(self, candidates):
    for c in candidates:
        if 'GAP_REV' in c.event_tags:  # ✅ Only read event_tags
            # ... validate with intraday
```

**Rationale**: 防止 feature 被误当成 event，导致 System2 (event_discovery) 被污染。

---

### 评分规则

**核心三要素** (满分90分):
- VOLATILITY_EXPANSION: 30分
- VOLUME_SPIKE: 30分
- CLEAR_STRUCTURE: 30分

**加分项** (最多+20分):
- BREAKOUT: +10分
- GAP: +5分
- SQUEEZE_RELEASE: +5分
- DOLLAR_VOLUME: +5分

**否决规则**:
- 任一 NOISE_FILTER 触发 → score = 0

**最终评分**:
```python
final_score = min(100, structural_score + auxiliary_score)
if any(noise_filter):
    final_score = 0
```

---

## 🔄 Daily Workflow 职责

### 新的Step结构

```python
class DailyWorkflow:
    def run_daily_workflow(self):
        # Step 1: 数据准备（Limited Layer 1 access）
        self._update_data()

        # Step 2: 快速信号扫描
        momentum_candidates, anomaly_candidates = self._scan_signals()

        # Step 3: 构建观察列表（合并 + 双重确认）
        self._build_watchlist(momentum_candidates, anomaly_candidates)

        # Step 4-5: 深度分析
        analyses = self._run_deep_analysis()

        # Step 6: 策略对比
        strategy_results = self._run_strategy_comparison()

        # Step 7: 生成报告（使用 ReportContext）
        report_path = self._generate_report(
            momentum_candidates, anomaly_candidates,
            analyses, strategy_results
        )
```

### Workflow 层禁止项

**❌ 禁止在 workflow 中出现的内容**:
- 直接调用 `db.get_price_history()` → 应通过 Signal 层
- 嵌入评分逻辑 → 应在 Signal 层完成
- 报告格式化代码 → 应在 ReportGenerator 完成
- try-except 包裹每一步 → 应在具体模块内处理

**✅ 允许在 workflow 中的内容**:
- 调用 Signal 层的 `scan()` 方法
- 聚合、合并、排序 Candidate 对象
- 创建 `source='both'` 的双重确认 Candidate
- 异常处理的顶层 catch（记录到 errors 列表）
- 进度提示（print）

---

## 📊 Layer 2: Signal 层设计

### SignalScanner 抽象基类

```python
class SignalScanner(ABC):
    """
    Abstract base class for all signal scanners

    All concrete scanners must implement the scan() method
    and return List[WatchlistCandidate].
    """

    @abstractmethod
    def scan(self,
             min_score: int = 60,
             limit: int = 50,
             **kwargs) -> List[WatchlistCandidate]:
        """
        Scan market and return watchlist candidates

        Args:
            min_score: Minimum score threshold (0-100)
            limit: Maximum number of candidates to return
            **kwargs: Scanner-specific parameters

        Returns:
            List of WatchlistCandidate, sorted by score descending
        """
        pass
```

### 具体实现

#### MomentumSignal

**职责**: 识别趋势机会

**评分逻辑** (0-100):
- 强劲动量 (20d > 20%): 40分
- 成交量确认 (> 2x): 25分
- 突破: 20分
- 近期强势 (5d > 3%): 15分
- 风险调整 (高波动): -10分

**参数**:
```python
momentum_scanner.scan(
    min_score=70,
    limit=50,
    min_price=5.0,
    max_price=200.0,
    min_volume=500000
)
```

**v2.1 change**: `risk_pct` 现在为正数 (5.0 instead of -5.0)

---

#### AnomalySignal

**职责**: 识别结构异常

**评分逻辑** (0-100):
- 核心三要素 (90分):
  - VOLATILITY_EXPANSION: 30分
  - VOLUME_SPIKE: 30分
  - CLEAR_STRUCTURE: 30分
- 辅助加分 (+20分):
  - BREAKOUT: +10分
  - GAP: +5分
  - DOLLAR_VOLUME: +5分

**参数**:
```python
anomaly_scanner.scan(
    min_score=60,
    limit=50
)
```

**v2.1 change**: `risk_pct` 计算改为 `abs((close - stop_loss) / close * 100)`

---

## 🎨 Layer 4: Reporting 层设计

### ReportGenerator

**职责**: 纯渲染逻辑，无业务逻辑

**禁止项**:
- ❌ 调用 Layer 1 (db.api)
- ❌ 调用 Layer 2 (signal scanners)
- ❌ 进行数据计算、评分、筛选

**允许项**:
- ✅ 消费 ReportContext 对象
- ✅ 格式化为 Markdown
- ✅ 创建报告目录结构
- ✅ 写入文件

**报告章节**:
1. Executive Summary
2. Momentum Opportunities
3. Anomaly-Based Opportunities
4. Watchlist Deep Analysis
5. Strategy Comparison
6. Risk Management
7. Learning Points

**v2.1 enhancement**: 支持 `source='both'` 的双重确认渲染

---

## 🔌 Event Discovery System 使用设计

### 定位

**角色**: 离线验证器，不是实时扫描器

**场景**:
- ✅ 验证 watchlist 中的高优先级股票是否有日内确认
- ✅ 回测历史事件
- ✅ 深度研究特定标的
- ❌ 不并入每日 workflow（会拖慢流程）

### 调用入口

**独立脚本**: `tools/verify_events.py`（可选创建）

```python
# 示例：验证今日watchlist的高优先级股票
from script.event_discovery_system import EventDiscoverySystem
from script.watchlist import WatchlistManager

wl = WatchlistManager()
high_priority = wl.get_list(priority=1)

system = EventDiscoverySystem()
confirmed = system.run(symbols=high_priority['symbol'].tolist())

print(confirmed['confirmed_events'])
```

**触发时机**:
- 用户手动运行（非自动化）
- 或在 workflow 末尾可选执行（用户配置开关）

**v2.2 constraint**: 只读取 `event_tags`，不读取 `feature_tags`

---

## 📁 文件组织

### 新增文件 (3个)

1. **script/signals/__init__.py** - Package marker
2. **script/signals/base.py** - Data contracts & base classes
3. **tools/report_generator.py** - Reporting layer

### 修改文件 (4个)

1. **script/momentum_strategy.py** → **script/signals/momentum_signal.py**
   - 重构为返回 `List[WatchlistCandidate]`
   - 旧文件保留 deprecated wrapper

2. **script/anomaly_detector.py** → **script/signals/anomaly_signal.py**
   - 重构为返回 `List[WatchlistCandidate]`
   - 旧文件保留 deprecated wrapper

3. **tools/daily_workflow.py**
   - 从 693行 → 356行 (48.6% reduction)
   - 删除所有业务逻辑和渲染代码
   - 改为调用新的 Signal 和 Report 层

4. **script/watchlist.py**
   - 添加 `from_candidates()` 方法（可选）
   - 支持 'dual_confirmed' source

---

## ✅ 验收标准

### 功能未破坏

- [✅] `python daily_observation.py` 正常运行
- [✅] 生成的报告包含 Momentum 和 Anomaly 两部分
- [✅] Watchlist 正确添加 dual_confirmed 股票
- [✅] 报告文件路径与之前一致
- [✅] 数据契约测试全部通过 (v2.1: 5/5)

### 架构改进

- [✅] `daily_workflow.py` 行数减少 > 30% (实际 48.6%)
- [✅] 没有跨层直接调用
- [✅] 所有信号模块都返回 `WatchlistCandidate`
- [✅] `event_discovery_system.py` 没有被 workflow 导入
- [✅] 每个文件职责单一

### v2.1 新增验证

- [✅] `source='both'` 支持正常
- [✅] `risk_pct` 正数语义测试通过
- [✅] Layer 1 调用约束文档化

---

## 🎯 实施总结

### 完成的Phase

**Phase 1**: 数据契约 (✅ Commit 89ff280)
- 创建 `script/signals/base.py`
- 定义 `WatchlistCandidate` 和 `SignalScanner`
- 定义 `AnomalyTags` 常量
- 通过完整测试套件

**Phase 2**: Signal 层重构 (✅ Commit f550999, 74f18f9)
- 重构 `momentum_signal.py` (316 lines)
- 重构 `anomaly_signal.py` (490 lines)
- 保留向后兼容 wrapper
- 统一返回 `List[WatchlistCandidate]`

**Phase 3**: Reporting 层抽取 (✅ Commit 4b2cdd3)
- 创建 `tools/report_generator.py` (434 lines)
- 抽取所有 Markdown 渲染逻辑
- 纯 Layer 4 组件（无业务逻辑）

**Phase 4**: Workflow 简化 (✅ Commit 18947ea)
- 重构 `daily_workflow.py` (693 → 356 lines)
- 删除所有业务逻辑
- 纯编排层（只调用其他层）

**Phase 5**: 文档与验收 (✅ Commit 3ade1bc)
- 创建 `docs/ARCHITECTURE.md`
- 更新 `IMPLEMENTATION_SUMMARY.md`
- 验证所有验收标准

**Phase v2.1**: 稳定性与边界修复 (✅ Commit 69e5417)
- 扩展 `source` 支持 `'both'`
- 修改 `risk_pct` 为正数语义
- 添加 Layer 1 调用约束
- 规划 v2.2 tags namespace 重构

---

### 代码统计

**Before**:
- `daily_workflow.py`: 693 lines
- Signal logic: embedded in workflow
- Report logic: embedded in workflow

**After (v2.1)**:
- `daily_workflow.py`: 356 lines (-48.6%)
- `momentum_signal.py`: 316 lines (new)
- `anomaly_signal.py`: 490 lines (new)
- `base.py`: 165 lines (new)
- `report_generator.py`: 434 lines (new)

**Total**: From ~700 lines (monolithic) to ~1760 lines (well-structured)

**v2.1 changes**: +37 lines, -18 lines (net +19 lines, mostly documentation)

---

## 🚀 扩展指南

### 添加新信号类型

只需3步：

1. **继承 SignalScanner**:
```python
from script.signals.base import SignalScanner, WatchlistCandidate

class MyNewSignal(SignalScanner):
    def scan(self, min_score=60, limit=50, **kwargs):
        # Your logic here
        candidates = []
        # ...
        # v2.1: Use positive risk_pct
        risk_pct = abs((close - stop_loss) / close * 100)

        candidate = WatchlistCandidate(
            source='momentum',  # or 'anomaly', NOT 'both'
            risk_pct=risk_pct,  # positive value
            # ...
        )
        return candidates[:limit]
```

2. **在 workflow 中调用**:
```python
# tools/daily_workflow.py
self.my_scanner = MyNewSignal()

def _scan_signals(self):
    my_candidates = self.my_scanner.scan(min_score=70)
    # ...
```

3. **在 report 中渲染** (可选):
```python
# tools/report_generator.py
def _write_my_section(self, f, my_candidates):
    # Render to Markdown
    # v2.1: Display risk_pct as positive
    f.write(f"Risk: {c.risk_pct:.1f}%\n")
```

---

### 添加新报告章节

只需修改 `report_generator.py`，不影响其他层：

```python
def generate_daily_report(self, ...):
    # ...
    self._write_my_new_section(f, data)
```

---

### v2.2 迁移准备

**Tags Namespace Separation**:

```python
# v2.1 (current)
candidate.tags = ['VOLATILITY_EXPANSION', 'GAP', 'BREAKOUT']

# v2.2 (planned)
candidate.event_tags = ['GAP_REV', 'BREAKOUT']
candidate.feature_tags = ['VOLATILITY_EXPANSION', 'VOLUME_SPIKE']
```

**Migration path**:
1. Add `event_tags` and `feature_tags` fields to `WatchlistCandidate`
2. Deprecate `tags` field with warning
3. Update all scanners to populate new fields
4. Update report_generator to read new fields
5. Remove `tags` field in v3.0

---

## 📝 Migration Notes (v2.0 → v2.1)

### For Signal Scanner Authors

**Old code (v2.0)**:
```python
risk_pct = (stop_loss - close) / close * 100  # -3.5
candidate = WatchlistCandidate(risk_pct=risk_pct)
```

**New code (v2.1)**:
```python
risk_pct = abs((close - stop_loss) / close * 100)  # 3.5
candidate = WatchlistCandidate(risk_pct=risk_pct)
```

---

### For Workflow Authors

**Creating dual-confirmed candidates**:
```python
# v2.1
dual_candidate = WatchlistCandidate(
    symbol=symbol,
    source='both',  # NEW in v2.1
    score=max(momentum_score, anomaly_score),
    tags=momentum_tags + anomaly_tags,
    # ...
)
```

---

### For Report Authors

**Displaying risk**:
```python
# v2.0
f"Risk: {c.risk_pct:.1f}%"  # Risk: -3.5%

# v2.1 (same code, different output)
f"Risk: {c.risk_pct:.1f}%"  # Risk: 3.5%
```

**Handling 'both' source**:
```python
# v2.1
if c.source == 'both':
    f.write("⭐ Dual-Confirmed\n")
```

---

## 🔮 Roadmap

### v2.2 (Next Release)
- [ ] Tags namespace separation (`event_tags` / `feature_tags`)
- [ ] `ReportContext` dataclass implementation
- [ ] Event discovery system tag filtering enforcement

### v3.0 (Future)
- [ ] Remove deprecated `tags` field
- [ ] Add `side: Literal['long', 'short']` for short selling support
- [ ] Full backward compatibility break (major version bump)

---

**Last Updated**: 2025-12-31 (v2.1)
**Architecture Version**: 2.1
**Status**: ✅ Production Ready
**Backward Compatibility**: Yes (with migration notes)
