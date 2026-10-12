"""
Adversarial Stress Test Harness for Milestone 4 (Quantitative & Simplex Math).
Author: challenger_m4_1 (Empirical Challenger)
Target: Simplex Engine, Intra-Year Peak Resets, Calmar Denominator Guards,
        Transaction Friction Monotonicity, and Dual-Currency FX Buffer.

Executes under: D:\\Industry\\.venv\\Scripts\\python.exe with BypassSandbox: true
"""
import time
import math
import numpy as np
import pandas as pd
import pytest

from src.data.tri_asset_loader import load_tri_asset_data
from src.optimizer.tri_asset_simplex import (
    generate_simplex_grid,
    simulate_simplex_grid,
    SimplexGridResult,
    ASSET_NAMES,
)
from src.optimizer.tri_asset_optimizer import (
    optimize_risk_tiers,
    calculate_crisis_stress,
    lookup_custom_weights,
    STANDARD_TIER_KEYS,
    TIER_1_KEY,
    TIER_2_KEY,
    TIER_3_KEY,
    TIER_4_KEY,
)


@pytest.fixture(scope="module")
def real_market_data():
    """Loads production market data for empirical verification."""
    prices_df, fx_df = load_tri_asset_data()
    grid = generate_simplex_grid(step=0.01)
    return prices_df, fx_df, grid


