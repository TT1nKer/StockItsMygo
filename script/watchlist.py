"""
Watchlist Manager
观察列表管理器

Features:
- Manual stock management (add/remove/update)
- Auto-add from momentum scanner (scores >= 80)
- Priority-based organization
- Intraday data synchronization
- CSV import/export

功能:
- 手动管理股票 (添加/删除/更新)
- 动量扫描器自动推荐 (评分>=80)
- 优先级管理
- 分钟数据同步
- CSV导入导出
"""

from db.api import StockDB
from script.momentum_strategy import MomentumScanner
import pandas as pd
from datetime import datetime


class WatchlistManager:
    """观察列表管理器"""

    def __init__(self):
        self.db = StockDB()
        self.scanner = MomentumScanner()

    # ============ 手动管理 (Manual Management) ============

    def add(self, symbol, priority=2, source='manual', notes='', target_price=None, stop_loss=None):
        """
        添加股票到观察列表

        Args:
            symbol: 股票代码
            priority: 优先级 (1=高, 2=中, 3=低)
            source: 来源 ('manual', 'momentum', 'anomaly', 'dual_confirmed') - v2.1+
            notes: 备注
            target_price: 目标价
            stop_loss: 止损价

        Returns:
            bool: 是否成功
        """
        return self.db.add_to_watchlist(
            symbol=symbol,
            priority=priority,
            source=source,
            notes=notes,
            target_price=target_price,
            stop_loss=stop_loss
        )

    def remove(self, symbol):
        """
        从观察列表移除股票

        Args:
            symbol: 股票代码

        Returns:
            bool: 是否成功
        """
        return self.db.remove_from_watchlist(symbol)

    def get_list(self, priority=None):
        """
        获取观察列表

        Args:
            priority: 优先级筛选 (1/2/3)

        Returns:
            pd.DataFrame: 观察列表
        """
        return self.db.get_watchlist(priority=priority)

    def update_prices(self, symbol, target_price=None, stop_loss=None):
        """
        更新目标价和止损价

        Args:
            symbol: 股票代码
            target_price: 目标价
            stop_loss: 止损价

        Returns:
            bool: 是否成功
        """
        return self.db.update_watchlist_prices(symbol, target_price, stop_loss)

    # ============ 自动推荐 (Auto Recommendations) ============

    def auto_add_from_momentum(self, min_score=80, max_additions=10, skip_existing=True):
        """
        从动量扫描器自动添加高分股票

        Args:
            min_score: 最低评分 (默认80)
            max_additions: 最多添加数量 (默认10)
            skip_existing: 跳过已在观察列表的股票

        Returns:
            list: 添加的股票列表
        """
        print("=" * 70)
        print("Running momentum scanner to find auto-recommendations...")
        print("=" * 70)
        print()

        # 运行动量扫描器
        candidates = self.scanner.scan_market(
            min_price=5,
            max_price=100,
            min_volume=500000,
            top_n=50
        )

        # 生成信号
        signals = self.scanner.generate_signals(candidates)

        # 获取现有观察列表
        existing_watchlist = self.get_list()
        existing_symbols = set(existing_watchlist['symbol'].tolist()) if len(existing_watchlist) > 0 else set()

        # 筛选高分股票
        added_stocks = []
        for signal in signals:
            if signal['score'] >= min_score:
                # 跳过已存在的股票
                if skip_existing and signal['symbol'] in existing_symbols:
                    print(f"{signal['symbol']}: Already in watchlist (score: {signal['score']})")
                    continue

                # 判断优先级
                if signal['score'] >= 90:
                    priority = 1  # 高
                elif signal['score'] >= 80:
                    priority = 2  # 中
                else:
                    priority = 3  # 低

                # 添加到观察列表
                success = self.db.add_to_watchlist(
                    symbol=signal['symbol'],
                    priority=priority,
                    source='momentum_auto',
                    notes=f"Auto-added: Score {signal['score']}, Momentum {signal['momentum_20d']:.1f}%",
                    target_price=signal['take_profit'],
                    stop_loss=signal['stop_loss']
                )

                if success:
                    added_stocks.append({
                        'symbol': signal['symbol'],
                        'score': signal['score'],
                        'priority': priority,
                        'price': signal['price']
                    })

                # 达到最大数量限制
                if len(added_stocks) >= max_additions:
                    break

        print()
        print(f"Auto-added {len(added_stocks)} stocks to watchlist")
        print()

        if added_stocks:
            print("Added stocks:")
            for stock in added_stocks:
                priority_str = {1: 'High', 2: 'Medium', 3: 'Low'}[stock['priority']]
                print(f"  - {stock['symbol']}: Score {stock['score']}, Priority: {priority_str}, Price: ${stock['price']:.2f}")

        return added_stocks

    # ============ 数据同步 (Data Synchronization) ============

    def update_intraday_data(self, interval='5m', period='7d', priority_filter=None):
        """
        为观察列表股票更新分钟数据

        Args:
            interval: 时间间隔 (默认5m)
            period: 时间周期 (默认7天)
            priority_filter: 优先级筛选 (1/2/3，None表示全部)

        Returns:
            dict: 更新结果
        """
        watchlist = self.get_list(priority=priority_filter)

        if len(watchlist) == 0:
            print("Watchlist is empty")
            return {'success': 0, 'failed': 0}

        symbols = watchlist['symbol'].tolist()

        print(f"Updating intraday data for {len(symbols)} watchlist stocks...")
        print()

        # 批量下载分钟数据
        results = self.db.batch_download_intraday(
            symbols=symbols,
            interval=interval,
            period=period,
            workers=3
        )

        return results

    # ============ 导入导出 (Import/Export) ============

    def export_to_csv(self, filepath='watchlist_export.csv'):
        """
        导出观察列表到CSV

        Args:
            filepath: CSV文件路径

        Returns:
            bool: 是否成功
        """
        return self.db.export_watchlist(filepath)

    def import_from_csv(self, filepath):
        """
        从CSV导入观察列表

        Args:
            filepath: CSV文件路径

        Returns:
            int: 导入数量
        """
        return self.db.import_watchlist(filepath)

    # ============ 报告生成 (Reporting) ============

    def print_summary(self):
        """打印观察列表摘要"""
        watchlist = self.get_list()

        if len(watchlist) == 0:
            print("Watchlist is empty")
            return

        print("=" * 90)
        print(f"WATCHLIST SUMMARY ({len(watchlist)} stocks)")
        print("=" * 90)
        print()

        # 按优先级分组
        priority_names = {1: 'High Priority', 2: 'Medium Priority', 3: 'Low Priority'}

        for priority in [1, 2, 3]:
            priority_stocks = watchlist[watchlist['priority'] == priority]

            if len(priority_stocks) == 0:
                continue

            print(f"{priority_names[priority]} ({len(priority_stocks)} stocks):")
            print("-" * 90)

            for _, stock in priority_stocks.iterrows():
                print(f"  {stock['symbol']:<8} | Source: {stock['source']:<15} | Added: {stock['added_date'][:10]}")

                if stock['notes']:
                    print(f"           Notes: {stock['notes']}")

                if stock['target_price'] or stock['stop_loss']:
                    target = f"${stock['target_price']:.2f}" if stock['target_price'] else "N/A"
                    stop = f"${stock['stop_loss']:.2f}" if stock['stop_loss'] else "N/A"
                    print(f"           Target: {target} | Stop Loss: {stop}")

                print()

        print("=" * 90)

    def get_statistics(self):
        """
        获取观察列表统计信息

        Returns:
            dict: 统计信息
        """
        watchlist = self.get_list()

        if len(watchlist) == 0:
            return {
                'total': 0,
                'by_priority': {1: 0, 2: 0, 3: 0},
                'by_source': {}
            }

        stats = {
            'total': len(watchlist),
            'by_priority': {
                1: len(watchlist[watchlist['priority'] == 1]),
                2: len(watchlist[watchlist['priority'] == 2]),
                3: len(watchlist[watchlist['priority'] == 3])
            },
            'by_source': watchlist['source'].value_counts().to_dict()
        }

        return stats


