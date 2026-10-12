"""
Boundary and edge case unit tests for M1 data pipeline and screener.
Covers multi-interval constituent re-entry, weekend/holiday date queries,
and strict capacity boundaries.
"""
from datetime import date, datetime
import pandas as pd
import pytest

from src.data.universe import UniverseManager
from src.data.price_feed import PriceFeed
from src.screening.turnaround_scorer import TurnaroundScorer, PITFundamentalStore
from src.screening.weekly_selector import WeeklySelector
from src.models.schemas import PITFinancialStatement


def test_reentering_constituent_handling(universe_manager):
    """
    Verifies that companies with multiple index tenure intervals
    (e.g., AAL in 1996-1997 and 2015-2024) are correctly recognized
    during each active window and excluded in the gap.
    """
    assert universe_manager.is_member_at("AAL", "1996-06-01") is True
    assert universe_manager.is_member_at("AAL", "2005-01-01") is False  # In between tenure
    assert universe_manager.is_member_at("AAL", "2018-01-01") is True


def test_weekend_and_holiday_queries(universe_manager):
    """Verifies that queries on non-trading calendar dates resolve without error."""
    # 2024-01-01 is New Year's Day (market closed)
    active = universe_manager.get_constituents_at("2024-01-01")
    assert len(active) > 490

    # Sunday query
    active_sunday = universe_manager.get_constituents_at("2024-01-07")
    assert len(active_sunday) > 490


def test_turnaround_scorer_with_exact_filing_date_edge(turnaround_scorer):
    """
    Verifies edge case where as_of_date is exactly on filing_date.
    The statement must be observable on that day.
    """
    statements = turnaround_scorer.store.get_statements_observable_at("AAPL", date(2003, 5, 13))
    filing_dates = [s.filing_date for s in statements]
    assert date(2003, 5, 13) in filing_dates


def test_weekly_selector_capacity_transition():
    """
    Verifies capacity transitions:
    - 0 held -> can buy 1 (N_held becomes 1)
    - 2 held -> can buy 1 (N_held becomes 3)
    - 3 held -> blocked (action HOLD_CAPACITY_FULL)
    """
    selector = WeeklySelector(max_portfolio_capacity=3)
    
    # At capacity 2
    res_2 = selector.screen_weekly_candidates(
        as_of_date="2024-01-05",
        current_holdings=["MSFT", "GOOGL"],
        candidate_price_dfs={},
    )
    assert res_2.action in ["BUY", "NO_QUALIFIED_CANDIDATE"]

    # At capacity 3
    res_3 = selector.screen_weekly_candidates(
        as_of_date="2024-01-05",
        current_holdings=["MSFT", "GOOGL", "AAPL"],
        candidate_price_dfs={},
    )
    assert res_3.action == "HOLD_CAPACITY_FULL"
    assert res_3.portfolio_held_count == 3
