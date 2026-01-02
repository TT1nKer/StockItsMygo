"""
Momentum Strategy
动量策略

适用场景: 趋势行情，强者恒强
核心逻辑: 买入近期涨幅大、成交量放大的股票

参数说明:
- lookback_days: 回看天数（默认20）
- min_momentum: 最低动量要求（默认10%）
- volume_multiplier: 成交量放大倍数（默认1.5）
- capital: 总资金（默认2000）
- position_pct: 单仓位占比（默认0.35）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from script.strategy_base import BaseStrategy
import pandas as pd
import numpy as np


class MomentumStrategy(BaseStrategy):
    """动量策略实现"""

    def __init__(self, params: dict = None):
        default_params = {
            'lookback_days': 20,
            'min_momentum': 10.0,  # 最低动量（%）
            'volume_multiplier': 1.5,  # 成交量放大倍数
            'capital': 2000,
            'position_pct': 0.35,
            'stop_loss_pct': 0.05,  # 止损比例
            'take_profit_pct': 0.12  # 止盈比例
        }

        if params:
            default_params.update(params)

        super().__init__(name="Momentum Strategy", params=default_params)

    def analyze(self, symbol: str, df: pd.DataFrame = None) -> dict:
        """
        分析股票动量

        Returns:
            dict: 信号字典
        """
        # 获取数据
        if df is None:
            df = self.get_price_data(symbol, days=90)

        if len(df) < self.params['lookback_days'] + 10:
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'score': 0,
                'reasons': ['Insufficient data']
            }

        # 计算指标
        df = df.sort_values('date').reset_index(drop=True)
        lookback = self.params['lookback_days']

        # 1. 价格动量
        price_momentum = ((df.iloc[-1]['close'] - df.iloc[-lookback]['close'])
                         / df.iloc[-lookback]['close'] * 100)

        # 2. 近期表现 (5日)
        recent_gain = ((df.iloc[-1]['close'] - df.iloc[-5]['close'])
                      / df.iloc[-5]['close'] * 100)

        # 3. 成交量动量
        recent_volume = df.tail(5)['volume'].mean()
        avg_volume = df.iloc[-25:-5]['volume'].mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

        # 4. 相对MA20位置
        ma20 = df['close'].tail(20).mean()
        latest_price = df.iloc[-1]['close']
        price_vs_ma20 = ((latest_price - ma20) / ma20 * 100) if pd.notna(ma20) else 0

        # 5. 突破检测
        recent_high = df.tail(20)['high'].max()
        is_breakout = latest_price >= recent_high * 0.99

        # 评分系统 (0-100)
        score = 0
        reasons = []

        # 动量评分 (40分)
        if price_momentum > 20:
            score += 40
            reasons.append(f"强劲动量 ({price_momentum:.1f}%)")
        elif price_momentum > self.params['min_momentum']:
            score += 25
            reasons.append(f"正动量 ({price_momentum:.1f}%)")
        else:
            reasons.append(f"动量不足 ({price_momentum:.1f}%)")

        # 成交量评分 (25分)
        if volume_ratio > 2.0:
            score += 25
            reasons.append(f"成交量爆发 ({volume_ratio:.2f}x)")
        elif volume_ratio > self.params['volume_multiplier']:
            score += 15
            reasons.append(f"成交量放大 ({volume_ratio:.2f}x)")
        else:
            reasons.append(f"成交量正常 ({volume_ratio:.2f}x)")

        # 突破评分 (20分)
        if is_breakout:
            score += 20
            reasons.append("突破近期高点")
        elif price_vs_ma20 > 5:
            score += 10
            reasons.append("价格在MA20上方")

        # 近期强势 (15分)
        if recent_gain > 3:
            score += 15
            reasons.append(f"近期强势 ({recent_gain:.1f}%)")
        elif recent_gain > 0:
            score += 8
            reasons.append(f"近期上涨 ({recent_gain:.1f}%)")

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

        # 计算仓位和价格
        position_value = self.params['capital'] * self.params['position_pct']
        shares = int(position_value / latest_price)
        actual_value = shares * latest_price

        stop_loss = latest_price * (1 - self.params['stop_loss_pct'])
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
                'price_momentum': price_momentum,
                'recent_gain': recent_gain,
                'volume_ratio': volume_ratio,
                'is_breakout': is_breakout,
                'position_value': actual_value
            }
        })


# 测试代码
if __name__ == "__main__":
    strategy = MomentumStrategy()

    # 测试单只股票
    signal = strategy.analyze('AAPL')
    print(f"\n{signal['symbol']}: {signal['signal']} (Score: {signal['score']})")
    print(f"Price: ${signal['entry_price']:.2f}")
    print(f"Stop Loss: ${signal['stop_loss']:.2f}")
    print(f"Take Profit: ${signal['take_profit']:.2f}")
    print("Reasons:")
    for reason in signal['reasons']:
        print(f"  - {reason}")

    # 扫描市场（Top 10）
    print("\n" + "="*70)
    print("Scanning market for momentum opportunities...")
    print("="*70)

    signals = strategy.scan_market(
        filters={
            'min_score': 70,
            'signal_types': ['STRONG_BUY', 'BUY']
        }
    )

    print(f"\nFound {len(signals)} strong signals\n")

    for i, sig in enumerate(signals[:10], 1):
        print(f"{i}. {sig['symbol']} - Score: {sig['score']}")
        print(f"   {sig['signal']} @ ${sig['entry_price']:.2f}")
        print(f"   {', '.join(sig['reasons'][:2])}")
        print()