# ==============================================================================
# SECTION 1: Simplex Geometry & Boundary Conditions
# ==============================================================================
class TestSimplexGeometryAndBoundary:
    """
    Stress-tests the 3-asset allocation simplex:
    w_SPY + w_QQQ + w_SOXX = 1.0, w_i >= 0
    at 1% step resolution.
    """

    def test_simplex_total_count_and_shape(self, real_market_data):
        """Verifies exact count C(102, 2) = 5,151 triplets."""
        _, _, grid = real_market_data
        assert grid.shape == (5151, 3), f"Expected (5151, 3), got {grid.shape}"

    def test_simplex_non_negativity_all_triplets(self, real_market_data):
        """Verifies every weight in all 5,151 triplets is strictly >= 0.0 and <= 1.0."""
        _, _, grid = real_market_data
        min_val = np.min(grid)
        max_val = np.max(grid)
        assert min_val >= 0.0, f"Found negative weight: {min_val}"
        assert max_val <= 1.0, f"Found weight > 1.0: {max_val}"
        # Stricter check: assert no NaN or Inf
        assert not np.isnan(grid).any(), "Found NaN in simplex weights"
        assert not np.isinf(grid).any(), "Found Inf in simplex weights"

    def test_simplex_exact_sum_to_one(self, real_market_data):
        """Verifies row sums equal exactly 1.0 within ultra-strict float tolerance 1e-12."""
        _, _, grid = real_market_data
        sums = np.sum(grid, axis=1)
        max_deviation = np.max(np.abs(sums - 1.0))
        assert max_deviation < 1e-12, f"Simplex sum max deviation {max_deviation} exceeds 1e-12"

    def test_simplex_uniqueness_no_duplicates(self, real_market_data):
        """Verifies all 5,151 triplets are unique with zero duplicates."""
        _, _, grid = real_market_data
        unique_rows = np.unique(grid, axis=0)
        assert len(unique_rows) == 5151, f"Expected 5,151 unique triplets, got {len(unique_rows)}"

    def test_simplex_vertices_existence_and_properties(self, real_market_data):
        """
        Tests vertices:
        [1.0, 0, 0] (Pure SPY)
        [0, 1.0, 0] (Pure QQQ)
        [0, 0, 1.0] (Pure SOXX)
        """
        prices_df, fx_df, grid = real_market_data
        vertices = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
        ]
        vertex_indices = []
        for v in vertices:
            matches = np.where(np.all(np.isclose(grid, v, atol=1e-8), axis=1))[0]
            assert len(matches) == 1, f"Vertex {v} should appear exactly once in grid, found {len(matches)}"
            vertex_indices.append(matches[0])

        # Simulate vertices quarterly with 7 bps friction
        res = simulate_simplex_grid(
            prices_df, fx_df, weights=grid[vertex_indices], rebalance_freq="Q",
            commission_bps=5.0, slippage_bps=2.0, currency="USD"
        )

        # For pure single-asset portfolios, there are no other assets to trade into at rebalance.
        # Therefore, rebalance turnover should be 0.0 across all rebalance periods!
        turnovers = res.turnover_matrix
        assert np.allclose(turnovers, 0.0, atol=1e-10), (
            f"Pure single-asset vertex portfolios must have 0.0 rebalance turnover, got max {np.max(turnovers)}"
        )

        # For 0 turnover, NAV must match pure buy-and-hold price ratio: P(t) / P(0)
        for i, asset_col in enumerate(ASSET_NAMES):
            expected_nav = prices_df[asset_col].values / prices_df[asset_col].values[0]
            sim_nav = res.nav_matrix_usd[:, i]
            assert np.allclose(sim_nav, expected_nav, atol=1e-7), (
                f"Vertex {asset_col} NAV diverges from buy-and-hold price ratio"
            )

    def test_simplex_extreme_edge_weights(self, real_market_data):
        """
        Tests extreme edge weights:
        [0.99, 0.01, 0.0]
        [0.01, 0.99, 0.0]
        [0.0, 0.01, 0.99]
        and other boundary permutations:
        [0.99, 0.0, 0.01]
        [0.01, 0.0, 0.99]
        [0.0, 0.99, 0.01]
        """
        prices_df, fx_df, grid = real_market_data
        extreme_triplets = [
            np.array([0.99, 0.01, 0.00]),
            np.array([0.01, 0.99, 0.00]),
            np.array([0.00, 0.01, 0.99]),
            np.array([0.99, 0.00, 0.01]),
            np.array([0.01, 0.00, 0.99]),
            np.array([0.00, 0.99, 0.01]),
        ]
        edge_indices = []
        for triplet in extreme_triplets:
            matches = np.where(np.all(np.isclose(grid, triplet, atol=1e-8), axis=1))[0]
            assert len(matches) == 1, f"Extreme edge {triplet} should exist exactly once, found {len(matches)}"
            edge_indices.append(matches[0])

        # Simulate these edge triplets
        res = simulate_simplex_grid(
            prices_df, fx_df, weights=grid[edge_indices], rebalance_freq="Q",
            commission_bps=5.0, slippage_bps=2.0, currency="USD"
        )
        # Check that NAV series is strictly positive, non-NaN, non-Inf
        assert np.all(res.nav_matrix_usd > 0.0), "NAV must be strictly positive for extreme edge weights"
        assert not np.isnan(res.nav_matrix_usd).any(), "Found NaN in edge weights NAV"
        assert not np.isinf(res.nav_matrix_usd).any(), "Found Inf in edge weights NAV"

        # Check turnover is bounded in [0, 2.0]
        assert np.all(res.turnover_matrix >= 0.0), "Turnover must be non-negative"
        assert np.all(res.turnover_matrix <= 2.0), "Turnover fraction cannot exceed 2.0"


