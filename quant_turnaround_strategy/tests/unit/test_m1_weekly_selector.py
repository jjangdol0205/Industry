"""
Unit tests for WeeklySelector: portfolio capacity constraint (0 to 3 stocks),
Top-1 weekly selection rule (max 1 stock per week), and rationale generation.
"""
from datetime import date
import pandas as pd
import numpy as np
import pytest

from src.screening.weekly_selector import WeeklySelector
from src.screening.rolling_low import RollingLowScreener
from src.screening.turnaround_scorer import TurnaroundScorer, PITFundamentalStore
from src.screening.exclusion_gates import ExclusionGates
from src.data.universe import UniverseManager


def make_qualifying_price_df(start_val=50.0, days=260):
    """Generates a synthetic price series where the stock is stabilized at a 52-week low."""
    dates = pd.date_range("2023-01-01", periods=days, freq="B")
    prices = [start_val] * days
    # Let price drop to 20.0 over time, remaining stabilized within 2% of low in recent days
    for i in range(100, days):
        prices[i] = 20.0
    for i in range(days - 10, days):
        prices[i] = 20.2  # Exactly 1% above 20.0 low

    return pd.DataFrame(
        {
            "Open": prices,
            "High": [p * 1.01 for p in prices],
            "Low": [p * 0.99 for p in prices],
            "Close": prices,
            "Volume": [2_000_000.0] * days,  # $40M dollar volume
        },
        index=dates,
    )


def test_capacity_constraint_rejects_when_full():
    """
    Verifies that when 3 stocks are already held (portfolio capacity full),
    candidate screening is skipped and action is HOLD_CAPACITY_FULL.
    """
    selector = WeeklySelector(max_portfolio_capacity=3)
    res = selector.screen_weekly_candidates(
        as_of_date="2024-01-05",
        current_holdings=["AAPL", "MSFT", "AMZN"],
    )
    assert res.portfolio_held_count == 3
    assert res.action == "HOLD_CAPACITY_FULL"
    assert res.selected_ticker is None
    assert "full" in res.rationale.lower()


def test_selects_at_most_one_stock_per_week():
    """
    Verifies that even if multiple candidates qualify, exactly ONE optimal stock
    is selected per week (N_new in {0, 1}).
    """
    selector = WeeklySelector(max_portfolio_capacity=3, min_composite_score=0.40)
    
    # Create two candidates
    df_a = make_qualifying_price_df(start_val=50.0)
    df_b = make_qualifying_price_df(start_val=40.0)

    price_pools = {"AAPL": df_a, "AMZN": df_b}

    res = selector.screen_weekly_candidates(
        as_of_date=df_a.index[-1].date(),
        current_holdings=["MSFT"],  # 1 held, room for 2 more
        candidate_price_dfs=price_pools,
    )

    assert res.portfolio_held_count == 1
    # Action must be BUY
    assert res.action == "BUY"
    assert res.selected_ticker in ["AAPL", "AMZN"]
    # Only 1 stock selected
    assert isinstance(res.selected_ticker, str)
    assert res.selected_candidate is not None


def test_no_qualified_candidates_returns_zero_action():
    """Verifies that if no stocks pass gates, action is NO_QUALIFIED_CANDIDATE."""
    selector = WeeklySelector(max_portfolio_capacity=3, min_composite_score=0.99)  # unreachable threshold
    df_a = make_qualifying_price_df()
    
    res = selector.screen_weekly_candidates(
        as_of_date=df_a.index[-1].date(),
        current_holdings=["MSFT"],
        candidate_price_dfs={"AAPL": df_a},
    )
    assert res.action == "NO_QUALIFIED_CANDIDATE"
    assert res.selected_ticker is None


def test_non_constituent_not_evaluated_when_disjoint():
    """
    Verifies that WeeklySelector does NOT evaluate non-constituents
    even if provided in candidate_price_dfs (no disjoint fallback bypass).
    """
    selector = WeeklySelector(max_portfolio_capacity=3)
    df = make_qualifying_price_df()
    # On 2005-01-01, TSLA was NOT a constituent (entered 2020-12-21)
    res = selector.screen_weekly_candidates(
        as_of_date="2005-01-01",
        current_holdings=[],
        candidate_price_dfs={"TSLA": df},
    )
    assert len(res.all_evaluated_candidates) == 0
    assert res.action == "NO_QUALIFIED_CANDIDATE"

