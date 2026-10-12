"""
Unit & Integration Tests for Milestone 1 (R1):
Tri-Asset Data Ingestion, Simplex Grid Combinatorics, and Vectorized Simulator.
"""
import time
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from src.data.tri_asset_loader import load_tri_asset_data, TriAssetDataLoader
from src.optimizer.tri_asset_simplex import (
    generate_simplex_grid,
    simulate_simplex_grid,
    SimplexGridResult,
)


class TestSimplexGridCombinatorics:
    """Validates the 3-asset allocation simplex mathematics and combinatorics."""

    def test_grid_size_and_dimensions(self):
        grid = generate_simplex_grid(step=0.01)
        # By stars and bars theorem: C(100+3-1, 3-1) = C(102, 2) = 5151
        assert grid.shape == (5151, 3), f"Expected shape (5151, 3), got {grid.shape}"

    def test_grid_weight_bounds(self):
        grid = generate_simplex_grid(step=0.01)
        assert np.all(grid >= 0.0), "All weights must be non-negative"
        assert np.all(grid <= 1.0), "All weights must be <= 1.0"

    def test_grid_sum_constraint(self):
        grid = generate_simplex_grid(step=0.01)
        row_sums = np.sum(grid, axis=1)
        assert np.allclose(row_sums, 1.0, atol=1e-5), "All rows must sum to 1.0"

    def test_grid_uniqueness(self):
        grid = generate_simplex_grid(step=0.01)
        unique_rows = np.unique(grid, axis=0)
        assert len(unique_rows) == 5151, "All 5,151 weight triplets must be distinct"

    def test_corner_and_midpoint_weights_exist(self):
        grid = generate_simplex_grid(step=0.01)
        # Pure SPY
        assert any(np.allclose(row, [1.0, 0.0, 0.0]) for row in grid)
        # Pure QQQ
        assert any(np.allclose(row, [0.0, 1.0, 0.0]) for row in grid)
        # Pure SOXX
        assert any(np.allclose(row, [0.0, 0.0, 1.0]) for row in grid)
        # 60/40 SPY/QQQ
        assert any(np.allclose(row, [0.6, 0.4, 0.0]) for row in grid)
        # Equal weights (approximate on 1% grid: 0.33, 0.33, 0.34 or 0.34, 0.33, 0.33)
        assert any(np.allclose(row, [0.34, 0.33, 0.33]) for row in grid)


class TestTriAssetDataLoader:
    """Validates historical data ingestion, cache persistence, and 0-NaN alignment."""

    def test_load_tri_asset_data_structure(self):
        prices_df, fx_df = load_tri_asset_data()
        assert isinstance(prices_df, pd.DataFrame)
        assert isinstance(fx_df, pd.DataFrame)
        assert set(prices_df.columns) == {"SPY", "QQQ", "SOXX"}
        assert "USDKRW" in fx_df.columns

    def test_date_bounds_and_monotony(self):
        prices_df, fx_df = load_tri_asset_data()
        assert prices_df.index[0] == pd.Timestamp("2001-07-10"), f"Expected start 2001-07-10, got {prices_df.index[0]}"
        assert prices_df.index[-1].year >= 2026, f"Expected end year >= 2026, got {prices_df.index[-1]}"
        assert prices_df.index.is_monotonic_increasing, "Prices index must be sorted"
        assert fx_df.index.is_monotonic_increasing, "FX index must be sorted"
        assert len(prices_df) == len(fx_df), "Prices and FX must have identical row count"
        assert (prices_df.index == fx_df.index).all(), "Prices and FX dates must match 1:1"

    def test_zero_nans(self):
        prices_df, fx_df = load_tri_asset_data()
        assert prices_df.isna().sum().sum() == 0, f"Found NaNs in prices_df: {prices_df.isna().sum().to_dict()}"
        assert fx_df.isna().sum().sum() == 0, f"Found NaNs in fx_df: {fx_df.isna().sum().to_dict()}"

    def test_cache_file_created(self):
        loader = TriAssetDataLoader()
        assert loader.tri_asset_path.exists(), f"Cache file {loader.tri_asset_path} does not exist"
        assert loader.tri_asset_path.stat().st_size > 0, "Cache file is empty"


@pytest.fixture(scope="module")
def market_data():
    prices_df, fx_df = load_tri_asset_data()
    weights = generate_simplex_grid(step=0.01)
    return prices_df, fx_df, weights


