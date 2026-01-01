"""
Label Policy - Convert Human Feedback to Filtering Rules

Analyzes label history to generate hard-coded rules (not ML).
Start simple: if you skip X for reason Y repeatedly → filter out X automatically.

Philosophy: Rules before models. 50-200 labels → stable policy.

Version: v2.2.0
"""

import os
import json
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd


class LabelPolicy:
    """
    Policy object that encodes learned preferences from labels

    Policy structure:
    {
        "version": "1.0",
        "generated_at": "2025-01-12",
        "rules": {
            "min_score_override": {"momentum": 75, "anomaly": 65},
            "required_tags": ["CLEAR_STRUCTURE"],
            "blacklist_tags": ["NO_CLEAR_STOP"],
            "min_liquidity_boost": 1.5  # multiply current threshold
        },
        "stats": {...}
    }
    """

    def __init__(self, policy_dict: Dict = None):
        self.policy = policy_dict or self._default_policy()

    @staticmethod
    def _default_policy() -> Dict:
        """Default policy (no filtering)"""
        return {
            "version": "1.0",
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
            "enabled": False,
            "rules": {},
            "stats": {}
        }

    def apply(self, candidates: List) -> List:
        """
        Apply policy to filter/rerank candidates

        Args:
            candidates: List[WatchlistCandidate]

        Returns:
            Filtered list
        """
        if not self.policy.get('enabled', False):
            return candidates

        filtered = candidates.copy()
        rules = self.policy.get('rules', {})

        # Rule 1: Score threshold override
        if 'min_score_override' in rules:
            overrides = rules['min_score_override']
            filtered = [
                c for c in filtered
                if c.score >= overrides.get(c.source, 0)
            ]

        # Rule 2: Required tags
        if 'required_tags' in rules:
            required = rules['required_tags']
            filtered = [
                c for c in filtered
                if c.has_all_tags(required)
            ]

        # Rule 3: Blacklist tags
        if 'blacklist_tags' in rules:
            blacklist = rules['blacklist_tags']
            filtered = [
                c for c in filtered
                if not any(c.has_tag(tag) for tag in blacklist)
            ]

        # Rule 4: Source preference
        if 'preferred_source' in rules:
            preferred = rules['preferred_source']
            # Boost score for preferred source
            for c in filtered:
                if c.source == preferred:
                    c.score = min(100, int(c.score * 1.1))

        return filtered

    def save(self, filepath: str = "DATA/labels/policy.json"):
        """Save policy to JSON"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.policy, f, indent=2)
        print(f"[Policy] Saved to {filepath}")

    @classmethod
    def load(cls, filepath: str = "DATA/labels/policy.json"):
        """Load policy from JSON"""
        if not os.path.exists(filepath):
            print(f"[Policy] No policy file found, using defaults")
            return cls()

        with open(filepath, 'r') as f:
            policy_dict = json.load(f)

        print(f"[Policy] Loaded from {filepath}")
        return cls(policy_dict)


def build_policy_from_labels(
    labels_df: pd.DataFrame,
    min_skip_threshold: int = 5,
    min_consider_threshold: int = 3
) -> LabelPolicy:
    """
    Generate policy from label history

    Args:
        labels_df: DataFrame from load_labels()
        min_skip_threshold: Minimum occurrences to create a filter rule
        min_consider_threshold: Minimum occurrences to boost priority

    Returns:
        LabelPolicy object

    Rules generated:
    - If skip_reason X appears >= min_skip_threshold → create filter
    - If tag Y appears in >= min_consider_threshold considers → boost
    """
    if len(labels_df) == 0:
        print("[Policy Build] No labels to analyze")
        return LabelPolicy()

    policy = {
        "version": "1.0",
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "enabled": True,
        "rules": {},
        "stats": {
            "total_labels": len(labels_df),
            "consider_count": len(labels_df[labels_df['label'] == 'consider']),
            "skip_count": len(labels_df[labels_df['label'] == 'skip'])
        }
    }

    rules = {}

    # Analyze skip reasons
    skips = labels_df[labels_df['label'] == 'skip']
    skip_reasons = skips['skip_reason'].value_counts()

    # Rule: NO_LIQUIDITY → raise liquidity threshold (handled in scanner config)
    if skip_reasons.get('NO_LIQUIDITY', 0) >= min_skip_threshold:
        rules['note_liquidity'] = f"Consider raising min_volume threshold (skipped {skip_reasons['NO_LIQUIDITY']} times)"

    # Rule: NO_CLEAR_STOP → require CLEAR_STRUCTURE tag
    if skip_reasons.get('NO_CLEAR_STOP', 0) >= min_skip_threshold:
        rules['required_tags'] = rules.get('required_tags', [])
        if 'CLEAR_STRUCTURE' not in rules['required_tags']:
            rules['required_tags'].append('CLEAR_STRUCTURE')

    # Rule: TOO_MESSY_STRUCTURE → filter by volatility expansion
    if skip_reasons.get('TOO_MESSY_STRUCTURE', 0) >= min_skip_threshold:
        rules['note_structure'] = f"Consider requiring VOLATILITY_EXPANSION (skipped {skip_reasons['TOO_MESSY_STRUCTURE']} times)"

    # Rule: TOO_EXTENDED → raise score threshold
    if skip_reasons.get('TOO_EXTENDED', 0) >= min_skip_threshold:
        rules['min_score_override'] = {
            'momentum': 80,  # Raise from default 70
            'anomaly': 70    # Raise from default 60
        }

    # Analyze considers
    considers = labels_df[labels_df['label'] == 'consider']

    # Source preference
    if len(considers) > 0:
        source_dist = considers['source'].value_counts()
        if len(source_dist) > 0:
            preferred = source_dist.idxmax()
            if source_dist[preferred] >= min_consider_threshold:
                rules['preferred_source'] = preferred

    # Tag patterns in considers
    consider_tags = {}
    for tags_str in considers['tags'].dropna():
        for tag in tags_str.split(','):
            tag = tag.strip()
            if tag:
                consider_tags[tag] = consider_tags.get(tag, 0) + 1

    # If certain tags appear frequently in considers, note them
    frequent_tags = {k: v for k, v in consider_tags.items() if v >= min_consider_threshold}
    if frequent_tags:
        policy['stats']['frequent_consider_tags'] = frequent_tags

    policy['rules'] = rules

    print("[Policy Build] Generated policy:")
    print(json.dumps(policy, indent=2))

    return LabelPolicy(policy)


def interactive_policy_review():
    """
    Interactive session to review and adjust policy

    Run after build_policy_from_labels() to fine-tune
    """
    from tools.label_tools import load_labels

    labels_df = load_labels()

    if len(labels_df) == 0:
        print("No labels found. Run daily workflow and fill todo_{date}.csv first.")
        return

    print("=" * 80)
    print("INTERACTIVE POLICY BUILDER")
    print("=" * 80)
    print()
    print(f"Total labels: {len(labels_df)}")
    print()

    # Build policy
    policy = build_policy_from_labels(labels_df)

    print()
    print("Policy generated. Review the rules above.")
    print()

    # Ask to save
    response = input("Save this policy? (yes/no): ").strip().lower()
    if response == 'yes':
        policy.save()
        print()
        print("Policy saved! It will be applied in next daily workflow.")
        print()
        print("To disable: edit DATA/labels/policy.json and set 'enabled': false")
    else:
        print("Policy not saved.")


def apply_policy_to_candidates(candidates: List, policy_path: str = "DATA/labels/policy.json") -> List:
    """
    Convenience function to apply saved policy

    Usage in daily_workflow.py Step 3:
        from script.label_policy import apply_policy_to_candidates
        filtered = apply_policy_to_candidates(candidates)
    """
    policy = LabelPolicy.load(policy_path)

    if not policy.policy.get('enabled', False):
        print("[Policy] Policy disabled, no filtering applied")
        return candidates

    filtered = policy.apply(candidates)

    print(f"[Policy] Applied policy: {len(candidates)} → {len(filtered)} candidates")
    if 'rules' in policy.policy:
        print(f"[Policy] Active rules: {list(policy.policy['rules'].keys())}")

    return filtered


if __name__ == '__main__':
    print("Label Policy Builder")
    print()
    print("This tool converts your labeling history into hard-coded filtering rules.")
    print()
    print("Run this after collecting 50+ labels to generate your first policy.")
    print()
    interactive_policy_review()
