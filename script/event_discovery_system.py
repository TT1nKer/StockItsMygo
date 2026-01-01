"""
Event Discovery System - 事件发现系统
================================================================================

System Positioning:
    An event discovery system (not a prediction engine)
    Uses Daily K for "discovery" and Intraday K for "confirmation"

Architecture:
    Daily Filter → Daily Anomaly Engine → Watchlist Builder
    → Intraday Loader → Intraday Confirmation → Output

Design Principles:
    1. Daily K only for "discovery"
    2. Intraday K only for "confirmation"
    3. All scores are relative/robust
    4. All thresholds configurable
    5. All events must be explainable

This is an event discovery layer, not a prediction engine.
================================================================================
"""

import sys
sys.path.insert(0, 'd:/strategy=Z')

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from db.api import StockDB
from datetime import datetime, timedelta


# ============================================================================
# MODULE A: Daily Filter
# ============================================================================

class DailyFilter:
    """
    Daily data filtering and cleaning

    Filters:
    - Minimum price threshold
    - Minimum dollar volume (rolling median)
    - Abnormal trading days (halt/resume/split)
    """

    def __init__(self, min_price: float = 5.0, min_dollar_volume: float = 1_000_000):
        self.min_price = min_price
        self.min_dollar_volume = min_dollar_volume

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter daily bars

        Args:
            df: DataFrame with columns [date, open, high, low, close, volume]

        Returns:
            Filtered DataFrame
        """
        if df is None or len(df) == 0:
            return df

        # Price filter
        df = df[df['close'] >= self.min_price].copy()

        # Dollar volume filter
        df['dollar_volume'] = df['close'] * df['volume']
        median_dv = df['dollar_volume'].rolling(20, min_periods=1).median()
        df = df[median_dv >= self.min_dollar_volume].copy()

        # Remove abnormal days (huge gaps, halts, etc.)
        # Gap > 50% likely corporate action
        df['prev_close'] = df['close'].shift(1)
        df['gap_pct'] = (df['open'] - df['prev_close']) / df['prev_close']
        df = df[df['gap_pct'].abs() < 0.5].copy()

        return df.drop(['dollar_volume', 'prev_close', 'gap_pct'], axis=1)


# ============================================================================
# MODULE B: Daily Anomaly Engine
# ============================================================================

class GapAnalyzer:
    """
    Gap anomaly detection

    Types:
    - REV (Reversal): Gap + intraday reversal
    - CONT (Continuation): Gap + intraday continuation
    """

    def __init__(self, lookback: int = 60):
        self.lookback = lookback

    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze gap behavior

        Returns:
            {
                'type': 'REV' | 'CONT' | None,
                'score': float,
                'gap_size': float,
                'reversal_ratio': float,
                'ref_levels': {'prev_close', 'open'}
            }
        """
        if len(df) < 2:
            return {'type': None, 'score': 0}

        # Latest bar
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Calculate gap and intraday move
        gap = (latest['open'] - prev['close']) / prev['close']
        intraday = (latest['close'] - latest['open']) / latest['open']

        # Gap too small, ignore
        if abs(gap) < 0.01:  # < 1%
            return {'type': None, 'score': 0}

        # Calculate z-score using MAD (robust)
        recent_gaps = []
        for i in range(min(self.lookback, len(df) - 1)):
            curr = df.iloc[-(i+1)]
            prev_bar = df.iloc[-(i+2)]
            g = (curr['open'] - prev_bar['close']) / prev_bar['close']
            recent_gaps.append(g)

        recent_gaps = np.array(recent_gaps)
        median = np.median(recent_gaps)
        mad = np.median(np.abs(recent_gaps - median))

        if mad == 0:
            z_score = 0
        else:
            z_score = (gap - median) / (mad * 1.4826)  # MAD to std conversion

        # Determine type
        reversal_ratio = -intraday / gap if gap != 0 else 0

        if reversal_ratio > 0.5:  # Gap up + close down (or vice versa)
            event_type = 'REV'
            score = abs(z_score) * reversal_ratio
        elif abs(intraday / gap) > 0.5 and np.sign(gap) == np.sign(intraday):
            event_type = 'CONT'
            score = abs(z_score) * abs(intraday / gap)
        else:
            event_type = None
            score = 0

        return {
            'type': event_type,
            'score': min(score, 100),  # Cap at 100
            'gap_size': gap,
            'reversal_ratio': reversal_ratio,
            'z_score': z_score,
            'ref_levels': {
                'prev_close': prev['close'],
                'open': latest['open'],
                'close': latest['close']
            }
        }