class TestVectorizedSimplexSimulator:
    """Validates simulation execution time, friction, periodic rebalancing, and metrics."""

    def test_quarterly_simulation_sub_second(self, market_data):
        prices_df, fx_df, weights = market_data
        t0 = time.time()
        res = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="Q", currency="USD")
        duration = time.time() - t0
        assert duration < 1.0, f"Quarterly simulation exceeded 1.0s threshold: {duration:.4f}s"
        assert res.execution_time_sec < 1.0
        assert res.nav_matrix_usd.shape == (len(prices_df), 5151)

    def test_monthly_and_annual_frequencies(self, market_data):
        prices_df, fx_df, weights = market_data
        res_m = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="M", currency="USD")
        assert res_m.execution_time_sec < 1.0
        assert len(res_m.rebalance_indices) > 250  # ~300+ monthly rebalances

        res_a = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="A", currency="USD")
        assert res_a.execution_time_sec < 1.0
        assert 24 <= len(res_a.rebalance_indices) <= 27  # ~26 annual rebalances

    def test_friction_drag_effect(self, market_data):
        prices_df, fx_df, weights = market_data
        # 0 friction vs realistic 7 bps friction
        res_zero = simulate_simplex_grid(
            prices_df, fx_df, weights=weights, rebalance_freq="Q",
            commission_bps=0.0, slippage_bps=0.0
        )
        res_friction = simulate_simplex_grid(
            prices_df, fx_df, weights=weights, rebalance_freq="Q",
            commission_bps=5.0, slippage_bps=2.0
        )

        # For balanced portfolios that rebalance, zero friction must strictly yield >= NAV than with friction
        # Pick balanced triplet (e.g. index with ~ equal weights)
        idx_balanced = res_zero.find_closest_triplet_index(0.33, 0.33, 0.34)
        assert res_zero.nav_matrix_usd[-1, idx_balanced] > res_friction.nav_matrix_usd[-1, idx_balanced], (
            "Portfolio with zero friction must outperform portfolio with transaction friction"
        )

    def test_dual_currency_tracking(self, market_data):
        prices_df, fx_df, weights = market_data
        res_usd = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="Q", currency="USD")
        res_krw = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="Q", currency="KRW")

        # Start NAV for both must be 1.0
        assert np.allclose(res_usd.nav_matrix[0], 1.0)
        assert np.allclose(res_krw.nav_matrix[0], 1.0)

        # Check FX relation: NAV_KRW(t) = NAV_USD(t) * FX(t) / FX(0)
        fx_ratio = fx_df["USDKRW"].values[-1] / fx_df["USDKRW"].values[0]
        expected_krw_end = res_usd.nav_matrix_usd[-1] * fx_ratio
        assert np.allclose(res_krw.nav_matrix[-1], expected_krw_end, rtol=1e-5)

    def test_calendar_intra_year_mdd_matrix(self, market_data):
        prices_df, fx_df, weights = market_data
        res = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="Q", currency="USD")
        annual_mdd = res.annual_mdd
        assert isinstance(annual_mdd, pd.DataFrame)
        assert len(annual_mdd) == 26  # 2001 through 2026
        assert annual_mdd.shape[1] == 5151
        assert (annual_mdd.values <= 0.0).all(), "Drawdowns must be non-positive"
        assert (annual_mdd.values >= -1.0).all(), "Drawdowns cannot exceed -100%"

    def test_worst_mdd_and_calmar_sanity(self, market_data):
        prices_df, fx_df, weights = market_data
        res = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="Q", currency="USD")
        worst_mdd = res.worst_annual_mdd
        calmar = res.calmar_ratio
        cagr = res.cagr

        assert len(worst_mdd) == 5151
        assert len(calmar) == 5151
        assert len(cagr) == 5151
        # All Worst Annual MDD must be negative
        assert np.all(worst_mdd < 0.0)
        # Pure SPY index [1, 0, 0]
        spy_idx = res.find_closest_triplet_index(1.0, 0.0, 0.0)
        # SPY worst annual MDD occurred in 2008 and is approx -47%
        assert -0.50 <= worst_mdd[spy_idx] <= -0.45, f"SPY worst annual MDD unexpected: {worst_mdd[spy_idx]}"
        # Calmar = CAGR / |worst_mdd|
        expected_calmar = cagr[spy_idx] / abs(worst_mdd[spy_idx])
        assert np.isclose(calmar[spy_idx], expected_calmar)

    def test_switch_currency(self, market_data):
        prices_df, fx_df, weights = market_data
        res = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="Q", currency="USD")
        assert res.currency == "USD"
        res_switched = res.switch_currency("KRW")
        assert res_switched.currency == "KRW"
        assert np.array_equal(res_switched.nav_matrix, res.nav_matrix_krw)
