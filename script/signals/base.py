"""
Signal Layer Base Classes and Data Contracts

Defines the standard interface for all signal scanners and the unified output format.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
from abc import ABC, abstractmethod


@dataclass
class WatchlistCandidate:
    """
    Unified output format for all signal scanners (Layer 2)

    Lifecycle:
    - Produced: Daily workflow Step 2, 2.5
    - Consumed: Step 3 (watchlist builder), Step 7 (report generator)
    - Storage: In-memory only, not persisted

    Philosophy: Represents a "worth-risking-1R" opportunity, not a prediction
    """

    # 基础信息
    symbol: str
    date: str  # YYYY-MM-DD
    close: float

    # 来源标识
    source: Literal['momentum', 'anomaly']

    # 评分 (0-100)
    score: int

    # 分类标签（用于报告分组）
    # STRUCTURAL tags: VOLATILITY_EXPANSION, VOLUME_SPIKE, CLEAR_STRUCTURE,
    #                  GAP, BREAKOUT, SQUEEZE_RELEASE
    # AUXILIARY tags: DOLLAR_VOLUME, MOMENTUM_CONFIRM
    tags: List[str] = field(default_factory=list)

    # 风险参数（如有）
    stop_loss: Optional[float] = None
    risk_pct: Optional[float] = None  # 止损百分比

    # 元数据（供报告详细展示）
    # 例: {'momentum_20d': 15.2, 'volume_ratio': 2.3, 'volatility': 3.5}
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据有效性"""
        assert 0 <= self.score <= 100, f"Score must be 0-100, got {self.score}"
        assert self.source in ['momentum', 'anomaly'], f"Invalid source: {self.source}"

        if self.risk_pct is not None:
            assert self.risk_pct < 0, "risk_pct should be negative (e.g., -3.5)"

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


class SignalScanner(ABC):
    """
    Abstract base class for all signal scanners

    All concrete scanners must implement the scan() method
    and return List[WatchlistCandidate].

    Layer constraints:
    - ✅ Can call Layer 1 (db.api) for data access
    - ❌ Cannot call Layer 3 (event_discovery_system)
    - ❌ Cannot call Layer 4 (report_generator)
    - ❌ Cannot call Layer 5 (daily_workflow)
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

        Raises:
            Should handle errors internally and return empty list if needed
        """
        pass

    def get_name(self) -> str:
        """返回扫描器名称"""
        return self.__class__.__name__


# Anomaly taxonomy constants
class AnomalyTags:
    """Anomaly classification taxonomy"""

    # STRUCTURAL (结构性异常) - 可生成 tag，参与评分
    VOLATILITY_EXPANSION = 'VOLATILITY_EXPANSION'  # TR/ATR > 2.0
    VOLUME_SPIKE = 'VOLUME_SPIKE'                  # Volume/MA > 1.5
    CLEAR_STRUCTURE = 'CLEAR_STRUCTURE'            # 止损位自然存在
    GAP = 'GAP'                                    # 跳空 > 1%
    BREAKOUT = 'BREAKOUT'                          # 突破20日高点
    SQUEEZE_RELEASE = 'SQUEEZE_RELEASE'            # 连续收敛→扩张

    # AUXILIARY (辅助指标) - 只加权，不单独触发
    DOLLAR_VOLUME = 'DOLLAR_VOLUME'                # 成交金额 > 历史70分位
    MOMENTUM_CONFIRM = 'MOMENTUM_CONFIRM'          # 与动量信号对齐

    # NOISE_FILTER (噪音过滤) - 一票否决（不生成tag，直接过滤）
    # LOW_LIQUIDITY, PENNY_STOCK, CORPORATE_ACTION

    @classmethod
    def get_structural_tags(cls) -> List[str]:
        """返回所有结构性标签"""
        return [
            cls.VOLATILITY_EXPANSION,
            cls.VOLUME_SPIKE,
            cls.CLEAR_STRUCTURE,
            cls.GAP,
            cls.BREAKOUT,
            cls.SQUEEZE_RELEASE
        ]

    @classmethod
    def get_auxiliary_tags(cls) -> List[str]:
        """返回所有辅助标签"""
        return [
            cls.DOLLAR_VOLUME,
            cls.MOMENTUM_CONFIRM
        ]
