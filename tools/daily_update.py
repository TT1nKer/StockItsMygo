"""
Daily Update Orchestrator
每日更新编排器

8-Step Workflow:
1. Update all daily price data (incremental, 5 workers)
2. Update watchlist intraday data (5m, 3 workers)
3. Recalculate technical indicators
4. Run momentum scanner
5. Auto-add high-score stocks to watchlist (80+)
6. Analyze watchlist stocks (advanced analysis)
7. Generate comprehensive daily report (Markdown)
8. Cleanup old intraday data (keep 30 days)

工作流程 (8步):
1. 更新所有股票日线数据 (增量，5 workers)
2. 更新观察列表5分钟数据 (3 workers)
3. 重新计算技术指标
4. 运行动量扫描器
5. 自动添加高分股票到观察列表 (80+分)
6. 分析观察列表股票 (高级分析)
7. 生成每日综合报告 (Markdown格式)
8. 清理旧分钟数据 (保留30天)
"""

from db.api import StockDB
from script.momentum_strategy import MomentumScanner
from script.watchlist import WatchlistManager
from script.advanced_analysis import AdvancedAnalyzer
from datetime import datetime
import time
import os


class DailyUpdater:
    """每日更新编排器"""

    def __init__(self):
        self.db = StockDB()
        self.scanner = MomentumScanner()
        self.watchlist_mgr = WatchlistManager()
        self.analyzer = AdvancedAnalyzer()

        # 创建报告目录
        self.reports_dir = 'd:/strategy=Z/docs/reports'
        os.makedirs(self.reports_dir, exist_ok=True)

    def run_daily_update(self):
        """
        运行每日完整更新

        Returns:
            dict: 执行结果统计
        """
        start_time = time.time()
        results = {
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'steps_completed': []
        }

        print("=" * 90)
        print("DAILY UPDATE ORCHESTRATOR")
        print(f"Started at: {results['start_time']}")
        print("=" * 90)
        print()

        # ========== Step 1: 更新日线数据 ==========
        print("STEP 1/8: Updating daily price data for all stocks...")
        print("-" * 90)
        step1_start = time.time()

        all_stocks = self.db.get_stock_list()
        batch_result = self.db.batch_download_prices(
            symbols=all_stocks,
            period='5d',  # 增量更新最近5天
            workers=5,
            delay=0.5
        )

        step1_time = time.time() - step1_start
        results['step1_daily_data'] = {
            'total_stocks': len(all_stocks),
            'success': batch_result.get('success', 0),
            'failed': batch_result.get('failed', 0),
            'time_seconds': step1_time
        }
        results['steps_completed'].append('step1_daily_data')

        print(f"Step 1 completed in {step1_time/60:.1f} minutes")
        print()

        # ========== Step 2: 更新观察列表分钟数据 ==========
        print("STEP 2/8: Updating intraday data for watchlist stocks...")
        print("-" * 90)
        step2_start = time.time()

        intraday_result = self.watchlist_mgr.update_intraday_data(
            interval='5m',
            period='7d',
            priority_filter=None  # 所有优先级
        )

        step2_time = time.time() - step2_start
        results['step2_intraday_data'] = {
            'success': intraday_result.get('success', 0),
            'failed': intraday_result.get('failed', 0),
            'time_seconds': step2_time
        }
        results['steps_completed'].append('step2_intraday_data')

        print(f"Step 2 completed in {step2_time:.1f} seconds")
        print()

        # ========== Step 3: 重新计算技术指标 ==========
        print("STEP 3/8: Recalculating technical indicators...")
        print("-" * 90)
        step3_start = time.time()

        # 为今天更新的股票计算技术指标
        indicators_calculated = 0
        for symbol in all_stocks[:100]:  # 演示：仅计算前100只
            try:
                self.db.calculate_technical_indicators(symbol)
                indicators_calculated += 1
            except:
                pass

        step3_time = time.time() - step3_start
        results['step3_indicators'] = {
            'calculated': indicators_calculated,
            'time_seconds': step3_time
        }
        results['steps_completed'].append('step3_indicators')

        print(f"Calculated indicators for {indicators_calculated} stocks")
        print(f"Step 3 completed in {step3_time:.1f} seconds")
        print()

        # ========== Step 4: 运行动量扫描器 ==========
        print("STEP 4/8: Running momentum scanner...")
        print("-" * 90)
        step4_start = time.time()

        candidates = self.scanner.scan_market(
            min_price=5,
            max_price=100,
            min_volume=500000,
            top_n=30
        )

        signals = self.scanner.generate_signals(candidates)

        step4_time = time.time() - step4_start
        results['step4_momentum'] = {
            'candidates_found': len(candidates),
            'signals_generated': len(signals),
            'time_seconds': step4_time
        }
        results['steps_completed'].append('step4_momentum')

        print(f"Found {len(signals)} momentum signals")
        print(f"Step 4 completed in {step4_time/60:.1f} minutes")
        print()

        # ========== Step 5: 自动添加高分股票到观察列表 ==========
        print("STEP 5/8: Auto-adding high-score stocks to watchlist...")
        print("-" * 90)
        step5_start = time.time()

        added_stocks = self.watchlist_mgr.auto_add_from_momentum(
            min_score=80,
            max_additions=10,
            skip_existing=True
        )

        step5_time = time.time() - step5_start
        results['step5_auto_add'] = {
            'stocks_added': len(added_stocks),
            'time_seconds': step5_time
        }
        results['steps_completed'].append('step5_auto_add')

        print(f"Step 5 completed in {step5_time:.1f} seconds")
        print()

        # ========== Step 6: 分析观察列表股票 ==========
        print("STEP 6/8: Analyzing watchlist stocks...")
        print("-" * 90)
        step6_start = time.time()

        watchlist = self.watchlist_mgr.get_list()
        watchlist_analyses = []

        for _, stock in watchlist.iterrows():
            try:
                analysis = self.analyzer.analyze_stock(
                    stock['symbol'],
                    include_intraday=True
                )
                if 'error' not in analysis:
                    watchlist_analyses.append(analysis)
            except Exception as e:
                print(f"{stock['symbol']}: Analysis failed - {str(e)}")

        step6_time = time.time() - step6_start
        results['step6_analysis'] = {
            'stocks_analyzed': len(watchlist_analyses),
            'time_seconds': step6_time
        }
        results['steps_completed'].append('step6_analysis')

        print(f"Analyzed {len(watchlist_analyses)} watchlist stocks")
        print(f"Step 6 completed in {step6_time:.1f} seconds")
        print()

        # ========== Step 7: 生成每日综合报告 ==========
        print("STEP 7/8: Generating comprehensive daily report...")
        print("-" * 90)
        step7_start = time.time()

        report_path = self._generate_daily_report(
            momentum_signals=signals[:10],  # Top 10
            watchlist_analyses=watchlist_analyses,
            execution_stats=results
        )

        step7_time = time.time() - step7_start
        results['step7_report'] = {
            'report_path': report_path,
            'time_seconds': step7_time
        }
        results['steps_completed'].append('step7_report')

        print(f"Report saved to: {report_path}")
        print(f"Step 7 completed in {step7_time:.1f} seconds")
        print()

        # ========== Step 8: 清理旧分钟数据 ==========
        print("STEP 8/8: Cleaning up old intraday data...")
        print("-" * 90)
        step8_start = time.time()

        deleted_count = self.db.cleanup_old_intraday_data(days_to_keep=30)

        step8_time = time.time() - step8_start
        results['step8_cleanup'] = {
            'records_deleted': deleted_count,
            'time_seconds': step8_time
        }
        results['steps_completed'].append('step8_cleanup')

        print(f"Step 8 completed in {step8_time:.1f} seconds")
        print()

        # ========== 完成 ==========
        total_time = time.time() - start_time
        results['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        results['total_time_seconds'] = total_time

        print("=" * 90)
        print("DAILY UPDATE COMPLETED")
        print(f"Total execution time: {total_time/60:.1f} minutes")
        print("=" * 90)
        print()

        return results

    def _generate_daily_report(self, momentum_signals, watchlist_analyses, execution_stats):
        """
        生成每日综合报告 (Markdown格式)

        Args:
            momentum_signals: 动量信号列表
            watchlist_analyses: 观察列表分析结果
            execution_stats: 执行统计信息

        Returns:
            str: 报告文件路径
        """
        report_date = datetime.now().strftime('%Y-%m-%d')
        report_path = f"{self.reports_dir}/daily_report_{report_date}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            # 标题
            f.write(f"# 每日股票分析报告\n")
            f.write(f"日期: {report_date}\n\n")

            # ========== 更新摘要 ==========
            f.write("## 📊 更新摘要\n\n")

            step1 = execution_stats.get('step1_daily_data', {})
            step2 = execution_stats.get('step2_intraday_data', {})
            step3 = execution_stats.get('step3_indicators', {})
            step4 = execution_stats.get('step4_momentum', {})
            step5 = execution_stats.get('step5_auto_add', {})
            step6 = execution_stats.get('step6_analysis', {})

            f.write(f"- **日线数据**: {step1.get('success', 0)}只更新成功, {step1.get('failed', 0)}只失败\n")
            f.write(f"- **分钟数据**: {step2.get('success', 0)}只更新成功\n")
            f.write(f"- **技术指标**: {step3.get('calculated', 0)}只计算完成\n")
            f.write(f"- **动量扫描**: 发现{step4.get('signals_generated', 0)}个信号\n")
            f.write(f"- **自动添加**: {step5.get('stocks_added', 0)}只新增到观察列表\n")
            f.write(f"- **观察列表**: {step6.get('stocks_analyzed', 0)}只分析完成\n\n")

            # ========== 今日动量机会 (Top 10) ==========
            f.write("## 🚀 今日动量机会（Top 10）\n\n")

            for i, signal in enumerate(momentum_signals, 1):
                f.write(f"### {i}. {signal['symbol']} - 评分: {signal['score']}/100\n\n")
                f.write(f"- **价格**: ${signal['price']:.2f}\n")
                f.write(f"- **20日动量**: +{signal['momentum_20d']:.1f}%\n")
                f.write(f"- **5日动量**: +{signal['momentum_5d']:.1f}%\n")
                f.write(f"- **成交量**: {signal['volume_ratio']:.2f}倍放量\n")
                f.write(f"- **理由**: {signal['reasons']}\n\n")

                f.write("**交易计划**:\n")
                f.write(f"- 买入: {signal['shares']}股 @ ${signal['price']:.2f} = ${signal['position_value']:.2f}\n")
                f.write(f"- 止损: ${signal['stop_loss']:.2f} (-5%)\n")
                f.write(f"- 止盈: ${signal['take_profit']:.2f} (+12%)\n\n")
                f.write("---\n\n")

            # ========== 观察列表深度分析 ==========
            f.write("## 📝 观察列表深度分析\n\n")

            for analysis in watchlist_analyses:
                f.write(f"### {analysis['symbol']} - 综合评分: {analysis['overall_score']}/100\n\n")
                f.write(f"**信号**: {analysis['signal']} (置信度: {analysis['confidence']}%)\n\n")
                f.write(f"**当前价格**: ${analysis['price']:.2f}\n\n")

                # 趋势分析
                trend = analysis['scores']['trend']
                f.write("**趋势分析**:\n")
                f.write(f"- 评分: {trend['score']}/100\n")
                f.write(f"- ADX: {trend['details']['adx']:.1f}\n")
                f.write(f"- 方向: +DI={trend['details']['plus_di']:.1f}, -DI={trend['details']['minus_di']:.1f}\n")
                f.write(f"- MA排列: {trend['details']['ma_alignment']}\n\n")

                # 动量分析
                momentum = analysis['scores']['momentum']
                f.write("**动量分析**:\n")
                f.write(f"- 评分: {momentum['score']}/100\n")
                f.write(f"- RSI: {momentum['details']['rsi']:.1f}\n")
                f.write(f"- Stochastic: K={momentum['details']['stochastic_k']:.1f} ({momentum['details']['stochastic_signal']})\n\n")

                # 支撑阻力位
                pp = analysis['pivot_points']
                f.write("**支撑阻力位**:\n")
                f.write(f"- R3: ${pp['r3']:.2f}, R2: ${pp['r2']:.2f}, R1: ${pp['r1']:.2f}\n")
                f.write(f"- Pivot: ${pp['pivot']:.2f}\n")
                f.write(f"- S1: ${pp['s1']:.2f}, S2: ${pp['s2']:.2f}, S3: ${pp['s3']:.2f}\n\n")

                # 识别形态
                if analysis['patterns']:
                    f.write("**识别形态**:\n")
                    for pattern in analysis['patterns']:
                        f.write(f"- {pattern}\n")
                    f.write("\n")

                # 综合评分详情
                f.write("**综合评分**:\n")
                f.write(f"- 趋势: {trend['score']}/100\n")
                f.write(f"- 动量: {momentum['score']}/100\n")
                f.write(f"- 波动率: {analysis['scores']['volatility']['score']}/100\n")
                f.write(f"- 成交量: {analysis['scores']['volume']['score']}/100\n\n")

                # 买卖建议
                f.write(f"**买卖建议**: {analysis['signal']}\n\n")
                f.write("**理由**:\n")
                for i, reason in enumerate(analysis['reasons'], 1):
                    f.write(f"{i}. {reason}\n")
                f.write("\n")

                f.write("---\n\n")

            # ========== 执行统计 ==========
            f.write("## ⏱️ 执行统计\n\n")
            f.write(f"- **开始时间**: {execution_stats['start_time']}\n")
            f.write(f"- **结束时间**: {execution_stats['end_time']}\n")
            f.write(f"- **总执行时间**: {execution_stats['total_time_seconds']/60:.1f} 分钟\n\n")

            f.write("**各步骤耗时**:\n")
            for i in range(1, 9):
                step_key = f'step{i}_' + ['daily_data', 'intraday_data', 'indicators', 'momentum',
                                          'auto_add', 'analysis', 'report', 'cleanup'][i-1]
                step = execution_stats.get(step_key, {})
                if 'time_seconds' in step:
                    f.write(f"- Step {i}: {step['time_seconds']:.1f} 秒\n")

            f.write("\n---\n\n")
            f.write("*报告由 Strategy=Z 自动生成*\n")

        print(f"Report generated: {report_path}")

        # 同时保存到数据库
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

            conn = self.db._connect()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO daily_reports
                (report_date, report_type, symbols_analyzed, signals_generated,
                 report_content, execution_time_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                report_date,
                'comprehensive',
                step6.get('stocks_analyzed', 0) + len(momentum_signals),
                len(momentum_signals),
                report_content,
                execution_stats['total_time_seconds']
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Warning: Failed to save report to database - {str(e)}")

        return report_path


# 使用示例和主入口
if __name__ == "__main__":
    updater = DailyUpdater()

    print("Starting daily update...")
    print()

    results = updater.run_daily_update()

    print()
    print("Summary:")
    print(f"  Started: {results['start_time']}")
    print(f"  Ended: {results['end_time']}")
    print(f"  Duration: {results['total_time_seconds']/60:.1f} minutes")
    print(f"  Steps completed: {len(results['steps_completed'])}/8")