class SqueezeReleaseAnalyzer:
    """
    Volatility squeeze-release detection

    Logic:
    - Detect low volatility period (squeeze)
    - Detect high volatility breakout (release)
    """

    def __init__(self, squeeze_period: int = 20, release_threshold: float = 2.0):
        self.squeeze_period = squeeze_period
        self.release_threshold = release_threshold

    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze volatility squeeze-release

        Returns:
            {
                'score': float,
                'squeeze_strength': float,
                'release_strength': float,
                'breakout_level': float,
                'box': {'upper', 'lower'}
            }
        """
        if len(df) < self.squeeze_period + 10:
            return {'score': 0}

        # Calculate True Range
        df = df.copy()
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'prev_close']].max(axis=1) - df[['low', 'prev_close']].min(axis=1)

        # Short and long volatility
        df['vol_short'] = df['tr'].rolling(5).mean()
        df['vol_long'] = df['tr'].rolling(20).mean()

        latest = df.iloc[-1]

        # Calculate volatility percentile
        recent_vol = df['vol_short'].tail(self.squeeze_period)
        vol_percentile = (recent_vol < recent_vol.quantile(0.2)).sum() / len(recent_vol)

        # Was squeezed?
        was_squeezed = vol_percentile > 0.6  # 60% of recent days in low vol

        # Is releasing?
        vol_ratio = latest['vol_short'] / latest['vol_long'] if latest['vol_long'] > 0 else 1
        is_releasing = vol_ratio > self.release_threshold

        if not (was_squeezed and is_releasing):
            return {'score': 0}

        # Calculate box (consolidation range)
        squeeze_df = df.tail(self.squeeze_period)
        box_upper = squeeze_df['high'].max()
        box_lower = squeeze_df['low'].min()

        # Breakout level
        if latest['close'] > box_upper:
            breakout_level = box_upper
            breakout_direction = 'UP'
        elif latest['close'] < box_lower:
            breakout_level = box_lower
            breakout_direction = 'DOWN'
        else:
            # Still in box
            return {'score': 0}

        # Score based on squeeze strength and release strength
        squeeze_strength = vol_percentile
        release_strength = min(vol_ratio / self.release_threshold, 3.0)  # Cap at 3x

        score = (squeeze_strength * 50) + (release_strength / 3.0 * 50)

        return {
            'score': min(score, 100),
            'squeeze_strength': squeeze_strength,
            'release_strength': release_strength,
            'breakout_level': breakout_level,
            'breakout_direction': breakout_direction,
            'box': {
                'upper': box_upper,
                'lower': box_lower
            },
            'vol_ratio': vol_ratio
        }


# ============================================================================
# MODULE C: Watchlist Builder
# ============================================================================

class WatchlistBuilder:
    """
    Aggregate anomaly events and build watchlist

    Logic:
    - Score aggregation: max(gap_score, squeeze_release_score)
    - Top N selection
    - Export key levels
    """

    def __init__(self, top_n: int = 20):
        self.top_n = top_n

    def build(self, events: List[Dict]) -> List[Dict]:
        """
        Build watchlist from events

        Args:
            events: List of {ticker, date, gap_event, squeeze_event, ...}

        Returns:
            Sorted watchlist with top N events
        """
        scored_events = []

        for event in events:
            gap_score = event.get('gap_event', {}).get('score', 0)
            squeeze_score = event.get('squeeze_event', {}).get('score', 0)

            daily_score = max(gap_score, squeeze_score)

            if daily_score >= 50:  # Minimum threshold
                # Determine event type
                if gap_score > squeeze_score:
                    event_type = f"GAP_{event['gap_event']['type']}"
                else:
                    event_type = "SQUEEZE_RELEASE"

                # Extract key levels
                key_levels = self._extract_key_levels(event)

                scored_events.append({
                    'ticker': event['ticker'],
                    'date': event['date'],
                    'event_type': event_type,
                    'score': daily_score,
                    'key_levels': key_levels,
                    'gap_event': event.get('gap_event'),
                    'squeeze_event': event.get('squeeze_event')
                })

        # Sort by score
        scored_events.sort(key=lambda x: x['score'], reverse=True)

        # Return top N
        return scored_events[:self.top_n]

    def _extract_key_levels(self, event: Dict) -> Dict:
        """Extract key price levels from event"""
        levels = {}

        # From gap event
        gap_event = event.get('gap_event', {})
        if gap_event.get('ref_levels'):
            levels.update(gap_event['ref_levels'])

        # From squeeze event
        squeeze_event = event.get('squeeze_event', {})
        if squeeze_event.get('box'):
            levels['box_upper'] = squeeze_event['box']['upper']
            levels['box_lower'] = squeeze_event['box']['lower']
        if squeeze_event.get('breakout_level'):
            levels['breakout_level'] = squeeze_event['breakout_level']

        return levels


# ============================================================================
# MODULE D: Intraday Data Loader
# ============================================================================

class IntradayDataLoader:
    """
    Load intraday data for watchlist tickers only

    Purpose: Minimize API calls, only fetch what we need
    """

    def __init__(self, db: StockDB):
        self.db = db

    def load(self, watchlist: List[Dict], days: int = 5) -> Dict:
        """
        Load intraday data for watchlist

        Args:
            watchlist: List of watchlist events
            days: Number of days to load

        Returns:
            {ticker: DataFrame}
        """
        tickers = [w['ticker'] for w in watchlist]

        intraday_data = {}

        print(f"Loading intraday data for {len(tickers)} tickers...")

        for ticker in tickers:
            try:
                # Download if not exists
                self.db.download_intraday_data(ticker, interval='5m', period=f'{days}d')

                # Load from database
                df = self.db.get_intraday_data(ticker, interval='5m')

                if df is not None and len(df) > 0:
                    intraday_data[ticker] = df
            except Exception as e:
                print(f"  Failed to load {ticker}: {e}")
                continue

        print(f"Loaded intraday data for {len(intraday_data)} tickers")

        return intraday_data


# ============================================================================
# MODULE E: Intraday Structure Confirmation
# ============================================================================

class IntradayConfirmation:
    """
    Confirm daily events using intraday structure

    Sub-modules:
    - Opening Range behavior
    - Key level reaction
    - Volume expansion
    """

    def __init__(self):
        pass

    def confirm(self, daily_event: Dict, intraday_df: pd.DataFrame) -> Dict:
        """
        Confirm event using intraday data

        Args:
            daily_event: Event from watchlist
            intraday_df: Intraday bars (5m)

        Returns:
            {
                'confirmed': True/False,
                'structure_tags': [...],
                'refined_levels': {...}
            }
        """
        if intraday_df is None or len(intraday_df) == 0:
            return {'confirmed': False}

        # Get today's intraday bars
        event_date = daily_event['date']
        today_bars = intraday_df[intraday_df['datetime'].str.startswith(event_date)]

        if len(today_bars) < 10:  # Need at least 10 bars (50 minutes)
            return {'confirmed': False}

        structure_tags = []
        confirmed = False

        # Check Opening Range behavior
        or_result = self._check_opening_range(daily_event, today_bars)
        if or_result['quality'] > 0.6:
            structure_tags.append(or_result['tag'])
            confirmed = True

        # Check key level reaction
        level_result = self._check_key_levels(daily_event, today_bars)
        if level_result['reacted']:
            structure_tags.append(level_result['tag'])
            confirmed = True

        # Check volume expansion
        vol_result = self._check_volume_expansion(today_bars)
        if vol_result['expanded']:
            structure_tags.append('VOL_EXPANSION')
            confirmed = True

        return {
            'confirmed': confirmed,
            'structure_tags': structure_tags,
            'or_analysis': or_result,
            'level_analysis': level_result,
            'vol_analysis': vol_result
        }

    def _check_opening_range(self, event: Dict, bars: pd.DataFrame) -> Dict:
        """Check Opening Range (first 30 mins) behavior"""
        # First 6 bars = 30 minutes
        or_bars = bars.head(6)

        if len(or_bars) < 6:
            return {'quality': 0}

        or_high = or_bars['high'].max()
        or_low = or_bars['low'].min()
        or_range = or_high - or_low

        # Later bars
        later_bars = bars.iloc[6:]
        if len(later_bars) == 0:
            return {'quality': 0}

        # Check breakout or rejection
        max_high = later_bars['high'].max()
        min_low = later_bars['low'].min()

        # Breakout quality
        if max_high > or_high:
            breakout_size = max_high - or_high
            quality = min(breakout_size / or_range, 1.0) if or_range > 0 else 0
            tag = 'OR_BREAKOUT_UP'
        elif min_low < or_low:
            breakout_size = or_low - min_low
            quality = min(breakout_size / or_range, 1.0) if or_range > 0 else 0
            tag = 'OR_BREAKOUT_DOWN'
        else:
            # Stayed in range
            quality = 0
            tag = 'OR_NO_BREAKOUT'

        return {
            'quality': quality,
            'tag': tag,
            'or_high': or_high,
            'or_low': or_low
        }

    def _check_key_levels(self, event: Dict, bars: pd.DataFrame) -> Dict:
        """Check reaction at key levels"""
        key_levels = event.get('key_levels', {})

        if not key_levels:
            return {'reacted': False}

        # Check if price tested any key level
        for level_name, level_price in key_levels.items():
            if pd.isna(level_price):
                continue

            # Find bars near this level (within 0.5%)
            tolerance = level_price * 0.005
            near_level = bars[
                (bars['low'] <= level_price + tolerance) &
                (bars['high'] >= level_price - tolerance)
            ]

            if len(near_level) > 0:
                # Reacted at level
                return {
                    'reacted': True,
                    'tag': f'LEVEL_{level_name.upper()}_TEST',
                    'level': level_price,
                    'bars_at_level': len(near_level)
                }

        return {'reacted': False}

    def _check_volume_expansion(self, bars: pd.DataFrame) -> Dict:
        """Check if volume is expanding intraday"""
        if len(bars) < 20:
            return {'expanded': False}

        # Compare first half vs second half volume
        mid = len(bars) // 2
        first_half_vol = bars.iloc[:mid]['volume'].mean()
        second_half_vol = bars.iloc[mid:]['volume'].mean()

        if first_half_vol == 0:
            return {'expanded': False}

        vol_ratio = second_half_vol / first_half_vol

        return {
            'expanded': vol_ratio > 1.5,
            'vol_ratio': vol_ratio
        }


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class EventDiscoverySystem:
    """
    Main orchestrator for event discovery system

    Pipeline:
    1. Daily Filter
    2. Daily Anomaly Engine
    3. Watchlist Builder
    4. Intraday Loader
    5. Intraday Confirmation
    6. Output
    """

    def __init__(self):
        self.db = StockDB()
        self.daily_filter = DailyFilter()
        self.gap_analyzer = GapAnalyzer()
        self.squeeze_analyzer = SqueezeReleaseAnalyzer()
        self.watchlist_builder = WatchlistBuilder(top_n=20)
        self.intraday_loader = IntradayDataLoader(self.db)
        self.intraday_confirmation = IntradayConfirmation()

    def run(self, symbols: List[str] = None) -> Dict:
        """
        Run complete event discovery pipeline

        Args:
            symbols: List of symbols to analyze (None = all)

        Returns:
            {
                'watchlist': [...],
                'confirmed_events': [...]
            }
        """
        print("=" * 80)
        print("EVENT DISCOVERY SYSTEM")
        print("=" * 80)
        print()

        # Get symbols
        if symbols is None:
            symbols = self.db.get_stock_list()

        print(f"Analyzing {len(symbols)} symbols...")
        print()

        # Step 1-3: Daily analysis
        print("Step 1-3: Daily anomaly detection...")
        events = []

        for symbol in symbols:
            try:
                df = self.db.get_price_history(symbol)
                if df is None or len(df) < 60:
                    continue

                # Filter
                df = self.daily_filter.filter(df)
                if df is None or len(df) < 30:
                    continue

                # Analyze
                gap_event = self.gap_analyzer.analyze(df)
                squeeze_event = self.squeeze_analyzer.analyze(df)

                # Aggregate
                if gap_event['score'] > 0 or squeeze_event['score'] > 0:
                    events.append({
                        'ticker': symbol,
                        'date': df.iloc[-1]['date'],
                        'gap_event': gap_event,
                        'squeeze_event': squeeze_event
                    })

            except Exception:
                continue

        print(f"Found {len(events)} daily anomaly events")
        print()

        # Build watchlist
        print("Step 4: Building watchlist...")
        watchlist = self.watchlist_builder.build(events)
        print(f"Watchlist: {len(watchlist)} events")
        print()

        # Load intraday
        print("Step 5: Loading intraday data...")
        intraday_data = self.intraday_loader.load(watchlist, days=5)
        print()

        # Confirm events
        print("Step 6: Intraday confirmation...")
        confirmed_events = []

        for event in watchlist:
            ticker = event['ticker']
            if ticker not in intraday_data:
                continue

            confirmation = self.intraday_confirmation.confirm(
                event,
                intraday_data[ticker]
            )

            if confirmation['confirmed']:
                confirmed_events.append({
                    **event,
                    'confirmation': confirmation
                })

        print(f"Confirmed: {len(confirmed_events)} events")
        print()

        return {
            'watchlist': watchlist,
            'confirmed_events': confirmed_events,
            'stats': {
                'total_analyzed': len(symbols),
                'daily_events': len(events),
                'watchlist_size': len(watchlist),
                'confirmed_count': len(confirmed_events)
            }
        }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    system = EventDiscoverySystem()

    # Test on subset
    test_symbols = system.db.get_stock_list()[:100]

    result = system.run(test_symbols)

    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    print(f"Daily events found: {result['stats']['daily_events']}")
    print(f"Watchlist size: {result['stats']['watchlist_size']}")
    print(f"Confirmed events: {result['stats']['confirmed_count']}")
    print()

    if result['confirmed_events']:
        print("Confirmed Events:")
        for event in result['confirmed_events'][:10]:
            print(f"\n{event['ticker']} - {event['event_type']} (Score: {event['score']:.1f})")
            print(f"  Structure tags: {event['confirmation']['structure_tags']}")
            print(f"  Key levels: {list(event['key_levels'].keys())}")