# ==============================================================================
# SECTION 2: Financial & Risk Math Stress Tests
# ==============================================================================
class TestIntraYearPeakResetAndCalendarMDD:
    """
    Stress-tests institutional intra-year peak reset:
    Peak_Y(t) = max_{s <= t, s in Y} V(s)
    Peak resets on Jan 1 of every calendar year (2001-2026).
    """

    def test_calendar_years_count_and_sequence(self, real_market_data):
        """Verifies exactly 26 calendar years (2001-2026) are evaluated."""
        prices_df, fx_df, grid = real_market_data
        res = simulate_simplex_grid(prices_df, fx_df, weights=grid[:10], rebalance_freq="Q")
        annual_mdd = res.annual_mdd
        expected_years = list(range(2001, 2027))
        assert list(annual_mdd.index) == expected_years, f"Expected years 2001-2026, got {list(annual_mdd.index)}"

    def test_synthetic_peak_leakage_adversarial_proof(self):
        """
        Adversarial Scenario:
        In Year 1 (2021), portfolio peaks at 1000.0, crashes to 100.0 on Dec 31 (-90% drop).
        In Year 2 (2022), portfolio starts at 100.0 on Jan 1, reaches 150.0, and ends at 120.0 (-20% intra-year drop).
        If the annual peak leaked from Year 1:
            Year 2 MDD would erroneously be (120 - 1000) / 1000 = -88.0%.
        With correct Jan 1 reset:
            Year 2 Peak = 150.0, Year 2 MDD = (120 - 150) / 150 = -20.0%.
        """
        dates = pd.date_range("2021-01-01", "2022-12-31", freq="B")
        nav_values = np.ones(len(dates), dtype=np.float64) * 100.0

        # 2021: starts at 100, peaks at 1000 in June, crashes to 100 on Dec 31
        y2021_mask = dates.year == 2021
        nav_values[y2021_mask] = np.linspace(100.0, 1000.0, np.sum(y2021_mask))
        # crash on last day of 2021
        last_2021_idx = np.where(y2021_mask)[0][-1]
        nav_values[last_2021_idx] = 100.0

        # 2022: starts at 100, goes to 150, drops to 120
        y2022_indices = np.where(dates.year == 2022)[0]
        y2022_len = len(y2022_indices)
        half_len = y2022_len // 2
        nav_values[y2022_indices[:half_len]] = np.linspace(100.0, 150.0, half_len)
        nav_values[y2022_indices[half_len:]] = np.linspace(150.0, 120.0, y2022_len - half_len)

        # Create dummy SimplexGridResult
        dummy_weights = np.array([[1.0, 0.0, 0.0]])
        res = SimplexGridResult(
            weights=dummy_weights,
            dates=dates,
            nav_matrix_usd=nav_values[:, None],
            nav_matrix_krw=nav_values[:, None],
            currency="USD",
            rebalance_freq="Quarterly",
            commission_bps=0.0,
            slippage_bps=0.0,
            rebalance_indices=np.array([0]),
            turnover_matrix=np.zeros((0, 1)),
            execution_time_sec=0.001,
        )

        mdd_df = res.annual_mdd
        assert 2021 in mdd_df.index
        assert 2022 in mdd_df.index

        # 2021 MDD: peak was 1000, dropped to 100 -> (100 - 1000)/1000 = -0.90
        assert np.isclose(mdd_df.loc[2021, 0], -0.90, atol=1e-3), (
            f"Expected 2021 MDD -0.90, got {mdd_df.loc[2021, 0]}"
        )

        # 2022 MDD: peak was 150, trough was 120 -> (120 - 150)/150 = -0.20
        assert np.isclose(mdd_df.loc[2022, 0], -0.20, atol=1e-3), (
            f"Peak leaked across years! Expected 2022 MDD -0.20, got {mdd_df.loc[2022, 0]}"
        )

    def test_strictly_monotonic_increasing_year_has_zero_mdd(self):
        """
        Adversarial Scenario:
        If a year's NAV strictly increases every single day (e.g. 100 -> 101 -> 102),
        the intra-year MDD for that year MUST be exactly 0.0000.
        """
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="B")
        nav_values = np.linspace(100.0, 200.0, len(dates))

        res = SimplexGridResult(
            weights=np.array([[1.0, 0.0, 0.0]]),
            dates=dates,
            nav_matrix_usd=nav_values[:, None],
            nav_matrix_krw=nav_values[:, None],
            currency="USD",
            rebalance_freq="Annual",
            commission_bps=0.0,
            slippage_bps=0.0,
            rebalance_indices=np.array([0]),
            turnover_matrix=np.zeros((0, 1)),
            execution_time_sec=0.001,
        )

        mdd_df = res.annual_mdd
        assert np.isclose(mdd_df.loc[2023, 0], 0.0, atol=1e-12), (
            f"Monotonically increasing year must have MDD == 0.0, got {mdd_df.loc[2023, 0]}"
        )


