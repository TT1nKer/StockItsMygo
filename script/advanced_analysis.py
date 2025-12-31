"""
Advanced Technical Analysis Engine
高级技术分析引擎

Features:
- 20+ Technical Indicators (ADX, Stochastic, ATR, OBV, VWAP, etc.)
- Candlestick Pattern Recognition (Hammer, Doji, Engulfing, etc.)
- Support/Resistance Levels (Pivot Points, Local highs/lows)
- Comprehensive Scoring System (0-100)
- Signal Generation with detailed reasoning

功能:
- 20+技术指标 (ADX, 随机指标, ATR, OBV, VWAP等)
- K线形态识别 (锤子线, 十字星, 吞没形态等)
- 支撑阻力位 (枢轴点, 局部高低点)
- 综合评分系统 (0-100分)
- 信号生成及详细理由
"""

from db.api import StockDB
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class AdvancedAnalyzer:
    """高级技术分析器"""

    def __init__(self):
        self.db = StockDB()

    # ============ 趋势指标 (Trend Indicators) ============

    def calculate_adx(self, df, period=14):
        """
        计算ADX (Average Directional Index) - 趋势强度指标

        Args:
            df: DataFrame with OHLC data
            period: ADX计算周期

        Returns:
            dict: {'adx': float, 'plus_di': float, 'minus_di': float}
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # 计算True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 计算方向性移动 (+DM, -DM)
        plus_dm = high - high.shift(1)
        minus_dm = low.shift(1) - low

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[(plus_dm - minus_dm) < 0] = 0
        minus_dm[(minus_dm - plus_dm) < 0] = 0

        # 平滑TR, +DM, -DM
        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

        # 计算DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period, adjust=False).mean()

        return {
            'adx': adx.iloc[-1],
            'plus_di': plus_di.iloc[-1],
            'minus_di': minus_di.iloc[-1]
        }

    def calculate_ma_alignment(self, df):
        """
        计算MA排列 (MA Alignment)
        完美看涨: Close > MA5 > MA10 > MA20 > MA60
        完美看跌: Close < MA5 < MA10 < MA20 < MA60

        Returns:
            dict: {'alignment': str, 'score': int}
        """
        close = df['close'].iloc[-1]
        ma5 = df['close'].tail(5).mean()
        ma10 = df['close'].tail(10).mean()
        ma20 = df['close'].tail(20).mean()
        ma60 = df['close'].tail(60).mean() if len(df) >= 60 else ma20

        # 看涨排列
        if close > ma5 > ma10 > ma20 > ma60:
            return {'alignment': 'Perfect Bullish', 'score': 100}
        elif close > ma5 > ma10 > ma20:
            return {'alignment': 'Strong Bullish', 'score': 80}
        elif close > ma5 > ma10:
            return {'alignment': 'Bullish', 'score': 60}

        # 看跌排列
        elif close < ma5 < ma10 < ma20 < ma60:
            return {'alignment': 'Perfect Bearish', 'score': 0}
        elif close < ma5 < ma10 < ma20:
            return {'alignment': 'Strong Bearish', 'score': 20}
        elif close < ma5 < ma10:
            return {'alignment': 'Bearish', 'score': 40}

        else:
            return {'alignment': 'Neutral', 'score': 50}

    # ============ 动量指标 (Momentum Indicators) ============

    def calculate_stochastic(self, df, k_period=14, d_period=3):
        """
        计算Stochastic Oscillator (随机指标)

        Returns:
            dict: {'k': float, 'd': float, 'signal': str}
        """
        high = df['high'].tail(k_period)
        low = df['low'].tail(k_period)
        close = df['close'].iloc[-1]

        highest_high = high.max()
        lowest_low = low.min()

        if highest_high == lowest_low:
            k = 50
        else:
            k = 100 * (close - lowest_low) / (highest_high - lowest_low)

        # 简化的D值 (K的3周期移动平均)
        k_values = []
        for i in range(min(d_period, len(df))):
            idx = -(i + 1)
            h = df['high'].iloc[max(0, idx-k_period):idx+1].max()
            l = df['low'].iloc[max(0, idx-k_period):idx+1].max()
            c = df['close'].iloc[idx]
            if h != l:
                k_values.append(100 * (c - l) / (h - l))

        d = np.mean(k_values) if k_values else k

        # 判断信号
        if k > 80:
            signal = 'Overbought'
        elif k < 20:
            signal = 'Oversold'
        else:
            signal = 'Neutral'

        return {'k': k, 'd': d, 'signal': signal}

    def calculate_atr(self, df, period=14):
        """
        计算ATR (Average True Range) - 真实波幅/波动率

        Returns:
            float: ATR值
        """
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        return atr.iloc[-1]

    def calculate_obv(self, df):
        """
        计算OBV (On-Balance Volume) - 能量潮

        Returns:
            dict: {'obv': float, 'trend': str}
        """
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        obv_ma = obv.tail(20).mean()

        current_obv = obv.iloc[-1]
        trend = 'Rising' if current_obv > obv_ma else 'Falling'

        return {'obv': current_obv, 'trend': trend}

    def calculate_vwap(self, df_intraday):
        """
        计算VWAP (Volume Weighted Average Price) - 成交量加权均价
        需要分钟级数据

        Returns:
            float: VWAP值
        """
        if df_intraday is None or len(df_intraday) == 0:
            return None

        typical_price = (df_intraday['high'] + df_intraday['low'] + df_intraday['close']) / 3
        vwap = (typical_price * df_intraday['volume']).sum() / df_intraday['volume'].sum()

        return vwap

    # ============ K线形态识别 (Candlestick Patterns) ============

    def detect_hammer(self, row):
        """检测锤子线 (Hammer) - 看涨反转信号"""
        body = abs(row['close'] - row['open'])
        total_range = row['high'] - row['low']
        lower_shadow = min(row['open'], row['close']) - row['low']
        upper_shadow = row['high'] - max(row['open'], row['close'])

        if total_range == 0:
            return False

        # 锤子线特征：下影线长，实体小，上影线短
        return (lower_shadow > body * 2 and
                upper_shadow < body * 0.5 and
                body / total_range < 0.3)

    def detect_shooting_star(self, row):
        """检测射击之星 (Shooting Star) - 看跌反转信号"""
        body = abs(row['close'] - row['open'])
        total_range = row['high'] - row['low']
        lower_shadow = min(row['open'], row['close']) - row['low']
        upper_shadow = row['high'] - max(row['open'], row['close'])

        if total_range == 0:
            return False

        # 射击之星特征：上影线长，实体小，下影线短
        return (upper_shadow > body * 2 and
                lower_shadow < body * 0.5 and
                body / total_range < 0.3)

    def detect_doji(self, row):
        """检测十字星 (Doji) - 犹豫不决信号"""
        body = abs(row['close'] - row['open'])
        total_range = row['high'] - row['low']

        if total_range == 0:
            return False

        # 十字星特征：实体极小
        return body / total_range < 0.1

    def detect_engulfing(self, df):
        """
        检测吞没形态 (Engulfing)

        Returns:
            str: 'Bullish Engulfing', 'Bearish Engulfing', or None
        """
        if len(df) < 2:
            return None

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        prev_body = abs(prev['close'] - prev['open'])
        curr_body = abs(curr['close'] - curr['open'])

        # 看涨吞没：前一天阴线，今天阳线，今天完全包住前一天
        if (prev['close'] < prev['open'] and
            curr['close'] > curr['open'] and
            curr['open'] < prev['close'] and
            curr['close'] > prev['open'] and
            curr_body > prev_body):
            return 'Bullish Engulfing'

        # 看跌吞没：前一天阳线，今天阴线，今天完全包住前一天
        if (prev['close'] > prev['open'] and
            curr['close'] < curr['open'] and
            curr['open'] > prev['close'] and
            curr['close'] < prev['open'] and
            curr_body > prev_body):
            return 'Bearish Engulfing'

        return None

    def detect_candlestick_patterns(self, df):
        """
        综合检测K线形态

        Returns:
            list: 检测到的形态列表
        """
        patterns = []

        if len(df) >= 1:
            last_row = df.iloc[-1]

            if self.detect_hammer(last_row):
                patterns.append('Hammer (Bullish)')
            if self.detect_shooting_star(last_row):
                patterns.append('Shooting Star (Bearish)')
            if self.detect_doji(last_row):
                patterns.append('Doji (Indecision)')

        if len(df) >= 2:
            engulfing = self.detect_engulfing(df)
            if engulfing:
                patterns.append(engulfing)

        return patterns

    # ============ 支撑阻力位 (Support/Resistance) ============

    def calculate_pivot_points(self, df):
        """
        计算经典枢轴点 (Pivot Points)

        Returns:
            dict: {'pivot', 'r1', 'r2', 'r3', 's1', 's2', 's3'}
        """
        last = df.iloc[-1]
        high = last['high']
        low = last['low']
        close = last['close']

        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)

        return {
            'pivot': pivot,
            'r1': r1, 'r2': r2, 'r3': r3,
            's1': s1, 's2': s2, 's3': s3
        }

    def find_support_resistance(self, df, window=20):
        """
        查找局部支撑阻力位

        Returns:
            dict: {'resistance': [list], 'support': [list]}
        """
        highs = df['high'].tail(window)
        lows = df['low'].tail(window)

        resistance_levels = []
        support_levels = []

        # 查找局部高点 (阻力位)
        for i in range(2, len(highs) - 2):
            if (highs.iloc[i] > highs.iloc[i-1] and
                highs.iloc[i] > highs.iloc[i-2] and
                highs.iloc[i] > highs.iloc[i+1] and
                highs.iloc[i] > highs.iloc[i+2]):
                resistance_levels.append(highs.iloc[i])

        # 查找局部低点 (支撑位)
        for i in range(2, len(lows) - 2):
            if (lows.iloc[i] < lows.iloc[i-1] and
                lows.iloc[i] < lows.iloc[i-2] and
                lows.iloc[i] < lows.iloc[i+1] and
                lows.iloc[i] < lows.iloc[i+2]):
                support_levels.append(lows.iloc[i])

        return {
            'resistance': sorted(resistance_levels, reverse=True)[:3],
            'support': sorted(support_levels, reverse=True)[:3]
        }

    # ============ 综合评分系统 (Comprehensive Scoring) ============

    def calculate_trend_score(self, df):
        """
        趋势评分 (0-100)
        权重35%

        Returns:
            dict: {'score': int, 'details': dict}
        """
        # ADX评分 (趋势强度)
        adx_result = self.calculate_adx(df)
        adx = adx_result['adx']
        plus_di = adx_result['plus_di']
        minus_di = adx_result['minus_di']

        if adx > 25:
            adx_score = min(100, (adx - 25) * 2)  # ADX > 25 表示强趋势
        else:
            adx_score = 0

        # 方向判断
        if plus_di > minus_di:
            direction_score = 100
        else:
            direction_score = 0

        # MA排列评分
        ma_result = self.calculate_ma_alignment(df)
        ma_score = ma_result['score']

        # 综合趋势评分
        trend_score = int((adx_score * 0.3 + direction_score * 0.3 + ma_score * 0.4))

        return {
            'score': trend_score,
            'details': {
                'adx': adx,
                'plus_di': plus_di,
                'minus_di': minus_di,
                'ma_alignment': ma_result['alignment']
            }
        }

    def calculate_momentum_score(self, df):
        """
        动量评分 (0-100)
        权重35%

        Returns:
            dict: {'score': int, 'details': dict}
        """
        # RSI评分 (假设已有RSI)
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if 40 < rsi < 70:
                rsi_score = 100  # 理想区间
            elif rsi > 70:
                rsi_score = 50  # 超买
            elif rsi < 30:
                rsi_score = 30  # 超卖
            else:
                rsi_score = 70
        else:
            # 手动计算简单RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).tail(14).mean()
            loss = (-delta.where(delta < 0, 0)).tail(14).mean()
            if loss == 0:
                rsi = 100
            else:
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
            rsi_score = 70 if 40 < rsi < 70 else 50

        # MACD评分 (假设已有MACD)
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd = df['macd'].iloc[-1]
            signal = df['macd_signal'].iloc[-1]

            if macd > signal and macd > 0:
                macd_score = 100  # 看涨交叉
            elif macd > signal:
                macd_score = 70  # 交叉但在零轴下方
            else:
                macd_score = 30  # 看跌
        else:
            macd_score = 50

        # Stochastic评分
        stoch_result = self.calculate_stochastic(df)
        k = stoch_result['k']

        if 20 < k < 80:
            stoch_score = 100  # 未超买超卖
        elif k > 80:
            stoch_score = 40  # 超买
        elif k < 20:
            stoch_score = 60  # 超卖（可能反转）
        else:
            stoch_score = 70

        # 综合动量评分
        momentum_score = int((rsi_score * 0.4 + macd_score * 0.35 + stoch_score * 0.25))

        return {
            'score': momentum_score,
            'details': {
                'rsi': rsi if 'rsi' not in df.columns else df['rsi'].iloc[-1],
                'macd': macd if 'macd' in df.columns else None,
                'stochastic_k': k,
                'stochastic_signal': stoch_result['signal']
            }
        }

    def calculate_volatility_score(self, df):
        """
        波动率评分 (0-100)
        权重15%
        低波动更优

        Returns:
            dict: {'score': int, 'details': dict}
        """
        atr = self.calculate_atr(df)
        close = df['close'].iloc[-1]

        # ATR相对于价格的百分比
        atr_pct = (atr / close) * 100

        # 低波动率得高分
        if atr_pct < 1:
            score = 100
        elif atr_pct < 2:
            score = 80
        elif atr_pct < 3:
            score = 60
        elif atr_pct < 5:
            score = 40
        else:
            score = 20

        return {
            'score': score,
            'details': {
                'atr': atr,
                'atr_pct': atr_pct
            }
        }

    def calculate_volume_score(self, df):
        """
        成交量评分 (0-100)
        权重15%

        Returns:
            dict: {'score': int, 'details': dict}
        """
        obv_result = self.calculate_obv(df)

        # 近期成交量 vs 平均成交量
        recent_volume = df['volume'].tail(5).mean()
        avg_volume = df['volume'].tail(20).mean()

        if avg_volume == 0:
            volume_ratio = 1
        else:
            volume_ratio = recent_volume / avg_volume

        # 成交量放大得高分
        if volume_ratio > 2.0:
            volume_score = 100
        elif volume_ratio > 1.5:
            volume_score = 85
        elif volume_ratio > 1.0:
            volume_score = 70
        elif volume_ratio > 0.8:
            volume_score = 50
        else:
            volume_score = 30

        # OBV趋势调整
        if obv_result['trend'] == 'Rising':
            volume_score = min(100, volume_score + 10)
        else:
            volume_score = max(0, volume_score - 10)

        return {
            'score': int(volume_score),
            'details': {
                'volume_ratio': volume_ratio,
                'obv_trend': obv_result['trend']
            }
        }

    def calculate_overall_score(self, df):
        """
        计算综合评分 (0-100)

        Returns:
            dict: {'overall_score': int, 'subscores': dict}
        """
        trend = self.calculate_trend_score(df)
        momentum = self.calculate_momentum_score(df)
        volatility = self.calculate_volatility_score(df)
        volume = self.calculate_volume_score(df)

        # 加权综合评分
        overall = int(
            trend['score'] * 0.35 +
            momentum['score'] * 0.35 +
            volatility['score'] * 0.15 +
            volume['score'] * 0.15
        )

        return {
            'overall_score': overall,
            'subscores': {
                'trend': trend,
                'momentum': momentum,
                'volatility': volatility,
                'volume': volume
            }
        }

    # ============ 信号生成 (Signal Generation) ============

    def generate_signal(self, overall_score):
        """
        根据综合评分生成交易信号

        Returns:
            dict: {'signal': str, 'confidence': int}
        """
        if overall_score >= 70:
            return {'signal': 'STRONG BUY', 'confidence': overall_score}
        elif overall_score >= 60:
            return {'signal': 'BUY', 'confidence': overall_score}
        elif overall_score >= 45:
            return {'signal': 'HOLD', 'confidence': overall_score}
        elif overall_score >= 35:
            return {'signal': 'SELL', 'confidence': 100 - overall_score}
        else:
            return {'signal': 'STRONG SELL', 'confidence': 100 - overall_score}

    def generate_reasoning(self, analysis):
        """
        生成详细的买卖理由

        Returns:
            list: 理由列表
        """
        reasons = []
        scores = analysis['subscores']

        # 趋势理由
        trend_score = scores['trend']['score']
        trend_details = scores['trend']['details']

        if trend_score > 70:
            reasons.append(f"强趋势确认 (ADX={trend_details['adx']:.1f})")
            if trend_details['plus_di'] > trend_details['minus_di']:
                reasons.append("方向指标显示上升趋势")
            reasons.append(f"MA排列: {trend_details['ma_alignment']}")
        elif trend_score < 30:
            reasons.append("弱趋势或下降趋势")

        # 动量理由
        momentum_score = scores['momentum']['score']
        momentum_details = scores['momentum']['details']

        if momentum_score > 70:
            reasons.append(f"动量指标强劲 (RSI={momentum_details['rsi']:.1f})")
            if momentum_details.get('macd') and momentum_details.get('macd') > 0:
                reasons.append("MACD看涨交叉")
        elif momentum_score < 30:
            reasons.append("动量减弱")

        # 波动率理由
        volatility_score = scores['volatility']['score']
        volatility_details = scores['volatility']['details']

        if volatility_score > 80:
            reasons.append(f"低波动率 (ATR={volatility_details['atr_pct']:.2f}%)")
        elif volatility_score < 40:
            reasons.append(f"高波动风险 (ATR={volatility_details['atr_pct']:.2f}%)")

        # 成交量理由
        volume_score = scores['volume']['score']
        volume_details = scores['volume']['details']

        if volume_score > 80:
            reasons.append(f"成交量放大 ({volume_details['volume_ratio']:.2f}x)")
        elif volume_score < 40:
            reasons.append("成交量萎缩")

        return reasons

    # ============ 完整分析 (Complete Analysis) ============

    def analyze_stock(self, symbol, include_intraday=False):
        """
        完整股票分析

        Args:
            symbol: 股票代码
            include_intraday: 是否包含分钟数据分析

        Returns:
            dict: 完整分析报告
        """
        try:
            # 获取日线数据
            df = self.db.get_price_history(symbol, start_date=(datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'))

            if len(df) < 60:
                return {'error': 'Insufficient data'}

            # 计算综合评分
            score_result = self.calculate_overall_score(df)
            overall_score = score_result['overall_score']

            # 生成信号
            signal_result = self.generate_signal(overall_score)

            # 生成理由
            reasons = self.generate_reasoning(score_result)

            # 检测K线形态
            patterns = self.detect_candlestick_patterns(df)

            # 计算支撑阻力位
            pivot_points = self.calculate_pivot_points(df)
            support_resistance = self.find_support_resistance(df)

            # VWAP (如果有分钟数据)
            vwap = None
            if include_intraday:
                df_intraday = self.db.get_intraday_data(
                    symbol,
                    interval='5m',
                    start_datetime=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                )
                if len(df_intraday) > 0:
                    vwap = self.calculate_vwap(df_intraday)

            return {
                'symbol': symbol,
                'price': df['close'].iloc[-1],
                'overall_score': overall_score,
                'signal': signal_result['signal'],
                'confidence': signal_result['confidence'],
                'scores': score_result['subscores'],
                'reasons': reasons,
                'patterns': patterns,
                'pivot_points': pivot_points,
                'support_resistance': support_resistance,
                'vwap': vwap,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            return {'error': str(e)}

    def print_analysis(self, analysis):
        """打印分析报告"""
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            return

        print("=" * 80)
        print(f"{analysis['symbol']} - 综合评分: {analysis['overall_score']}/100")
        print("=" * 80)
        print()

        print(f"**信号**: {analysis['signal']} (置信度: {analysis['confidence']}%)")
        print(f"**当前价格**: ${analysis['price']:.2f}")
        print()

        print("**趋势分析**:")
        trend = analysis['scores']['trend']
        print(f"  - 评分: {trend['score']}/100")
        print(f"  - ADX: {trend['details']['adx']:.1f}")
        print(f"  - 方向: +DI={trend['details']['plus_di']:.1f}, -DI={trend['details']['minus_di']:.1f}")
        print(f"  - MA排列: {trend['details']['ma_alignment']}")
        print()

        print("**动量分析**:")
        momentum = analysis['scores']['momentum']
        print(f"  - 评分: {momentum['score']}/100")
        print(f"  - RSI: {momentum['details']['rsi']:.1f}")
        print(f"  - Stochastic: K={momentum['details']['stochastic_k']:.1f} ({momentum['details']['stochastic_signal']})")
        print()

        print("**支撑阻力位**:")
        pp = analysis['pivot_points']
        print(f"  - R3: ${pp['r3']:.2f}")
        print(f"  - R2: ${pp['r2']:.2f}")
        print(f"  - R1: ${pp['r1']:.2f}")
        print(f"  - Pivot: ${pp['pivot']:.2f}")
        print(f"  - S1: ${pp['s1']:.2f}")
        print(f"  - S2: ${pp['s2']:.2f}")
        print(f"  - S3: ${pp['s3']:.2f}")
        print()

        if analysis['patterns']:
            print("**识别形态**:")
            for pattern in analysis['patterns']:
                print(f"  - {pattern}")
            print()

        print("**买卖建议**: " + analysis['signal'])
        print("**理由**:")
        for i, reason in enumerate(analysis['reasons'], 1):
            print(f"  {i}. {reason}")
        print()

        print("=" * 80)


# 使用示例
if __name__ == "__main__":
    analyzer = AdvancedAnalyzer()

    # 分析单只股票
    result = analyzer.analyze_stock('AAPL', include_intraday=True)
    analyzer.print_analysis(result)
