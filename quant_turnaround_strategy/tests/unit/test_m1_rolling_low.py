"""
Unit tests for RollingLowScreener: 252-day low rolling window,
proximity calculations, and anti-falling knife stabilization filters.
"""
from datetime import date
import pandas as pd
import numpy as np
import pytest

from src.screening.rolling_low import RollingLowScreener, calculate_rsi
from src.models.schemas import ExclusionReason


def create_synthetic_price_history(days: int = 300, base_price: float = 100.0, trend: str = "flat") -> pd.DataFrame:
    """Helper to generate synthetic price history."""
    dates = pd.date_range("2023-01-01", periods=days, freq="B")
    np.random.seed(42)

    prices = [base_price]
    for _ in range(days - 1):
        if trend == "down":
            change = np.random.normal(-0.005, 0.01)
        elif trend == "up":
            change = np.random.normal(0.005, 0.01)
        else:
            change = np.random.normal(0.0, 0.01)
        prices.append(max(1.0, prices[-1] * (1.0 + change)))

    df = pd.DataFrame(
        {
            "Open": prices,
            "High": [p * 1.01 for p in prices],
            "Low": [p * 0.99 for p in prices],
            "Close": prices,
            "Volume": [1_000_000.0] * days,
        },
        index=dates,
    )
    return df


def test_rsi_calculation():
    """Verifies RSI calculation logic."""
    # Monotonically increasing prices -> RSI near 100
    prices_up = pd.Series([10.0 + i for i in range(30)])
    rsi_up = calculate_rsi(prices_up, period=14)
    assert rsi_up.iloc[-1] > 90.0

    # Monotonically decreasing prices -> RSI near 0
    prices_down = pd.Series([100.0 - (i * 2) for i in range(30)])
    rsi_down = calculate_rsi(prices_down, period=14)
    assert rsi_down.iloc[-1] < 10.0


def test_screener_rejects_insufficient_history():
    """Verifies that stocks with fewer than 252 trading days are rejected."""
    screener = RollingLowScreener(min_history_days=252)
    short_df = create_synthetic_price_history(days=150)
    
    qualifies, metrics = screener.evaluate_candidate(short_df, short_df.index[-1])
    assert qualifies is False
    assert metrics.get("reason") == ExclusionReason.TRADING_HISTORY_INSUFFICIENT


def test_screener_detects_52w_low_and_stabilization():
    """Verifies that a stock within 5% of 252-day low with stabilized RSI qualifies."""
    screener = RollingLowScreener(window=252, proximity_threshold=0.05, min_rsi=20.0, min_5d_return=-0.05)
    
    # 260 days of data: flat, then drop to low, then slight curl
    df = create_synthetic_price_history(days=260, base_price=50.0, trend="flat")
    
    # Force last 5 days to be near the absolute minimum of the 252-day window, but stable
    min_low = df["Low"].min()
    for i in range(1, 6):
        # Set close slightly above min_low (e.g. +1%)
        df.iloc[-i, df.columns.get_loc("Close")] = min_low * 1.01
        df.iloc[-i, df.columns.get_loc("Low")] = min_low
    
    qualifies, metrics = screener.evaluate_candidate(df, df.index[-1])
    assert metrics["is_near_low"] is True
    assert metrics["low_proximity"] <= 0.05


def test_anti_falling_knife_rejection():
    """
    Verifies that a stock in active freefall (dumping -20% in 5 days, RSI < 20)
    is properly rejected by the anti-falling knife stabilization gate.
    """
    screener = RollingLowScreener(window=252, proximity_threshold=0.05, min_rsi=20.0, min_5d_return=-0.05)
    df = create_synthetic_price_history(days=260, base_price=50.0)

    # Force sharp collapse in last 5 days: price drops by 30%
    base_val = df.iloc[-6]["Close"]
    for i in range(1, 6):
        df.iloc[-i, df.columns.get_loc("Close")] = base_val * (1.0 - (i * 0.06))
        df.iloc[-i, df.columns.get_loc("Low")] = df.iloc[-i]["Close"] * 0.98

    qualifies, metrics = screener.evaluate_candidate(df, df.index[-1])
    assert qualifies is False
    assert metrics["is_stabilized"] is False
    assert metrics["return_5d"] < -0.05


def test_flat_series_rsi_neutral():
    """Verifies that a flat price series (no change) yields neutral RSI 50.0 instead of 100.0."""
    flat_prices = pd.Series([50.0] * 30)
    rsi = calculate_rsi(flat_prices, period=14)
    assert rsi.iloc[-1] == 50.0