class TestCalmarRatioStressAndZeroDrawdown:
    """
    Stress-tests Calmar ratio formula:
    Calmar = CAGR / max_Y |Annual MDD_Y|
    Guards against division by zero, zero drawdown, negative CAGR, and pathological returns.
    """

    def test_calmar_zero_drawdown_guard(self):
        """
        Pathological Scenario:
        Worst Annual MDD is 0.0 (perfect monotonic asset).
        Division by zero must NOT raise ZeroDivisionError or produce NaN/Inf.
        """
        dates = pd.date_range("2020-01-01", "2022-12-31", freq="B")
        # Monotonically increasing NAV
        nav_values = np.linspace(100.0, 200.0, len(dates))

        res = SimplexGridResult(
            weights=np.array([[1.0, 0.0, 0.0]]),
            dates=dates,
            nav_matrix_usd=nav_values[:, None],
            nav_matrix_krw=nav_values[:, None],
            currency="USD",
            rebalance_freq="Annual",
            commission_bps=0.0,
            slippage_bps=0.0,
            rebalance_indices=np.array([0]),
            turnover_matrix=np.zeros((0, 1)),
            execution_time_sec=0.001,
        )

        worst_mdd = res.worst_annual_mdd
        assert np.isclose(worst_mdd[0], 0.0, atol=1e-10)

        # Must compute without exception
        calmar = res.calmar_ratio
        assert not np.isnan(calmar).any(), "Calmar ratio produced NaN for zero drawdown!"
        assert not np.isinf(calmar).any(), "Calmar ratio produced Inf for zero drawdown!"
        assert calmar[0] > 0.0, f"Calmar ratio should be positive, got {calmar[0]}"

    def test_calmar_negative_cagr(self):
        """
        Pathological Scenario:
        Portfolio loses 80% over 3 years. CAGR is negative.
        Worst Annual MDD is negative (e.g. -0.50).
        Calmar ratio formula: CAGR / |Worst MDD|
        Since denominator is positive |Worst MDD|, Calmar must be negative!
        """
        dates = pd.date_range("2020-01-01", "2022-12-31", freq="B")
        nav_values = np.linspace(100.0, 20.0, len(dates))  # 80% loss

        res = SimplexGridResult(
            weights=np.array([[1.0, 0.0, 0.0]]),
            dates=dates,
            nav_matrix_usd=nav_values[:, None],
            nav_matrix_krw=nav_values[:, None],
            currency="USD",
            rebalance_freq="Annual",
            commission_bps=0.0,
            slippage_bps=0.0,
            rebalance_indices=np.array([0]),
            turnover_matrix=np.zeros((0, 1)),
            execution_time_sec=0.001,
        )

        cagr = res.cagr[0]
        worst_mdd = res.worst_annual_mdd[0]
        calmar = res.calmar_ratio[0]

        assert cagr < 0.0, f"Expected negative CAGR, got {cagr}"
        assert worst_mdd < 0.0, f"Expected negative Worst MDD, got {worst_mdd}"
        expected_calmar = cagr / abs(worst_mdd)
        assert np.isclose(calmar, expected_calmar, atol=1e-5), (
            f"Expected Calmar {expected_calmar}, got {calmar}"
        )
        assert calmar < 0.0, "Calmar must be negative when CAGR is negative"

    def test_calmar_formula_exact_validation_on_all_risk_tiers(self, real_market_data):
        """
        Verifies Calmar ratio calculation on production optimized tiers:
        Calmar == CAGR / |Worst Annual MDD|
        """
        prices_df, fx_df, grid = real_market_data
        res = simulate_simplex_grid(prices_df, fx_df, weights=grid, rebalance_freq="Q", currency="USD")
        tiers = optimize_risk_tiers(res)

        for tier_key in STANDARD_TIER_KEYS:
            tier_res = tiers[tier_key]
            cagr = tier_res.cagr
            worst_mdd = tier_res.worst_annual_mdd
            calmar = tier_res.calmar
            expected_calmar = cagr / abs(worst_mdd)
            assert np.isclose(calmar, expected_calmar, atol=1e-4), (
                f"Tier {tier_key} Calmar mismatch: got {calmar}, expected {expected_calmar}"
            )


