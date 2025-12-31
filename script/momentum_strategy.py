"""
Momentum Trading Strategy for Small Capital (2000 CAD)
小资金动量交易策略

Strategy Rules:
1. Find stocks with strong recent performance (20-day momentum)
2. Confirm with volume surge (volume > 1.5x average)
3. Enter when price breaks above recent high
4. Exit with trailing stop or when momentum weakens

风险管理:
- 每次交易最多投入30-40%资金 (600-800 CAD)
- 止损: -3% 到 -5%
- 止盈: +8% 到 +15%
- 最多持有2-3只股票
"""

from db.api import StockDB
import pandas as pd
from datetime import datetime, timedelta

class MomentumScanner:
    def __init__(self, capital=2000, max_position_pct=0.35):
        """
        初始化动量扫描器

        Args:
            capital: 总资金 (默认2000)
            max_position_pct: 单个仓位最大占比 (默认35%)
        """
        self.db = StockDB()
        self.capital = capital
        self.max_position = capital * max_position_pct

    def calculate_momentum(self, symbol, lookback_days=20):
        """
        计算股票的动量指标

        Returns:
            dict: 包含各种动量指标
        """
        # 获取过去3个月数据
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        df = self.db.get_price_history(symbol, start_date=start_date)

        if len(df) < lookback_days + 10:
            return None

        # 计算各种指标
        df = df.sort_values('date').reset_index(drop=True)

        # 1. 价格动量 (过去N天涨幅)
        price_momentum = ((df.iloc[-1]['close'] - df.iloc[-lookback_days]['close'])
                         / df.iloc[-lookback_days]['close'] * 100)

        # 2. 成交量动量 (最近5天平均 vs 之前20天平均)
        recent_volume = df.tail(5)['volume'].mean()
        avg_volume = df.iloc[-25:-5]['volume'].mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

        # 3. 相对强弱 (与20日均价比较)
        df['ma20'] = df['close'].rolling(window=20).mean()
        latest_price = df.iloc[-1]['close']
        ma20 = df.iloc[-1]['ma20']
        price_vs_ma20 = ((latest_price - ma20) / ma20 * 100) if pd.notna(ma20) else 0

        # 4. 近期表现 (最近5天)
        recent_gain = ((df.iloc[-1]['close'] - df.iloc[-5]['close'])
                      / df.iloc[-5]['close'] * 100)

        # 5. 波动率 (用于风险评估)
        returns = df['close'].pct_change()
        volatility = returns.tail(20).std() * 100

        # 6. 突破检测 (是否突破近期高点)
        recent_high = df.tail(20)['high'].max()
        is_breakout = latest_price >= recent_high * 0.99  # 接近或突破

        return {
            'symbol': symbol,
            'price': latest_price,
            'momentum_20d': price_momentum,
            'momentum_5d': recent_gain,
            'volume_ratio': volume_ratio,
            'price_vs_ma20': price_vs_ma20,
            'volatility': volatility,
            'is_breakout': is_breakout,
            'ma20': ma20,
            'recent_high': recent_high,
            'volume': df.iloc[-1]['volume']
        }

    def scan_market(self, min_price=5, max_price=200, min_volume=500000, top_n=20):
        """
        扫描市场寻找动量股票

        Args:
            min_price: 最低价格 (避免垃圾股)
            max_price: 最高价格 (小资金避免太贵的股票)
            min_volume: 最低成交量 (保证流动性)
            top_n: 返回前N只股票
        """
        print("=" * 70)
        print(f"Momentum Stock Scanner - Scanning Market...")
        print(f"Capital: ${self.capital:.2f} | Max Position: ${self.max_position:.2f}")
        print("=" * 70)
        print()

        all_stocks = self.db.get_stock_list()
        candidates = []

        print(f"Analyzing {len(all_stocks)} stocks...")
        print()

        for i, symbol in enumerate(all_stocks, 1):
            if i % 200 == 0:
                print(f"Progress: {i}/{len(all_stocks)} ({i/len(all_stocks)*100:.1f}%)")

            try:
                momentum = self.calculate_momentum(symbol)

                if momentum is None:
                    continue

                # 过滤条件
                if (momentum['price'] >= min_price and
                    momentum['price'] <= max_price and
                    momentum['volume'] >= min_volume and
                    momentum['momentum_20d'] > 5 and  # 20天涨幅 > 5%
                    momentum['volume_ratio'] > 1.2):  # 成交量放大

                    candidates.append(momentum)

            except Exception as e:
                continue

        print()
        print(f"Found {len(candidates)} candidates")
        print()

        # 按20日动量排序
        candidates_df = pd.DataFrame(candidates)
        if len(candidates_df) == 0:
            print("No stocks found matching criteria")
            return candidates_df

        candidates_df = candidates_df.sort_values('momentum_20d', ascending=False)

        return candidates_df.head(top_n)

    def generate_signals(self, candidates_df):
        """
        生成交易信号

        Returns:
            list: BUY信号列表，按优先级排序
        """
        if len(candidates_df) == 0:
            return []

        signals = []

        for _, row in candidates_df.iterrows():
            # 评分系统 (0-100)
            score = 0
            reasons = []

            # 1. 强劲动量 (最高40分)
            if row['momentum_20d'] > 20:
                score += 40
                reasons.append("Strong 20d momentum")
            elif row['momentum_20d'] > 10:
                score += 25
                reasons.append("Good 20d momentum")

            # 2. 成交量确认 (最高25分)
            if row['volume_ratio'] > 2.0:
                score += 25
                reasons.append("Huge volume surge")
            elif row['volume_ratio'] > 1.5:
                score += 15
                reasons.append("Volume surge")

            # 3. 价格位置 (最高20分)
            if row['is_breakout']:
                score += 20
                reasons.append("Breakout")
            elif row['price_vs_ma20'] > 5:
                score += 10
                reasons.append("Above MA20")

            # 4. 近期强势 (最高15分)
            if row['momentum_5d'] > 3:
                score += 15
                reasons.append("Recent strength")
            elif row['momentum_5d'] > 0:
                score += 8
                reasons.append("Positive short-term")

            # 风险调整
            if row['volatility'] > 5:
                score -= 10
                reasons.append("High volatility (risk)")

            # 计算建议仓位
            shares = int(self.max_position / row['price'])
            position_value = shares * row['price']

            # 止损价和止盈价
            stop_loss = row['price'] * 0.95  # -5%
            take_profit = row['price'] * 1.12  # +12%

            signals.append({
                'symbol': row['symbol'],
                'score': score,
                'price': row['price'],
                'momentum_20d': row['momentum_20d'],
                'momentum_5d': row['momentum_5d'],
                'volume_ratio': row['volume_ratio'],
                'reasons': ', '.join(reasons),
                'shares': shares,
                'position_value': position_value,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            })

        # 按评分排序
        signals = sorted(signals, key=lambda x: x['score'], reverse=True)

        return signals

    def print_signals(self, signals, top_n=10):
        """打印交易信号"""
        print("=" * 90)
        print("TOP MOMENTUM TRADING SIGNALS")
        print("=" * 90)
        print()

        if len(signals) == 0:
            print("No signals generated")
            return

        for i, signal in enumerate(signals[:top_n], 1):
            print(f"{i}. {signal['symbol']} - Score: {signal['score']}/100")
            print(f"   Price: ${signal['price']:.2f}")
            print(f"   Momentum: 20d={signal['momentum_20d']:.1f}%, 5d={signal['momentum_5d']:.1f}%")
            print(f"   Volume Ratio: {signal['volume_ratio']:.2f}x")
            print(f"   Reasons: {signal['reasons']}")
            print()
            print(f"   TRADE PLAN:")
            print(f"   - Buy: {signal['shares']} shares @ ${signal['price']:.2f} = ${signal['position_value']:.2f}")
            print(f"   - Stop Loss: ${signal['stop_loss']:.2f} (-5%)")
            print(f"   - Take Profit: ${signal['take_profit']:.2f} (+12%)")
            print(f"   - Risk/Reward: 1:2.4")
            print()
            print("-" * 90)

        print()
        print("RISK MANAGEMENT:")
        print(f"- Max 2-3 positions at once")
        print(f"- Max ${self.max_position:.2f} per position")
        print(f"- Always use stop loss (-5%)")
        print(f"- Take profit at +12% or trail stop")
        print("=" * 90)


def main():
    """运行动量策略扫描"""
    # 初始化 (2000加元资金)
    scanner = MomentumScanner(capital=2000, max_position_pct=0.35)

    # 扫描市场
    candidates = scanner.scan_market(
        min_price=5,      # 最低$5
        max_price=100,    # 最高$100 (小资金买得起)
        min_volume=500000,  # 至少50万成交量
        top_n=30
    )

    # 生成信号
    signals = scanner.generate_signals(candidates)

    # 打印结果
    scanner.print_signals(signals, top_n=10)


if __name__ == '__main__':
    main()
