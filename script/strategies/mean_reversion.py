"""
Mean Reversion Strategy
均值回归策略

适用场景: 震荡行情，超跌反弹
核心逻辑: 买入短期超卖、远离均线的股票，等待回归

参数说明:
- rsi_period: RSI周期（默认14）
- rsi_oversold: RSI超卖线（默认30）
- rsi_overbought: RSI超买线（默认70）
- bb_period: 布林带周期（默认20）
- bb_std: 布林带标准差（默认2）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from script.strategy_base import BaseStrategy
import pandas as pd
import numpy as np


class MeanReversionStrategy(BaseStrategy):
    """均值回归策略实现"""

    def __init__(self, params: dict = None):
        default_params = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_period': 20,
            'bb_std': 2,
            'capital': 2000,
            'position_pct': 0.35,
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.10
        }

        if params:
            default_params.update(params)

        super().__init__(name="Mean Reversion Strategy", params=default_params)

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        if loss.iloc[-1] == 0:
            return 100
        rs = gain.iloc[-1] / loss.iloc[-1]
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std: float = 2):
        """计算布林带"""
        sma = prices.rolling(window=period).mean()
        std_dev = prices.rolling(window=period).std()

        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)

        return {
            'upper': upper.iloc[-1],
            'middle': sma.iloc[-1],
            'lower': lower.iloc[-1]
        }

    def analyze(self, symbol: str, df: pd.DataFrame = None) -> dict:
        """
        分析均值回归机会

        Returns:
            dict: 信号字典
        """
        # 获取数据
        if df is None:
            df = self.get_price_data(symbol, days=60)

        if len(df) < 30:
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'score': 0,
                'reasons': ['Insufficient data']
            }

        df = df.sort_values('date').reset_index(drop=True)

        # 计算指标
        latest_price = df.iloc[-1]['close']

        # 1. RSI
        rsi = self.calculate_rsi(df['close'], self.params['rsi_period'])

        # 2. 布林带
        bb = self.calculate_bollinger_bands(
            df['close'],
            self.params['bb_period'],
            self.params['bb_std']
        )

        # 3. 布林带位置 (0-100, 0=下轨, 50=中轨, 100=上轨)
        bb_position = ((latest_price - bb['lower']) / (bb['upper'] - bb['lower']) * 100) if bb['upper'] != bb['lower'] else 50

        # 4. 距离MA20的偏离
        ma20 = df['close'].tail(20).mean()
        deviation_from_ma = ((latest_price - ma20) / ma20 * 100)

        # 5. 近期跌幅
        recent_drop = ((df.iloc[-1]['close'] - df.iloc[-5]['close']) / df.iloc[-5]['close'] * 100)

        # 评分系统 (0-100, 高分=超卖买入机会)
        score = 50  # 基础分
        reasons = []

        # RSI评分 (30分)
        if rsi < self.params['rsi_oversold']:
            oversold_degree = (self.params['rsi_oversold'] - rsi) / self.params['rsi_oversold']
            score += int(30 * min(oversold_degree, 1.0))
            reasons.append(f"RSI超卖 ({rsi:.1f})")
        elif rsi > self.params['rsi_overbought']:
            overbought_degree = (rsi - self.params['rsi_overbought']) / (100 - self.params['rsi_overbought'])
            score -= int(30 * min(overbought_degree, 1.0))
            reasons.append(f"RSI超买 ({rsi:.1f})")
        else:
            score += 10
            reasons.append(f"RSI中性 ({rsi:.1f})")

        # 布林带位置评分 (30分)
        if bb_position < 10:  # 接近下轨
            score += 30
            reasons.append(f"接近布林下轨 ({bb_position:.0f}%)")
        elif bb_position < 30:
            score += 20
            reasons.append(f"布林带下半区 ({bb_position:.0f}%)")
        elif bb_position > 90:  # 接近上轨
            score -= 30
            reasons.append(f"接近布林上轨 ({bb_position:.0f}%)")
        elif bb_position > 70:
            score -= 20
            reasons.append(f"布林带上半区 ({bb_position:.0f}%)")

        # MA偏离度评分 (20分)
        if deviation_from_ma < -5:  # 远低于均线
            score += 20
            reasons.append(f"远低于MA20 ({deviation_from_ma:.1f}%)")
        elif deviation_from_ma < -2:
            score += 10
            reasons.append(f"低于MA20 ({deviation_from_ma:.1f}%)")
        elif deviation_from_ma > 5:
            score -= 20
            reasons.append(f"远高于MA20 ({deviation_from_ma:.1f}%)")

        # 近期跌幅评分 (20分)
        if recent_drop < -5:  # 大幅下跌
            score += 20
            reasons.append(f"近期大幅下跌 ({recent_drop:.1f}%)")
        elif recent_drop < -2:
            score += 10
            reasons.append(f"近期下跌 ({recent_drop:.1f}%)")
        elif recent_drop > 5:
            score -= 20
            reasons.append(f"近期大幅上涨 ({recent_drop:.1f}%)")

        # 限制评分范围
        score = max(0, min(100, score))

        # 生成信号
        if score >= 70:
            signal = 'STRONG_BUY'  # 严重超卖
        elif score >= 60:
            signal = 'BUY'  # 超卖
        elif score >= 45:
            signal = 'HOLD'  # 中性
        elif score >= 35:
            signal = 'SELL'  # 超买
        else:
            signal = 'STRONG_SELL'  # 严重超买

        # 计算仓位
        position_value = self.params['capital'] * self.params['position_pct']
        shares = int(position_value / latest_price)

        # 止损止盈
        stop_loss = latest_price * (1 - self.params['stop_loss_pct'])
        # 均值回归：目标是回到中轨
        take_profit = min(
            latest_price * (1 + self.params['take_profit_pct']),
            bb['middle']
        )

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
                'rsi': rsi,
                'bb_position': bb_position,
                'bb_upper': bb['upper'],
                'bb_middle': bb['middle'],
                'bb_lower': bb['lower'],
                'deviation_from_ma': deviation_from_ma,
                'recent_drop': recent_drop
            }
        })


# 测试代码
if __name__ == "__main__":
    strategy = MeanReversionStrategy()

    # 测试
    signal = strategy.analyze('AAPL')
    print(f"\n{signal['symbol']}: {signal['signal']} (Score: {signal['score']})")
    print(f"Price: ${signal['entry_price']:.2f}")
    print(f"Target: ${signal['take_profit']:.2f}")
    print("Reasons:")
    for reason in signal['reasons']:
        print(f"  - {reason}")

    print("\nMetadata:")
    for key, value in signal['metadata'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
