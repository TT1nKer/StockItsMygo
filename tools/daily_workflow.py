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
1. Check trading calendar + data freshness (with auto-update option)
2. Run signal scanners (momentum + anomaly) + apply learned policy
3. Build watchlist from signals
4. Download intraday data for watchlist stocks
5. Run advanced analysis on watchlist
6. Run strategies comparison
7. Generate comprehensive daily report
8. Export label worksheet for human feedback (v2.2.0)

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
from script.trading_calendar import TradingCalendar  # v2.2.0: Trading day detection
from tools.report_generator import ReportGenerator
from tools.label_tools import export_label_todo  # v2.2.0: Human feedback loop
from script.label_policy import apply_policy_to_candidates  # v2.2.0: Apply learned preferences
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

            # Step 8: Export label worksheet (v2.2.0 - human feedback loop)
            self._export_label_worksheet(momentum_candidates, anomaly_candidates)

            # Print summary
            self._print_summary(report_path)

        except Exception as e:
            self.stats['errors'].append(f"Workflow error: {str(e)}")
            print(f"[ERROR] Workflow failed: {e}")
            raise

    def _update_data(self):
        """Step 1: Check trading calendar and verify data freshness"""
        print("[Step 1/8] Checking trading calendar and data freshness...")

        try:
            # Check trading calendar
            calendar_status = TradingCalendar.should_update_data()
            expected_date = TradingCalendar.get_expected_data_date()

            print(f"  Today: {self.today_str} ({self.today.strftime('%A')})")
            print(f"  Trading Day: {calendar_status['today_is_trading_day']}")
            print(f"  Expected Data Date: {expected_date.strftime('%Y-%m-%d')}")

            # Check data freshness (get latest date in database)
            stock_list = self.db.get_stock_list()
            if len(stock_list) > 0:
                # Sample a few stocks to check latest data date
                sample_symbol = stock_list[0]
                latest_data = self.db.get_price_history(sample_symbol)

                if latest_data is not None and len(latest_data) > 0:
                    # Sort by date descending to get latest
                    latest_data = latest_data.sort_values('date', ascending=False)
                    latest_db_date = latest_data.iloc[0]['date']
                    if isinstance(latest_db_date, str):
                        latest_db_date = datetime.strptime(latest_db_date, '%Y-%m-%d').date()

                    print(f"  Latest Data in DB: {latest_db_date.strftime('%Y-%m-%d')}")

                    if latest_db_date >= expected_date:
                        print(f"  [OK] Data is up-to-date")
                    else:
                        days_behind = (expected_date - latest_db_date).days
                        print(f"  [WARNING] Data is {days_behind} day(s) behind expected")

                        # Offer update regardless of trading day status
                        print()
                        response = input(f"  Update last {min(days_behind + 2, 10)} days now? (yes/no): ").strip().lower()
                        if response == 'yes':
                            self._run_incremental_update(days_behind)

            self.stats['updated_stocks'] = len(stock_list)
            print(f"  Total stocks in database: {len(stock_list)}")

            if not calendar_status['should_update']:
                print(f"  Note: {calendar_status['reason']}")

        except Exception as e:
            self.stats['errors'].append(f"Data check error: {str(e)}")
            print(f"  [WARNING] Data check failed: {e}")

    def _run_incremental_update(self, days_behind):
        """Run incremental data update for recent days"""
        print(f"  Starting incremental update...")
        print()

        # Calculate update period (add buffer days)
        days_to_update = min(days_behind + 2, 10)  # Max 10 days
        period = f"{days_to_update}d"

        try:
            stock_list = self.db.get_stock_list()
            batch_size = 200
            workers = 3  # Reduced from 10 to avoid SQLite lock issues
            total_success = 0
            total_failed = 0

            print(f"  Updating {len(stock_list)} stocks (last {days_to_update} days)...")
            print(f"  Batch size: {batch_size}, Workers: {workers}")
            print()

            # Process in batches
            total_batches = (len(stock_list) + batch_size - 1) // batch_size

            for i in range(0, len(stock_list), batch_size):
                batch_num = (i // batch_size) + 1
                batch = stock_list[i:i+batch_size]

                print(f"  [Batch {batch_num}/{total_batches}] Updating {len(batch)} stocks...", end=' ')

                results = self.db.batch_download_prices(
                    symbols=batch,
                    period=period,
                    workers=workers
                )

                total_success += results['success']
                total_failed += results['failed']

                print(f"Success: {results['success']}/{len(batch)}")

                if batch_num < total_batches:
                    time.sleep(1)  # Brief pause between batches

            print()
            print(f"  Update completed: {total_success} success, {total_failed} failed")

            # Verify update
            sample_symbol = stock_list[0]
            latest_data = self.db.get_price_history(sample_symbol)
            if latest_data is not None and len(latest_data) > 0:
                latest_data = latest_data.sort_values('date', ascending=False)
                latest_db_date = latest_data.iloc[0]['date']
                if isinstance(latest_db_date, str):
                    latest_db_date = datetime.strptime(latest_db_date, '%Y-%m-%d').date()

                expected_date = TradingCalendar.get_expected_data_date()
                if latest_db_date >= expected_date:
                    print(f"  [OK] Data is now up-to-date ({latest_db_date.strftime('%Y-%m-%d')})")
                else:
                    print(f"  [WARNING] Still behind (latest: {latest_db_date.strftime('%Y-%m-%d')})")

            print()

        except Exception as e:
            self.stats['errors'].append(f"Incremental update error: {str(e)}")
            print(f"  [ERROR] Update failed: {e}")
            print()

    def _scan_signals(self):
        """Step 2: Run momentum and anomaly scanners + apply learned policy"""
        print("[Step 2/8] Scanning for signals...")

        # Step 2.1: Momentum scanner
        print("  [2.1] Running momentum scanner...")
        momentum_candidates = self.momentum_scanner.scan(
            min_score=70,
            limit=50,
            min_price=5.0,
            max_price=200.0,
            min_volume=500000
        )
        print(f"  Found {len(momentum_candidates)} momentum signals")

        # Step 2.2: Anomaly scanner
        print("  [2.2] Running anomaly scanner...")
        anomaly_candidates = self.anomaly_scanner.scan(
            min_score=60,
            limit=50
        )
        print(f"  Found {len(anomaly_candidates)} anomaly signals")

        # Step 2.3: Apply learned policy (v2.2.0 - human feedback loop)
        print("  [2.3] Applying learned policy...")
        all_candidates = momentum_candidates + anomaly_candidates
        raw_count = len(all_candidates)

        try:
            filtered_candidates = apply_policy_to_candidates(all_candidates)

            # Split back to momentum/anomaly
            momentum_candidates = [c for c in filtered_candidates if c.source == 'momentum']
            anomaly_candidates = [c for c in filtered_candidates if c.source == 'anomaly']

            filtered_count = len(filtered_candidates)
            if filtered_count < raw_count:
                print(f"  Policy filtered: {raw_count} → {filtered_count} candidates ({raw_count - filtered_count} removed)")
            else:
                print(f"  No policy active or no filtering applied")

        except Exception as e:
            print(f"  [WARNING] Policy application failed: {e}, using unfiltered candidates")

        self.stats['momentum_signals'] = len(momentum_candidates)
        self.stats['anomaly_signals'] = len(anomaly_candidates)

        return momentum_candidates, anomaly_candidates

    def _build_watchlist(self, momentum_candidates, anomaly_candidates):
        """Step 3: Build watchlist from signals"""
        print("[Step 3/8] Building watchlist...")

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
        print("[Step 4/8] Downloading intraday data...")

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
        print("[Step 5/8] Running deep analysis...")

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
        print("[Step 6/8] Running strategy comparison...")

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
        print("[Step 7/8] Generating report...")

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

    def _export_label_worksheet(self, momentum_candidates, anomaly_candidates):
        """Step 8: Export labeling worksheet for human feedback (v2.2.0)"""
        print("[Step 8/8] Exporting label worksheet...")

        try:
            all_candidates = momentum_candidates + anomaly_candidates

            if len(all_candidates) == 0:
                print("  No candidates to export")
                return

            label_path = export_label_todo(
                date=self.today_str,
                candidates=all_candidates,
                output_dir=f"{self.base_dir}/DATA/labels"
            )

            print()
            print("  " + "=" * 76)
            print("  HUMAN FEEDBACK LOOP - ACTION REQUIRED")
            print("  " + "=" * 76)
            print(f"  1. Open: {label_path}")
            print(f"  2. Fill columns: 'label' (consider/skip) and 'skip_reason'")
            print(f"  3. Save the file")
            print(f"  4. Run: python -c \"from tools.label_tools import collect_labels; collect_labels('{self.today_str}')\"")
            print("  " + "=" * 76)
            print()
            print("  After 50+ labels, run: python script/label_policy.py")
            print("  This will generate filtering rules from your preferences.")
            print()

        except Exception as e:
            print(f"  [WARNING] Label export failed: {e}")
            # Don't fail the workflow if labeling export fails

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