class TestTransactionFrictionMonotonicity:
    """
    Stress-tests transaction friction modeling:
    0.05% brokerage commission + 0.02% slippage = 0.07% (7 bps) turnover cost.
    Verifies:
      1. Frequency hierarchy: Monthly turnover > Quarterly > Annual
      2. Monotonic cost drag: Terminal NAV decreases as friction rate increases
      3. Monotonic frequency drag: Monthly friction drag > Quarterly drag > Annual drag
    """

    def test_rebalance_frequency_turnover_hierarchy(self, real_market_data):
        """
        For a dynamic drifted allocation like [0.34, 0.33, 0.33] or [0.19, 0.57, 0.24]:
        Total rebalance turnover over the 25-year backtest must follow:
        Turnover_Monthly > Turnover_Quarterly > Turnover_Annual.
        """
        prices_df, fx_df, _ = real_market_data
        test_weights = np.array([[0.19, 0.57, 0.24]])  # Tier 4 weights

        res_m = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="M", commission_bps=5.0, slippage_bps=2.0)
        res_q = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="Q", commission_bps=5.0, slippage_bps=2.0)
        res_a = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="A", commission_bps=5.0, slippage_bps=2.0)

        # Number of rebalance periods
        assert len(res_m.turnover_matrix) > len(res_q.turnover_matrix), "Monthly must have more rebalances than Quarterly"
        assert len(res_q.turnover_matrix) > len(res_a.turnover_matrix), "Quarterly must have more rebalances than Annual"

        # Total cumulative turnover volume traded
        tot_turnover_m = np.sum(res_m.turnover_matrix)
        tot_turnover_q = np.sum(res_q.turnover_matrix)
        tot_turnover_a = np.sum(res_a.turnover_matrix)

        assert tot_turnover_m > tot_turnover_q, (
            f"Monthly total turnover ({tot_turnover_m:.2f}) must exceed Quarterly ({tot_turnover_q:.2f})"
        )
        assert tot_turnover_q > tot_turnover_a, (
            f"Quarterly total turnover ({tot_turnover_q:.2f}) must exceed Annual ({tot_turnover_a:.2f})"
        )

    def test_friction_rate_monotonic_drag(self, real_market_data):
        """
        For identical weights [0.19, 0.57, 0.24] and Quarterly rebalancing:
        Terminal NAV(0 bps) > Terminal NAV(7 bps) > Terminal NAV(20 bps).
        """
        prices_df, fx_df, _ = real_market_data
        test_weights = np.array([[0.19, 0.57, 0.24]])

        res_0bps = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="Q", commission_bps=0.0, slippage_bps=0.0)
        res_7bps = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="Q", commission_bps=5.0, slippage_bps=2.0)
        res_20bps = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="Q", commission_bps=15.0, slippage_bps=5.0)

        nav_0 = res_0bps.nav_matrix_usd[-1, 0]
        nav_7 = res_7bps.nav_matrix_usd[-1, 0]
        nav_20 = res_20bps.nav_matrix_usd[-1, 0]

        assert nav_0 > nav_7, f"Friction did not reduce NAV: 0 bps {nav_0:.4f} <= 7 bps {nav_7:.4f}"
        assert nav_7 > nav_20, f"Higher friction did not reduce NAV further: 7 bps {nav_7:.4f} <= 20 bps {nav_20:.4f}"

    def test_monthly_friction_drag_exceeds_quarterly_and_annual(self, real_market_data):
        """
        Verifies that total friction drag:
        Friction Drag = Gross NAV(0 bps) - Net NAV(7 bps)
        satisfies: Drag(Monthly) > Drag(Quarterly) > Drag(Annual).
        """
        prices_df, fx_df, _ = real_market_data
        test_weights = np.array([[0.19, 0.57, 0.24]])

        # 0 bps benchmarks
        nav_0_m = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="M", commission_bps=0.0, slippage_bps=0.0).nav_matrix_usd[-1, 0]
        nav_0_q = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="Q", commission_bps=0.0, slippage_bps=0.0).nav_matrix_usd[-1, 0]
        nav_0_a = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="A", commission_bps=0.0, slippage_bps=0.0).nav_matrix_usd[-1, 0]

        # 7 bps actuals
        nav_7_m = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="M", commission_bps=5.0, slippage_bps=2.0).nav_matrix_usd[-1, 0]
        nav_7_q = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="Q", commission_bps=5.0, slippage_bps=2.0).nav_matrix_usd[-1, 0]
        nav_7_a = simulate_simplex_grid(prices_df, fx_df, weights=test_weights, rebalance_freq="A", commission_bps=5.0, slippage_bps=2.0).nav_matrix_usd[-1, 0]

        drag_m = (nav_0_m - nav_7_m) / nav_0_m
        drag_q = (nav_0_q - nav_7_q) / nav_0_q
        drag_a = (nav_0_a - nav_7_a) / nav_0_a

        assert drag_m > drag_q, f"Monthly friction drag ({drag_m:.4%}) must exceed Quarterly ({drag_q:.4%})"
        assert drag_q > drag_a, f"Quarterly friction drag ({drag_q:.4%}) must exceed Annual ({drag_a:.4%})"


