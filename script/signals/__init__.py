"""
Signal Layer Package

This package contains fast screening signals for watchlist candidates.
All signal scanners must return List[WatchlistCandidate].

Available signals:
- momentum_signal: Trend-based momentum scanner
- anomaly_signal: Structure-based anomaly detector
"""

from script.signals.base import WatchlistCandidate, SignalScanner

__all__ = ['WatchlistCandidate', 'SignalScanner']
