import pytest

from script.contracts import WatchlistCandidate


def test_watchlist_candidate_serializes():
    candidate = WatchlistCandidate(
        symbol="AAPL",
        date="2026-01-07",
        close=200.0,
        source="momentum",
        score=80,
        tags=["BREAKOUT"],
    )
    payload = candidate.to_dict()
    assert payload["symbol"] == "AAPL"
    assert payload["score"] == 80


def test_watchlist_candidate_rejects_invalid_score():
    with pytest.raises(AssertionError):
        WatchlistCandidate(
            symbol="AAPL",
            date="2026-01-07",
            close=200.0,
            source="momentum",
            score=101,
        )

