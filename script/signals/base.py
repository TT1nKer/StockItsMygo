"""
Signal Layer Base Classes

Defines the standard interface for all signal scanners.
Data contracts are now in script/contracts.py to prevent coupling.

Version: v2.1.1
"""

from typing import List
from abc import ABC, abstractmethod

# Import data contracts from separate module (v2.1.1)
from script.contracts import WatchlistCandidate, AnomalyTags


class SignalScanner(ABC):
    """
    Abstract base class for all signal scanners

    All concrete scanners must implement the scan() method
    and return List[WatchlistCandidate].

    Layer constraints:
    - ✅ Can call Layer 1 (db.api) for data access
    - ❌ Cannot call Layer 3 (event_discovery_system)
    - ❌ Cannot call Layer 4 (report_generator)
    - ❌ Cannot call Layer 5 (daily_workflow)
    """

    @abstractmethod
    def scan(self,
             min_score: int = 60,
             limit: int = 50,
             **kwargs) -> List[WatchlistCandidate]:
        """
        Scan market and return watchlist candidates

        Args:
            min_score: Minimum score threshold (0-100)
            limit: Maximum number of candidates to return
            **kwargs: Scanner-specific parameters

        Returns:
            List of WatchlistCandidate, sorted by score descending

        Raises:
            Should handle errors internally and return empty list if needed
        """
        pass

    def get_name(self) -> str:
        """返回扫描器名称"""
        return self.__class__.__name__
