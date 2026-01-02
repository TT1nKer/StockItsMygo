"""
Custom Strategy Template
自定义策略模板

这是一个空白模板，你可以复制它来创建自己的策略。

使用步骤:
1. 复制此文件并重命名 (例如: my_strategy.py)
2. 修改类名 (例如: MyStrategy)
3. 在 __init__ 中定义策略参数
4. 在 analyze() 中实现你的交易逻辑
5. 返回标准格式的信号字典

提示:
- self.get_price_data(symbol, days) - 获取日线数据
- self.get_intraday_data(symbol, interval, days) - 获取分钟数据
- self.db - 访问数据库API
- self.params - 访问策略参数
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from script.strategy_base import BaseStrategy
import pandas as pd
import numpy as np


class CustomStrategy(BaseStrategy):
    """
    自定义策略模板

    在这里实现你自己的交易策略逻辑
    """

    def __init__(self, params: dict = None):
        """
        初始化策略参数

        在这里定义你的策略需要的所有参数
        """
        default_params = {
            # 示例参数
            'lookback_period': 20,
            'threshold': 0.5,
            'capital': 2000,
            'position_pct': 0.35,
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.12,

            # 添加你自己的参数...
            # 'my_param': value,
        }

        if params:
            default_params.update(params)

        super().__init__(name="My Custom Strategy", params=default_params)

    def analyze(self, symbol: str, df: pd.DataFrame = None) -> dict:
        """
        分析股票并生成交易信号

        Args:
            symbol: 股票代码
            df: 价格数据 (可选)

        Returns:
            dict: 信号字典，包含以下字段:
                - symbol: 股票代码
                - signal: 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
                - score: 0-100分
                - confidence: 置信度 0-100
                - reasons: 理由列表
                - entry_price: 入场价
                - stop_loss: 止损价
                - take_profit: 止盈价
                - position_size: 建议股数
                - metadata: 额外信息字典
        """
        # ========== 步骤1: 获取数据 ==========
        if df is None:
            df = self.get_price_data(symbol, days=60)

        # 检查数据充足性
        if len(df) < 20:
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'score': 0,
                'reasons': ['Insufficient data']
            }

        df = df.sort_values('date').reset_index(drop=True)

        # ========== 步骤2: 计算指标 ==========
        latest_price = df.iloc[-1]['close']

        # 示例: 计算简单移动平均线
        ma20 = df['close'].tail(20).mean()

        # 添加你自己的指标计算...
        # indicator1 = ...
        # indicator2 = ...

        # ========== 步骤3: 生成信号 ==========
        score = 50  # 基础分数
        reasons = []

        # 示例规则1: 价格vs均线
        if latest_price > ma20:
            score += 20
            reasons.append(f"价格在MA20上方")
        else:
            score -= 20
            reasons.append(f"价格在MA20下方")

        # 添加你自己的规则...
        # if condition1:
        #     score += points
        #     reasons.append("理由描述")

        # ========== 步骤4: 确定信号类型 ==========
        if score >= 70:
            signal = 'STRONG_BUY'
        elif score >= 60:
            signal = 'BUY'
        elif score >= 45:
            signal = 'HOLD'
        elif score >= 35:
            signal = 'SELL'
        else:
            signal = 'STRONG_SELL'

        # ========== 步骤5: 计算仓位和价格 ==========
        position_value = self.params['capital'] * self.params['position_pct']
        shares = int(position_value / latest_price)

        stop_loss = latest_price * (1 - self.params['stop_loss_pct'])
        take_profit = latest_price * (1 + self.params['take_profit_pct'])

        # ========== 步骤6: 返回标准格式信号 ==========
        return self.validate_signal({
            'symbol': symbol,
            'signal': signal,
            'score': score,
            'confidence': score,
            'reasons': reasons,
            'entry_price': latest_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': shares,
            'metadata': {
                'ma20': ma20,
                # 添加你想保存的额外信息...
                # 'indicator1': value1,
                # 'indicator2': value2,
            }
        })


# ========== 测试代码 ==========
if __name__ == "__main__":
    # 创建策略实例
    strategy = CustomStrategy()

    # 测试单只股票
    print("Testing custom strategy on AAPL...")
    signal = strategy.analyze('AAPL')

    print(f"\nSymbol: {signal['symbol']}")
    print(f"Signal: {signal['signal']}")
    print(f"Score: {signal['score']}")
    print(f"Entry Price: ${signal['entry_price']:.2f}")
    print(f"Stop Loss: ${signal['stop_loss']:.2f}")
    print(f"Take Profit: ${signal['take_profit']:.2f}")
    print(f"Position Size: {signal['position_size']} shares")

    print("\nReasons:")
    for reason in signal['reasons']:
        print(f"  - {reason}")

    print("\nMetadata:")
    for key, value in signal['metadata'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    # 扫描市场示例
    print("\n" + "="*70)
    print("Scanning market with custom strategy...")
    print("="*70)

    # 获取少量股票测试
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']

    signals = []
    for sym in test_symbols:
        try:
            sig = strategy.analyze(sym)
            signals.append(sig)
        except Exception as e:
            print(f"{sym}: Error - {e}")

    # 按分数排序
    signals.sort(key=lambda x: x['score'], reverse=True)

    print(f"\nTop signals:\n")
    for i, sig in enumerate(signals[:5], 1):
        print(f"{i}. {sig['symbol']}: {sig['signal']} (Score: {sig['score']})")
        print(f"   @ ${sig['entry_price']:.2f}")
        print(f"   {', '.join(sig['reasons'])}")
        print()
