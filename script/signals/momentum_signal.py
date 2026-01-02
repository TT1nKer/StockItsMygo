"""
Momentum Signal Scanner (Layer 2)

Scans for stocks with strong momentum trends.
Returns List[WatchlistCandidate] for workflow consumption.

Philosophy: Identifies trending opportunities, not predictions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from script.signals.base import SignalScanner, WatchlistCandidate, AnomalyTags
from db.api import StockDB
from typing import List
from datetime import datetime, timedelta
import pandas as pd


class MomentumSignal(SignalScanner):
    """
    Momentum-based signal scanner

    Detects stocks with:
    - Strong 20-day price momentum (> 5%)
    - Volume confirmation (volume ratio > 1.2x)
    - Breakout patterns
    """

    def __init__(self):
        self.db = StockDB()

    def scan(self,
             min_score: int = 70,
             limit: int = 50,
             min_price: float = 5.0,
             max_price: float = 200.0,
             min_volume: int = 500000,
             **kwargs) -> List[WatchlistCandidate]:
        """
        Scan market for momentum signals

        Args:
            min_score: Minimum momentum score (0-100)
            limit: Maximum number of candidates
            min_price: Minimum stock price (avoid penny stocks)
            max_price: Maximum stock price
            min_volume: Minimum daily volume (liquidity filter)

        Returns:
            List[WatchlistCandidate] sorted by score descending
        """
        try:
            all_symbols = self.db.get_stock_list()
            candidates = []

            for symbol in all_symbols:
                try:
                    momentum_data = self._calculate_momentum(symbol)

                    if momentum_data is None:
                        continue

                    # Apply filters
                    if (momentum_data['price'] < min_price or
                        momentum_data['price'] > max_price or
                        momentum_data['volume'] < min_volume or
                        momentum_data['momentum_20d'] < 5 or  # At least 5% gain
                        momentum_data['volume_ratio'] < 1.2):  # Volume confirmation
                        continue

                    # Calculate score
                    score = self._calculate_score(momentum_data)

                    if score < min_score:
                        continue

                    # Build tags
                    tags = self._build_tags(momentum_data)

                    # Calculate stop loss
                    stop_loss = momentum_data['price'] * 0.95  # -5%
                    risk_pct = 5.0  # stored as positive percentage

                    # Create candidate
                    candidate = WatchlistCandidate(
                        symbol=symbol,
                        date=datetime.now().strftime('%Y-%m-%d'),
                        close=momentum_data['price'],
                        source='momentum',
                        score=score,
                        tags=tags,
                        stop_loss=stop_loss,
                        risk_pct=risk_pct,
                        metadata={
                            'momentum_20d': momentum_data['momentum_20d'],
                            'momentum_5d': momentum_data['momentum_5d'],
                            'volume_ratio': momentum_data['volume_ratio'],
                            'price_vs_ma20': momentum_data['price_vs_ma20'],
                            'volatility': momentum_data['volatility'],
                            'is_breakout': momentum_data['is_breakout']
                        }
                    )

                    candidates.append(candidate)

                except Exception:
                    continue

            # Sort by score descending
            candidates.sort(key=lambda x: x.score, reverse=True)

            return candidates[:limit]

        except Exception as e:
            print(f"[ERROR] Momentum scan failed: {e}")
            return []

    def _calculate_momentum(self, symbol: str, lookback_days: int = 20) -> dict:
        """Calculate momentum indicators for a symbol"""
        try:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            df = self.db.get_price_history(symbol, start_date=start_date)

            if df is None or len(df) < lookback_days + 10:
                return None

            df = df.sort_values('date').reset_index(drop=True)

            # 1. Price momentum (20-day gain)
            price_momentum = ((df.iloc[-1]['close'] - df.iloc[-lookback_days]['close'])
                             / df.iloc[-lookback_days]['close'] * 100)

            # 2. Volume momentum (recent 5d avg vs previous 20d avg)
            recent_volume = df.tail(5)['volume'].mean()
            avg_volume = df.iloc[-25:-5]['volume'].mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

            # 3. Relative strength (vs MA20)
            df['ma20'] = df['close'].rolling(window=20).mean()
            latest_price = df.iloc[-1]['close']
            ma20 = df.iloc[-1]['ma20']
            price_vs_ma20 = ((latest_price - ma20) / ma20 * 100) if pd.notna(ma20) else 0

            # 4. Recent performance (5-day)
            recent_gain = ((df.iloc[-1]['close'] - df.iloc[-5]['close'])
                          / df.iloc[-5]['close'] * 100)

            # 5. Volatility (for risk assessment)
            returns = df['close'].pct_change()
            volatility = returns.tail(20).std() * 100

            # 6. Breakout detection
            recent_high = df.tail(20)['high'].max()
            is_breakout = latest_price >= recent_high * 0.99

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

        except Exception:
            return None

    def _calculate_score(self, data: dict) -> int:
        """
        Calculate momentum score (0-100)

        Scoring components:
        - Strong momentum (20d > 20%): 40 points
        - Volume surge (> 2x): 25 points
        - Breakout: 20 points
        - Recent strength (5d > 3%): 15 points
        - Risk penalty (high volatility): -10 points
        """
        score = 0

        # 1. Price momentum (max 40 points)
        if data['momentum_20d'] > 20:
            score += 40
        elif data['momentum_20d'] > 10:
            score += 25
        elif data['momentum_20d'] > 5:
            score += 15

        # 2. Volume confirmation (max 25 points)
        if data['volume_ratio'] > 2.0:
            score += 25
        elif data['volume_ratio'] > 1.5:
            score += 15
        elif data['volume_ratio'] > 1.2:
            score += 10

        # 3. Breakout (20 points)
        if data['is_breakout']:
            score += 20
        elif data['price_vs_ma20'] > 5:
            score += 10

        # 4. Recent strength (max 15 points)
        if data['momentum_5d'] > 3:
            score += 15
        elif data['momentum_5d'] > 0:
            score += 8

        # 5. Risk adjustment (volatility penalty)
        if data['volatility'] > 5:
            score -= 10

        return max(0, min(100, score))

    def _build_tags(self, data: dict) -> List[str]:
        """Build tag list based on momentum characteristics"""
        tags = []

        if data['is_breakout']:
            tags.append(AnomalyTags.BREAKOUT)

        if data['volume_ratio'] > 1.5:
            tags.append(AnomalyTags.VOLUME_SPIKE)

        # Add MOMENTUM_CONFIRM as auxiliary tag
        if data['momentum_20d'] > 10:
            tags.append(AnomalyTags.MOMENTUM_CONFIRM)

        return tags


# For backward compatibility and standalone usage
class MomentumScanner:
    """
    DEPRECATED: Use MomentumSignal instead.

    This wrapper maintains backward compatibility with existing code.
    Will be removed in future version.
    """

    def __init__(self, capital=2000, max_position_pct=0.35):
        import warnings
        warnings.warn(
            "MomentumScanner is deprecated. Use MomentumSignal instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.signal = MomentumSignal()
        self.capital = capital
        self.max_position = capital * max_position_pct

    def scan_market(self, min_price=5, max_price=200, min_volume=500000, top_n=20):
        """Backward compatible scan_market method"""
        candidates = self.signal.scan(
            min_score=70,
            limit=top_n,
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume
        )

        # Convert to old format for compatibility
        results = []
        for c in candidates:
            results.append({
                'symbol': c.symbol,
                'price': c.close,
                'momentum_score': c.score,
                'momentum_20d': c.metadata.get('momentum_20d', 0),
                'momentum_5d': c.metadata.get('momentum_5d', 0),
                'volume_ratio': c.metadata.get('volume_ratio', 0),
                'is_breakout': c.metadata.get('is_breakout', False),
                'stop_loss': c.stop_loss,
                'take_profit': c.close * 1.12  # +12%
            })

        return results


def main():
    """Test the momentum signal scanner"""
    print("=" * 80)
    print("MOMENTUM SIGNAL SCANNER TEST")
    print("=" * 80)
    print()

    scanner = MomentumSignal()

    print("Scanning market for momentum signals...")
    candidates = scanner.scan(min_score=70, limit=10)

    print(f"\nFound {len(candidates)} momentum signals (score >= 70)")
    print()

    if candidates:
        print("Top Momentum Signals:")
        print("-" * 80)

        for i, c in enumerate(candidates[:10], 1):
            print(f"\n{i}. {c.symbol} - Score: {c.score}/100")
            print(f"   Price: ${c.close:.2f}")
            print(f"   Tags: {', '.join(c.tags)}")
            print(f"   Momentum 20d: {c.metadata.get('momentum_20d', 0):.1f}%")
            print(f"   Volume Ratio: {c.metadata.get('volume_ratio', 0):.2f}x")
            print(f"   Stop Loss: ${c.stop_loss:.2f} ({c.risk_pct:.1f}%)")


if __name__ == '__main__':
    main()
