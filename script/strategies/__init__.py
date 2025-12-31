"""
Strategies Package
策略包

包含各种交易策略的实现

Available Strategies:
- MomentumStrategy: 动量策略（适合趋势行情）
- MeanReversionStrategy: 均值回归策略（适合震荡行情）
- BreakoutStrategy: 突破策略（适合关键位突破）
- ValueStrategy: 价值策略（适合长线投资）
- CustomStrategy: 自定义策略模板
"""

from script.strategies.momentum import MomentumStrategy
from script.strategies.mean_reversion import MeanReversionStrategy
from script.strategies.breakout import BreakoutStrategy

__all__ = [
    'MomentumStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',
]
