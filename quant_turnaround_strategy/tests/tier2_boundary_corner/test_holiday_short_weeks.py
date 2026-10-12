"""
Tier 2 Boundary & Corner Cases: Short Trading Weeks & Market Holidays.
Verifies:
- Weekly rebalance executes on the last valid trading day of the week
  (e.g., Thursday close when Friday is Good Friday holiday).
- Thanksgiving week handling (4-day week).
- Extreme closure: Post-9/11 market shutdown (Sept 11-14, 2001, resumed Sept 17).
- Rebalances never execute on weekends or market holidays.
- Rebalance cadence remains strictly monotonic without skipping intervals.
"""
from datetime import date
from typing import List
import pytest
import pandas as pd


class MockCalendarRebalancer:
    """Resolves weekly rebalance dates against market trading calendars."""

    @staticmethod
    def get_weekly_rebalance_dates(trading_days: List[pd.Timestamp]) -> List[pd.Timestamp]:
        """
        Groups trading days by calendar week (Year-Week) and selects
        the LAST available trading day in each week as the rebalance execution day.
        """
        df = pd.DataFrame({"trade_date": trading_days})
        df["year"] = df["trade_date"].dt.isocalendar().year
        df["week"] = df["trade_date"].dt.isocalendar().week

        rebalance_dates = df.groupby(["year", "week"])["trade_date"].max().tolist()
        return sorted(rebalance_dates)


class TestHolidayShortWeeks:
    """Test suite for holiday short weeks."""

    def test_good_friday_closed_rebalances_on_thursday(self):
        """
        Derivation:
        Easter 2021: Good Friday fell on April 2, 2021 (markets closed).
        Trading days in week: Monday Mar 29, Tue Mar 30, Wed Mar 31, Thursday Apr 1.
        The weekly rebalance must execute on Thursday, April 1, 2021.
        """
        trading_days = [
            pd.Timestamp("2021-03-29"),  # Mon
            pd.Timestamp("2021-03-30"),  # Tue
            pd.Timestamp("2021-03-31"),  # Wed
            pd.Timestamp("2021-04-01"),  # Thu (Last trading day)
            # Friday Apr 2 closed!
        ]
        rebal_dates = MockCalendarRebalancer.get_weekly_rebalance_dates(trading_days)

        assert len(rebal_dates) == 1
        assert rebal_dates[0] == pd.Timestamp("2021-04-01")
        assert rebal_dates[0].day_name() == "Thursday"

    def test_thanksgiving_4_day_week_rebalance_on_friday(self):
        """
        Derivation:
        Thanksgiving 2021 fell on Thursday, Nov 25 (closed).
        Friday, Nov 26 was an early close trading day.
        Weekly rebalance must execute on Friday, Nov 26.
        """
        trading_days = [
            pd.Timestamp("2021-11-22"),  # Mon
            pd.Timestamp("2021-11-23"),  # Tue
            pd.Timestamp("2021-11-24"),  # Wed
            # Thu Nov 25 closed
            pd.Timestamp("2021-11-26"),  # Fri (Half day)
        ]
        rebal_dates = MockCalendarRebalancer.get_weekly_rebalance_dates(trading_days)

        assert len(rebal_dates) == 1
        assert rebal_dates[0] == pd.Timestamp("2021-11-26")
        assert rebal_dates[0].day_name() == "Friday"

    def test_post_9_11_market_closure_week_september_2001(self):
        """
        Derivation:
        On Tuesday, Sept 11, 2001, US markets shut down and remained closed
        through Friday, Sept 14, 2001. Only Monday, Sept 10 was a trading day that week.
        The rebalance for that week must fall on Monday, Sept 10 (or no post-event trade),
        and the following week begins Monday, Sept 17, 2001.
        """
        trading_days = [
            pd.Timestamp("2001-09-10"),  # Mon (Only day traded in week 37)
            # Sept 11-14 closed
            pd.Timestamp("2001-09-17"),  # Mon (Market reopened, week 38)
            pd.Timestamp("2001-09-18"),
            pd.Timestamp("2001-09-19"),
            pd.Timestamp("2001-09-20"),
            pd.Timestamp("2001-09-21"),  # Fri
        ]
        rebal_dates = MockCalendarRebalancer.get_weekly_rebalance_dates(trading_days)

        assert len(rebal_dates) == 2
        assert rebal_dates[0] == pd.Timestamp("2001-09-10")
        assert rebal_dates[1] == pd.Timestamp("2001-09-21")

    def test_rebalance_dates_never_fall_on_saturday_or_sunday(self):
        """Expected: Rebalance timestamps strictly have dayofweek in [0, 4] (Mon-Fri)."""
        dates = pd.date_range("2001-07-10", "2002-12-31", freq="B")
        rebal_dates = MockCalendarRebalancer.get_weekly_rebalance_dates(list(dates))

        for d in rebal_dates:
            assert d.dayofweek < 5, f"{d} is on a weekend: {d.day_name()}"

    def test_rebalance_cadence_strictly_monotonic(self):
        """Expected: Successive rebalance dates are strictly increasing."""
        dates = pd.date_range("2001-07-10", "2002-07-10", freq="B")
        rebal_dates = MockCalendarRebalancer.get_weekly_rebalance_dates(list(dates))

        for i in range(len(rebal_dates) - 1):
            assert rebal_dates[i] < rebal_dates[i + 1]