# 使用示例
if __name__ == "__main__":
    manager = WatchlistManager()

    # 示例1: 手动添加股票
    print("Example 1: Manual add")
    print("-" * 70)
    manager.add('AAPL', priority=1, notes='Strong performer', target_price=200, stop_loss=180)
    manager.add('MSFT', priority=1, notes='Tech leader', target_price=420, stop_loss=380)
    print()

    # 示例2: 从动量扫描器自动添加
    print("Example 2: Auto-add from momentum scanner")
    print("-" * 70)
    manager.auto_add_from_momentum(min_score=80, max_additions=5)
    print()

    # 示例3: 打印摘要
    print("Example 3: Watchlist summary")
    print("-" * 70)
    manager.print_summary()
    print()

    # 示例4: 统计信息
    print("Example 4: Statistics")
    print("-" * 70)
    stats = manager.get_statistics()
    print(f"Total stocks: {stats['total']}")
    print(f"High priority: {stats['by_priority'][1]}")
    print(f"Medium priority: {stats['by_priority'][2]}")
    print(f"Low priority: {stats['by_priority'][3]}")
    print(f"By source: {stats['by_source']}")
    print()

    # 示例5: 更新分钟数据
    print("Example 5: Update intraday data")
    print("-" * 70)
    # manager.update_intraday_data(interval='5m', period='1d', priority_filter=1)
    print("Intraday data update completed")
