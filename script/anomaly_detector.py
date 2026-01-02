"""
Anomaly Detector - 异常信号检测器
去玄学的市场异常识别系统

Philosophy:
    不预测涨跌，只识别"相对于自身历史的异常"
    异常 ≠ 一定会涨，异常 = 值得冒一次 -1R 风险

Core Principle:
    值得关注的不是"涨跌"，而是：相对于自身历史，突然"不像平时"的地方
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from db.api import StockDB
from typing import Dict, List
from datetime import datetime


class AnomalyDetector:
    """
    市场异常检测器

    检测8类异常：
    1. 波动异常（最重要）
    2. 区间突破/破坏
    3. Gap（跳空）
    4. 成交量放大
    5. 成交金额异常
    6. 止损自然存在
    7. 连续收敛→突然扩张
    8. 稀疏性检查
    """

    def __init__(self):
        self.db = StockDB()

        # 参数设置（可调）
        self.params = {
            # 波动异常
            'atr_long_period': 20,          # ATR长周期
            'volatility_threshold': 2.0,     # TR/ATR > 2 视为异常

            # 区间突破
            'breakout_period': 20,           # N日高低点

            # 成交量异常
            'volume_ma_period': 20,          # 成交量均值周期
            'volume_threshold': 1.5,         # Volume/MA > 1.5 视为放量

            # 成交金额异常
            'dollar_volume_percentile': 0.7, # 前30%

            # 收敛扩张
            'consolidation_days': 5,         # 至少5天收敛
            'consolidation_threshold': 0.6,  # ATR收敛到60%以下
            'expansion_threshold': 1.5,      # 扩张到1.5倍以上
        }

    def calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """
        计算真实波动幅度 TR
        TR = max(H-L, |H-C_prev|, |L-C_prev|)
        """
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)

        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()

        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    def detect_volatility_anomaly(self, df: pd.DataFrame) -> Dict:
        """
        1️⃣ 波动异常检测：TR / ATR_long ≫ 1

        最重要的异常：市场正在重新定价
        """
        # 计算TR和ATR
        df['tr'] = self.calculate_true_range(df)
        df['atr_long'] = df['tr'].rolling(self.params['atr_long_period']).mean()

        # 最新数据
        latest = df.iloc[-1]

        if pd.isna(latest['atr_long']) or latest['atr_long'] == 0:
            return {'detected': False}

        # 波动率比值
        volatility_ratio = latest['tr'] / latest['atr_long']

        detected = volatility_ratio > self.params['volatility_threshold']

        return {
            'detected': detected,
            'tr': latest['tr'],
            'atr_long': latest['atr_long'],
            'ratio': volatility_ratio,
            'threshold': self.params['volatility_threshold'],
            'description': f"TR={latest['tr']:.2f}, ATR={latest['atr_long']:.2f}, Ratio={volatility_ratio:.2f}x"
        }

    def detect_breakout(self, df: pd.DataFrame) -> Dict:
        """
        2️⃣ 区间突破/破坏：Close > N日高点 或 < N日低点

        多空力量失衡，有一方被迫认输
        """
        period = self.params['breakout_period']

        # 计算N日高低点（不包括今天）
        high_n = df['high'].shift(1).rolling(period).max()
        low_n = df['low'].shift(1).rolling(period).min()

        latest = df.iloc[-1]

        if pd.isna(high_n.iloc[-1]) or pd.isna(low_n.iloc[-1]):
            return {'detected': False}

        # 检测突破
        upside_breakout = latest['close'] > high_n.iloc[-1]
        downside_breakdown = latest['close'] < low_n.iloc[-1]

        detected = upside_breakout or downside_breakdown

        return {
            'detected': detected,
            'type': 'UPSIDE' if upside_breakout else ('DOWNSIDE' if downside_breakdown else None),
            'close': latest['close'],
            'high_n': high_n.iloc[-1],
            'low_n': low_n.iloc[-1],
            'period': period,
            'description': f"{'突破' if upside_breakout else '跌破'} {period}日{'高点' if upside_breakout else '低点'}" if detected else ""
        }

    def detect_gap(self, df: pd.DataFrame) -> Dict:
        """
        3️⃣ Gap检测：Low_t > High_{t-1} 或 High_t < Low_{t-1}

        夜盘/信息冲击，被动成交集中发生
        """
        if len(df) < 2:
            return {'detected': False}

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        gap_up = latest['low'] > prev['high']
        gap_down = latest['high'] < prev['low']

        detected = gap_up or gap_down

        if detected:
            gap_size = (latest['low'] - prev['high']) if gap_up else (prev['low'] - latest['high'])
            gap_pct = (gap_size / prev['close']) * 100
        else:
            gap_size = 0
            gap_pct = 0

        return {
            'detected': detected,
            'type': 'GAP_UP' if gap_up else ('GAP_DOWN' if gap_down else None),
            'gap_size': gap_size,
            'gap_pct': gap_pct,
            'description': f"{'向上' if gap_up else '向下'}跳空 {abs(gap_pct):.2f}%" if detected else ""
        }

    def detect_volume_spike(self, df: pd.DataFrame) -> Dict:
        """
        4️⃣ 成交量异常：Volume / EMA(Volume) ≫ 1

        更多资金参与，不是几个人在拉
        """
        # 计算成交量均值
        volume_ma = df['volume'].rolling(self.params['volume_ma_period']).mean()

        latest = df.iloc[-1]

        if pd.isna(volume_ma.iloc[-1]) or volume_ma.iloc[-1] == 0:
            return {'detected': False}

        volume_ratio = latest['volume'] / volume_ma.iloc[-1]

        detected = volume_ratio > self.params['volume_threshold']

        return {
            'detected': detected,
            'volume': latest['volume'],
            'volume_ma': volume_ma.iloc[-1],
            'ratio': volume_ratio,
            'threshold': self.params['volume_threshold'],
            'description': f"成交量 {volume_ratio:.2f}x 均值"
        }

    def detect_dollar_volume_anomaly(self, df: pd.DataFrame, market_percentile: float = None) -> Dict:
        """
        5️⃣ 成交金额异常：过滤垃圾股

        有真实流动性，能进能出

        注意：需要市场整体数据才能计算分位数，这里简化为绝对值判断
        """
        latest = df.iloc[-1]
        dollar_volume = latest['close'] * latest['volume']

        # 简化判断：至少100万美元成交额
        min_liquidity = 1_000_000

        detected = dollar_volume >= min_liquidity

        return {
            'detected': detected,
            'dollar_volume': dollar_volume,
            'threshold': min_liquidity,
            'description': f"成交金额 ${dollar_volume:,.0f}"
        }

    def detect_stop_structure(self, df: pd.DataFrame) -> Dict:
        """
        6️⃣ 止损结构：止损位是否自然存在

        结构 = 能否迅速知道自己错了
        """
        latest = df.iloc[-1]

        # 检测最近的区间
        period = self.params['breakout_period']
        recent_high = df['high'].tail(period).max()
        recent_low = df['low'].tail(period).min()

        # 止损位计算
        if latest['close'] > recent_high:
            # 向上突破，止损在区间顶部下方
            stop_loss = recent_high
            stop_type = 'BREAKOUT_LONG'
        elif latest['close'] < recent_low:
            # 向下破位，止损在区间底部上方
            stop_loss = recent_low
            stop_type = 'BREAKDOWN_SHORT'
        else:
            # 区间内，无明确结构
            return {'detected': False, 'description': '无明确止损结构'}

        # 风险百分比
        risk_pct = abs(latest['close'] - stop_loss) / latest['close'] * 100

        # 结构清晰：止损距离合理（2-8%）
        detected = 2 <= risk_pct <= 8

        return {
            'detected': detected,
            'stop_type': stop_type,
            'entry': latest['close'],
            'stop_loss': stop_loss,
            'risk_pct': risk_pct,
            'description': f"{stop_type}: 止损@{stop_loss:.2f} (-{risk_pct:.1f}%)"
        }

    def detect_consolidation_expansion(self, df: pd.DataFrame) -> Dict:
        """
        7️⃣ 连续收敛→突然扩张

        能量积累后的释放，波动率regime切换
        """
        # 计算ATR
        df['tr'] = self.calculate_true_range(df)
        df['atr'] = df['tr'].rolling(14).mean()

        consol_days = self.params['consolidation_days']

        if len(df) < consol_days + 1:
            return {'detected': False}

        # 检查前N天是否收敛
        recent_atr = df['atr'].tail(consol_days + 1)

        if recent_atr.isna().any():
            return {'detected': False}

        # 收敛期的ATR
        consol_atr = recent_atr.iloc[:-1].mean()
        # 最新ATR
        current_atr = recent_atr.iloc[-1]

        # 判断收敛
        was_consolidating = current_atr < (consol_atr * self.params['consolidation_threshold'])

        # 判断扩张
        is_expanding = current_atr > (consol_atr * self.params['expansion_threshold'])

        detected = was_consolidating and is_expanding

        return {
            'detected': detected,
            'consol_atr': consol_atr,
            'current_atr': current_atr,
            'expansion_ratio': current_atr / consol_atr if consol_atr > 0 else 0,
            'description': f"收敛后扩张: ATR {consol_atr:.2f} → {current_atr:.2f}" if detected else ""
        }

    def analyze_stock(self, symbol: str, min_history: int = 60) -> Dict:
        """
        分析单只股票的所有异常

        返回异常检测结果和综合评分
        """
        # 获取数据
        df = self.db.get_price_history(symbol)

        if df is None or len(df) < min_history:
            return {
                'symbol': symbol,
                'error': 'Insufficient data',
                'anomaly_score': 0
            }

        # 按日期排序
        df = df.sort_values('date').reset_index(drop=True)

        # 检测各类异常
        anomalies = {
            'volatility': self.detect_volatility_anomaly(df),
            'breakout': self.detect_breakout(df),
            'gap': self.detect_gap(df),
            'volume': self.detect_volume_spike(df),
            'liquidity': self.detect_dollar_volume_anomaly(df),
            'structure': self.detect_stop_structure(df),
            'expansion': self.detect_consolidation_expansion(df),
        }

        # 计算异常分数（0-100）
        # 核心三要素权重最高
        score = 0

        # 波动异常 (30分)
        if anomalies['volatility']['detected']:
            score += 30

        # 成交量异常 (30分)
        if anomalies['volume']['detected']:
            score += 30

        # 结构清晰 (30分)
        if anomalies['structure']['detected']:
            score += 30

        # 附加分数
        if anomalies['breakout']['detected']:
            score += 5
        if anomalies['gap']['detected']:
            score += 5
        if anomalies['expansion']['detected']:
            score += 5

        # 流动性是必要条件，不是加分项
        if not anomalies['liquidity']['detected']:
            score = 0  # 没有流动性，直接归零

        # 稀疏性检查（异常应该罕见）
        # 如果最近经常触发，降低可信度
        # TODO: 实现历史触发频率统计

        latest = df.iloc[-1]

        return {
            'symbol': symbol,
            'date': latest['date'],
            'close': latest['close'],
            'anomaly_score': min(score, 100),
            'anomalies': anomalies,
            'tradeable': score >= 60,  # 至少满足核心三要素中的两个
            'summary': self._generate_summary(symbol, anomalies, score)
        }

    def _generate_summary(self, symbol: str, anomalies: Dict, score: int) -> str:
        """生成异常摘要"""
        detected_anomalies = []

        for name, result in anomalies.items():
            if result.get('detected'):
                desc = result.get('description', name)
                detected_anomalies.append(desc)

        if not detected_anomalies:
            return f"{symbol}: 无明显异常"

        return f"{symbol} (分数: {score}): " + " | ".join(detected_anomalies)

    def quick_scan_symbols(self, symbols: List[str], min_score: int = 60) -> pd.DataFrame:
        """
        快速扫描指定股票列表（用于Step 2.5）

        只检测核心三要素：波动 + 成交量 + 结构
        跳过次要检测以提高速度

        Args:
            symbols: 股票列表
            min_score: 最低异常分数（建议60）

        Returns:
            DataFrame: 异常标的列表，按分数排序
        """
        results = []

        print(f"  Quick scanning {len(symbols)} symbols for anomalies...")

        for symbol in symbols:
            try:
                # 获取数据
                df = self.db.get_price_history(symbol)

                if df is None or len(df) < 60:
                    continue

                df = df.sort_values('date').reset_index(drop=True)

                # 只检测核心三要素
                vol_anomaly = self.detect_volatility_anomaly(df)
                volume_spike = self.detect_volume_spike(df)
                structure = self.detect_stop_structure(df)
                liquidity = self.detect_dollar_volume_anomaly(df)

                # 快速评分（只看核心）
                score = 0
                if vol_anomaly['detected']:
                    score += 30
                if volume_spike['detected']:
                    score += 30
                if structure['detected']:
                    score += 30

                # 流动性是必要条件
                if not liquidity['detected']:
                    score = 0

                if score >= min_score:
                    latest = df.iloc[-1]
                    results.append({
                        'symbol': symbol,
                        'score': score,
                        'close': latest['close'],
                        'volatility': vol_anomaly['detected'],
                        'volume': volume_spike['detected'],
                        'structure': structure['detected'],
                        'stop_loss': structure.get('stop_loss', 0) if structure['detected'] else 0,
                        'risk_pct': structure.get('risk_pct', 0) if structure['detected'] else 0,
                    })
            except Exception:
                continue

        if not results:
            print(f"    No anomalies found (score >= {min_score})")
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df = df.sort_values('score', ascending=False).reset_index(drop=True)

        print(f"    Found {len(df)} anomalies (score >= {min_score})")

        return df

    def scan_market(self, symbols: List[str] = None, min_score: int = 60) -> pd.DataFrame:
        """
        扫描市场，找出所有异常标的

        Args:
            symbols: 股票列表，None则扫描所有
            min_score: 最低异常分数

        Returns:
            DataFrame: 异常标的列表，按分数排序
        """
        if symbols is None:
            # 获取所有股票
            symbols = self.db.get_stock_list()

        results = []

        print(f"Scanning {len(symbols)} stocks for anomalies...")
        print()

        for i, symbol in enumerate(symbols, 1):
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(symbols)}")

            try:
                result = self.analyze_stock(symbol)

                if result['anomaly_score'] >= min_score:
                    results.append({
                        'symbol': symbol,
                        'score': result['anomaly_score'],
                        'close': result['close'],
                        'tradeable': result['tradeable'],
                        'summary': result['summary'],
                        'volatility': result['anomalies']['volatility']['detected'],
                        'volume': result['anomalies']['volume']['detected'],
                        'structure': result['anomalies']['structure']['detected'],
                        'breakout': result['anomalies']['breakout']['detected'],
                        'gap': result['anomalies']['gap']['detected'],
                    })
            except Exception as e:
                # 跳过有问题的股票
                continue

        if not results:
            print(f"No anomalies found with score >= {min_score}")
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df = df.sort_values('score', ascending=False).reset_index(drop=True)

        print(f"\nFound {len(df)} anomalies (score >= {min_score})")

        return df


if __name__ == "__main__":
    # 测试
    detector = AnomalyDetector()

    # 测试单只股票
    print("=" * 80)
    print("ANOMALY DETECTION TEST")
    print("=" * 80)
    print()

    test_symbols = ['AAPL', 'NVDA', 'TSLA', 'AMD', 'MSFT']

    for symbol in test_symbols:
        result = detector.analyze_stock(symbol)
        print(result['summary'])
        print()

    print("=" * 80)
    print("\nScanning market for high-score anomalies...")
    print("=" * 80)

    # 扫描市场（限制数量以加快测试）
    all_symbols = detector.db.get_stock_list()[:100]  # 先测试前100只
    anomalies = detector.scan_market(all_symbols, min_score=70)

    if not anomalies.empty:
        print("\nTop 10 Anomalies:")
        print(anomalies[['symbol', 'score', 'volatility', 'volume', 'structure']].head(10))