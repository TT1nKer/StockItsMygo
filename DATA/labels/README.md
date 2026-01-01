# Human Labeling System

**Purpose**: Teach the system what candidates you actually want to see, without adding more indicators.

## Quick Start

### 1. Daily Workflow (Automatic)
After running `python daily_observation.py`, you'll see:

```
[Step 8/8] Exporting label worksheet...
  1. Open: DATA/labels/todo_2025-01-05.csv
  2. Fill columns: 'label' (consider/skip) and 'skip_reason'
  3. Save the file
```

### 2. Labeling (10 seconds per ticker)

Open the CSV in Excel/Google Sheets. You'll see:

| candidate_id | symbol | source | score | close | tags | label | skip_reason | notes |
|--------------|--------|--------|-------|-------|------|-------|-------------|-------|
| 2025-01-05:AAPL:momentum:80 | AAPL | momentum | 85 | 175.00 | BREAKOUT,VOLUME_SPIKE | | | |

**Fill only 2 columns**:
- `label`: Type `consider` or `skip`
- `skip_reason`: If you skipped, use one of these exact strings:
  - `NO_LIQUIDITY`
  - `NO_CLEAR_STOP`
  - `TOO_MESSY_STRUCTURE`
  - `NEWS_GAP_SUSPECT`
  - `TOO_EXTENDED`
  - `DONT_UNDERSTAND`
  - `OTHER`

**Example**:
```
label: skip
skip_reason: NO_CLEAR_STOP
```

### 3. Collect Labels

After filling:
```bash
python -c "from tools.label_tools import collect_labels; collect_labels('2025-01-05')"
```

This appends your labels to `labels.csv` (master log).

### 4. Generate Policy (After 50+ labels)

```bash
python script/label_policy.py
```

This will:
1. Analyze your label history
2. Generate filtering rules (e.g., "NO_CLEAR_STOP appears 15 times → require CLEAR_STRUCTURE tag")
3. Save to `policy.json`

**Policy will be auto-applied in next daily workflow!**

---

## Files Structure

```
DATA/labels/
├── README.md           # This file
├── todo_2025-01-05.csv # Daily worksheet (you fill this)
├── todo_2025-01-06.csv
├── labels.csv          # Master log (all historical labels)
└── policy.json         # Auto-generated filtering rules
```

---

## How Policy Works

**Example 1**: You skip 10 candidates with `NO_CLEAR_STOP`
→ Policy adds rule: `required_tags: ["CLEAR_STRUCTURE"]`
→ Next day, only candidates with clear stop structure appear

**Example 2**: You skip 8 candidates with `TOO_EXTENDED`
→ Policy raises score threshold: `min_score_override: {momentum: 80}`
→ Next day, only momentum score >= 80 appears

**Example 3**: You always `consider` anomaly signals, rarely momentum
→ Policy sets: `preferred_source: "anomaly"`
→ Next day, anomaly candidates get boosted

---

## Philosophy

**Don't add indicators → Build a learning loop**

- System proposes 50 candidates
- You label 20 (takes 3-4 minutes)
- After 2 weeks (200+ labels), system knows your preferences
- Candidates shrink to the 10-15 you actually want to see

**No ML required**. Just hard-coded rules from your patterns.

---

## Tips

1. **Don't overthink**: If you don't immediately see the trade, mark `skip`
2. **Be consistent**: Use same `skip_reason` for same problems
3. **Start small**: Label just top 10-20 high-score candidates daily
4. **Review weekly**: Run `python -c "from tools.label_tools import print_label_summary; print_label_summary()"`
5. **Iterate policy**: After first policy, adjust and re-run after 100 more labels

---

## Advanced Usage

### View Label Summary
```python
from tools.label_tools import print_label_summary
print_label_summary()
```

### Manually Build Policy
```python
from tools.label_tools import load_labels
from script.label_policy import build_policy_from_labels

labels = load_labels()
policy = build_policy_from_labels(labels, min_skip_threshold=5)
policy.save()
```

### Disable Policy Temporarily
Edit `policy.json`:
```json
{
  "enabled": false
}
```

---

**Next Steps**:
1. Run today's workflow: `python daily_observation.py`
2. Open the generated `todo_{date}.csv`
3. Fill 10 labels in 2 minutes
4. Repeat for 5-10 days
5. Run `python script/label_policy.py`
6. Enjoy refined candidates!