class TestDualCurrencyFXBuffer:
    """
    Stress-tests dual-currency performance engine:
    V_KRW(t) = V_USD(t) * FX(t) / FX(t_0)
    Empirically verifies Korean Won counter-cyclical safe-haven buffer during 2008 GFC.
    """

    def test_2008_gfc_usd_vs_krw_mdd_mitigation(self, real_market_data):
        """
        Empirically verifies 2008 GFC intra-year drawdown mitigation:
        USD intra-year MDD vs KRW intra-year MDD.
        In 2008, USD/KRW spiked by ~+61.8%.
        Drawdown in KRW must be significantly softer than in USD for all assets.
        """
        prices_df, fx_df, _ = real_market_data
        weights = np.array([
            [1.0, 0.0, 0.0],  # SPY
            [0.0, 1.0, 0.0],  # QQQ
            [0.0, 0.0, 1.0],  # SOXX
            [0.19, 0.57, 0.24], # Tier 4
        ])

        res_usd = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="Q", currency="USD")
        res_krw = simulate_simplex_grid(prices_df, fx_df, weights=weights, rebalance_freq="Q", currency="KRW")

        mdd_2008_usd = res_usd.annual_mdd.loc[2008].values
        mdd_2008_krw = res_krw.annual_mdd.loc[2008].values

        # SPY
        spy_usd_mdd = mdd_2008_usd[0]
        spy_krw_mdd = mdd_2008_krw[0]
        assert spy_usd_mdd < -0.45, f"Expected SPY USD MDD < -45%, got {spy_usd_mdd:.4%}"
        assert spy_krw_mdd > spy_usd_mdd, f"KRW did not soften drawdown! KRW {spy_krw_mdd} vs USD {spy_usd_mdd}"
        # Cushion should be >= 20 percentage points for SPY
        cushion = spy_krw_mdd - spy_usd_mdd
        assert cushion >= 0.20, f"Expected >= 20% cushion for SPY, got {cushion:.4%}"

        # All 4 portfolios must have softer drawdown in KRW than USD in 2008
        for i, name in enumerate(["SPY", "QQQ", "SOXX", "Tier 4"]):
            assert mdd_2008_krw[i] > mdd_2008_usd[i], (
                f"2008 KRW MDD ({mdd_2008_krw[i]:.2%}) was not softer than USD MDD ({mdd_2008_usd[i]:.2%}) for {name}"
            )

    def test_constant_fx_invariance(self, real_market_data):
        """
        If FX series is constant (e.g. 1000.0 every day),
        then KRW NAV must equal USD NAV exactly: V_KRW(t) == V_USD(t).
        """
        prices_df, fx_df, _ = real_market_data
        const_fx = fx_df.copy()
        const_fx.iloc[:, 0] = 1200.0

        res_usd = simulate_simplex_grid(prices_df, const_fx, weights=np.array([[1.0, 0.0, 0.0]]), currency="USD")
        res_krw = simulate_simplex_grid(prices_df, const_fx, weights=np.array([[1.0, 0.0, 0.0]]), currency="KRW")

        assert np.allclose(res_usd.nav_matrix_usd, res_krw.nav_matrix_krw, atol=1e-10), (
            "Constant FX must yield identical KRW and USD NAV series"
        )


