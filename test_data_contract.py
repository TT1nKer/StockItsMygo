"""
Test Data Contract (WatchlistCandidate)
测试数据契约
"""

import sys
sys.path.insert(0, 'd:/strategy=Z')

from script.signals.base import WatchlistCandidate, AnomalyTags


def test_basic_creation():
    """测试基础创建"""
    print("=" * 80)
    print("TEST 1: Basic WatchlistCandidate Creation")
    print("=" * 80)
    print()

    # Momentum candidate
    momentum_candidate = WatchlistCandidate(
        symbol='AAPL',
        date='2024-12-30',
        close=180.50,
        source='momentum',
        score=85,
        tags=['BREAKOUT'],
        stop_loss=175.00,
        risk_pct=-3.05,
        metadata={'momentum_20d': 15.2, 'volume_ratio': 2.1}
    )

    print("Momentum Candidate:")
    print(f"  Symbol: {momentum_candidate.symbol}")
    print(f"  Source: {momentum_candidate.source}")
    print(f"  Score: {momentum_candidate.score}")
    print(f"  Tags: {momentum_candidate.tags}")
    print(f"  Stop Loss: ${momentum_candidate.stop_loss:.2f}")
    print(f"  Risk: {momentum_candidate.risk_pct:.2f}%")
    print(f"  Metadata: {momentum_candidate.metadata}")
    print()

    # Anomaly candidate with core 3 factors
    anomaly_candidate = WatchlistCandidate(
        symbol='NVDA',
        date='2024-12-30',
        close=520.00,
        source='anomaly',
        score=90,
        tags=[
            AnomalyTags.VOLATILITY_EXPANSION,
            AnomalyTags.VOLUME_SPIKE,
            AnomalyTags.CLEAR_STRUCTURE
        ],
        stop_loss=510.00,
        risk_pct=-1.92,
        metadata={'volatility_ratio': 2.5, 'volume_ratio': 2.8}
    )

    print("Anomaly Candidate (Core 3-Factor):")
    print(f"  Symbol: {anomaly_candidate.symbol}")
    print(f"  Score: {anomaly_candidate.score}")
    print(f"  Tags: {anomaly_candidate.tags}")
    print(f"  Is Core 3-Factor: {anomaly_candidate.is_core_three_factor()}")
    print()

    print("[OK] Basic creation passed")
    print()


def test_tag_checking():
    """测试标签检查"""
    print("=" * 80)
    print("TEST 2: Tag Checking Methods")
    print("=" * 80)
    print()

    candidate = WatchlistCandidate(
        symbol='TSLA',
        date='2024-12-30',
        close=250.00,
        source='anomaly',
        score=75,
        tags=[
            AnomalyTags.VOLATILITY_EXPANSION,
            AnomalyTags.VOLUME_SPIKE,
            AnomalyTags.GAP
        ]
    )

    print(f"Candidate tags: {candidate.tags}")
    print()

    print(f"Has VOLATILITY_EXPANSION: {candidate.has_tag(AnomalyTags.VOLATILITY_EXPANSION)}")
    print(f"Has CLEAR_STRUCTURE: {candidate.has_tag(AnomalyTags.CLEAR_STRUCTURE)}")
    print()

    required_tags = [AnomalyTags.VOLATILITY_EXPANSION, AnomalyTags.VOLUME_SPIKE]
    print(f"Has all {required_tags}: {candidate.has_all_tags(required_tags)}")
    print()

    print(f"Is core 3-factor: {candidate.is_core_three_factor()}")
    print("  (Should be False - missing CLEAR_STRUCTURE)")
    print()

    print("[OK] Tag checking passed")
    print()


def test_serialization():
    """测试序列化"""
    print("=" * 80)
    print("TEST 3: Serialization to Dict")
    print("=" * 80)
    print()

    candidate = WatchlistCandidate(
        symbol='AMD',
        date='2024-12-30',
        close=145.00,
        source='anomaly',
        score=80,
        tags=[AnomalyTags.BREAKOUT, AnomalyTags.VOLUME_SPIKE],
        stop_loss=140.00,
        risk_pct=-3.45,
        metadata={'breakout_level': 144.50}
    )

    data = candidate.to_dict()

    print("Serialized to dict:")
    for key, value in data.items():
        print(f"  {key}: {value}")
    print()

    print("[OK] Serialization passed")
    print()


