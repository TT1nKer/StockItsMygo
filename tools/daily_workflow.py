"""
Daily Workflow - Observation Mode
每日工作流程 - 观察模式

Daily workflow for finding and analyzing potential stocks before actual trading.
在实际交易前寻找和分析潜在股票的每日工作流程。

Workflow steps:
1. Update all stock data (daily prices)
2. Run momentum scanner to find promising stocks
3. Auto-add high-score stocks to watchlist
4. Download intraday data for watchlist stocks
5. Run advanced analysis on watchlist
6. Run all strategies comparison
7. Generate comprehensive daily report
8. Save report organized by year/month/week

Report structure:
  reports/
    2025/
      01-January/
        Week_01/
          2025-01-01_Monday.md
          2025-01-02_Tuesday.md
        Week_02/
          ...
"""

import sys
sys.path.insert(0, 'd:/strategy=Z')

from db.api import StockDB
from script.momentum_scanner import MomentumScanner
from script.watchlist import WatchlistManager
from script.advanced_analysis import AdvancedAnalyzer
from script.strategy_manager import StrategyManager
from datetime import datetime, timedelta
import os
import time


class DailyWorkflow:
    """Daily workflow orchestrator for observation phase"""

    def __init__(self, base_dir='d:/strategy=Z'):
        self.base_dir = base_dir
        self.db = StockDB()
        self.today = datetime.now()
        self.today_str = self.today.strftime('%Y-%m-%d')
        self.day_name = self.today.strftime('%A')

        # Create reports directory structure
        self.report_dir = self._create_report_structure()

        # Stats tracking
        self.stats = {
            'start_time': time.time(),
            'updated_stocks': 0,
            'new_watchlist_stocks': 0,
            'total_watchlist': 0,
            'momentum_signals': 0,
            'strategies_used': [],
            'errors': []
        }

    def _create_report_structure(self):
        """
        Create report folder structure: reports/YYYY/MM-MonthName/Week_XX/

        Returns:
            str: Path to today's report directory
        """
        year = self.today.strftime('%Y')
        month = self.today.strftime('%m-%B')  # 01-January

        # Calculate week number (ISO week)
        week_num = self.today.isocalendar()[1]
        week_folder = f"Week_{week_num:02d}"

        # Build path
        report_path = os.path.join(
            self.base_dir,
            'reports',
            year,
            month,
            week_folder
        )

        # Create directories
        os.makedirs(report_path, exist_ok=True)

        return report_path

    def _get_report_filepath(self):
        """Get today's report file path"""
        filename = f"{self.today_str}_{self.day_name}.md"
        return os.path.join(self.report_dir, filename)

    def run_daily_workflow(self):
        """
        Execute complete daily workflow

        Steps:
        1. Update daily data
        2. Find promising stocks (momentum scan)
        3. Update watchlist
        4. Download intraday data
        5. Advanced analysis
        6. Strategy comparison
        7. Generate report
        """
        print("=" * 80)
        print(f"DAILY WORKFLOW - OBSERVATION MODE")
        print(f"Date: {self.today_str} ({self.day_name})")
        print("=" * 80)
        print()

        # Step 1: Update daily data
        print("Step 1/7: Updating daily price data...")
        print("-" * 80)
        try:
            # Note: This would update all stocks - skip for now if data is recent
            # In production, you would run: self.db.update_all_stocks()
            print("[INFO] Skipping full update - using existing data")
            print("       To update all stocks, run: python script/update_data.py")
            self.stats['updated_stocks'] = 0  # Would be actual count
        except Exception as e:
            print(f"[ERROR] Data update failed: {e}")
            self.stats['errors'].append(f"Data update: {e}")
        print()

        # Step 2: Run momentum scanner
        print("Step 2/7: Running momentum scanner...")
        print("-" * 80)
        momentum_signals = []
        try:
            scanner = MomentumScanner()
            momentum_signals = scanner.scan(
                min_score=70,
                min_volume=500000,
                sort_by='momentum_score',
                limit=20
            )
            self.stats['momentum_signals'] = len(momentum_signals)
            print(f"[OK] Found {len(momentum_signals)} promising stocks (score >= 70)")

            # Show top 5
            print("\nTop 5 momentum opportunities:")
            for i, sig in enumerate(momentum_signals[:5], 1):
                print(f"  {i}. {sig['symbol']:6s} | Score: {sig['momentum_score']:3.0f} | "
                      f"Momentum: {sig['momentum_pct']:+6.2f}% | Signal: {sig['signal']}")
        except Exception as e:
            print(f"[ERROR] Momentum scan failed: {e}")
            self.stats['errors'].append(f"Momentum scan: {e}")
        print()

        # Step 3: Update watchlist (auto-add high scores)
        print("Step 3/7: Updating watchlist...")
        print("-" * 80)
        try:
            wl_mgr = WatchlistManager()

            # Auto-add top momentum stocks
            added = wl_mgr.auto_add_from_momentum(
                min_score=80,
                max_additions=10,
                skip_existing=True
            )
            self.stats['new_watchlist_stocks'] = len(added)

            # Get current watchlist
            watchlist = wl_mgr.get_watchlist()
            self.stats['total_watchlist'] = len(watchlist)

            print(f"[OK] Added {len(added)} new stocks to watchlist")
            print(f"[OK] Total watchlist stocks: {len(watchlist)}")
        except Exception as e:
            print(f"[ERROR] Watchlist update failed: {e}")
            self.stats['errors'].append(f"Watchlist: {e}")
            watchlist = []
        print()

        # Step 4: Download intraday data for watchlist
        print("Step 4/7: Downloading intraday data for watchlist...")
        print("-" * 80)
        try:
            if watchlist:
                symbols = [w['symbol'] for w in watchlist]
                print(f"[INFO] Downloading 5-minute data for {len(symbols)} stocks...")

                self.db.batch_download_intraday(
                    symbols=symbols,
                    interval='5m',
                    period='7d',
                    workers=3
                )
                print(f"[OK] Intraday data updated")
            else:
                print("[INFO] No stocks in watchlist")
        except Exception as e:
            print(f"[ERROR] Intraday download failed: {e}")
            self.stats['errors'].append(f"Intraday: {e}")
        print()

        # Step 5: Advanced analysis on watchlist
        print("Step 5/7: Running advanced analysis on watchlist...")
        print("-" * 80)
        watchlist_analyses = []
        try:
            analyzer = AdvancedAnalyzer()

            for stock in watchlist[:10]:  # Limit to top 10 for speed
                symbol = stock['symbol']
                print(f"  Analyzing {symbol}...", end=' ')

                try:
                    analysis = analyzer.analyze_stock(symbol, include_intraday=True)
                    watchlist_analyses.append(analysis)
                    print(f"[OK] Score: {analysis['overall_score']}/100")
                except Exception as e:
                    print(f"[ERROR] {e}")

            print(f"\n[OK] Completed {len(watchlist_analyses)} advanced analyses")
        except Exception as e:
            print(f"[ERROR] Advanced analysis failed: {e}")
            self.stats['errors'].append(f"Advanced analysis: {e}")
        print()

        # Step 6: Strategy comparison
        print("Step 6/7: Running multi-strategy comparison...")
        print("-" * 80)
        strategy_results = {}
        try:
            mgr = StrategyManager()
            strategies = ['momentum', 'mean_reversion', 'breakout']
            self.stats['strategies_used'] = strategies

            # Run on top watchlist stocks
            for stock in watchlist[:5]:  # Top 5 only
                symbol = stock['symbol']
                print(f"  Comparing strategies for {symbol}...")

                try:
                    comparison = mgr.compare_strategies(symbol, strategies)
                    strategy_results[symbol] = comparison
                except Exception as e:
                    print(f"    [ERROR] {e}")

            print(f"\n[OK] Strategy comparison completed for {len(strategy_results)} stocks")
        except Exception as e:
            print(f"[ERROR] Strategy comparison failed: {e}")
            self.stats['errors'].append(f"Strategy comparison: {e}")
        print()

        # Step 7: Generate comprehensive report
        print("Step 7/7: Generating daily report...")
        print("-" * 80)
        try:
            report_path = self._generate_daily_report(
                momentum_signals,
                watchlist,
                watchlist_analyses,
                strategy_results
            )
            print(f"[OK] Report saved: {report_path}")
        except Exception as e:
            print(f"[ERROR] Report generation failed: {e}")
            self.stats['errors'].append(f"Report: {e}")
        print()

        # Summary
        self._print_summary()

    def _generate_daily_report(self, momentum_signals, watchlist, analyses, strategy_results):
        """Generate comprehensive markdown report"""

        report_path = self._get_report_filepath()
        execution_time = time.time() - self.stats['start_time']

        with open(report_path, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"# Daily Market Report - {self.today_str} ({self.day_name})\n\n")
            f.write(f"**Mode**: Observation (No Trading)\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Momentum Opportunities Found**: {len(momentum_signals)}\n")
            f.write(f"- **Watchlist Stocks**: {len(watchlist)}\n")
            f.write(f"- **New Additions Today**: {self.stats['new_watchlist_stocks']}\n")
            f.write(f"- **Deep Analyses Completed**: {len(analyses)}\n")
            f.write(f"- **Strategies Used**: {', '.join(self.stats['strategies_used'])}\n")
            f.write(f"- **Execution Time**: {execution_time:.1f} seconds\n\n")

            # Section 1: Top Momentum Opportunities
            f.write("---\n\n")
            f.write("## 1. Top Momentum Opportunities\n\n")
            f.write("*Stocks showing strong momentum (Score >= 70)*\n\n")

            if momentum_signals:
                f.write("| Rank | Symbol | Score | Signal | Momentum | Volume | Entry | Stop Loss | Take Profit |\n")
                f.write("|------|--------|-------|--------|----------|--------|-------|-----------|-------------|\n")

                for i, sig in enumerate(momentum_signals[:10], 1):
                    f.write(f"| {i} | **{sig['symbol']}** | "
                           f"{sig['momentum_score']:.0f} | {sig['signal']} | "
                           f"{sig['momentum_pct']:+.2f}% | {sig['volume']:,.0f} | "
                           f"${sig.get('entry_price', 0):.2f} | "
                           f"${sig.get('stop_loss', 0):.2f} | "
                           f"${sig.get('take_profit', 0):.2f} |\n")

                f.write("\n### Trade Plans (Top 3)\n\n")
                for i, sig in enumerate(momentum_signals[:3], 1):
                    f.write(f"#### {i}. {sig['symbol']} - {sig['signal']}\n\n")
                    f.write(f"**Score**: {sig['momentum_score']:.0f}/100\n\n")
                    f.write(f"**Reasons**:\n")
                    for reason in sig.get('reasons', []):
                        f.write(f"- {reason}\n")
                    f.write(f"\n**Trade Setup** (For when trading starts):\n")
                    f.write(f"- Entry: ${sig.get('entry_price', 0):.2f}\n")
                    f.write(f"- Stop Loss: ${sig.get('stop_loss', 0):.2f} "
                           f"({((sig.get('stop_loss', 0) - sig.get('entry_price', 1)) / sig.get('entry_price', 1) * 100):.1f}%)\n")
                    f.write(f"- Take Profit: ${sig.get('take_profit', 0):.2f} "
                           f"({((sig.get('take_profit', 0) - sig.get('entry_price', 1)) / sig.get('entry_price', 1) * 100):.1f}%)\n")
                    f.write(f"- Position Size: {sig.get('position_size', 0)} shares\n\n")
            else:
                f.write("*No momentum opportunities found today.*\n\n")

            # Section 2: Watchlist Deep Analysis
            f.write("---\n\n")
            f.write("## 2. Watchlist - Deep Analysis\n\n")

            if watchlist:
                f.write(f"**Current Watchlist**: {len(watchlist)} stocks\n\n")

                # Summary table
                f.write("| Symbol | Priority | Added | Source | Notes |\n")
                f.write("|--------|----------|-------|--------|-------|\n")
                for w in watchlist:
                    pri_map = {1: 'High', 2: 'Medium', 3: 'Low'}
                    f.write(f"| **{w['symbol']}** | {pri_map.get(w['priority'], 'N/A')} | "
                           f"{w['added_date'][:10]} | {w['source']} | {w.get('notes', '')[:30]} |\n")
                f.write("\n")

                # Detailed analyses
                if analyses:
                    f.write("### Detailed Technical Analysis\n\n")

                    for analysis in analyses:
                        symbol = analysis['symbol']
                        f.write(f"#### {symbol}\n\n")
                        f.write(f"**Overall Score**: {analysis['overall_score']}/100\n\n")
                        f.write(f"**Signal**: {analysis['signal']}\n\n")

                        # Technical indicators
                        f.write("**Technical Indicators**:\n")
                        indicators = analysis.get('indicators', {})
                        f.write(f"- ADX: {indicators.get('adx', 0):.2f} (Trend Strength)\n")
                        f.write(f"- RSI: {indicators.get('rsi', 0):.2f}\n")
                        f.write(f"- Stochastic K%: {indicators.get('stoch_k', 0):.2f}\n")
                        f.write(f"- ATR: ${indicators.get('atr', 0):.2f} (Volatility)\n")
                        f.write(f"- OBV Trend: {indicators.get('obv_trend', 'N/A')}\n")

                        if indicators.get('vwap'):
                            f.write(f"- VWAP: ${indicators['vwap']:.2f}\n")

                        f.write("\n**Candlestick Patterns**:\n")
                        patterns = analysis.get('patterns', [])
                        if patterns:
                            for pattern in patterns:
                                f.write(f"- {pattern}\n")
                        else:
                            f.write("- None detected\n")

                        f.write("\n**Support/Resistance**:\n")
                        sr = indicators.get('support_resistance', {})
                        f.write(f"- Resistance 2: ${sr.get('r2', 0):.2f}\n")
                        f.write(f"- Resistance 1: ${sr.get('r1', 0):.2f}\n")
                        f.write(f"- Pivot: ${sr.get('pivot', 0):.2f}\n")
                        f.write(f"- Support 1: ${sr.get('s1', 0):.2f}\n")
                        f.write(f"- Support 2: ${sr.get('s2', 0):.2f}\n")

                        f.write("\n**Analysis Reasons**:\n")
                        for reason in analysis.get('reasons', []):
                            f.write(f"- {reason}\n")

                        f.write("\n---\n\n")
            else:
                f.write("*Watchlist is empty.*\n\n")

            # Section 3: Multi-Strategy Comparison
            f.write("---\n\n")
            f.write("## 3. Multi-Strategy Comparison\n\n")
            f.write(f"**Strategies**: {', '.join(self.stats['strategies_used'])}\n\n")

            if strategy_results:
                for symbol, df in strategy_results.items():
                    f.write(f"### {symbol}\n\n")
                    f.write("| Strategy | Signal | Score | Confidence | Entry | Stop Loss | Take Profit |\n")
                    f.write("|----------|--------|-------|------------|-------|-----------|-------------|\n")

                    for _, row in df.iterrows():
                        f.write(f"| {row['strategy']} | {row['signal']} | "
                               f"{row['score']}/100 | {row['confidence']:.1%} | "
                               f"${row['entry_price']:.2f} | ${row['stop_loss']:.2f} | "
                               f"${row['take_profit']:.2f} |\n")
                    f.write("\n")
            else:
                f.write("*No strategy comparisons performed.*\n\n")

            # Section 4: Observations & Notes
            f.write("---\n\n")
            f.write("## 4. Daily Observations\n\n")
            f.write("*This section is for manual notes and observations.*\n\n")
            f.write("### Market Conditions\n\n")
            f.write("- [ ] Bull market / Trending up\n")
            f.write("- [ ] Bear market / Trending down\n")
            f.write("- [ ] Ranging / Consolidating\n")
            f.write("- [ ] High volatility\n\n")
            f.write("### Personal Notes\n\n")
            f.write("```\n")
            f.write("Add your observations here:\n")
            f.write("- What patterns did you notice?\n")
            f.write("- Which stocks look most promising?\n")
            f.write("- What would you do differently?\n")
            f.write("- Questions to research?\n")
            f.write("```\n\n")

            # Section 5: Learning Points
            f.write("---\n\n")
            f.write("## 5. Learning Points\n\n")
            f.write("*Track what you're learning during this observation period*\n\n")
            f.write("- [ ] Strategy performance observation\n")
            f.write("- [ ] Pattern recognition practice\n")
            f.write("- [ ] Risk management review\n")
            f.write("- [ ] Market sentiment analysis\n\n")

            # Footer
            f.write("---\n\n")
            f.write(f"*Report generated by Daily Workflow System*\n\n")
            f.write(f"**Next Steps**:\n")
            f.write(f"1. Review all sections\n")
            f.write(f"2. Add your personal observations\n")
            f.write(f"3. Update watchlist priorities based on analysis\n")
            f.write(f"4. Track these stocks' performance tomorrow\n\n")

            if self.stats['errors']:
                f.write("**Errors Encountered**:\n")
                for error in self.stats['errors']:
                    f.write(f"- {error}\n")

        return report_path

    def _print_summary(self):
        """Print execution summary"""
        print("=" * 80)
        print("DAILY WORKFLOW COMPLETED")
        print("=" * 80)
        print()
        print(f"Report saved to: {self._get_report_filepath()}")
        print()
        print("Summary:")
        print(f"  - Momentum signals found: {self.stats['momentum_signals']}")
        print(f"  - Watchlist stocks: {self.stats['total_watchlist']}")
        print(f"  - New additions: {self.stats['new_watchlist_stocks']}")
        print(f"  - Strategies used: {', '.join(self.stats['strategies_used'])}")
        print(f"  - Execution time: {time.time() - self.stats['start_time']:.1f}s")

        if self.stats['errors']:
            print(f"  - Errors: {len(self.stats['errors'])}")

        print()
        print("Next steps:")
        print("  1. Open the report and review all sections")
        print("  2. Add your personal observations and notes")
        print("  3. Track these stocks over the coming days")
        print("  4. Run this workflow daily to build experience")
        print()


if __name__ == "__main__":
    workflow = DailyWorkflow()
    workflow.run_daily_workflow()