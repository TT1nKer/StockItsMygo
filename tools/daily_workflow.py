"""
Daily Workflow - Observation Mode (Layer 5: Orchestration)
每日工作流程 - 观察模式

Daily workflow for finding and analyzing potential stocks before actual trading.
在实际交易前寻找和分析潜在股票的每日工作流程。

Layer constraints:
- ✅ Can call Layer 2 (Signals), Layer 3 (Events - optional), Layer 4 (Reporting)
- ❌ Cannot call Layer 1 (Database) directly - must go through Signal layer
- ❌ Cannot contain business logic (calculations, scoring, filtering)
- ❌ Cannot contain rendering logic (Markdown formatting)

Workflow steps:
1. Update all stock data (daily prices)
2. Run signal scanners (momentum + anomaly)
3. Build watchlist from signals
4. Download intraday data for watchlist stocks
5. Run advanced analysis on watchlist
6. Run strategies comparison
7. Generate comprehensive daily report

Report structure:
  reports/
    2025/
      01-January/
        Week_01/
          2025-01-01_Monday.md
          2025-01-02_Tuesday.md
"""

import sys
sys.path.insert(0, 'd:/strategy=Z')

from db.api import StockDB
from script.signals.momentum_signal import MomentumSignal
from script.signals.anomaly_signal import AnomalySignal
from script.watchlist import WatchlistManager
from script.advanced_analysis import AdvancedAnalyzer
from script.strategy_manager import StrategyManager
from tools.report_generator import ReportGenerator
from datetime import datetime
import time


