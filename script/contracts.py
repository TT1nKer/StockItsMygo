"""
Data Contracts (Layer-agnostic)

Unified data structures used across all layers.
Isolated from business logic to prevent coupling.

Version: v2.1.1
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal


@dataclass
class WatchlistCandidate:
    """
    Unified output format for all signal scanners (Layer 2)

    Lifecycle:
    - Produced: Daily workflow Step 2 (momentum + anomaly scanners)
    - Consumed: Step 3 (watchlist builder), Step 7 (report generator)
    - Storage: In-memory only, not persisted

    Philosophy: Represents a "worth-risking-1R" opportunity, not a prediction
    """

    # 基础信息
    symbol: str
    date: str  # YYYY-MM-DD
    close: float

    # 来源标识
    # 'momentum': 趋势信号
    # 'anomaly': 异常信号
    # 'both': 双重确认（由 workflow 在合并时标记）
    source: Literal['momentum', 'anomaly', 'both']

    # 评分 (0-100)
    score: int

    # 分类标签（用于报告分组）
    # TODO v2.2: Refactor to separate event_tags / feature_tags namespaces
    # - event_tags (STRUCTURAL EVENTS): GAP_REV, GAP_CONT, SQUEEZE_RELEASE, BREAKOUT
    # - feature_tags (STRUCTURAL FEATURES): VOLATILITY_EXPANSION, VOLUME_SPIKE, CLEAR_STRUCTURE, DOLLAR_VOLUME, MOMENTUM_CONFIRM
    # Current (v2.1): Mixed usage, backward compatible
    tags: List[str] = field(default_factory=list)

    # 风险参数（如有）
    stop_loss: Optional[float] = None
    risk_pct: Optional[float] = None  # 止损幅度（正数百分比，0-100）

    # 元数据（供报告详细展示）
    # 例: {'momentum_20d': 15.2, 'volume_ratio': 2.3, 'volatility': 3.5}
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据有效性"""
        assert 0 <= self.score <= 100, f"Score must be 0-100, got {self.score}"
        assert self.source in ['momentum', 'anomaly', 'both'], f"Invalid source: {self.source}"

        if self.risk_pct is not None:
            assert 0 <= self.risk_pct <= 100, f"risk_pct must be 0-100 (positive percentage), got {self.risk_pct}"

    def has_tag(self, tag: str) -> bool:
        """检查是否包含指定标签"""
        return tag in self.tags

    def has_all_tags(self, tags: List[str]) -> bool:
        """检查是否包含所有指定标签"""
        return all(tag in self.tags for tag in tags)

    def is_core_three_factor(self) -> bool:
        """检查是否满足核心三要素（仅异常信号）"""
        if self.source != 'anomaly':
            return False
        return self.has_all_tags(['VOLATILITY_EXPANSION', 'VOLUME_SPIKE', 'CLEAR_STRUCTURE'])

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于报告生成）"""
        return {
            'symbol': self.symbol,
            'date': self.date,
            'close': self.close,
            'source': self.source,
            'score': self.score,
            'tags': self.tags,
            'stop_loss': self.stop_loss,
            'risk_pct': self.risk_pct,
            'metadata': self.metadata
        }


# Anomaly taxonomy constants
class AnomalyTags:
    """
    Anomaly classification taxonomy (v2.1.1)

    Two semantic categories (will be separated in v2.2):
    - STRUCTURAL EVENTS: Define event identity (for event_discovery_system)
    - STRUCTURAL FEATURES: Descriptive characteristics (for scoring only)
    """

    # STRUCTURAL EVENTS (结构性事件) - Will become event_tags in v2.2
    # These define what happened, not why
    GAP = 'GAP'                                    # 跳空 > 1%
    BREAKOUT = 'BREAKOUT'                          # 突破20日高点
    SQUEEZE_RELEASE = 'SQUEEZE_RELEASE'            # 连续收敛→扩张

    # STRUCTURAL FEATURES (结构性特征) - Will become feature_tags in v2.2
    # These describe characteristics, used for scoring
    VOLATILITY_EXPANSION = 'VOLATILITY_EXPANSION'  # TR/ATR > 2.0
    VOLUME_SPIKE = 'VOLUME_SPIKE'                  # Volume/MA > 1.5
    CLEAR_STRUCTURE = 'CLEAR_STRUCTURE'            # 止损位自然存在

    # AUXILIARY (辅助指标) - Will remain as feature_tags in v2.2
    # Only add weight, don't trigger alone
    DOLLAR_VOLUME = 'DOLLAR_VOLUME'                # 成交金额 > 历史70分位
    MOMENTUM_CONFIRM = 'MOMENTUM_CONFIRM'          # 与动量信号对齐

    # NOISE_FILTER (噪音过滤) - Not stored as tags
    # One-vote veto, filtered before creating WatchlistCandidate
    # LOW_LIQUIDITY, PENNY_STOCK, CORPORATE_ACTION

    @classmethod
    def get_event_tags(cls) -> List[str]:
        """
        返回事件标签（v2.2 将分离）

        These will be read by event_discovery_system
        """
        return [
            cls.GAP,
            cls.BREAKOUT,
            cls.SQUEEZE_RELEASE
        ]

    @classmethod
    def get_feature_tags(cls) -> List[str]:
        """
        返回特征标签（v2.2 将分离）

        These are for scoring and filtering only
        """
        return [
            cls.VOLATILITY_EXPANSION,
            cls.VOLUME_SPIKE,
            cls.CLEAR_STRUCTURE,
            cls.DOLLAR_VOLUME,
            cls.MOMENTUM_CONFIRM
        ]

    @classmethod
    def get_structural_tags(cls) -> List[str]:
        """返回所有结构性标签（v2.1 兼容方法）"""
        return cls.get_event_tags() + [
            cls.VOLATILITY_EXPANSION,
            cls.VOLUME_SPIKE,
            cls.CLEAR_STRUCTURE
        ]

    @classmethod
    def get_auxiliary_tags(cls) -> List[str]:
        """返回所有辅助标签"""
        return [
            cls.DOLLAR_VOLUME,
            cls.MOMENTUM_CONFIRM
        ]
