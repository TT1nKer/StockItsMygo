# Daily Stock Recommendations - Filtering Guide

## Overview

The web dashboard provides flexible filtering for daily stock recommendations, allowing you to see ALL stocks worth watching (not just top 20).

**URL**: http://localhost:8080

---

## Score-Based Filtering System

### AI Scoring Algorithm (0-100 points)

Each stock is analyzed daily and assigned a score based on multiple technical indicators:

**RSI (Relative Strength Index)** - up to 20 points
- Oversold (RSI 30-40): +20 points
- Strong momentum (RSI 60-70): +10 points

**Price Momentum** - up to 30 points
- Positive 10-day momentum (>5%): +15 points
- Strong 20-day trend (>10%): +15 points

**Volume Trends** - up to 25 points
- Increasing volume (>20% above average): +15 points
- Volume surge (>150% of 20-day average): +10 points

**Breakout Patterns** - up to 15 points
- Close above 20-day high: +15 points

**52-Week High Proximity** - up to 10 points
- Within 5% of 52-week high: +10 points

**Total possible**: 100 points

---

## Filter Controls

### 1. Score Slider (Adjustable Threshold)

**Range**: 20 - 70 (step size: 5)
**Default**: 30

- **20 (More stocks)**: Shows more opportunities, lower quality threshold
- **30 (Balanced)**: Good mix of quantity and quality *(default)*
- **45 (Balanced)**: Fewer stocks, higher confidence
- **70 (Fewer, Higher Quality)**: Only the strongest signals

**How it works**:
- Adjusting the slider dynamically reloads recommendations from the server
- Only stocks with score >= selected value are shown
- Example: Setting to 60 shows only "High" quality stocks

---

### 2. Category Filter Buttons

Quick filters for predefined score ranges:

**All** - Shows all stocks meeting current slider threshold
- No additional filtering
- Count badge shows total stocks

**High (60+)** - Premium quality signals
- Very strong technical setup
- Multiple positive indicators
- Higher probability opportunities

**Medium (40-59)** - Good quality signals
- Solid technical setup
- Several positive indicators
- Moderate probability opportunities

**Low (30-39)** - Acceptable quality signals
- Basic technical setup
- Some positive indicators
- Watch list candidates

**How it works**:
- Click a button to instantly filter stocks by category
- Client-side filtering (no server reload needed)
- Active button highlighted in blue

---

## Typical Usage Scenarios

### Scenario 1: Daily Quick Review (High-quality only)

1. Set slider to **60**
2. Review all High (60+) stocks
3. Typically: 4-20 stocks
4. Best for: Quick daily scan, high-confidence plays

### Scenario 2: Comprehensive Watchlist (All opportunities)

1. Set slider to **30**
2. Click "All" button
3. Typically: 100-300 stocks
4. Best for: Building a broad watchlist, finding hidden gems

### Scenario 3: Balanced Approach (Medium+High)

1. Set slider to **40**
2. Review Medium and High categories
3. Typically: 30-80 stocks
4. Best for: Moderate watchlist size, good quality threshold

### Scenario 4: Custom Threshold

1. Adjust slider to your preferred score (e.g., 35, 50, 65)
2. See exactly how many stocks meet that criteria
3. Use category buttons to further refine

---

## Understanding the Counts

Count badges on filter buttons show:

```
All (203)          - Total stocks with score >= current slider value
High 60+ (18)      - Stocks with score 60-100
Medium 40-59 (67)  - Stocks with score 40-59
Low 30-39 (118)    - Stocks with score 30-39
```

**Example interpretation**:
- If slider is at **30**: "All (203)" means 203 stocks have score >= 30
- If slider is at **60**: "All (18)" means only 18 stocks have score >= 60
- Category counts (High/Medium/Low) remain constant regardless of slider

---

## Stock Display Information

Each stock shows:

**Header**: Showing X stocks (Scores: Y - Z)
- X = Number of stocks currently displayed
- Y = Minimum score in current view
- Z = Maximum score in current view

**Example**: "Showing 67 stocks (Scores: 40 - 59)"
- You're viewing 67 stocks
- All have scores between 40 and 59
- This happens when filtering by "Medium" category

---

## Performance Notes

**Server Query Limit**: Up to 500 stocks
- The system fetches maximum 500 stocks from database
- This covers all realistic filtering scenarios
- If you have >500 stocks with score >= slider value, only top 500 shown

**Client-Side Filtering**: Instant response
- Category buttons (All/High/Medium/Low) filter instantly
- No server round-trip needed
- Smooth user experience

