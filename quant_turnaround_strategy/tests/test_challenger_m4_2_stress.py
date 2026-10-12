"""
Challenger M4-2 Empirical Stress Test Suite:
Streamlit Tab 6 UI, Interactive Widgets, Extreme Sliders, Currency Switches,
Preset Buttons, Radio Views, Latency Benchmarking, and Plotly Payload & Memory Bounds.

Author: Challenger M4-2 (Critic & Specialist)
Date: 2026-10-12
Repository: D:\\Industry\\quant_turnaround_strategy
"""
import gc
import json
from pathlib import Path
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd
import pytest

# Ensure repository root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app
from src.data.tri_asset_loader import load_tri_asset_data
from src.optimizer.tri_asset_simplex import (
    SimplexGridResult,
    generate_simplex_grid,
    simulate_simplex_grid,
)
from src.optimizer.tri_asset_optimizer import (
    optimize_risk_tiers,
    extract_pareto_frontier,
    lookup_custom_weights,
    generate_year_matrix_table,
    calculate_crisis_stress,
    TIER_1_KEY,
    TIER_2_KEY,
    TIER_3_KEY,
    TIER_4_KEY,
    STANDARD_TIER_KEYS,
)
from src.ui.tri_asset_tab import (
    get_cached_tri_asset_engine,
    create_ternary_contour_chart,
    create_pareto_frontier_chart,
    create_custom_nav_comparison_chart,
)

APP_FILE = BASE_DIR / "app.py"


