"""
Strategy Manager
策略管理器

功能:
- 列出所有可用策略
- 加载和切换策略
- 比较不同策略的表现
- 策略组合
- 策略回测 (TODO)

使用示例:
    from script.strategy_manager import StrategyManager

    # 列出所有策略
    mgr = StrategyManager()
    mgr.list_strategies()

    # 使用单个策略
    strategy = mgr.get_strategy('momentum')
    signal = strategy.analyze('AAPL')

    # 使用策略组合
    combo = mgr.create_combo(['momentum', 'mean_reversion'], weights=[0.6, 0.4])
    signal = combo.analyze('AAPL')

    # 比较策略
    results = mgr.compare_strategies('AAPL', ['momentum', 'mean_reversion', 'breakout'])
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from script.strategy_base import BaseStrategy, StrategyComposer
from script.strategies.momentum import MomentumStrategy
from script.strategies.mean_reversion import MeanReversionStrategy
from script.strategies.breakout import BreakoutStrategy
from typing import List, Dict
import pandas as pd


class StrategyManager:
    """策略管理器"""

    def __init__(self):
        """初始化策略管理器"""
        self.available_strategies = {
            'momentum': {
                'class': MomentumStrategy,
                'name': 'Momentum Strategy',
                'description': 'Buy strong trending stocks in bull markets',
                'best_for': 'Bull markets, uptrends'
            },
            'mean_reversion': {
                'class': MeanReversionStrategy,
                'name': 'Mean Reversion Strategy',
                'description': 'Buy oversold stocks in ranging markets',
                'best_for': 'Ranging markets, consolidation'
            },
            'breakout': {
                'class': BreakoutStrategy,
                'name': 'Breakout Strategy',
                'description': 'Buy breakouts from consolidation or key resistance',
                'best_for': 'Post-consolidation, key resistance levels'
            }
        }

    def list_strategies(self):
        """列出所有可用策略"""
        print("=" * 80)
        print("Available Strategies")
        print("=" * 80)
        print()

        for key, info in self.available_strategies.items():
            print(f"[{key}]")
            print(f"  Name: {info['name']}")
            print(f"  Description: {info['description']}")
            print(f"  Best for: {info['best_for']}")
            print()

        print("Usage:")
        print("  strategy = mgr.get_strategy('momentum')")
        print("  signal = strategy.analyze('AAPL')")
        print()

    def get_strategy(self, strategy_name: str, params: Dict = None) -> BaseStrategy:
        """
        获取策略实例

        Args:
            strategy_name: 策略名称 ('momentum', 'mean_reversion', 'breakout')
            params: 自定义参数

        Returns:
            BaseStrategy: 策略实例
        """
        if strategy_name not in self.available_strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}. "
                           f"Available: {list(self.available_strategies.keys())}")

        strategy_class = self.available_strategies[strategy_name]['class']
        return strategy_class(params=params)

    def create_combo(self, strategy_names: List[str], weights: List[float] = None,
                     params_list: List[Dict] = None) -> StrategyComposer:
        """
        创建策略组合

        Args:
            strategy_names: 策略名称列表
            weights: 权重列表 (None则平均权重)
            params_list: 每个策略的参数列表 (None则用默认参数)

        Returns:
            StrategyComposer: 策略组合器

        Example:
            combo = mgr.create_combo(
                ['momentum', 'mean_reversion'],
                weights=[0.6, 0.4]
            )
        """
        if params_list is None:
            params_list = [None] * len(strategy_names)

        strategies = [
            self.get_strategy(name, params)
            for name, params in zip(strategy_names, params_list)
        ]

        return StrategyComposer(strategies, weights)

    def compare_strategies(self, symbol: str, strategy_names: List[str] = None) -> pd.DataFrame:
        """
        比较不同策略在同一股票上的表现

        Args:
            symbol: 股票代码
            strategy_names: 策略名称列表 (None则比较所有)

        Returns:
            pd.DataFrame: 比较结果
        """
        if strategy_names is None:
            strategy_names = list(self.available_strategies.keys())

        results = []

        print(f"\nComparing strategies for: {symbol}")
        print("=" * 80)

        for name in strategy_names:
            try:
                strategy = self.get_strategy(name)
                signal = strategy.analyze(symbol)

                results.append({
                    'strategy': name,
                    'signal': signal['signal'],
                    'score': signal['score'],
                    'confidence': signal['confidence'],
                    'entry_price': signal.get('entry_price', 0),
                    'stop_loss': signal.get('stop_loss', 0),
                    'take_profit': signal.get('take_profit', 0),
                    'risk_reward': ((signal.get('take_profit', 0) - signal.get('entry_price', 1)) /
                                   (signal.get('entry_price', 1) - signal.get('stop_loss', 0)))
                                  if signal.get('entry_price') and signal.get('stop_loss') else 0
                })

                print(f"\n{self.available_strategies[name]['name']}:")
                print(f"  Signal: {signal['signal']} (Score: {signal['score']})")
                # Skip printing reasons to avoid encoding issues

            except Exception as e:
                print(f"\n{name}: Analysis failed - {str(e)}")
                continue

        print("\n" + "=" * 80)

        if results:
            df = pd.DataFrame(results)
            df = df.sort_values('score', ascending=False)
            return df
        else:
            return pd.DataFrame()

    def scan_with_all_strategies(self, symbols: List[str] = None,
                                 top_n: int = 10) -> Dict[str, List]:
        """
        用所有策略扫描市场

        Args:
            symbols: 股票列表 (None则扫描所有)
            top_n: 每个策略返回前N只

        Returns:
            dict: {strategy_name: [signals]}
        """
        results = {}

        for name in self.available_strategies.keys():
            print(f"\n使用 {self.available_strategies[name]['name']} 扫描市场...")
            print("-" * 70)

            strategy = self.get_strategy(name)

            if symbols:
                signals = []
                for symbol in symbols:
                    try:
                        sig = strategy.analyze(symbol)
                        signals.append(sig)
                    except:
                        continue
                signals.sort(key=lambda x: x['score'], reverse=True)
            else:
                signals = strategy.scan_market(
                    filters={'min_score': 60, 'signal_types': ['STRONG_BUY', 'BUY']}
                )

            results[name] = signals[:top_n]

            print(f"发现 {len(signals)} 个信号，Top {min(top_n, len(signals))}:")
            for i, sig in enumerate(results[name], 1):
                print(f"  {i}. {sig['symbol']}: {sig['signal']} (Score: {sig['score']})")

        return results

    def recommend_strategy(self, market_condition: str = None) -> Dict:
        """
        Recommend strategy based on market condition

        Args:
            market_condition: 'trending', 'ranging', 'volatile', None

        Returns:
            dict: {'recommended': str, 'reason': str}
        """
        recommendations = {
            'trending': {
                'strategy': 'momentum',
                'reason': 'Bull markets and uptrends favor momentum strategies'
            },
            'ranging': {
                'strategy': 'mean_reversion',
                'reason': 'Range-bound markets favor mean reversion strategies'
            },
            'volatile': {
                'strategy': 'breakout',
                'reason': 'Volatile markets favor breakout strategies'
            }
        }

        if market_condition and market_condition in recommendations:
            rec = recommendations[market_condition]
            return {
                'recommended': rec['strategy'],
                'reason': rec['reason'],
                'strategy_name': self.available_strategies[rec['strategy']]['name']
            }

        return {
            'recommended': 'combo',
            'reason': 'No specific condition - use combination of all strategies',
            'strategy_name': 'Strategy Combination'
        }


# 使用示例
if __name__ == "__main__":
    mgr = StrategyManager()

    # 示例1: 列出所有策略
    print("示例1: 列出所有策略")
    print("=" * 80)
    mgr.list_strategies()

    # 示例2: 使用单个策略
    print("\n示例2: 使用动量策略分析AAPL")
    print("=" * 80)
    momentum = mgr.get_strategy('momentum')
    signal = momentum.analyze('AAPL')
    print(f"信号: {signal['signal']} (评分: {signal['score']})")
    print(f"理由: {', '.join(signal['reasons'])}")

    # 示例3: 策略组合
    print("\n示例3: 使用策略组合分析AAPL")
    print("=" * 80)
    combo = mgr.create_combo(
        ['momentum', 'mean_reversion'],
        weights=[0.7, 0.3]
    )
    signal = combo.analyze('AAPL')
    print(f"综合信号: {signal['signal']} (评分: {signal['score']})")

    # 示例4: 比较策略
    print("\n示例4: 比较所有策略在AAPL上的表现")
    print("=" * 80)
    comparison = mgr.compare_strategies('AAPL')
    if len(comparison) > 0:
        print("\n比较结果:")
        print(comparison[['strategy', 'signal', 'score', 'risk_reward']].to_string(index=False))

    # 示例5: 推荐策略
    print("\n示例5: 策略推荐")
    print("=" * 80)
    mgr.recommend_strategy('trending')
