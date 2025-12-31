"""
Anomaly Signal Scanner (Layer 2)

Scans for stocks with structural anomalies.
Returns List[WatchlistCandidate] for workflow consumption.

Philosophy: Anomaly ≠ prediction, Anomaly = worth risking -1R
Focuses on "relative to own history, suddenly unlike usual"
"""

import sys
sys.path.insert(0, 'd:/strategy=Z')

from script.signals.base import SignalScanner, WatchlistCandidate, AnomalyTags
from db.api import StockDB
from typing import List, Dict
from datetime import datetime
import pandas as pd
import numpy as np


class AnomalySignal(SignalScanner):
    """
    Anomaly-based signal scanner

    Detects structural anomalies:
    - Core 3 factors: Volatility + Volume + Clear Structure
    - Auxiliary factors: Dollar volume, gaps, breakouts
    - Noise filters: Low liquidity, penny stocks, corporate actions
    """

    def __init__(self):
        self.db = StockDB()

        # Anomaly detection parameters
        self.params = {
            'atr_long_period': 20,
            'volatility_threshold': 2.0,      # TR/ATR > 2x
            'volume_threshold': 1.5,          # Volume/MA > 1.5x
            'volume_ma_period': 20,
            'dollar_volume_percentile': 0.7,  # Top 30%
            'min_price': 5.0,                 # Penny stock filter
            'min_dollar_volume': 1_000_000,   # Liquidity filter
            'corporate_action_gap': 0.50,     # 50% gap = likely corporate action
        }

    def scan(self,
             min_score: int = 60,
             limit: int = 50,
             symbols: List[str] = None,
             **kwargs) -> List[WatchlistCandidate]:
        """
        Scan for anomaly signals

        Args:
            min_score: Minimum anomaly score (0-100)
            limit: Maximum number of candidates
            symbols: Optional list of symbols to scan (if None, scans subset)

        Returns:
            List[WatchlistCandidate] sorted by score descending
        """
        try:
            if symbols is None:
                # Quick scan: use limited symbol list
                all_symbols = self.db.get_stock_list()[:200]
            else:
                all_symbols = symbols

            candidates = []

            for symbol in all_symbols:
                try:
                    df = self.db.get_price_history(symbol)

                    if df is None or len(df) < 60:
                        continue

                    df = df.sort_values('date').reset_index(drop=True)

                    # Apply noise filters first (fail fast)
                    if self._is_noise(df):
                        continue

                    # Detect core 3 factors
                    volatility_anomaly = self._detect_volatility_anomaly(df)
                    volume_spike = self._detect_volume_spike(df)
                    clear_structure = self._detect_clear_structure(df)

                    # Check auxiliary factors
                    liquidity_ok = self._check_liquidity(df)
                    gap_detected = self._detect_gap(df)
                    breakout_detected = self._detect_breakout(df)

                    # Build tags
                    tags = []
                    if volatility_anomaly['detected']:
                        tags.append(AnomalyTags.VOLATILITY_EXPANSION)
                    if volume_spike['detected']:
                        tags.append(AnomalyTags.VOLUME_SPIKE)
                    if clear_structure['detected']:
                        tags.append(AnomalyTags.CLEAR_STRUCTURE)
                    if gap_detected:
                        tags.append(AnomalyTags.GAP)
                    if breakout_detected:
                        tags.append(AnomalyTags.BREAKOUT)
                    if liquidity_ok:
                        tags.append(AnomalyTags.DOLLAR_VOLUME)

                    # Calculate score
                    score = self._calculate_score(
                        volatility_anomaly, volume_spike, clear_structure,
                        gap_detected, breakout_detected, liquidity_ok
                    )

                    # Noise filter: no liquidity = score 0
                    if not liquidity_ok:
                        score = 0

                    if score < min_score:
                        continue

                    # Get latest data
                    latest = df.iloc[-1]

                    # Create candidate
                    candidate = WatchlistCandidate(
                        symbol=symbol,
                        date=latest['date'],
                        close=latest['close'],
                        source='anomaly',
                        score=score,
                        tags=tags,
                        stop_loss=clear_structure.get('stop_loss'),
                        risk_pct=clear_structure.get('risk_pct'),
                        metadata={
                            'volatility_ratio': volatility_anomaly.get('ratio', 0),
                            'volume_ratio': volume_spike.get('ratio', 0),
                            'has_structure': clear_structure['detected'],
                            'gap_detected': gap_detected,
                            'breakout_detected': breakout_detected,
                        }
                    )

                    candidates.append(candidate)

                except Exception:
                    continue

            # Sort by score descending
            candidates.sort(key=lambda x: x.score, reverse=True)

            return candidates[:limit]

        except Exception as e:
            print(f"[ERROR] Anomaly scan failed: {e}")
            return []

    def _is_noise(self, df: pd.DataFrame) -> bool:
        """
        Check noise filters (one-vote veto)

        Returns True if stock should be filtered out
        """
        latest = df.iloc[-1]

        # NOISE_FILTER 1: Penny stock (price < $5)
        if latest['close'] < self.params['min_price']:
            return True

        # NOISE_FILTER 2: Corporate action (single-day gap > 50%)
        if len(df) >= 2:
            prev_close = df.iloc[-2]['close']
            gap = abs(latest['close'] - prev_close) / prev_close
            if gap > self.params['corporate_action_gap']:
                return True

        return False

    def _detect_volatility_anomaly(self, df: pd.DataFrame) -> Dict:
        """
        STRUCTURAL: Volatility expansion detection

        Logic: TR / ATR_long > threshold
        """
        # Calculate True Range
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df.apply(
            lambda row: max(
                row['high'] - row['low'],
                abs(row['high'] - row['prev_close']) if pd.notna(row['prev_close']) else 0,
                abs(row['low'] - row['prev_close']) if pd.notna(row['prev_close']) else 0
            ),
            axis=1
        )

        # ATR long-term
        df['atr_long'] = df['tr'].rolling(window=self.params['atr_long_period']).mean()

        latest = df.iloc[-1]

        if pd.notna(latest['atr_long']) and latest['atr_long'] > 0:
            ratio = latest['tr'] / latest['atr_long']
            detected = ratio > self.params['volatility_threshold']

            return {
                'detected': detected,
                'ratio': ratio,
                'tr': latest['tr'],
                'atr_long': latest['atr_long']
            }

        return {'detected': False, 'ratio': 0}

    def _detect_volume_spike(self, df: pd.DataFrame) -> Dict:
        """
        STRUCTURAL: Volume spike detection

        Logic: Volume / MA(Volume) > threshold
        """
        df['volume_ma'] = df['volume'].rolling(window=self.params['volume_ma_period']).mean()

        latest = df.iloc[-1]

        if pd.notna(latest['volume_ma']) and latest['volume_ma'] > 0:
            ratio = latest['volume'] / latest['volume_ma']
            detected = ratio > self.params['volume_threshold']

            return {
                'detected': detected,
                'ratio': ratio,
                'volume': latest['volume'],
                'volume_ma': latest['volume_ma']
            }

        return {'detected': False, 'ratio': 0}

    def _detect_clear_structure(self, df: pd.DataFrame) -> Dict:
        """
        STRUCTURAL: Clear structure (natural stop-loss exists)

        Logic: Find recent swing low as natural stop level
        """
        if len(df) < 20:
            return {'detected': False}

        recent_20 = df.tail(20)
        latest = df.iloc[-1]

        # Find swing low (lowest low in recent period)
        swing_low = recent_20['low'].min()

        # Stop loss: slightly below swing low
        stop_loss = swing_low * 0.98

        # Risk percentage (stored as positive value)
        if latest['close'] > 0:
            risk_pct = abs((latest['close'] - stop_loss) / latest['close'] * 100)

            # Structure is clear if risk is reasonable (<7%)
            detected = 0 < risk_pct < 7.0

            return {
                'detected': detected,
                'stop_loss': stop_loss,
                'risk_pct': risk_pct,
                'swing_low': swing_low
            }

        return {'detected': False}

    def _check_liquidity(self, df: pd.DataFrame) -> bool:
        """
        AUXILIARY: Dollar volume check (not a filter, but adds score)

        Returns True if dollar volume > threshold
        """
        if len(df) < 20:
            return False

        recent_20 = df.tail(20).copy()

        # Calculate dollar volume
        recent_20['dollar_volume'] = recent_20['close'] * recent_20['volume']

        median_dollar_volume = recent_20['dollar_volume'].median()

        return median_dollar_volume >= self.params['min_dollar_volume']

    def _detect_gap(self, df: pd.DataFrame) -> bool:
        """
        STRUCTURAL: Gap detection (跳空 > 1%)
        """
        if len(df) < 2:
            return False

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        gap = abs(latest['open'] - prev['close']) / prev['close']

        return gap > 0.01  # 1% gap

    def _detect_breakout(self, df: pd.DataFrame) -> bool:
        """
        STRUCTURAL: Breakout detection (突破20日高点)
        """
        if len(df) < 20:
            return False

        recent_20 = df.iloc[-20:]
        latest = df.iloc[-1]

        recent_high = recent_20['high'].max()

        # Breakout if close >= 99% of recent high
        return latest['close'] >= recent_high * 0.99

    def _calculate_score(self,
                        volatility: Dict,
                        volume: Dict,
                        structure: Dict,
                        gap: bool,
                        breakout: bool,
                        liquidity: bool) -> int:
        """
        Calculate anomaly score (0-100)

        Scoring rules:
        - Core 3 factors (90 points total):
          - VOLATILITY_EXPANSION: 30
          - VOLUME_SPIKE: 30
          - CLEAR_STRUCTURE: 30
        - Auxiliary bonus (max +20):
          - BREAKOUT: +10
          - GAP: +5
          - DOLLAR_VOLUME: +5
        - Noise veto: handled in scan()
        """
        score = 0

        # Core 3 factors (structural, worth 90 points)
        if volatility['detected']:
            score += 30
        if volume['detected']:
            score += 30
        if structure['detected']:
            score += 30

        # Auxiliary bonus (max +20)
        if breakout:
            score += 10
        if gap:
            score += 5
        if liquidity:
            score += 5

        return min(100, score)