**Slider Changes**: Quick reload
- Changing slider triggers new server query
- Typically responds in <1 second
- Fetches fresh data for new threshold

---

## Examples by Score Range

### High Quality (60-100)
**Characteristics**:
- Multiple strong signals (3-5 indicators)
- Often includes: breakout + volume surge + momentum
- RSI in strong zone (60-70) or oversold bounce (30-40)
- May be near 52-week high

**Example Signals**:
- "Strong momentum, Breakout pattern, Volume surge"
- "Oversold (RSI), Positive 10-day momentum, Increasing volume"

### Medium Quality (40-59)
**Characteristics**:
- 2-3 positive signals
- Good momentum or volume, but not both
- Solid technical setup

**Example Signals**:
- "Positive 10-day momentum, Increasing volume"
- "Strong 20-day trend, Near 52-week high"

### Low Quality (30-39)
**Characteristics**:
- 1-2 positive signals
- Basic technical setup
- Good for watchlist, monitor for improvement

**Example Signals**:
- "Oversold (RSI)"
- "Increasing volume"
- "Near 52-week high"

---

## Daily Workflow Recommendations

### Morning Routine (5-10 minutes)
1. Set slider to **60**
2. Review High (60+) stocks
3. Add top candidates to personal watchlist
4. Set price alerts on key stocks

### Deep Dive (30+ minutes)
1. Set slider to **40**
2. Review Medium and High categories
3. Check charts on TradingView (click links)
4. Read analysis on Seeking Alpha (click links)
5. Add promising stocks to watchlist

### Weekend Research (1-2 hours)
1. Set slider to **30**
2. Click "All" to see full list
3. Sort by different criteria
4. Research fundamentals on Yahoo Finance
5. Build comprehensive watchlist for next week

---

## Filter Persistence

**Current Session**:
- Filter settings (slider position, category selection) are NOT persisted
- Refreshing the page resets to defaults (slider=30, All selected)

**Recommendation**:
- Bookmark specific filter settings won't work
- Take notes on stocks that interest you
- Add stocks to personal watchlist for permanent tracking

---

## Tips for Best Results

### 1. Don't Over-Filter
- Setting slider too high (>65) may miss good opportunities
- Balance between quality and quantity
- Recommended: Start at 40-45, adjust based on market conditions

### 2. Combine with External Research
- Use the provided links (Yahoo Finance, TradingView, etc.)
- Verify fundamentals before trading
- Check recent news on MarketWatch

### 3. Track Performance
- Add interesting stocks to personal watchlist
- Monitor over 14-day observation period
- Learn which score ranges work best for you

### 4. Adjust for Market Conditions
- **Bull Market**: Lower threshold (30-35) to catch momentum
- **Bear Market**: Higher threshold (50-60) for safety
- **Volatile Market**: Medium threshold (40-45) for balance

### 5. Use Categories Strategically
- **Monday**: Review "High" for week ahead
- **Mid-Week**: Check "Medium" for additions
- **Friday**: Scan "Low" for weekend research

---

## Troubleshooting

**No stocks showing**:
- Slider may be set too high (try lowering to 30)
- Recommendations may not be generated today (click "Update Data")
- Check counts on category buttons - if all show 0, run strategy_recommender.py

**Too many stocks**:
- Raise slider threshold (try 45-60)
- Use category buttons to focus on High or Medium
- Consider: This is intentional! You have many opportunities.

**Counts don't match**:
- Category counts (High/Medium/Low) show ALL stocks in database for today
- Slider affects what's fetched from server
- If slider=60, "All" count will equal "High" count

---

## Technical Details

**Database Table**: `daily_recommendations`
- Updated daily by `strategy_recommender.py`
- Stores ALL stocks with score >= 30
- Includes: symbol, price, score, signals, RSI, momentum, volume, breakout flags

**API Endpoint**: `/api/recommendations?min_score=X&limit=Y`
- `min_score`: Minimum score threshold (default: 30)
- `limit`: Maximum stocks to return (default: 200, max: 500)
- Returns: {recommendations: [...], counts: {high, medium, low, total}}

**Refresh Frequency**: Daily
- Click "Update Data" button to refresh
- Runs: tools/update_recent_data.py (fetches last 5 days)
- Runs: strategy_recommender.py (analyzes all stocks)
- Takes: 5-10 minutes for full update

---

## Future Enhancements (Planned)

- [ ] Save filter preferences per user
- [ ] Export filtered list to CSV
- [ ] Historical score tracking
- [ ] Custom score thresholds (save presets)
- [ ] Email alerts for new High-quality stocks
- [ ] Mobile app with push notifications

---

*Last updated: January 4, 2026*