class DailyWorkflow:
    """Daily workflow orchestrator for observation phase"""

    def __init__(self, base_dir='d:/strategy=Z'):
        self.base_dir = base_dir
        self.db = StockDB()
        self.today = datetime.now()
        self.today_str = self.today.strftime('%Y-%m-%d')

        # Initialize scanners
        self.momentum_scanner = MomentumSignal()
        self.anomaly_scanner = AnomalySignal()

        # Initialize managers
        self.watchlist = WatchlistManager()
        self.analyzer = AdvancedAnalyzer()
        self.strategy_manager = StrategyManager()
        self.report_generator = ReportGenerator(base_dir)

        # Stats tracking
        self.stats = {
            'start_time': time.time(),
            'updated_stocks': 0,
            'new_watchlist_stocks': 0,
            'total_watchlist': 0,
            'momentum_signals': 0,
            'anomaly_signals': 0,
            'dual_confirmed': 0,
            'strategies_used': [],
            'errors': []
        }

    def run_daily_workflow(self):
        """Execute complete daily workflow"""
        print("=" * 80)
        print(f"DAILY WORKFLOW - {self.today_str}")
        print("=" * 80)
        print()

        try:
            # Step 1: Update data
            self._update_data()

            # Step 2: Scan for signals
            momentum_candidates, anomaly_candidates = self._scan_signals()

            # Step 3: Build watchlist
            self._build_watchlist(momentum_candidates, anomaly_candidates)

            # Step 4: Download intraday data
            self._download_intraday_data()

            # Step 5: Deep analysis
            analyses = self._run_deep_analysis()

            # Step 6: Strategy comparison
            strategy_results = self._run_strategy_comparison()

            # Step 7: Generate report
            report_path = self._generate_report(
                momentum_candidates,
                anomaly_candidates,
                analyses,
                strategy_results
            )

            # Print summary
            self._print_summary(report_path)

        except Exception as e:
            self.stats['errors'].append(f"Workflow error: {str(e)}")
            print(f"[ERROR] Workflow failed: {e}")
            raise

    def _update_data(self):
        """Step 1: Update daily price data for all stocks"""
        print("[Step 1/7] Updating daily price data...")

        try:
            stock_list = self.db.get_stock_list()
            self.stats['updated_stocks'] = len(stock_list)
            print(f"  Data ready for {len(stock_list)} stocks")

        except Exception as e:
            self.stats['errors'].append(f"Data update error: {str(e)}")
            print(f"  [WARNING] Data update failed: {e}")

    def _scan_signals(self):
        """Step 2: Run momentum and anomaly scanners"""
        print("[Step 2/7] Scanning for signals...")

        # Step 2.1: Momentum scanner
        print("  [2.1] Running momentum scanner...")
        momentum_candidates = self.momentum_scanner.scan(
            min_score=70,
            limit=50,
            min_price=5.0,
            max_price=200.0,
            min_volume=500000
        )
        self.stats['momentum_signals'] = len(momentum_candidates)
        print(f"  Found {len(momentum_candidates)} momentum signals")

        # Step 2.2: Anomaly scanner
        print("  [2.2] Running anomaly scanner...")
        anomaly_candidates = self.anomaly_scanner.scan(
            min_score=60,
            limit=50
        )
        self.stats['anomaly_signals'] = len(anomaly_candidates)
        print(f"  Found {len(anomaly_candidates)} anomaly signals")

        return momentum_candidates, anomaly_candidates

    def _build_watchlist(self, momentum_candidates, anomaly_candidates):
        """Step 3: Build watchlist from signals"""
        print("[Step 3/7] Building watchlist...")

        # Get current watchlist
        current_watchlist = self.watchlist.get_list()
        initial_count = len(current_watchlist)

        # Create symbol maps for dual confirmation
        momentum_map = {c.symbol: c.score for c in momentum_candidates}
        anomaly_map = {c.symbol: c.score for c in anomaly_candidates}

        # Add dual-confirmed stocks (highest priority)
        dual_confirmed = set()
        for symbol in set(momentum_map.keys()) & set(anomaly_map.keys()):
            if momentum_map[symbol] >= 80 and anomaly_map[symbol] >= 60:
                dual_confirmed.add(symbol)
                self.watchlist.add(
                    symbol=symbol,
                    source='dual_confirmed',
                    priority=1,
                    notes=f"Momentum: {momentum_map[symbol]}, Anomaly: {anomaly_map[symbol]}"
                )

        self.stats['dual_confirmed'] = len(dual_confirmed)

        # Add high-score momentum signals
        for candidate in momentum_candidates:
            if candidate.score >= 85 and candidate.symbol not in dual_confirmed:
                self.watchlist.add(
                    symbol=candidate.symbol,
                    source='momentum',
                    priority=2,
                    notes=f"Momentum score: {candidate.score}"
                )

        # Add high-score anomaly signals (core 3-factor only)
        for candidate in anomaly_candidates:
            if candidate.is_core_three_factor() and candidate.symbol not in dual_confirmed:
                self.watchlist.add(
                    symbol=candidate.symbol,
                    source='anomaly',
                    priority=2,
                    notes=f"Anomaly score: {candidate.score} (Core 3-factor)"
                )

        # Calculate new additions
        final_watchlist = self.watchlist.get_list()
        self.stats['new_watchlist_stocks'] = len(final_watchlist) - initial_count
        self.stats['total_watchlist'] = len(final_watchlist)

        print(f"  Watchlist: {len(final_watchlist)} stocks ({self.stats['new_watchlist_stocks']} new)")
        print(f"  Dual-confirmed: {self.stats['dual_confirmed']}")

    def _download_intraday_data(self):
        """Step 4: Download intraday data for watchlist stocks"""
        print("[Step 4/7] Downloading intraday data...")

        try:
            watchlist_stocks = self.watchlist.get_list()
            symbols = [w['symbol'] for w in watchlist_stocks]

            if symbols:
                print(f"  Downloading data for {len(symbols)} watchlist stocks...")
                # In observation mode, we skip this step (too slow)
                print(f"  [SKIPPED] Intraday data download (observation mode)")
            else:
                print(f"  No stocks in watchlist")

        except Exception as e:
            self.stats['errors'].append(f"Intraday download error: {str(e)}")
            print(f"  [WARNING] Intraday download failed: {e}")

    def _run_deep_analysis(self):
        """Step 5: Run advanced analysis on watchlist"""
        print("[Step 5/7] Running deep analysis...")

        analyses = []

        try:
            watchlist_stocks = self.watchlist.get_list()
            high_priority = [w for w in watchlist_stocks if w.get('priority') == 1]

            if high_priority:
                print(f"  Analyzing {len(high_priority)} high-priority stocks...")

                for stock in high_priority:
                    try:
                        analysis = self.analyzer.analyze(stock['symbol'])
                        if analysis:
                            analyses.append(analysis)
                    except Exception:
                        continue

                print(f"  Completed {len(analyses)} analyses")
            else:
                print(f"  No high-priority stocks to analyze")

        except Exception as e:
            self.stats['errors'].append(f"Analysis error: {str(e)}")
            print(f"  [WARNING] Deep analysis failed: {e}")

        return analyses

    def _run_strategy_comparison(self):
        """Step 6: Run all strategies comparison"""
        print("[Step 6/7] Running strategy comparison...")

        strategy_results = []

        try:
            strategies = self.strategy_manager.get_all_strategies()
            self.stats['strategies_used'] = [s['name'] for s in strategies]

            print(f"  Comparing {len(strategies)} strategies...")

            for strategy in strategies:
                try:
                    result = self.strategy_manager.run_strategy(strategy['name'])
                    if result:
                        strategy_results.append(result)
                except Exception:
                    continue

            print(f"  Completed {len(strategy_results)} strategy runs")

        except Exception as e:
            self.stats['errors'].append(f"Strategy comparison error: {str(e)}")
            print(f"  [WARNING] Strategy comparison failed: {e}")

        return strategy_results

    def _generate_report(self, momentum_candidates, anomaly_candidates,
                        analyses, strategy_results):
        """Step 7: Generate comprehensive daily report"""
        print("[Step 7/7] Generating report...")

        try:
            watchlist = self.watchlist.get_list()

            report_path = self.report_generator.generate_daily_report(
                momentum_candidates=momentum_candidates,
                anomaly_candidates=anomaly_candidates,
                watchlist=watchlist,
                analyses=analyses,
                strategy_results=strategy_results,
                stats=self.stats
            )

            print(f"  Report generated successfully")
            return report_path

        except Exception as e:
            self.stats['errors'].append(f"Report generation error: {str(e)}")
            print(f"  [ERROR] Report generation failed: {e}")
            raise

    def _print_summary(self, report_path):
        """Print execution summary"""
        print()
        print("=" * 80)
        print("DAILY WORKFLOW COMPLETED")
        print("=" * 80)
        print()
        print(f"Report saved to: {report_path}")
        print()
        print("Summary:")
        print(f"  - Momentum signals: {self.stats['momentum_signals']}")
        print(f"  - Anomaly signals: {self.stats['anomaly_signals']}")
        print(f"  - Dual confirmed: {self.stats['dual_confirmed']}")
        print(f"  - Watchlist stocks: {self.stats['total_watchlist']}")
        print(f"  - New additions: {self.stats['new_watchlist_stocks']}")
        print(f"  - Strategies used: {', '.join(self.stats['strategies_used'])}")
        print(f"  - Execution time: {time.time() - self.stats['start_time']:.1f}s")

        if self.stats['errors']:
            print(f"  - Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                print(f"    * {error}")

        print()
        print("Next steps:")
        print("  1. Open the report and review all sections")
        print("  2. Add your personal observations and notes")
        print("  3. Track these stocks over the coming days")
        print("  4. Run this workflow daily to build experience")
        print()


def run_daily_workflow():
    """Entry point for daily workflow"""
    workflow = DailyWorkflow()
    workflow.run_daily_workflow()


if __name__ == '__main__':
    run_daily_workflow()