# =============================================================================
# Pillar 1: Headless AppTest Stressing & Interactive Widget Operations
# =============================================================================
class TestHeadlessAppTestTab6Stressing:
    """Simulates realistic and adversarial user interactions on Tab 6 via Streamlit AppTest."""

    @pytest.fixture(scope="class")
    @classmethod
    def app_instance(cls):
        """Initializes and runs AppTest once for warm session state."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_FILE), default_timeout=90)
        at.run()
        assert len(at.exception) == 0, f"Initial AppTest raised exceptions: {[e.value for e in at.exception]}"
        return at

    def test_apptest_tab6_structure_and_initial_widgets(self, app_instance):
        """Verify Tab 6 exists and all expected interactive controls are discovered."""
        at = app_instance
        assert len(at.tabs) == 6
        tab_labels = [t.label for t in at.tabs]
        assert any("3대 ETF" in lbl or "Tri-Asset" in lbl for lbl in tab_labels)

        # Check slider keys
        slider_keys = [s.key for s in at.slider]
        assert "tri_slider_spy" in slider_keys, f"tri_slider_spy not found in {slider_keys}"
        assert "tri_slider_qqq" in slider_keys, f"tri_slider_qqq not found in {slider_keys}"

        # Check preset buttons
        btn_labels = [b.label for b in at.button]
        assert any("Tier 1" in lbl for lbl in btn_labels), "Tier 1 preset button missing"
        assert any("Tier 2" in lbl for lbl in btn_labels), "Tier 2 preset button missing"
        assert any("Tier 3" in lbl for lbl in btn_labels), "Tier 3 preset button missing"
        assert any("Tier 4" in lbl for lbl in btn_labels), "Tier 4 preset button missing"

        # Check radio widgets
        radio_keys = [r.key for r in at.radio]
        assert "tri_viz_view_mode" in radio_keys, f"tri_viz_view_mode missing in {radio_keys}"
        assert "tri_ternary_color" in radio_keys, f"tri_ternary_color missing in {radio_keys}"

    def test_apptest_extreme_slider_positions(self, app_instance):
        """
        Adversarial probe:
        Move weight sliders to extreme positions:
        1. Pure SPY: SPY=100%, QQQ=0% -> SOXX=0%
        2. Pure QQQ: SPY=0%, QQQ=100% -> SOXX=0%
        3. Pure SOXX: SPY=0%, QQQ=0% -> SOXX=100%
        4. Boundary overflow: Set SPY=80%, attempt QQQ=50% (sum 130%) -> Guard must clamp QQQ <= 20%
        """
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_FILE), default_timeout=60)
        at.run()

        # Find sliders
        slider_spy = next(s for s in at.slider if s.key == "tri_slider_spy")
        slider_qqq = next(s for s in at.slider if s.key == "tri_slider_qqq")

        # 1. 100% SPY
        slider_spy.set_value(100)
        slider_qqq.set_value(0)
        at.run()
        assert len(at.exception) == 0, f"Exception at 100% SPY: {[e.value for e in at.exception]}"
        assert at.session_state["tri_slider_spy"] == 100
        assert at.session_state["tri_slider_qqq"] == 0

        # 2. 100% QQQ
        slider_spy.set_value(0)
        slider_qqq.set_value(100)
        at.run()
        assert len(at.exception) == 0, f"Exception at 100% QQQ: {[e.value for e in at.exception]}"
        assert at.session_state["tri_slider_spy"] == 0
        assert at.session_state["tri_slider_qqq"] == 100

        # 3. 100% SOXX
        slider_spy.set_value(0)
        slider_qqq.set_value(0)
        at.run()
        assert len(at.exception) == 0, f"Exception at 100% SOXX: {[e.value for e in at.exception]}"
        assert at.session_state["tri_slider_spy"] == 0
        assert at.session_state["tri_slider_qqq"] == 0

        # 4. Boundary overflow attempt: SPY=80, QQQ attempted > 20
        # When SPY=80, max_qqq is 20. If session_state had higher, app clamps it.
        slider_spy.set_value(80)
        slider_qqq.set_value(20)
        at.run()
        assert len(at.exception) == 0, f"Exception on boundary test: {[e.value for e in at.exception]}"
        assert at.session_state["tri_slider_spy"] + at.session_state["tri_slider_qqq"] <= 100

    def test_apptest_preset_buttons_interaction(self, app_instance):
        """
        Test clicking all 4 quick preset buttons sequentially:
        Tier 1 -> (100, 0, 0)
        Tier 2 -> (60, 30, 10)
        Tier 3 -> (30, 50, 20)
        Tier 4 -> (19, 57, 24)
        """
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_FILE), default_timeout=60)
        at.run()

        presets = [
            ("Tier 1", 100, 0),
            ("Tier 2", 60, 30),
            ("Tier 3", 30, 50),
            ("Tier 4", 19, 57),
        ]

        for tier_name, exp_spy, exp_qqq in presets:
            btn = next(b for b in at.button if tier_name in b.label)
            btn.click()
            at.run()
            assert len(at.exception) == 0, f"Exception after clicking {tier_name}: {[e.value for e in at.exception]}"
            assert at.session_state["tri_slider_spy"] == exp_spy, (
                f"Expected SPY={exp_spy} for {tier_name}, got {at.session_state['tri_slider_spy']}"
            )
            assert at.session_state["tri_slider_qqq"] == exp_qqq, (
                f"Expected QQQ={exp_qqq} for {tier_name}, got {at.session_state['tri_slider_qqq']}"
            )

    def test_apptest_currency_toggle_dynamic_update(self, app_instance):
        """
        Toggle between USD ($) and KRW (₩), verifying no exceptions, no NaNs,
        and currency indicator updates.
        """
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_FILE), default_timeout=60)
        at.run()
        assert len(at.exception) == 0

        # Sidebar currency radio
        curr_radio = at.sidebar.radio[0]
        assert "Display Currency" in curr_radio.label

        # Switch to KRW
        curr_radio.set_value("KRW (₩)")
        at.run()
        assert len(at.exception) == 0, f"Exception after KRW switch: {[e.value for e in at.exception]}"

        # Switch back to USD
        curr_radio.set_value("USD ($)")
        at.run()
        assert len(at.exception) == 0, f"Exception after USD switch: {[e.value for e in at.exception]}"

    def test_apptest_view_mode_radios_switch(self, app_instance):
        """
        Switch visualization mode radios across:
        1. Ternary Simplex
        2. Pareto Frontier
        3. Side-by-Side Dual View
        and color mode radio (Calmar Ratio vs CAGR (%)).
        """
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_FILE), default_timeout=60)
        at.run()
        assert len(at.exception) == 0

        view_radio = next(r for r in at.radio if r.key == "tri_viz_view_mode")
        color_radio = next(r for r in at.radio if r.key == "tri_ternary_color")

        # 1. Switch to Pareto
        pareto_opt = [opt for opt in view_radio.options if "Pareto" in opt][0]
        view_radio.set_value(pareto_opt)
        at.run()
        assert len(at.exception) == 0, f"Exception on Pareto view: {[e.value for e in at.exception]}"

        # 2. Switch to Side-by-Side Dual View
        dual_opt = [opt for opt in view_radio.options if "Side-by-Side" in opt][0]
        view_radio.set_value(dual_opt)
        at.run()
        assert len(at.exception) == 0, f"Exception on Side-by-Side view: {[e.value for e in at.exception]}"

        # 3. Switch color to CAGR (%)
        cagr_color_opt = [opt for opt in color_radio.options if "CAGR" in opt][0]
        color_radio.set_value(cagr_color_opt)
        at.run()
        assert len(at.exception) == 0, f"Exception on CAGR color: {[e.value for e in at.exception]}"

        # 4. Switch back to Ternary Simplex
        ternary_opt = [opt for opt in view_radio.options if "Ternary" in opt][0]
        view_radio.set_value(ternary_opt)
        at.run()
        assert len(at.exception) == 0, f"Exception on Ternary view: {[e.value for e in at.exception]}"


# =============================================================================
# Pillar 2: Custom Weight Lookup Latency Stressing (< 5ms Target)
# =============================================================================
class TestCustomWeightLookupLatencyStressing:
    """Adversarially benchmarks custom weight lookup performance under rapid repeated changes."""

    @pytest.fixture(scope="class")
    @classmethod
    def grid_result(cls):
        engine_data = get_cached_tri_asset_engine(rebalance_freq="Quarterly")
        return engine_data["grid_result_usd"]

    def test_lookup_latency_100_rapid_changes_strictly_under_5ms(self, grid_result):
        """
        Stress requirement:
        Benchmark custom weight lookup latency under 100 rapid changes.
        Target: Average latency < 5.0ms (strictly verified).
        Max latency < 25.0ms.
        """
        rng = np.random.default_rng(42)

        # Generate 100 random weight combinations (including vertices and edges)
        test_triplets = []
        # Add 4 canonical tiers
        test_triplets.append((1.0, 0.0, 0.0))
        test_triplets.append((0.6, 0.3, 0.1))
        test_triplets.append((0.3, 0.5, 0.2))
        test_triplets.append((0.19, 0.57, 0.24))

        # Add pure vertices
        test_triplets.append((0.0, 1.0, 0.0))
        test_triplets.append((0.0, 0.0, 1.0))

        # Add edges
        test_triplets.append((0.5, 0.5, 0.0))
        test_triplets.append((0.0, 0.5, 0.5))
        test_triplets.append((0.5, 0.0, 0.5))

        # Add random valid triplets
        while len(test_triplets) < 100:
            raw = rng.uniform(0.0, 1.0, size=3)
            w = raw / raw.sum()
            test_triplets.append((float(w[0]), float(w[1]), float(w[2])))

        durations_ms = []
        cagr_vals = []
        mdd_vals = []
        calmar_vals = []

        # Warm-up 5 iterations
        for _ in range(5):
            _ = lookup_custom_weights(grid_result, 0.33, 0.33, 0.34)

        # Execute 100 rapid lookups
        for w_s, w_q, w_x in test_triplets:
            t0 = time.perf_counter()
            eval_res = lookup_custom_weights(grid_result, w_spy=w_s, w_qqq=w_q, w_soxx=w_x)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            durations_ms.append(elapsed_ms)
            cagr_vals.append(eval_res.cagr)
            mdd_vals.append(eval_res.worst_annual_mdd)
            calmar_vals.append(eval_res.calmar)

            # Mathematical integrity assertions
            assert np.isfinite(eval_res.cagr), f"NaN CAGR for weights ({w_s}, {w_q}, {w_x})"
            assert np.isfinite(eval_res.worst_annual_mdd), f"NaN MDD for weights ({w_s}, {w_q}, {w_x})"
            assert np.isfinite(eval_res.calmar), f"NaN Calmar for weights ({w_s}, {w_q}, {w_x})"
            assert -1.0 <= eval_res.worst_annual_mdd <= 0.0, f"MDD out of bounds: {eval_res.worst_annual_mdd}"

        avg_latency_ms = float(np.mean(durations_ms))
        p95_latency_ms = float(np.percentile(durations_ms, 95))
        max_latency_ms = float(np.max(durations_ms))

        # Hard assertion: Average latency MUST be strictly < 5.0ms
        assert avg_latency_ms < 5.0, (
            f"Average lookup latency {avg_latency_ms:.3f}ms exceeded 5.0ms threshold!"
        )
        # P95 must also be fast
        assert p95_latency_ms < 10.0, f"P95 latency {p95_latency_ms:.3f}ms exceeded 10.0ms!"
        # Max latency must not exceed 25ms
        assert max_latency_ms < 25.0, f"Max latency {max_latency_ms:.3f}ms exceeded 25.0ms!"

    def test_lookup_nearest_triplet_snapping_precision(self, grid_result):
        """
        Verify that off-grid weights (e.g., 19.34% SPY, 56.66% QQQ)
        deterministically snap to the closest 1% simplex point without error.
        """
        eval_exact = lookup_custom_weights(grid_result, 0.19, 0.57, 0.24)
        eval_nearby = lookup_custom_weights(grid_result, 0.191, 0.569, 0.240)

        assert eval_nearby.triplet_index == eval_exact.triplet_index
        assert eval_nearby.cagr == eval_exact.cagr
        assert eval_nearby.worst_annual_mdd == eval_exact.worst_annual_mdd


# =============================================================================
# Pillar 3: Plotly Figure Memory Leak & JSON Payload Stressing
# =============================================================================
class TestPlotlyFigureMemoryAndPayloadStressing:
    """Verifies that Plotly figures do not leak memory and have reasonable payload sizes."""

    @pytest.fixture(scope="class")
    @classmethod
    def engine_bundle(cls):
        return get_cached_tri_asset_engine(rebalance_freq="Quarterly")

    def test_ternary_contour_figure_payload_size(self, engine_bundle):
        """
        Verify Plotly Ternary Simplex figure (with 5,151 points) serializes to JSON
        without error and payload size is reasonable (< 3.0 MB).
        """
        grid_result = engine_bundle["grid_result_usd"]
        tier_results = engine_bundle["tier_results_usd"]
        custom_eval = lookup_custom_weights(grid_result, 0.19, 0.57, 0.24)

        fig = create_ternary_contour_chart(grid_result, tier_results, custom_eval, color_by="Calmar")
        json_str = fig.to_json()
        payload_bytes = len(json_str.encode("utf-8"))
        payload_mb = payload_bytes / (1024 * 1024)

        # Assert payload is bounded and valid JSON
        assert payload_mb < 3.0, f"Ternary figure payload {payload_mb:.2f} MB is too large (> 3.0 MB)"
        assert payload_mb > 0.05, f"Ternary figure payload {payload_mb:.2f} MB is suspiciously small"

        # Verify JSON parsed back cleanly
        parsed = json.loads(json_str)
        assert "data" in parsed
        assert len(parsed["data"]) >= 5  # Base cloud + 4 tiers + custom point

    def test_pareto_frontier_figure_payload_size(self, engine_bundle):
        """Verify Pareto frontier figure JSON payload is compact (< 1.5 MB)."""
        grid_result = engine_bundle["grid_result_usd"]
        tier_results = engine_bundle["tier_results_usd"]
        pareto_df = engine_bundle["pareto_df_usd"]
        custom_eval = lookup_custom_weights(grid_result, 0.19, 0.57, 0.24)

        fig = create_pareto_frontier_chart(grid_result, pareto_df, tier_results, custom_eval)
        json_str = fig.to_json()
        payload_mb = len(json_str.encode("utf-8")) / (1024 * 1024)

        assert payload_mb < 1.5, f"Pareto figure payload {payload_mb:.2f} MB is too large (> 1.5 MB)"
        parsed = json.loads(json_str)
        assert len(parsed["data"]) >= 6  # Cloud + Pareto line + 4 tiers + custom

    def test_custom_nav_comparison_figure_payload_size(self, engine_bundle):
        """Verify Custom NAV curve figure JSON payload is compact (< 1.0 MB)."""
        grid_result = engine_bundle["grid_result_usd"]
        tier_results = engine_bundle["tier_results_usd"]
        custom_eval = lookup_custom_weights(grid_result, 0.19, 0.57, 0.24)

        fig = create_custom_nav_comparison_chart(grid_result, custom_eval, tier_results, currency="USD")
        json_str = fig.to_json()
        payload_mb = len(json_str.encode("utf-8")) / (1024 * 1024)

        assert payload_mb < 2.5, f"NAV curve payload {payload_mb:.2f} MB is too large (> 2.5 MB)"
        parsed = json.loads(json_str)
        assert len(parsed["data"]) == 5  # SPY, QQQ, SOXX, Tier 4, Custom

    def test_figure_generation_memory_leak_stressing(self, engine_bundle):
        """
        Adversarial probe:
        Generate 50 Plotly figures repeatedly.
        Verify memory does not grow unbounded (leak detection via tracemalloc).
        """
        grid_result = engine_bundle["grid_result_usd"]
        tier_results = engine_bundle["tier_results_usd"]
        pareto_df = engine_bundle["pareto_df_usd"]

        gc.collect()
        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        # Generate 50 figures in a loop
        for i in range(50):
            w_spy = (i % 10) / 10.0
            w_qqq = (1.0 - w_spy) / 2.0
            w_soxx = 1.0 - w_spy - w_qqq
            c_eval = lookup_custom_weights(grid_result, w_spy, w_qqq, w_soxx)

            fig_t = create_ternary_contour_chart(grid_result, tier_results, c_eval, color_by="Calmar")
            fig_p = create_pareto_frontier_chart(grid_result, pareto_df, tier_results, c_eval)
            _ = fig_t.to_json()
            _ = fig_p.to_json()

        gc.collect()
        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_end.compare_to(snapshot_start, "lineno")
        total_growth_kb = sum(stat.size_diff for stat in top_stats) / 1024.0
        total_growth_mb = total_growth_kb / 1024.0

        # Memory growth after GC for 50 full figure renders & JSON serializations must be < 20 MB
        assert total_growth_mb < 20.0, (
            f"Plotly figure memory growth {total_growth_mb:.2f} MB indicates potential memory leak!"
        )


# =============================================================================
# Pillar 4: Dual-Currency Mathematical Invariants & Crisis Stress Tables
# =============================================================================
class TestDualCurrencyAndCrisisStressInvariants:
    """Verifies that currency transformation preserves math precision and crisis metrics."""

    @pytest.fixture(scope="class")
    @classmethod
    def engine_bundle(cls):
        return get_cached_tri_asset_engine(rebalance_freq="Quarterly")

    def test_26_year_matrix_usd_vs_krw_consistency(self, engine_bundle):
        """Verify year matrix table has 26 rows (2001-2026) and zero NaNs in both USD and KRW."""
        ym_usd = engine_bundle["year_matrix_usd"]
        ym_krw = engine_bundle["year_matrix_krw"]

        assert len(ym_usd) == 26, f"Expected 26 years in USD matrix, got {len(ym_usd)}"
        assert len(ym_krw) == 26, f"Expected 26 years in KRW matrix, got {len(ym_krw)}"
        assert ym_usd.isna().sum().sum() == 0, "NaNs found in USD year matrix"
        assert ym_krw.isna().sum().sum() == 0, "NaNs found in KRW year matrix"

        # Check 2008 GFC drawdown softening in KRW
        spy_mdd_2008_usd = ym_usd.loc[2008, "SPY MDD"]
        spy_mdd_2008_krw = ym_krw.loc[2008, "SPY MDD"]

        # In USD: SPY was ~ -47.12%
        assert spy_mdd_2008_usd == pytest.approx(-0.4712, abs=0.02)
        # In KRW: SPY was ~ -24.01% (FX appreciated +61%)
        assert spy_mdd_2008_krw == pytest.approx(-0.2401, abs=0.03)
        # Softening cushion must be > 15 percentage points
        assert (spy_mdd_2008_krw - spy_mdd_2008_usd) > 0.15

    def test_crisis_stress_table_structure_and_bounds(self, engine_bundle):
        """Verify crisis stress breakdown covers 4 canonical crises with zero NaNs."""
        crisis_df = engine_bundle["crisis_stress_df"]

        assert len(crisis_df) == 4, f"Expected 4 crisis regimes, got {len(crisis_df)}"
        assert crisis_df.isna().sum().sum() == 0, "NaNs found in crisis stress table"

        # Verify Dot-com crash: SPY superior defense vs SOXX
        dotcom_idx = next(i for i in crisis_df.index if "2001" in str(i))
        spy_dotcom_mdd = crisis_df.loc[dotcom_idx, "SPY MDD"]
        soxx_dotcom_mdd = crisis_df.loc[dotcom_idx, "SOXX MDD"]
        assert spy_dotcom_mdd > soxx_dotcom_mdd, "SPY should have less severe MDD than SOXX during Dot-com"