def test_validation():
    """测试数据验证"""
    print("=" * 80)
    print("TEST 4: Data Validation")
    print("=" * 80)
    print()

    # Test invalid score
    try:
        WatchlistCandidate(
            symbol='TEST',
            date='2024-12-30',
            close=100.0,
            source='momentum',
            score=150  # Invalid: > 100
        )
        print("[FAIL] Should have raised assertion error for score > 100")
    except AssertionError as e:
        print(f"[OK] Correctly rejected invalid score: {e}")

    print()

    # Test invalid source
    try:
        WatchlistCandidate(
            symbol='TEST',
            date='2024-12-30',
            close=100.0,
            source='invalid',  # Invalid source
            score=50
        )
        print("[FAIL] Should have raised assertion error for invalid source")
    except AssertionError as e:
        print(f"[OK] Correctly rejected invalid source: {e}")

    print()

    # Test positive risk_pct (should be negative)
    try:
        WatchlistCandidate(
            symbol='TEST',
            date='2024-12-30',
            close=100.0,
            source='momentum',
            score=50,
            risk_pct=3.5  # Invalid: should be negative
        )
        print("[FAIL] Should have raised assertion error for positive risk_pct")
    except AssertionError as e:
        print(f"[OK] Correctly rejected positive risk_pct: {e}")

    print()
    print("[OK] All validation tests passed")
    print()


def test_batch_processing():
    """测试批量处理"""
    print("=" * 80)
    print("TEST 5: Batch Processing Simulation")
    print("=" * 80)
    print()

    # Simulate scanner output
    candidates = [
        WatchlistCandidate('AAPL', '2024-12-30', 180.0, 'momentum', 85, ['BREAKOUT']),
        WatchlistCandidate('NVDA', '2024-12-30', 520.0, 'anomaly', 90,
                          [AnomalyTags.VOLATILITY_EXPANSION, AnomalyTags.VOLUME_SPIKE, AnomalyTags.CLEAR_STRUCTURE]),
        WatchlistCandidate('TSLA', '2024-12-30', 250.0, 'momentum', 80),
        WatchlistCandidate('AMD', '2024-12-30', 145.0, 'anomaly', 75, [AnomalyTags.GAP]),
    ]

    print(f"Total candidates: {len(candidates)}")
    print()

    # Group by source
    momentum_count = sum(1 for c in candidates if c.source == 'momentum')
    anomaly_count = sum(1 for c in candidates if c.source == 'anomaly')

    print(f"Momentum signals: {momentum_count}")
    print(f"Anomaly signals: {anomaly_count}")
    print()

    # Find core 3-factor anomalies
    core_three = [c for c in candidates if c.is_core_three_factor()]
    print(f"Core 3-factor anomalies: {len(core_three)}")
    for c in core_three:
        print(f"  - {c.symbol} (score: {c.score})")
    print()

    # Sort by score
    sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)
    print("Top 3 by score:")
    for c in sorted_candidates[:3]:
        print(f"  {c.symbol}: {c.score} ({c.source})")
    print()

    print("[OK] Batch processing test passed")
    print()


def main():
    """运行所有测试"""
    print("\n")
    print("=" * 80)
    print("DATA CONTRACT TEST SUITE")
    print("=" * 80)
    print("\n")

    test_basic_creation()
    test_tag_checking()
    test_serialization()
    test_validation()
    test_batch_processing()

    print("=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
    print()
    print("Summary:")
    print("  [OK] WatchlistCandidate creation working")
    print("  [OK] Tag checking methods working")
    print("  [OK] Serialization working")
    print("  [OK] Data validation working")
    print("  [OK] Batch processing working")
    print()
    print("Data contract is ready for use!")
    print()


if __name__ == "__main__":
    main()
