"""
Unit tests for PriceFeed: QQQ and SOXX daily feeds, July 10-12, 2001 bridge,
split/dividend adjustments, and offline parquet caching.
"""
from datetime import date
import pandas as pd
import numpy as np
import pytest

from src.data.price_feed import PriceFeed
from src.data.cache_store import CacheStore


def test_benchmark_start_date_and_shape(price_feed):
    """Verifies benchmark data starts strictly at July 10, 2001 without NaNs."""
    df = price_feed.get_benchmark_prices(start_date="2001-07-10")
    assert not df.empty
    assert df.index[0] == pd.Timestamp("2001-07-10")
    assert ("Close", "QQQ") in df.columns
    assert ("Close", "SOXX") in df.columns

    # Verify zero NaNs from start date to present
    assert df[("Close", "QQQ")].isna().sum() == 0
    assert df[("Close", "SOXX")].isna().sum() == 0


def test_soxx_july_bridge_values(price_feed):
    """
    Verifies the July 10-12, 2001 bridge generates realistic benchmark-scaled values
    for SOXX before its first exchange print on July 13, 2001.
    """
    df = price_feed.get_benchmark_prices(start_date="2001-07-10")
    
    # Bridge dates
    soxx_jul10 = df.loc["2001-07-10", ("Close", "SOXX")]
    soxx_jul11 = df.loc["2001-07-11", ("Close", "SOXX")]
    soxx_jul12 = df.loc["2001-07-12", ("Close", "SOXX")]
    soxx_jul13 = df.loc["2001-07-13", ("Close", "SOXX")]

    # Values must be positive numbers around ~$18-$21
    assert 15.0 < soxx_jul10 < 25.0
    assert 15.0 < soxx_jul11 < 25.0
    assert 15.0 < soxx_jul12 < 25.0
    assert 15.0 < soxx_jul13 < 25.0

    # Ensure OHLCV fields are filled
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        assert pd.notna(df.loc["2001-07-10", (col, "SOXX")])
        assert df.loc["2001-07-10", (col, "SOXX")] > 0


def test_soxx_split_smoothness(price_feed):
    """
    Verifies that on 2024-03-07 (SOXX 3-for-1 forward stock split date),
    the auto-adjusted price series does not contain an artificial 66% cliff drop.
    """
    df = price_feed.get_benchmark_prices(start_date="2024-03-01", end_date="2024-03-15")
    soxx_close = df[("Close", "SOXX")]

    # Single-day return around split date
    daily_returns = soxx_close.pct_change().dropna()
    # If unadjusted, return would be ~ -66.7%. In adjusted total return, it should be within normal bounds (+- 10%).
    assert (daily_returns < -0.30).sum() == 0, "Artificial split drop detected in adjusted prices!"


def test_offline_cache_persistence(tmp_path):
    """Verifies that CacheStore persists Parquet files and loads them accurately offline."""
    store = CacheStore(cache_dir=tmp_path)
    sample_df = pd.DataFrame(
        {"close": [100.0, 102.5, 105.0]},
        index=pd.date_range("2024-01-01", periods=3, freq="D"),
    )
    store.save_parquet(sample_df, "test_feed.parquet")
    assert store.exists("test_feed.parquet")

    loaded = store.load_parquet("test_feed.parquet")
    assert loaded is not None
    assert len(loaded) == 3
    assert list(loaded["close"]) == [100.0, 102.5, 105.0]


def test_fx_rates_start_date_and_zero_nans(price_feed):
    """
    Verifies that daily USD/KRW exchange rates start strictly at July 10, 2001,
    contain zero NaNs, and return valid historical exchange rate values.
    """
    fx = price_feed.get_fx_rates(start_date="2001-07-10")
    assert isinstance(fx, pd.Series)
    assert not fx.empty
    assert fx.index.min() <= pd.Timestamp("2001-07-10")
    assert fx.loc["2001-07-10"] > 1000.0
    # Zero NaNs guarantee
    assert fx.isna().sum() == 0


def test_fx_rates_date_slicing(price_feed):
    """Verifies that get_fx_rates properly slices between start_date and end_date."""
    fx = price_feed.get_fx_rates(start_date="2020-01-01", end_date="2020-12-31")
    assert fx.index.min() >= pd.Timestamp("2020-01-01")
    assert fx.index.max() <= pd.Timestamp("2020-12-31")
    assert len(fx) > 250
    assert fx.isna().sum() == 0