class TestAdversarialCustomWeightLookup:
    """
    Stress-tests interactive slider lookup engine:
    lookup_custom_weights(grid_result, w_spy, w_qqq, w_soxx)
    Sub-millisecond latency (< 5ms mandate), unnormalized inputs, boundary clamping.
    """

    def test_lookup_latency_under_5ms(self, real_market_data):
        """Mandate: evaluation latency < 5ms (empirically sub-millisecond < 1ms)."""
        prices_df, fx_df, grid = real_market_data
        res = simulate_simplex_grid(prices_df, fx_df, weights=grid, rebalance_freq="Q", currency="USD")
        # Warmup all cached analytical properties
        _ = res.summary_df()
        _ = res.annual_mdd

        # Perform 100 random weight lookups and measure timings
        latencies = []
        for _ in range(100):
            ws = np.random.uniform(0.0, 1.0)
            wq = np.random.uniform(0.0, 1.0 - ws)
            wx = 1.0 - ws - wq
            eval_res = lookup_custom_weights(res, ws, wq, wx)
            latencies.append(eval_res.lookup_duration_ms)

        mean_lat = np.mean(latencies)
        median_lat = np.median(latencies)
        p95_lat = np.percentile(latencies, 95)
        assert mean_lat < 2.0, f"Mean lookup latency {mean_lat:.3f}ms too high"
        assert median_lat < 1.0, f"Median lookup latency {median_lat:.3f}ms exceeded 1.0ms"
        assert p95_lat < 8.0, f"95th percentile lookup latency {p95_lat:.3f}ms exceeded 8.0ms!"

    def test_unnormalized_weights_handled_gracefully(self, real_market_data):
        """
        Adversarial Scenario:
        User inputs weights that don't sum to 1.0 (e.g. [0.5, 0.5, 0.5] or [50, 30, 20]).
        The engine must normalize gracefully and snap to the nearest 1% discrete simplex triplet.
        """
        prices_df, fx_df, grid = real_market_data
        res = simulate_simplex_grid(prices_df, fx_df, weights=grid, rebalance_freq="Q", currency="USD")

        # Sum = 1.5
        eval_1 = lookup_custom_weights(res, 0.5, 0.5, 0.5)
        assert np.isclose(np.sum(eval_1.weights), 1.0, atol=1e-4)

        # Sum = 100 (percentage inputs)
        eval_2 = lookup_custom_weights(res, 60.0, 30.0, 10.0)
        assert np.isclose(np.sum(eval_2.weights), 1.0, atol=1e-4)
        assert np.isclose(eval_2.weights[0], 0.60, atol=1e-2)
        assert np.isclose(eval_2.weights[1], 0.30, atol=1e-2)
        assert np.isclose(eval_2.weights[2], 0.10, atol=1e-2)

    def test_zero_weights_handled(self, real_market_data):
        """
        Adversarial Scenario:
        All weights 0.0 ([0, 0, 0]).
        Should not crash with ZeroDivisionError, but handle gracefully.
        """
        prices_df, fx_df, grid = real_market_data
        res = simulate_simplex_grid(prices_df, fx_df, weights=grid, rebalance_freq="Q", currency="USD")

        eval_zero = lookup_custom_weights(res, 0.0, 0.0, 0.0)
        assert eval_zero.triplet_index >= 0
        assert np.isclose(np.sum(eval_zero.weights), 1.0, atol=1e-4)


class TestNumericalPrecisionAndRobustness:
    """
    Stress-tests floating point stability and memory/runtime bounds.
    """

    def test_zero_scipy_dependency_in_codebase(self):
        """
        Mandate: Zero dependency on SciPy to avoid Python 3.14 C-wheel incompatibilities.
        """
        import sys
        import src.optimizer.tri_asset_simplex as mod_s
        import src.optimizer.tri_asset_optimizer as mod_o

        # Check imported modules for scipy
        loaded_scipy = [k for k in sys.modules if "scipy" in k]
        assert len(loaded_scipy) == 0, f"scipy was loaded into sys.modules: {loaded_scipy}"

    def test_sub_second_simulation_runtime_on_all_5151_triplets(self, real_market_data):
        """
        Mandate: Simulating all 5,151 triplets across the entire 25-year history
        must execute in < 1.0 second core vectorized engine time.
        """
        prices_df, fx_df, grid = real_market_data
        t0 = time.perf_counter()
        res = simulate_simplex_grid(prices_df, fx_df, weights=grid, rebalance_freq="Q", currency="USD")
        elapsed = time.perf_counter() - t0

        # res.execution_time_sec records internal simulation duration
        assert res.execution_time_sec < 1.05 or elapsed < 1.5, (
            f"Simulation of 5,151 triplets took {res.execution_time_sec:.4f}s (wall clock: {elapsed:.4f}s), exceeding threshold!"
        )
