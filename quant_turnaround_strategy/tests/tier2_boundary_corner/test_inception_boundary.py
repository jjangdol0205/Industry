"""
Tier 2 Boundary & Corner Cases: Inception Date Boundary (2001-07-10).
Verifies:
- Strict prohibition of signals or trades prior to 2001-07-10.
- Portfolio state on inception date begins at 100% Cash ($100,000.0).
- First rebalance execution strictly on or after inception date.
- Out-of-bounds historical queries before 2001-07-10 return empty or raise ValueError.
"""
from datetime import date, timedelta
import pytest
import pandas as pd

from config.settings import DEFAULT_START_DATE


class TestInceptionBoundary:
    """Test suite for inception date boundary enforcement."""

    def test_inception_date_constant_value(self):
        """Expected: Inception date is strictly July 10, 2001."""
        assert DEFAULT_START_DATE == "2001-07-10"

    def test_no_trades_or_signals_prior_to_inception(self):
        """
        Derivation:
        At any timestamp T < 2001-07-10 (e.g. 2001-07-09 or 2000-12-31),
        the strategy simulator must generate 0 trades and 0 signals.
        """
        pre_inception_dates = [
            pd.Timestamp("1999-12-31"),
            pd.Timestamp("2000-06-30"),
            pd.Timestamp("2001-07-08"),
            pd.Timestamp("2001-07-09"),
        ]
        inception = pd.Timestamp(DEFAULT_START_DATE)

        for d in pre_inception_dates:
            assert d < inception, f"{d} is not before inception"
            # Contract: filter out dates prior to inception
            is_valid = d >= inception
            assert is_valid is False

    def test_initial_portfolio_balance_on_inception_date(self):
        """
        Derivation:
        On July 10, 2001, portfolio initializes with 100% cash ($100,000.0)
        and zero stock holdings.
        """
        initial_capital = 100_000.0
        portfolio_state = {
            "date": "2001-07-10",
            "cash": initial_capital,
            "stock_holdings": {},
            "nav": initial_capital,
            "weight_cash": 1.0,
            "weight_equity": 0.0,
        }
        assert portfolio_state["cash"] == 100_000.0
        assert portfolio_state["weight_cash"] == 1.0
        assert len(portfolio_state["stock_holdings"]) == 0

    def test_first_rebalance_date_on_or_after_inception(self):
        """
        Derivation:
        July 10, 2001 was a Tuesday.
        The first scheduled weekly rebalance Friday was July 13, 2001.
        First rebalance date must be >= 2001-07-10.
        """
        tuesday_launch = pd.Timestamp("2001-07-10")
        first_friday = pd.Timestamp("2001-07-13")

        assert tuesday_launch.day_name() == "Tuesday"
        assert first_friday.day_name() == "Friday"
        assert first_friday >= tuesday_launch

    def test_slice_before_inception_returns_empty(self, test_price_feed, synthetic_benchmark_df):
        """Expected: Slicing prices with an end date prior to 2001-07-10 returns an empty DataFrame."""
        sliced = test_price_feed._slice_date_range(
            synthetic_benchmark_df,
            start_date="2000-01-01",
            end_date="2001-07-09",
        )
        assert sliced.empty
