"""
Breakout Strategy
突破策略

适用场景: 盘整后突破，关键位突破
核心逻辑: 买入突破阻力位或盘整区间的股票

参数说明:
- consolidation_days: 盘整天数（默认20）
- breakout_threshold: 突破阈值（默认1.02, 即突破2%）
- volume_confirmation: 需要成交量确认（默认True）
- min_volume_ratio: 最低成交量倍数（默认1.5）
"""

import sys
sys.path.insert(0, 'd:/strategy=Z')

from script.strategy_base import BaseStrategy
import pandas as pd
import numpy as np


class BreakoutStrategy(BaseStrategy):
    """突破策略实现"""

    def __init__(self, params: dict = None):
        default_params = {
            'consolidation_days': 20,
            'breakout_threshold': 1.02,  # 突破阈值
            'volume_confirmation': True,
            'min_volume_ratio': 1.5,
            'atr_period': 14,
            'capital': 2000,
            'position_pct': 0.35,
            'stop_loss_atr_multiplier': 2.0,  # ATR倍数止损
            'take_profit_pct': 0.15
        }

        if params:
            default_params.update(params)

        super().__init__(name="Breakout Strategy", params=default_params)

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算ATR (Average True Range)"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=period).mean()
        return atr.iloc[-1]

    def detect_consolidation(self, df: pd.DataFrame, days: int) -> dict:
        """
        检测盘整

        Returns:
            dict: {
                'is_consolidating': bool,
                'range_high': float,
                'range_low': float,
                'range_pct': float
            }
        """
        recent_data = df.tail(days)

        range_high = recent_data['high'].max()
        range_low = recent_data['low'].min()
        range_pct = ((range_high - range_low) / range_low) * 100

        # 盘整判断：波动范围小于10%
        is_consolidating = range_pct < 10

        return {
            'is_consolidating': is_consolidating,
            'range_high': range_high,
            'range_low': range_low,
            'range_pct': range_pct
        }

    def analyze(self, symbol: str, df: pd.DataFrame = None) -> dict:
        """
        分析突破机会

        Returns:
            dict: 信号字典
        """
        # 获取数据
        if df is None:
            df = self.get_price_data(symbol, days=60)

        if len(df) < self.params['consolidation_days'] + 10:
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'score': 0,
                'reasons': ['Insufficient data']
            }

        df = df.sort_values('date').reset_index(drop=True)

        # 当前价格
        latest_price = df.iloc[-1]['close']
        latest_high = df.iloc[-1]['high']
        latest_volume = df.iloc[-1]['volume']

        # 1. 检测盘整
        consolidation = self.detect_consolidation(
            df.iloc[:-1],  # 不包括今天
            self.params['consolidation_days']
        )

        # 2. 检测突破
        is_breakout = latest_high >= consolidation['range_high'] * self.params['breakout_threshold']

        # 3. 成交量确认
        avg_volume = df.iloc[-21:-1]['volume'].mean()
        volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
        volume_confirmed = volume_ratio >= self.params['min_volume_ratio']

        # 4. ATR
        atr = self.calculate_atr(df, self.params['atr_period'])
        atr_pct = (atr / latest_price) * 100

        # 5. 阻力位（过去60天高点）
        resistance_60d = df.tail(60)['high'].max()
        near_resistance = latest_price >= resistance_60d * 0.98

        # 6. 趋势方向（MA20 vs MA60）
        ma20 = df['close'].tail(20).mean()
        ma60 = df['close'].tail(60).mean() if len(df) >= 60 else ma20
        uptrend = ma20 > ma60

        # 评分系统
        score = 0
        reasons = []

        # 盘整评分 (20分)
        if consolidation['is_consolidating']:
            score += 20
            reasons.append(f"盘整{self.params['consolidation_days']}天 (波动{consolidation['range_pct']:.1f}%)")
        else:
            score += 5
            reasons.append(f"波动较大 ({consolidation['range_pct']:.1f}%)")

        # 突破评分 (35分)
        if is_breakout:
            breakout_strength = ((latest_high - consolidation['range_high'])
                                / consolidation['range_high']) * 100
            if breakout_strength > 3:
                score += 35
                reasons.append(f"强势突破 (+{breakout_strength:.1f}%)")
            else:
                score += 25
                reasons.append(f"突破盘整区间 (+{breakout_strength:.1f}%)")
        else:
            distance_to_breakout = ((consolidation['range_high'] - latest_price)
                                   / latest_price) * 100
            if distance_to_breakout < 2:
                score += 15
                reasons.append(f"接近突破 (距离{distance_to_breakout:.1f}%)")
            else:
                reasons.append(f"未突破 (距离{distance_to_breakout:.1f}%)")

        # 成交量评分 (25分)
        if self.params['volume_confirmation']:
            if volume_confirmed:
                score += 25
                reasons.append(f"成交量确认 ({volume_ratio:.2f}x)")
            else:
                score += 5
                reasons.append(f"成交量不足 ({volume_ratio:.2f}x)")
        else:
            score += 15

        # 阻力位评分 (10分)
        if near_resistance:
            score += 10
            reasons.append("接近/突破60日高点")

        # 趋势评分 (10分)
        if uptrend:
            score += 10
            reasons.append("上升趋势 (MA20 > MA60)")
        else:
            reasons.append("下降趋势")

        # 生成信号
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

        # 计算仓位
        position_value = self.params['capital'] * self.params['position_pct']
        shares = int(position_value / latest_price)

        # 止损：使用ATR
        stop_loss = latest_price - (atr * self.params['stop_loss_atr_multiplier'])

        # 止盈
        take_profit = latest_price * (1 + self.params['take_profit_pct'])

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
                'is_consolidating': consolidation['is_consolidating'],
                'range_high': consolidation['range_high'],
                'range_low': consolidation['range_low'],
                'range_pct': consolidation['range_pct'],
                'is_breakout': is_breakout,
                'volume_ratio': volume_ratio,
                'atr': atr,
                'atr_pct': atr_pct,
                'resistance_60d': resistance_60d
            }
        })


# 测试代码
if __name__ == "__main__":
    strategy = BreakoutStrategy()

    # 测试
    signal = strategy.analyze('AAPL')
    print(f"\n{signal['symbol']}: {signal['signal']} (Score: {signal['score']})")
    print(f"Price: ${signal['entry_price']:.2f}")
    print(f"Stop Loss: ${signal['stop_loss']:.2f} (ATR-based)")
    print(f"Take Profit: ${signal['take_profit']:.2f}")
    print("\nReasons:")
    for reason in signal['reasons']:
        print(f"  - {reason}")

    print("\nBreakout Analysis:")
    meta = signal['metadata']
    print(f"  Consolidating: {meta['is_consolidating']}")
    print(f"  Range: ${meta['range_low']:.2f} - ${meta['range_high']:.2f} ({meta['range_pct']:.1f}%)")
    print(f"  Breakout: {meta['is_breakout']}")
    print(f"  Volume Ratio: {meta['volume_ratio']:.2f}x")
