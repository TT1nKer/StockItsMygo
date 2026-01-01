"""
Trading Calendar - US Market Trading Days

Determines if today is a trading day and what the last trading day was.

Features:
- NYSE/NASDAQ holiday calendar
- Weekend detection
- Last trading day calculation
- Next trading day calculation

Version: 1.0
"""

from datetime import datetime, timedelta
import pandas as pd


class TradingCalendar:
    """US Stock Market Trading Calendar"""

    # US Market Holidays (2024-2026)
    # Format: (month, day, name)
    HOLIDAYS = {
        2024: [
            (1, 1, "New Year's Day"),
            (1, 15, "MLK Jr. Day"),
            (2, 19, "Presidents Day"),
            (3, 29, "Good Friday"),
            (5, 27, "Memorial Day"),
            (6, 19, "Juneteenth"),
            (7, 4, "Independence Day"),
            (9, 2, "Labor Day"),
            (11, 28, "Thanksgiving"),
            (12, 25, "Christmas"),
        ],
        2025: [
            (1, 1, "New Year's Day"),
            (1, 20, "MLK Jr. Day"),
            (2, 17, "Presidents Day"),
            (4, 18, "Good Friday"),
            (5, 26, "Memorial Day"),
            (6, 19, "Juneteenth"),
            (7, 4, "Independence Day"),
            (9, 1, "Labor Day"),
            (11, 27, "Thanksgiving"),
            (12, 25, "Christmas"),
        ],
        2026: [
            (1, 1, "New Year's Day"),
            (1, 19, "MLK Jr. Day"),
            (2, 16, "Presidents Day"),
            (4, 3, "Good Friday"),
            (5, 25, "Memorial Day"),
            (6, 19, "Juneteenth"),
            (7, 3, "Independence Day (observed)"),  # 7/4 is Saturday
            (9, 7, "Labor Day"),
            (11, 26, "Thanksgiving"),
            (12, 25, "Christmas"),
        ],
    }

    @classmethod
    def is_trading_day(cls, date=None):
        """
        Check if a given date is a trading day

        Args:
            date: datetime.date or None (uses today if None)

        Returns:
            bool: True if trading day, False otherwise
        """
        if date is None:
            date = datetime.now().date()
        elif isinstance(date, datetime):
            date = date.date()
        elif isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()

        # Weekend check
        if date.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Holiday check
        year = date.year
        if year in cls.HOLIDAYS:
            holidays = cls.HOLIDAYS[year]
            for month, day, _ in holidays:
                if date.month == month and date.day == day:
                    return False

        return True

    @classmethod
    def get_last_trading_day(cls, from_date=None):
        """
        Get the last trading day before a given date

        Args:
            from_date: datetime.date or None (uses today if None)

        Returns:
            datetime.date: Last trading day
        """
        if from_date is None:
            from_date = datetime.now().date()
        elif isinstance(from_date, datetime):
            from_date = from_date.date()
        elif isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()

        # Go back day by day until we find a trading day
        check_date = from_date - timedelta(days=1)
        max_lookback = 10  # Don't go back more than 10 days

        for _ in range(max_lookback):
            if cls.is_trading_day(check_date):
                return check_date
            check_date -= timedelta(days=1)

        # Fallback: just return yesterday
        return from_date - timedelta(days=1)

    @classmethod
    def get_next_trading_day(cls, from_date=None):
        """
        Get the next trading day after a given date

        Args:
            from_date: datetime.date or None (uses today if None)

        Returns:
            datetime.date: Next trading day
        """
        if from_date is None:
            from_date = datetime.now().date()
        elif isinstance(from_date, datetime):
            from_date = from_date.date()
        elif isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()

        # Go forward day by day until we find a trading day
        check_date = from_date + timedelta(days=1)
        max_lookforward = 10

        for _ in range(max_lookforward):
            if cls.is_trading_day(check_date):
                return check_date
            check_date += timedelta(days=1)

        # Fallback: just return tomorrow
        return from_date + timedelta(days=1)

    @classmethod
    def should_update_data(cls):
        """
        Determine if we should update data today

        Returns:
            dict: {
                'should_update': bool,
                'reason': str,
                'today_is_trading_day': bool,
                'last_trading_day': date
            }
        """
        today = datetime.now().date()
        today_is_trading = cls.is_trading_day(today)
        last_trading = cls.get_last_trading_day(today)

        current_hour = datetime.now().hour

        if not today_is_trading:
            # Not a trading day
            return {
                'should_update': False,
                'reason': f"Today ({today.strftime('%Y-%m-%d %A')}) is not a trading day (weekend/holiday)",
                'today_is_trading_day': False,
                'last_trading_day': last_trading
            }

        # Trading day logic
        if current_hour < 16:  # Before 4pm ET (market close)
            return {
                'should_update': False,
                'reason': f"Market not closed yet (current hour: {current_hour}:00, wait until 16:00 ET)",
                'today_is_trading_day': True,
                'last_trading_day': last_trading
            }
        else:
            return {
                'should_update': True,
                'reason': f"Trading day data ready (market closed at 16:00 ET)",
                'today_is_trading_day': True,
                'last_trading_day': today  # Today's data is the latest
            }

    @classmethod
    def get_expected_data_date(cls):
        """
        Get the date we expect to have data for

        Returns:
            datetime.date: Expected latest data date
        """
        status = cls.should_update_data()

        if status['today_is_trading_day'] and datetime.now().hour >= 16:
            # Market closed today, expect today's data
            return datetime.now().date()
        else:
            # Use last trading day
            return status['last_trading_day']


def check_calendar_status():
    """Print current calendar status (for testing)"""
    today = datetime.now().date()

    print("=" * 80)
    print("US STOCK MARKET CALENDAR STATUS")
    print("=" * 80)
    print()
    print(f"Today: {today.strftime('%Y-%m-%d %A')}")
    print(f"Current Time: {datetime.now().strftime('%H:%M:%S ET')}")
    print()

    is_trading = TradingCalendar.is_trading_day()
    print(f"Is Trading Day: {is_trading}")

    if not is_trading:
        reason = "Weekend" if today.weekday() >= 5 else "Holiday"
        print(f"Reason: {reason}")

    print()
    print(f"Last Trading Day: {TradingCalendar.get_last_trading_day().strftime('%Y-%m-%d %A')}")
    print(f"Next Trading Day: {TradingCalendar.get_next_trading_day().strftime('%Y-%m-%d %A')}")
    print()

    status = TradingCalendar.should_update_data()
    print("Data Update Status:")
    print(f"  Should Update: {status['should_update']}")
    print(f"  Reason: {status['reason']}")
    print(f"  Expected Data Date: {TradingCalendar.get_expected_data_date().strftime('%Y-%m-%d')}")
    print()
    print("=" * 80)


if __name__ == '__main__':
    check_calendar_status()
