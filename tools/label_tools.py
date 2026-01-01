"""
Label Tools - Human Feedback Loop

Enables collecting human judgment on candidates to refine the system.

Workflow:
1. Daily: export_label_todo() -> DATA/labels/todo_{date}.csv
2. Human: Fill label/skip_reason columns (10 sec per ticker)
3. Weekly: collect_labels() -> DATA/labels/labels.csv (master log)
4. Analysis: build_policy_from_labels() -> policy.json

Philosophy: Don't add more indicators, build a learning loop.

Version: v2.2.0
"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import json
import hashlib


def make_candidate_id(candidate) -> str:
    """
    Generate stable candidate ID for traceability

    Format: {date}:{symbol}:{source}:{score_bucket}
    Score bucketed to avoid ID changes from minor score fluctuations
    """
    score_bucket = (candidate.score // 10) * 10  # Round to nearest 10
    return f"{candidate.date}:{candidate.symbol}:{candidate.source}:{score_bucket}"


def export_label_todo(date: str, candidates: List, output_dir: str = "DATA/labels") -> str:
    """
    Export today's candidates to CSV for human labeling

    Args:
        date: YYYY-MM-DD
        candidates: List[WatchlistCandidate]
        output_dir: Where to save the file

    Returns:
        Path to created file

    Usage:
        After daily workflow:
        path = export_label_todo("2025-01-05", all_candidates)
        # Open path in Excel, fill label/skip_reason columns
    """
    os.makedirs(output_dir, exist_ok=True)

    # Build labeling worksheet
    rows = []
    for c in candidates:
        rows.append({
            # Identity
            'candidate_id': make_candidate_id(c),
            'date': c.date,
            'symbol': c.symbol,
            'source': c.source,

            # Key metrics (what you need to decide)
            'score': c.score,
            'close': c.close,
            'tags': ','.join(c.tags),
            'stop_loss': c.stop_loss if c.stop_loss else '',
            'risk_pct': c.risk_pct if c.risk_pct else '',

            # Quick decision aids
            'momentum_20d': c.metadata.get('momentum_20d', ''),
            'volume_ratio': c.metadata.get('volume_ratio', ''),
            'is_core_3': c.is_core_three_factor() if c.source == 'anomaly' else False,

            # Human input columns (LEAVE EMPTY, you fill these)
            'label': '',  # consider / skip
            'skip_reason': '',  # see SKIP_REASONS below
            'notes': ''
        })

    df = pd.DataFrame(rows)

    # Sort by score descending (review high-score first)
    df = df.sort_values('score', ascending=False)

    filepath = os.path.join(output_dir, f"todo_{date}.csv")
    df.to_csv(filepath, index=False)

    print(f"[Label Export] Created labeling worksheet: {filepath}")
    print(f"[Label Export] Total candidates: {len(df)}")
    print(f"[Label Export] Please fill 'label' and 'skip_reason' columns")
    print()
    print("SKIP_REASONS (use exact strings):")
    print("  - NO_LIQUIDITY")
    print("  - NO_CLEAR_STOP")
    print("  - TOO_MESSY_STRUCTURE")
    print("  - NEWS_GAP_SUSPECT")
    print("  - TOO_EXTENDED")
    print("  - DONT_UNDERSTAND")
    print("  - OTHER")

    return filepath


def collect_labels(date: str, labels_dir: str = "DATA/labels") -> Dict[str, Any]:
    """
    Read today's completed labels and append to master log

    Args:
        date: YYYY-MM-DD
        labels_dir: Where label files are stored

    Returns:
        Stats dict with label counts

    Usage:
        After filling todo_{date}.csv:
        stats = collect_labels("2025-01-05")
    """
    todo_file = os.path.join(labels_dir, f"todo_{date}.csv")
    master_file = os.path.join(labels_dir, "labels.csv")

    if not os.path.exists(todo_file):
        print(f"[Label Collect] No todo file found: {todo_file}")
        return {'error': 'file_not_found'}

    df = pd.read_csv(todo_file)

    # Filter rows that have been labeled
    labeled = df[df['label'].notna() & (df['label'] != '')]

    if len(labeled) == 0:
        print(f"[Label Collect] No labels filled in {todo_file}")
        return {'labeled_count': 0}

    # Append to master log
    if os.path.exists(master_file):
        master = pd.read_csv(master_file)
        # Remove duplicates by candidate_id (allow relabeling)
        master = master[~master['candidate_id'].isin(labeled['candidate_id'])]
        combined = pd.concat([master, labeled], ignore_index=True)
    else:
        combined = labeled

    combined.to_csv(master_file, index=False)

    # Stats
    stats = {
        'labeled_count': len(labeled),
        'consider_count': len(labeled[labeled['label'] == 'consider']),
        'skip_count': len(labeled[labeled['label'] == 'skip']),
        'skip_reasons': labeled[labeled['label'] == 'skip']['skip_reason'].value_counts().to_dict(),
        'total_in_master': len(combined)
    }

    print(f"[Label Collect] Collected {stats['labeled_count']} labels")
    print(f"  Consider: {stats['consider_count']}")
    print(f"  Skip: {stats['skip_count']}")
    print(f"  Skip reasons: {stats['skip_reasons']}")
    print(f"  Total in master log: {stats['total_in_master']}")

    return stats


def load_labels(labels_dir: str = "DATA/labels") -> pd.DataFrame:
    """
    Load master label log

    Returns:
        DataFrame with all historical labels
    """
    master_file = os.path.join(labels_dir, "labels.csv")

    if not os.path.exists(master_file):
        return pd.DataFrame()

    return pd.read_csv(master_file)


def analyze_label_patterns(min_count: int = 5, labels_dir: str = "DATA/labels") -> Dict[str, Any]:
    """
    Analyze labeling patterns to inform policy updates

    Args:
        min_count: Minimum occurrences to report a pattern

    Returns:
        Analysis dict with:
        - most_common_skips: Top skip reasons
        - consider_tags: Tags frequently in 'consider' candidates
        - skip_tags: Tags frequently in 'skip' candidates
        - source_preference: Distribution of labels by source
    """
    df = load_labels(labels_dir)

    if len(df) == 0:
        return {'error': 'no_labels'}

    # Most common skip reasons
    skips = df[df['label'] == 'skip']
    skip_reasons = skips['skip_reason'].value_counts()
    skip_reasons = skip_reasons[skip_reasons >= min_count].to_dict()

    # Tag analysis
    considers = df[df['label'] == 'consider']

    def count_tags(rows):
        tag_counts = {}
        for tags_str in rows['tags'].dropna():
            for tag in tags_str.split(','):
                tag = tag.strip()
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return {k: v for k, v in tag_counts.items() if v >= min_count}

    consider_tags = count_tags(considers)
    skip_tags = count_tags(skips)

    # Source preference
    source_dist = df.groupby(['source', 'label']).size().unstack(fill_value=0)

    analysis = {
        'total_labels': len(df),
        'consider_count': len(considers),
        'skip_count': len(skips),
        'most_common_skips': skip_reasons,
        'consider_tags': consider_tags,
        'skip_tags': skip_tags,
        'source_distribution': source_dist.to_dict(),
        'label_by_source': {
            source: {
                'consider': len(df[(df['source'] == source) & (df['label'] == 'consider')]),
                'skip': len(df[(df['source'] == source) & (df['label'] == 'skip')])
            }
            for source in df['source'].unique()
        }
    }

    return analysis


def print_label_summary(labels_dir: str = "DATA/labels"):
    """Print human-readable summary of labeling history"""
    analysis = analyze_label_patterns(labels_dir=labels_dir)

    if 'error' in analysis:
        print("[Label Summary] No labels collected yet")
        return

    print("=" * 80)
    print("LABEL SUMMARY")
    print("=" * 80)
    print()
    print(f"Total labels: {analysis['total_labels']}")
    print(f"  Consider: {analysis['consider_count']} ({analysis['consider_count']/analysis['total_labels']*100:.1f}%)")
    print(f"  Skip: {analysis['skip_count']} ({analysis['skip_count']/analysis['total_labels']*100:.1f}%)")
    print()

    print("Most Common Skip Reasons:")
    for reason, count in sorted(analysis['most_common_skips'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {reason}: {count}")
    print()

    print("Tags in 'Consider' Candidates:")
    for tag, count in sorted(analysis['consider_tags'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {tag}: {count}")
    print()

    print("Tags in 'Skip' Candidates:")
    for tag, count in sorted(analysis['skip_tags'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {tag}: {count}")
    print()

    print("Label Distribution by Source:")
    for source, stats in analysis['label_by_source'].items():
        total = stats['consider'] + stats['skip']
        if total > 0:
            print(f"  {source}: {stats['consider']}/{total} consider ({stats['consider']/total*100:.1f}%)")


if __name__ == '__main__':
    print("Label Tools - Human Feedback Loop")
    print()
    print("This tool helps you teach the system what candidates you actually want to see.")
    print()
    print("Workflow:")
    print("1. After daily_workflow, a todo_{date}.csv is created")
    print("2. Open it, fill 'label' (consider/skip) and 'skip_reason'")
    print("3. Run: python -c \"from tools.label_tools import collect_labels; collect_labels('2025-01-05')\"")
    print("4. After 2 weeks: Run label_policy.py to generate filtering rules")
    print()
    print_label_summary()
