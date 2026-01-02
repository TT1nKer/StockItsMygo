"""
Daily Observation - Quick Start
每日观察 - 快速启动

One-command daily workflow for stock observation before live trading.
一键运行每日股票观察工作流程（交易前练习）。

Usage:
    python daily_observation.py

This will:
1. Find promising stocks (momentum scan)
2. Update your watchlist automatically
3. Download detailed data for watchlist
4. Analyze stocks with all strategies
5. Generate comprehensive daily report

Reports saved to: reports/YYYY/MM-Month/Week_XX/YYYY-MM-DD_DayName.md
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.daily_workflow import DailyWorkflow
from datetime import datetime


def main():
    print("""
================================================================================
    DAILY STOCK OBSERVATION WORKFLOW
================================================================================

Welcome! This system will help you:
  - Find promising stocks to watch
  - Track and analyze your watchlist
  - Compare different trading strategies
  - Build experience before live trading

Mode: OBSERVATION ONLY (No actual trades)

""")

    # Confirm
    print("Starting daily workflow...")
    print()

    # Run workflow
    workflow = DailyWorkflow()
    workflow.run_daily_workflow()

    # Next steps
    print()
    print("=" * 80)
    print("WHAT TO DO NEXT")
    print("=" * 80)
    print()
    print("1. Open today's report:")
    print(f"   {workflow._get_report_filepath()}")
    print()
    print("2. Review each section carefully:")
    print("   - Top momentum opportunities")
    print("   - Watchlist deep analysis")
    print("   - Multi-strategy comparison")
    print()
    print("3. Add your observations:")
    print("   - What patterns do you see?")
    print("   - Which stocks look most promising?")
    print("   - What would you do if you were trading?")
    print()
    print("4. Track performance:")
    print("   - Check back tomorrow to see how these stocks performed")
    print("   - Note which strategies were most accurate")
    print("   - Build your understanding over time")
    print()
    print("5. Run daily:")
    print("   - Run this script every day to build experience")
    print("   - After a few weeks, you'll have great data and confidence")
    print()
    print("=" * 80)
    print()
    print(f"Report location: {workflow.report_dir}")
    print()
    print("Tip: Review past reports to see how your observations matched reality!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWorkflow cancelled by user.")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        print("\nIf you need help, check:")
        print("  - Database exists: d:/strategy=Z/db/stock.db")
        print("  - All scripts are in place")
        print("  - Run: python db/init_db.py (if first time)")