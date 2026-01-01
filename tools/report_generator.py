"""
Report Generator (Layer 4)

Consumes standardized data objects and generates Markdown reports.
Does NOT access database or perform calculations - only renders data.

Layer constraints:
- ✅ Can consume WatchlistCandidate, ConfirmedEvent (read-only)
- ❌ Cannot call Layer 1 (db.api)
- ❌ Cannot call Layer 2 (signal scanners)
- ❌ Cannot call Layer 3 (event discovery)
"""

from typing import List, Dict, Any
from datetime import datetime
import os
import time


class ReportGenerator:
    """
    Report generator for daily workflow

    Renders standardized data objects into Markdown format.
    Pure rendering logic - no business logic or data access.
    """

    def __init__(self, base_dir: str = 'd:/strategy=Z'):
        self.base_dir = base_dir
        self.today = datetime.now()
        self.today_str = self.today.strftime('%Y-%m-%d')
        self.day_name = self.today.strftime('%A')

    def generate_daily_report(self,
                             momentum_candidates: List,
                             anomaly_candidates: List,
                             watchlist: List[Dict],
                             analyses: List[Dict],
                             strategy_results: List[Dict],
                             stats: Dict[str, Any]) -> str:
        """
        Generate comprehensive daily report

        Args:
            momentum_candidates: List of momentum signals (dicts or WatchlistCandidate)
            anomaly_candidates: List of anomaly signals (dicts or WatchlistCandidate)
            watchlist: List of watchlist entries
            analyses: List of detailed analyses
            strategy_results: List of strategy comparison results
            stats: Execution statistics dict

        Returns:
            str: Path to generated report file
        """
        report_dir = self._create_report_structure()
        report_path = self._get_report_filepath(report_dir)
        execution_time = time.time() - stats.get('start_time', time.time())

        with open(report_path, 'w', encoding='utf-8') as f:
            # Header
            self._write_header(f, stats, execution_time,
                              len(momentum_candidates), len(anomaly_candidates),
                              len(watchlist), len(analyses))

            # Section 1: Momentum Opportunities
            self._write_momentum_section(f, momentum_candidates)

            # Section 2: Anomaly-Based Opportunities
            self._write_anomaly_section(f, anomaly_candidates, momentum_candidates, stats)

            # Section 3: Watchlist Analysis
            self._write_watchlist_section(f, watchlist, analyses)

            # Section 4: Strategy Comparison
            self._write_strategy_section(f, strategy_results, stats)

            # Section 5: Risk Management
            self._write_risk_section(f)

            # Section 6: Learning Points
            self._write_learning_section(f)

            # Footer
            self._write_footer(f, stats)

        return report_path

    def _create_report_structure(self) -> str:
        """Create report folder structure: reports/YYYY/MM-MonthName/Week_XX/"""
        year = self.today.strftime('%Y')
        month = self.today.strftime('%m-%B')
        week_num = self.today.isocalendar()[1]
        week_folder = f"Week_{week_num:02d}"

        report_path = os.path.join(self.base_dir, 'reports', year, month, week_folder)
        os.makedirs(report_path, exist_ok=True)

        return report_path

    def _get_report_filepath(self, report_dir: str) -> str:
        """Get today's report file path"""
        filename = f"{self.today_str}_{self.day_name}.md"
        return os.path.join(report_dir, filename)

    def _write_header(self, f, stats, execution_time,
                     momentum_count, anomaly_count, watchlist_count, analysis_count):
        """Write report header and executive summary"""
        f.write(f"# Daily Market Report - {self.today_str} ({self.day_name})\n\n")
        f.write(f"**Mode**: Observation (No Trading)\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        f.write(f"- **Momentum Opportunities Found**: {momentum_count}\n")
        f.write(f"- **Anomaly Signals Detected**: {anomaly_count}\n")
        f.write(f"- **Dual Confirmed Stocks**: {stats.get('dual_confirmed', 0)}\n")
        f.write(f"- **Watchlist Stocks**: {watchlist_count}\n")
        f.write(f"- **New Additions Today**: {stats.get('new_watchlist_stocks', 0)}\n")
        f.write(f"- **Deep Analyses Completed**: {analysis_count}\n")
        f.write(f"- **Strategies Used**: {', '.join(stats.get('strategies_used', []))}\n")
        f.write(f"- **Execution Time**: {execution_time:.1f} seconds\n\n")

    def _write_momentum_section(self, f, momentum_signals):
        """Write momentum opportunities section"""
        f.write("---\n\n")
        f.write("## 1. Top Momentum Opportunities\n\n")
        f.write("*Stocks showing strong momentum (Score >= 70)*\n\n")

        if momentum_signals:
            # Convert to dict format if needed (support both old dict and new WatchlistCandidate)
            signals = []
            for sig in momentum_signals:
                if hasattr(sig, 'to_dict'):  # WatchlistCandidate
                    # Convert to old format for now
                    signals.append({
                        'symbol': sig.symbol,
                        'momentum_score': sig.score,
                        'signal': ', '.join(sig.tags) if sig.tags else 'N/A',
                        'momentum_pct': sig.metadata.get('momentum_20d', 0),
                        'volume': sig.metadata.get('volume', 0),
                        'entry_price': sig.close,
                        'stop_loss': sig.stop_loss or 0,
                        'take_profit': sig.close * 1.12,  # +12%
                        'position_size': 0,
                        'reasons': sig.tags
                    })
                else:  # Old dict format
                    signals.append(sig)

            # Summary table
            f.write("| Rank | Symbol | Score | Signal | Momentum | Volume | Entry | Stop Loss | Take Profit |\n")
            f.write("|------|--------|-------|--------|----------|--------|-------|-----------|-------------|\n")

            for i, sig in enumerate(signals[:10], 1):
                f.write(f"| {i} | **{sig['symbol']}** | "
                       f"{sig.get('momentum_score', 0):.0f} | {sig.get('signal', 'N/A')} | "
                       f"{sig.get('momentum_pct', 0):+.2f}% | {sig.get('volume', 0):,.0f} | "
                       f"${sig.get('entry_price', 0):.2f} | "
                       f"${sig.get('stop_loss', 0):.2f} | "
                       f"${sig.get('take_profit', 0):.2f} |\n")

            # Trade plans for top 3
            f.write("\n### Trade Plans (Top 3)\n\n")
            for i, sig in enumerate(signals[:3], 1):
                f.write(f"#### {i}. {sig['symbol']} - {sig.get('signal', 'N/A')}\n\n")
                f.write(f"**Score**: {sig.get('momentum_score', 0):.0f}/100\n\n")
                f.write(f"**Reasons**:\n")
                for reason in sig.get('reasons', []):
                    f.write(f"- {reason}\n")
                f.write(f"\n**Trade Setup** (For when trading starts):\n")
                entry = sig.get('entry_price', 0)
                stop = sig.get('stop_loss', 0)
                take = sig.get('take_profit', 0)
                f.write(f"- Entry: ${entry:.2f}\n")
                if entry > 0:
                    f.write(f"- Stop Loss: ${stop:.2f} ({(stop - entry) / entry * 100:.1f}%)\n")
                    f.write(f"- Take Profit: ${take:.2f} ({(take - entry) / entry * 100:.1f}%)\n")
                f.write(f"- Position Size: {sig.get('position_size', 0)} shares\n\n")
        else:
            f.write("*No momentum opportunities found today.*\n\n")

    def _write_anomaly_section(self, f, anomaly_signals, momentum_signals, stats):
        """Write anomaly-based opportunities section"""
        f.write("---\n\n")
        f.write("## 2. Anomaly-Based Opportunities\n\n")
        f.write("**Philosophy**: Not predicting direction, only identifying structural anomalies\n\n")
        f.write("**Core Principle**: Worth risking -1R when 3 factors align:\n")
        f.write("- Volatility anomaly (TR/ATR > 2x)\n")
        f.write("- Volume spike (Volume/MA > 1.5x)\n")
        f.write("- Clear structure (Stop loss naturally exists)\n\n")

        if anomaly_signals:
            # Convert to unified format
            signals = []
            for sig in anomaly_signals:
                if hasattr(sig, 'to_dict'):  # WatchlistCandidate
                    signals.append({
                        'symbol': sig.symbol,
                        'score': sig.score,
                        'close': sig.close,
                        'volatility': sig.has_tag('VOLATILITY_EXPANSION'),
                        'volume': sig.has_tag('VOLUME_SPIKE'),
                        'structure': sig.has_tag('CLEAR_STRUCTURE'),
                        'stop_loss': sig.stop_loss or 0,
                        'risk_pct': sig.risk_pct or 0
                    })
                else:  # Old dict format
                    signals.append(sig)

            # Core 3-Factor Signals
            f.write("### Core 3-Factor Signals\n\n")
            f.write("*Stocks with volatility + volume + structure alignment*\n\n")

            core_three = [s for s in signals if s.get('volatility') and s.get('volume') and s.get('structure')]

            if core_three:
                f.write("| Symbol | Score | Vol | Amt | Struct | Stop Loss | Risk % | Close |\n")
                f.write("|--------|-------|-----|-----|--------|-----------|--------|-------|\n")

                for sig in core_three[:10]:
                    vol_check = "[OK]" if sig.get('volatility') else "[X]"
                    volume_check = "[OK]" if sig.get('volume') else "[X]"
                    struct_check = "[OK]" if sig.get('structure') else "[X]"

                    f.write(f"| **{sig['symbol']}** | {sig['score']} | "
                           f"{vol_check} | {volume_check} | {struct_check} | "
                           f"${sig.get('stop_loss', 0):.2f} | "
                           f"{sig.get('risk_pct', 0):.1f}% | "
                           f"${sig['close']:.2f} |\n")

                f.write(f"\n**Count**: {len(core_three)} stocks with all 3 factors aligned\n\n")
            else:
                f.write("*No stocks with all 3 core factors today*\n\n")

            # Anomaly Distribution
            f.write("### Anomaly Distribution\n\n")
            volatility_count = sum(1 for s in signals if s.get('volatility'))
            volume_count = sum(1 for s in signals if s.get('volume'))
            structure_count = sum(1 for s in signals if s.get('structure'))

            f.write(f"- Volatility anomaly: {volatility_count} stocks\n")
            f.write(f"- Volume spike: {volume_count} stocks\n")
            f.write(f"- Clear structure: {structure_count} stocks\n")
            f.write(f"- **All 3 factors**: {len(core_three)} stocks <- Focus here\n\n")

            # Dual Confirmed Signals
            if stats.get('dual_confirmed', 0) > 0:
                self._write_dual_confirmed(f, signals, momentum_signals)

            # Method Comparison
            if momentum_signals and signals:
                self._write_method_comparison(f, signals, momentum_signals)
        else:
            f.write("*No anomalies detected today (market behaving normally)*\n\n")

    def _write_dual_confirmed(self, f, anomaly_signals, momentum_signals):
        """Write dual confirmed signals subsection"""
        f.write("### Dual Confirmed Signals\n\n")
        f.write("*Stocks with BOTH momentum >= 80 AND anomaly >= 60*\n\n")

        # Create momentum map
        momentum_map = {}
        for sig in momentum_signals:
            if hasattr(sig, 'symbol'):
                momentum_map[sig.symbol] = sig.score
            else:
                momentum_map[sig['symbol']] = sig.get('momentum_score', 0)

        dual_stocks = []
        for sig in anomaly_signals:
            symbol = sig.get('symbol')
            if symbol in momentum_map:
                mom_score = momentum_map[symbol]
                anom_score = sig.get('score', 0)
                if mom_score >= 80 and anom_score >= 60:
                    dual_stocks.append((symbol, mom_score, anom_score))

        if dual_stocks:
            f.write("| Symbol | Momentum Score | Anomaly Score | Status |\n")
            f.write("|--------|----------------|---------------|--------|\n")

            for symbol, mom_score, anom_score in dual_stocks[:10]:
                status = "Strong" if anom_score >= 80 else "Good"
                f.write(f"| **{symbol}** | {mom_score:.0f} | {anom_score} | {status} |\n")

            f.write(f"\n**Count**: {len(dual_stocks)} dual-confirmed stocks\n\n")

    def _write_method_comparison(self, f, anomaly_signals, momentum_signals):
        """Write method comparison subsection"""
        f.write("### Method Comparison: Momentum vs Anomaly\n\n")

        # Create maps
        momentum_map = {}
        anomaly_map = {}

        for sig in momentum_signals:
            if hasattr(sig, 'symbol'):
                momentum_map[sig.symbol] = sig.score
            else:
                momentum_map[sig['symbol']] = sig.get('momentum_score', 0)

        for sig in anomaly_signals:
            anomaly_map[sig['symbol']] = sig['score']

        all_symbols = set()
        all_symbols.update(momentum_map.keys())
        all_symbols.update(anomaly_map.keys())

        comparison = []
        for symbol in all_symbols:
            mom_score = momentum_map.get(symbol, 0)
            anom_score = anomaly_map.get(symbol, 0)

            if mom_score >= 70 or anom_score >= 60:
                comparison.append((symbol, mom_score, anom_score))

        # Sort: dual high priority
        comparison.sort(key=lambda x: (x[1] + x[2], min(x[1], x[2])), reverse=True)

        if comparison:
            f.write("| Symbol | Momentum | Anomaly | Recommended Action |\n")
            f.write("|--------|----------|---------|--------------------|\n")

            for symbol, mom, anom in comparison[:15]:
                if mom >= 80 and anom >= 60:
                    action = "Strong Watch (Dual Confirmed)"
                elif mom >= 85:
                    action = "Trend Trade (Momentum Only)"
                elif anom >= 70:
                    action = "Structure Trade (Anomaly Only)"
                else:
                    action = "Monitor"

                f.write(f"| **{symbol}** | {mom:.0f} | {anom} | {action} |\n")

            f.write("\n")

    def _write_watchlist_section(self, f, watchlist, analyses):
        """Write watchlist deep analysis section"""
        f.write("---\n\n")
        f.write("## 3. Watchlist - Deep Analysis\n\n")

        if len(watchlist) > 0:
            f.write(f"**Current Watchlist**: {len(watchlist)} stocks\n\n")

            # Summary table
            f.write("| Symbol | Priority | Added | Source | Notes |\n")
            f.write("|--------|----------|-------|--------|-------|\n")
            for _, w in watchlist.iterrows():
                pri_map = {1: 'High', 2: 'Medium', 3: 'Low'}
                priority = w.get('priority', 3)
                added_date = str(w.get('added_date', ''))[:10]
                source = w.get('source', 'N/A')
                notes = str(w.get('notes', ''))[:30]
                f.write(f"| **{w['symbol']}** | {pri_map.get(priority, 'N/A')} | "
                       f"{added_date} | {source} | {notes} |\n")
            f.write("\n")

            # Detailed analyses
            if analyses:
                f.write("### Detailed Technical Analysis\n\n")

                for analysis in analyses:
                    symbol = analysis['symbol']
                    f.write(f"#### {symbol}\n\n")
                    f.write(f"**Overall Score**: {analysis.get('overall_score', 0)}/100\n\n")
                    f.write(f"**Signal**: {analysis.get('signal', 'N/A')}\n\n")

                    # Technical indicators
                    if 'indicators' in analysis:
                        f.write("**Technical Indicators**:\n")
                        for key, value in analysis['indicators'].items():
                            f.write(f"- {key}: {value}\n")
                        f.write("\n")

                    # Recommendations
                    if 'recommendation' in analysis:
                        f.write(f"**Recommendation**: {analysis['recommendation']}\n\n")
        else:
            f.write("*No stocks in watchlist*\n\n")

    def _write_strategy_section(self, f, strategy_results, stats):
        """Write strategy comparison section"""
        f.write("---\n\n")
        f.write("## 4. Strategy Comparison\n\n")
        f.write("*Performance comparison across different strategies*\n\n")

        if strategy_results:
            f.write("| Strategy | Signals | Avg Score | Top Symbol | Win Rate |\n")
            f.write("|----------|---------|-----------|------------|----------|\n")

            for result in strategy_results:
                f.write(f"| {result.get('strategy', 'N/A')} | "
                       f"{result.get('signal_count', 0)} | "
                       f"{result.get('avg_score', 0):.1f} | "
                       f"{result.get('top_symbol', 'N/A')} | "
                       f"{result.get('win_rate', 0):.1f}% |\n")
            f.write("\n")
        else:
            f.write("*No strategy results available*\n\n")

    def _write_risk_section(self, f):
        """Write risk management section"""
        f.write("---\n\n")
        f.write("## 5. Risk Management Reminders\n\n")
        f.write("**IMPORTANT: Currently in OBSERVATION MODE - No real trades**\n\n")
        f.write("When you start trading, remember:\n\n")
        f.write("- Max 2-3 positions at once\n")
        f.write("- Position size: 30-40% of capital per trade\n")
        f.write("- Always use stop loss (-3% to -5%)\n")
        f.write("- Take profit: +8% to +15%\n")
        f.write("- Never risk more than 2% of total capital per trade\n\n")

    def _write_learning_section(self, f):
        """Write learning points section"""
        f.write("---\n\n")
        f.write("## 6. Learning Points\n\n")
        f.write("*Track what you're learning during this observation period*\n\n")
        f.write("- [ ] Strategy performance observation\n")
        f.write("- [ ] Pattern recognition practice\n")
        f.write("- [ ] Risk management review\n")
        f.write("- [ ] Market sentiment analysis\n\n")

    def _write_footer(self, f, stats):
        """Write report footer"""
        f.write("---\n\n")
        f.write(f"*Report generated by Daily Workflow System*\n\n")
        f.write(f"**Next Steps**:\n")
        f.write(f"1. Review all sections\n")
        f.write(f"2. Add your personal observations\n")
        f.write(f"3. Update watchlist priorities based on analysis\n")
        f.write(f"4. Track these stocks' performance tomorrow\n\n")

        if stats.get('errors'):
            f.write("**Errors Encountered**:\n")
            for error in stats['errors']:
                f.write(f"- {error}\n")
