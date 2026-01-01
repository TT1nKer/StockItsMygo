"""
Signal Layer Package

This package contains fast screening signals for watchlist candidates.
All signal scanners must return List[WatchlistCandidate].

Available signals:
- momentum_signal: Trend-based momentum scanner
- anomaly_signal: Structure-based anomaly detector

Version: v2.1.1
"""

# Re-export from base (which imports from contracts)
from script.signals.base import SignalScanner, WatchlistCandidate, AnomalyTags

__all__ = ['SignalScanner', 'WatchlistCandidate', 'AnomalyTags']