# Backward compatibility wrapper
class AnomalyDetector:
    """
    DEPRECATED: Use AnomalySignal instead.

    This wrapper maintains backward compatibility.
    Will be removed in future version.
    """

    def __init__(self):
        import warnings
        warnings.warn(
            "AnomalyDetector is deprecated. Use AnomalySignal instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.signal = AnomalySignal()
        self.db = self.signal.db
        self.params = self.signal.params

    def quick_scan_symbols(self, symbols: List[str], min_score: int = 60) -> pd.DataFrame:
        """Backward compatible quick_scan method"""
        candidates = self.signal.scan(min_score=min_score, symbols=symbols, limit=100)

        if not candidates:
            return pd.DataFrame()

        # Convert to old DataFrame format
        results = []
        for c in candidates:
            results.append({
                'symbol': c.symbol,
                'score': c.score,
                'close': c.close,
                'volatility': c.has_tag(AnomalyTags.VOLATILITY_EXPANSION),
                'volume': c.has_tag(AnomalyTags.VOLUME_SPIKE),
                'structure': c.has_tag(AnomalyTags.CLEAR_STRUCTURE),
                'stop_loss': c.stop_loss if c.stop_loss else 0,
                'risk_pct': c.risk_pct if c.risk_pct else 0,
            })

        return pd.DataFrame(results)

    def analyze_stock(self, symbol: str) -> Dict:
        """Backward compatible analyze_stock method"""
        candidates = self.signal.scan(min_score=0, symbols=[symbol], limit=1)

        if not candidates:
            return {'error': f'No data for {symbol}'}

        c = candidates[0]

        return {
            'symbol': c.symbol,
            'date': c.date,
            'close': c.close,
            'anomaly_score': c.score,
            'tradeable': c.score >= 60,
            'anomalies': {
                'volatility': {
                    'detected': c.has_tag(AnomalyTags.VOLATILITY_EXPANSION),
                    'description': 'Volatility expansion (TR/ATR > 2x)'
                },
                'volume': {
                    'detected': c.has_tag(AnomalyTags.VOLUME_SPIKE),
                    'description': 'Volume spike (> 1.5x average)'
                },
                'structure': {
                    'detected': c.has_tag(AnomalyTags.CLEAR_STRUCTURE),
                    'description': 'Clear structure (natural stop exists)',
                    'stop_loss': c.stop_loss,
                    'risk_pct': c.risk_pct
                },
                'gap': {
                    'detected': c.has_tag(AnomalyTags.GAP),
                    'description': 'Gap detected (> 1%)'
                },
                'breakout': {
                    'detected': c.has_tag(AnomalyTags.BREAKOUT),
                    'description': 'Breakout (near 20d high)'
                }
            }
        }


def main():
    """Test the anomaly signal scanner"""
    print("=" * 80)
    print("ANOMALY SIGNAL SCANNER TEST")
    print("=" * 80)
    print()

    scanner = AnomalySignal()

    # Test with a few specific symbols
    test_symbols = ['AAPL', 'NVDA', 'TSLA', 'AMD', 'MSFT']

    print(f"Scanning {len(test_symbols)} symbols for anomalies...")
    candidates = scanner.scan(min_score=60, symbols=test_symbols)

    print(f"\nFound {len(candidates)} anomaly signals (score >= 60)")
    print()

    if candidates:
        print("Anomaly Signals:")
        print("-" * 80)

        for i, c in enumerate(candidates, 1):
            print(f"\n{i}. {c.symbol} - Score: {c.score}/100")
            print(f"   Close: ${c.close:.2f}")
            print(f"   Tags: {', '.join(c.tags)}")
            print(f"   Core 3-Factor: {c.is_core_three_factor()}")

            if c.stop_loss:
                print(f"   Stop Loss: ${c.stop_loss:.2f} ({c.risk_pct:.1f}%)")

            print(f"   Metadata:")
            for key, value in c.metadata.items():
                if isinstance(value, float):
                    print(f"     {key}: {value:.2f}")
                else:
                    print(f"     {key}: {value}")
    else:
        print("No anomalies detected in test symbols")
        print("(This is normal - anomalies are rare events)")


if __name__ == '__main__':
    main()
