"""
Strategy Framework Base Class
策略框架基类

提供统一的策略接口，让用户可以轻松自定义交易策略。

Features:
- 统一的策略接口
- 可插拔的策略设计
- 策略组合支持
- 回测兼容
- 参数配置化

使用方法:
1. 继承 BaseStrategy 类
2. 实现 analyze() 方法
3. 返回标准化的信号格式
"""

from abc import ABC, abstractmethod
from db.api import StockDB
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class BaseStrategy(ABC):
    """
    策略基类

    所有自定义策略都应该继承这个类并实现 analyze() 方法
    """

    def __init__(self, name: str = "Unnamed Strategy", params: Dict = None):
        """
        初始化策略

        Args:
            name: 策略名称
            params: 策略参数字典
        """
        self.name = name
        self.params = params or {}
        self.db = StockDB()

    @abstractmethod
    def analyze(self, symbol: str, df: pd.DataFrame = None) -> Dict:
        """
        分析股票并生成信号

        Args:
            symbol: 股票代码
            df: 价格数据 DataFrame (可选，如果为None则自动获取)

        Returns:
            dict: {
                'symbol': str,
                'signal': str,  # 'BUY', 'SELL', 'HOLD', 'STRONG_BUY', 'STRONG_SELL'
                'score': int,  # 0-100
                'confidence': float,  # 0-100
                'reasons': list,  # 理由列表
                'entry_price': float,  # 建议入场价
                'stop_loss': float,  # 止损价
                'take_profit': float,  # 止盈价
                'position_size': int,  # 建议仓位大小
                'metadata': dict  # 额外信息
            }
        """
        pass

    def get_price_data(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """
        获取价格数据

        Args:
            symbol: 股票代码
            days: 获取天数

        Returns:
            pd.DataFrame: 价格数据
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        return self.db.get_price_history(symbol, start_date=start_date)

    def get_intraday_data(self, symbol: str, interval: str = '5m', days: int = 7) -> pd.DataFrame:
        """
        获取分钟数据

        Args:
            symbol: 股票代码
            interval: 时间间隔
            days: 获取天数

        Returns:
            pd.DataFrame: 分钟数据
        """
        start_datetime = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        return self.db.get_intraday_data(symbol, interval=interval, start_datetime=start_datetime)

    def validate_signal(self, signal: Dict) -> Dict:
        """
        验证信号格式

        Args:
            signal: 信号字典

        Returns:
            dict: 验证并补全后的信号
        """
        required_fields = ['symbol', 'signal', 'score']
        for field in required_fields:
            if field not in signal:
                raise ValueError(f"Signal missing required field: {field}")

        # 设置默认值
        signal.setdefault('confidence', signal['score'])
        signal.setdefault('reasons', [])
        signal.setdefault('entry_price', None)
        signal.setdefault('stop_loss', None)
        signal.setdefault('take_profit', None)
        signal.setdefault('position_size', 0)
        signal.setdefault('metadata', {})

        # 验证信号类型
        valid_signals = ['BUY', 'SELL', 'HOLD', 'STRONG_BUY', 'STRONG_SELL']
        if signal['signal'] not in valid_signals:
            raise ValueError(f"Invalid signal type: {signal['signal']}")

        # 验证评分范围
        if not 0 <= signal['score'] <= 100:
            raise ValueError(f"Score must be between 0-100, got {signal['score']}")

        return signal

    def scan_market(self, symbols: List[str] = None, filters: Dict = None) -> List[Dict]:
        """
        扫描市场

        Args:
            symbols: 股票列表 (None则扫描所有)
            filters: 过滤条件 (price_min, price_max, volume_min等)

        Returns:
            list: 信号列表，按score降序排序
        """
        if symbols is None:
            symbols = self.db.get_stock_list()

        signals = []
        filters = filters or {}

        for symbol in symbols:
            try:
                signal = self.analyze(symbol)

                # 应用过滤条件
                if self._apply_filters(signal, filters):
                    signals.append(signal)

            except Exception as e:
                # 跳过失败的股票
                continue

        # 按评分排序
        signals.sort(key=lambda x: x['score'], reverse=True)

        return signals

    def _apply_filters(self, signal: Dict, filters: Dict) -> bool:
        """
        应用过滤条件

        Args:
            signal: 信号
            filters: 过滤条件

        Returns:
            bool: 是否通过过滤
        """
        # 评分过滤
        if 'min_score' in filters and signal['score'] < filters['min_score']:
            return False

        # 信号类型过滤
        if 'signal_types' in filters and signal['signal'] not in filters['signal_types']:
            return False

        # 价格过滤
        if signal.get('entry_price'):
            if 'price_min' in filters and signal['entry_price'] < filters['price_min']:
                return False
            if 'price_max' in filters and signal['entry_price'] > filters['price_max']:
                return False

        return True

    def backtest(self, symbol: str, start_date: str, end_date: str) -> Dict:
        """
        简单回测 (可被子类重写以实现更复杂的回测)

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            dict: 回测结果
        """
        # TODO: 实现完整回测功能
        raise NotImplementedError("Backtest not implemented yet")

    def __str__(self):
        return f"{self.name} (params: {self.params})"


class StrategyComposer:
    """
    策略组合器

    可以组合多个策略，综合它们的信号
    """

    def __init__(self, strategies: List[BaseStrategy], weights: List[float] = None):
        """
        初始化策略组合

        Args:
            strategies: 策略列表
            weights: 权重列表 (如果为None则平均权重)
        """
        self.strategies = strategies

        if weights is None:
            self.weights = [1.0 / len(strategies)] * len(strategies)
        else:
            if len(weights) != len(strategies):
                raise ValueError("Weights length must match strategies length")
            total = sum(weights)
            self.weights = [w / total for w in weights]

    def analyze(self, symbol: str) -> Dict:
        """
        组合分析

        Args:
            symbol: 股票代码

        Returns:
            dict: 综合信号
        """
        signals = []

        for strategy in self.strategies:
            try:
                signal = strategy.analyze(symbol)
                signals.append(signal)
            except Exception as e:
                print(f"{strategy.name} failed for {symbol}: {e}")
                continue

        if not signals:
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'score': 50,
                'confidence': 0,
                'reasons': ['No valid signals from any strategy'],
                'metadata': {'strategies_failed': len(self.strategies)}
            }

        # 加权综合评分
        total_score = sum(s['score'] * w for s, w in zip(signals, self.weights[:len(signals)]))

        # 综合信号
        if total_score >= 70:
            final_signal = 'STRONG_BUY'
        elif total_score >= 60:
            final_signal = 'BUY'
        elif total_score >= 45:
            final_signal = 'HOLD'
        elif total_score >= 35:
            final_signal = 'SELL'
        else:
            final_signal = 'STRONG_SELL'

        # 综合理由
        all_reasons = []
        for signal, strategy in zip(signals, self.strategies):
            all_reasons.append(f"[{strategy.name}] Score: {signal['score']}")
            all_reasons.extend(signal['reasons'])

        return {
            'symbol': symbol,
            'signal': final_signal,
            'score': int(total_score),
            'confidence': int(total_score),
            'reasons': all_reasons,
            'entry_price': signals[0].get('entry_price'),
            'stop_loss': min((s.get('stop_loss') for s in signals if s.get('stop_loss')), default=None),
            'take_profit': max((s.get('take_profit') for s in signals if s.get('take_profit')), default=None),
            'metadata': {
                'strategies_used': len(signals),
                'individual_scores': [s['score'] for s in signals],
                'strategy_names': [strategy.name for strategy in self.strategies]
            }
        }

    def scan_market(self, symbols: List[str] = None, filters: Dict = None) -> List[Dict]:
        """
        使用组合策略扫描市场

        Args:
            symbols: 股票列表
            filters: 过滤条件

        Returns:
            list: 信号列表
        """
        if symbols is None:
            symbols = self.strategies[0].db.get_stock_list()

        signals = []
        filters = filters or {}

        for symbol in symbols:
            try:
                signal = self.analyze(symbol)

                # 应用过滤
                if self._apply_filters(signal, filters):
                    signals.append(signal)

            except Exception as e:
                continue

        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals

    def _apply_filters(self, signal: Dict, filters: Dict) -> bool:
        """应用过滤条件"""
        if 'min_score' in filters and signal['score'] < filters['min_score']:
            return False
        if 'signal_types' in filters and signal['signal'] not in filters['signal_types']:
            return False
        return True


# 使用示例
if __name__ == "__main__":
    # 这里只是基类示例，实际策略在其他文件中实现
    print("Strategy Framework Base Class loaded")
    print("Import specific strategies from:")
    print("  - script.strategies.momentum_strategy")
    print("  - script.strategies.mean_reversion_strategy")
    print("  - script.strategies.breakout_strategy")
    print("  - Or create your own by inheriting BaseStrategy")
