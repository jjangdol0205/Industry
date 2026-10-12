"""
Challenger M4-1 Empirical Stress Test Suite:
Streamlit UI, Headless Data Loading, Dual-Currency NAV Transformation,
Korean Capital Gains Taxation, and Simulation Parameter Extremes.

Author: Challenger M4-1
Date: 2026-10-12
Repository: D:\\Industry\\quant_turnaround_strategy
"""
import ast
from datetime import date
from pathlib import Path
import py_compile
import sys
import time

import numpy as np
import pandas as pd
import pytest

# Ensure repository root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import CACHE_DIR, DEFAULT_START_DATE
from src.data.cache_store import CacheStore
from src.data.price_feed import PriceFeed
from src.engine.backtester import BacktestEngine, BacktestResult
from src.engine.metrics import PerformanceMetrics
from src.engine.tax import KoreanTaxEngine, AnnualTaxRecord
from src.strategies.base_strategy import BaseStrategy, StrategyParameters
from src.strategies.enhanced_strategy import EnhancedStrategy, EnhancedStrategyParameters
from src.ui.components import fmt_currency, fmt_pct, fmt_ratio, render_metric_card
import app


APP_FILE = BASE_DIR / "app.py"
UI_DIR = BASE_DIR / "src" / "ui"


# =============================================================================
# Pillar 1: Headless Compilation, AST Validation & Streamlit AppTest Execution
# =============================================================================
class TestAppHeadlessExecutionAndCompilation:
    """Verifies that app.py and UI modules compile cleanly and execute headless via AppTest."""

    def test_app_and_ui_modules_ast_and_bytecode_compilation(self):
        """Expected: app.py and all src/ui/*.py modules compile with zero syntax errors."""
        target_files = [APP_FILE] + list(UI_DIR.glob("*.py"))
        assert len(target_files) >= 7, f"Expected at least 7 UI files, found {len(target_files)}"

        for py_path in target_files:
            # 1. AST parse check
            with open(py_path, "r", encoding="utf-8") as f:
                code_content = f.read()
            tree = ast.parse(code_content, filename=str(py_path))
            assert tree is not None, f"Failed to parse AST for {py_path.name}"

            # 2. Bytecode compilation
            compiled = py_compile.compile(str(py_path), doraise=True)
            assert compiled is not None, f"Bytecode compilation failed for {py_path.name}"

    def test_streamlit_apptest_headless_initial_run(self):
        """Expected: AppTest executes app.py headless with 0 unhandled exceptions across all 5 tabs."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_FILE), default_timeout=60)
        at.run()

        # Zero unhandled exceptions
        assert len(at.exception) == 0, f"AppTest raised exceptions: {[e.value for e in at.exception]}"

        # 5 tabs rendered
        assert len(at.tabs) == 5, f"Expected 5 tabs, got {len(at.tabs)}"

        # Sidebar configuration controls present
        assert len(at.sidebar.radio) >= 2, f"Expected at least 2 sidebar radio widgets, got {len(at.sidebar.radio)}"

    def test_streamlit_apptest_currency_toggle_interaction(self):
        """Expected: AppTest dynamically switches currency radio to 'KRW (₩)' without exceptions."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_FILE), default_timeout=60)
        at.run()
        assert len(at.exception) == 0

        # Toggle currency radio to KRW
        currency_radio = at.sidebar.radio[0]
        assert "Display Currency" in currency_radio.label
        currency_radio.set_value("KRW (₩)")
        at.run()

        assert len(at.exception) == 0, f"Exceptions after KRW toggle: {[e.value for e in at.exception]}"

    def test_streamlit_apptest_tax_mode_toggle_interaction(self):
        """Expected: AppTest dynamically switches tax mode radio to 'Gross Pre-Tax' without exceptions."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(APP_FILE), default_timeout=60)
        at.run()
        assert len(at.exception) == 0

        # Toggle tax radio to Gross Pre-Tax
        tax_radio = at.sidebar.radio[1]
        assert "Tax Mode" in tax_radio.label
        tax_radio.set_value("Gross Pre-Tax")
        at.run()

        assert len(at.exception) == 0, f"Exceptions after Gross tax toggle: {[e.value for e in at.exception]}"


# =============================================================================
# Pillar 2: @st.cache_data Benchmark Loading & Simulation Performance
# =============================================================================
class TestCacheDataBenchmarkPerformance:
    """Verifies that @st.cache_data functions execute rapidly, without errors, and deterministically."""

    def test_load_market_data_speed_and_completeness(self):
        """Expected: load_market_data() returns complete benchmark and FX feeds in < 100ms on warm cache."""
        t0 = time.time()
        prices_df, fx_series = app.load_market_data()
        elapsed_cold = time.time() - t0

        assert prices_df is not None and not prices_df.empty
        assert fx_series is not None and not fx_series.empty

        # Date bound checks
        assert prices_df.index[0] <= pd.Timestamp(DEFAULT_START_DATE)
        assert fx_series.index[0] <= pd.Timestamp(DEFAULT_START_DATE)

        # Zero NaNs
        assert prices_df[("Close", "QQQ")].isna().sum() == 0
        assert prices_df[("Close", "SOXX")].isna().sum() == 0
        assert fx_series.isna().sum() == 0

        # Warm cache latency test (must be < 50ms)
        t1 = time.time()
        prices_warm, fx_warm = app.load_market_data()
        elapsed_warm = time.time() - t1

        assert elapsed_warm < 0.05, f"Warm cache took {elapsed_warm:.4f}s, expected < 0.05s"
        assert prices_warm.shape == prices_df.shape
        assert len(fx_warm) == len(fx_series)

    def test_run_baseline_simulations_caching_and_idempotency(self):
        """Expected: run_baseline_simulations() returns identical BacktestResults with instant warm cache retrieval."""
        t0 = time.time()
        sim_data = app.run_baseline_simulations()
        elapsed_1 = time.time() - t0

        required_keys = [
            "prices", "fx_series", "res_base", "res_enh",
            "qqq_nav_usd", "soxx_nav_usd", "qqq_nav_krw", "soxx_nav_krw",
        ]
        for k in required_keys:
            assert k in sim_data, f"Missing key in simulation data: {k}"

        res_enh: BacktestResult = sim_data["res_enh"]
        res_base: BacktestResult = sim_data["res_base"]

        # Enhanced strategy superiority sanity check
        assert res_enh.calmar_ratio_usd > res_base.calmar_ratio_usd, (
            f"Enhanced Calmar ({res_enh.calmar_ratio_usd:.3f}) should exceed Base ({res_base.calmar_ratio_usd:.3f})"
        )
        assert abs(res_enh.max_annual_mdd_usd) < abs(res_base.max_annual_mdd_usd), (
            f"Enhanced MDD ({res_enh.max_annual_mdd_usd:.1%}) should be less severe than Base ({res_base.max_annual_mdd_usd:.1%})"
        )

        # Second invocation: warm cache check
        t2 = time.time()
        sim_data_warm = app.run_baseline_simulations()
        elapsed_warm = time.time() - t2

        assert elapsed_warm < 0.05, f"Warm simulation retrieval took {elapsed_warm:.4f}s, expected < 0.05s"
        assert sim_data_warm["res_enh"].cagr_usd == res_enh.cagr_usd
        assert sim_data_warm["res_base"].cagr_usd == res_base.cagr_usd


# =============================================================================
# Pillar 3: Currency Toggle NAV Transformation (USD vs KRW)
# =============================================================================
class TestCurrencyToggleNAVTransformation:
    """Verifies that currency transformation between USD and KRW strictly preserves mathematical integrity."""

    def test_daily_nav_krw_equals_nav_usd_times_fx_rate(self):
        """Expected: For all dates t, NAV_KRW[t] == NAV_USD[t] * USDKRW[t] within floating precision."""
        sim_data = app.run_baseline_simulations()
        res_enh: BacktestResult = sim_data["res_enh"]
        fx_series: pd.Series = sim_data["fx_series"]

        nav_usd = res_enh.after_tax_nav_usd
        nav_krw = res_enh.after_tax_nav_krw
        reindexed_fx = fx_series.reindex(nav_usd.index).ffill()

        expected_krw = nav_usd * reindexed_fx
        pct_diff = np.abs((nav_krw - expected_krw) / expected_krw)

        max_err = float(pct_diff.max())
        assert max_err < 1e-4, f"Discrepancy in USD -> KRW transformation math: max error = {max_err:.6e}"

    def test_benchmark_nav_krw_initial_capital_equivalence(self):
        """Expected: Initial KRW NAV = $100,000 * starting USDKRW exchange rate."""
        sim_data = app.run_baseline_simulations()
        fx_series: pd.Series = sim_data["fx_series"]
        sim_idx = sim_data["res_enh"].daily_nav_usd.index
        init_fx = float(fx_series.reindex(sim_idx).ffill().iloc[0])

        assert sim_data["qqq_nav_usd"].iloc[0] == pytest.approx(100_000.0)
        assert sim_data["soxx_nav_usd"].iloc[0] == pytest.approx(100_000.0)

        expected_init_krw = 100_000.0 * init_fx
        assert sim_data["qqq_nav_krw"].iloc[0] == pytest.approx(expected_init_krw, rel=1e-3)
        assert sim_data["soxx_nav_krw"].iloc[0] == pytest.approx(expected_init_krw, rel=1e-3)

    def test_fx_drawdown_characteristics_between_currencies(self):
        """
        Adversarial probe:
        Examine empirical MDD relationship between USD and KRW.
        Because NAV_KRW = NAV_USD * USDKRW, currency exchange volatility interacts
        with asset price drawdowns, producing distinct intra-year drawdowns in KRW.
        """
        sim_data = app.run_baseline_simulations()
        res_enh: BacktestResult = sim_data["res_enh"]

        ann_usd = PerformanceMetrics.calculate_calendar_year_mdd(res_enh.after_tax_nav_usd)
        ann_krw = PerformanceMetrics.calculate_calendar_year_mdd(res_enh.after_tax_nav_krw)

        mdd_2008_usd = float(ann_usd[ann_usd["Year"] == 2008]["Annual_MDD"].values[0])
        mdd_2008_krw = float(ann_krw[ann_krw["Year"] == 2008]["Annual_MDD"].values[0])

        # Empirically, FX volatility creates distinct intra-year drawdown profiles:
        assert mdd_2008_usd < 0 and mdd_2008_krw < 0
        assert abs(mdd_2008_usd - mdd_2008_krw) > 0.01  # Distinct values (> 1% delta)


    def test_ui_currency_formatter_bounds_and_edge_cases(self):
        """Expected: fmt_currency formats USD ($) and KRW (₩) properly across magnitudes."""
        # USD formatting
        assert fmt_currency(0.0, "USD") == "$0.00"
        assert fmt_currency(1234.56, "USD") == "$1,234.56"
        assert fmt_currency(1_500_000.0, "USD") == "$1,500,000"
        assert fmt_currency(np.nan, "USD") == "-"

        # KRW formatting
        assert fmt_currency(0.0, "KRW") == "₩0"
        assert fmt_currency(50_000.0, "KRW") == "₩50,000"
        assert fmt_currency(250_000_000.0, "KRW") == "₩2.50억"
        assert fmt_currency(1_000_000_000.0, "KRW") == "₩10.00억"
        assert fmt_currency(np.nan, "KRW") == "-"


# =============================================================================
# Pillar 4: Tax Toggle & Annual 22% Capital Gains Deduction
# =============================================================================
class TestTaxToggleAndAnnualDeductionLogic:
    """Verifies that Korean overseas stock capital gains tax is debited annually and Gross >= Net."""

    def test_gross_nav_always_greater_than_or_equal_to_after_tax_nav(self):
        """Expected: gross_nav_usd[t] >= after_tax_nav_usd[t] for all dates t."""
        sim_data = app.run_baseline_simulations()
        res_enh: BacktestResult = sim_data["res_enh"]

        gross_usd = res_enh.gross_nav_usd
        after_tax_usd = res_enh.after_tax_nav_usd

        diff = gross_usd - after_tax_usd
        assert (diff >= -1e-6).all(), "Gross NAV must be strictly >= After-Tax NAV for all dates"

        # On inception day 0, tax paid is 0.0 -> gross == after_tax
        assert gross_usd.iloc[0] == pytest.approx(after_tax_usd.iloc[0], abs=1e-3)

        # After years of profitable trading, gross NAV must be strictly greater than net NAV
        assert gross_usd.iloc[-1] > after_tax_usd.iloc[-1]

    def test_korean_tax_engine_basic_deduction_boundary_conditions(self):
        """Expected: KoreanTaxEngine accurately applies 2.5M KRW deduction and 22% rate."""
        engine = KoreanTaxEngine(enabled=True)

        # Scenario 1: Net gain under basic deduction (2,000,000 KRW)
        engine.record_realized_trade(2023, gain_usd=1500.0, gain_krw=2_000_000.0)
        rec1 = engine.calculate_annual_tax(2023, year_end_fx=1300.0)
        assert rec1.taxable_base_krw == 0.0
        assert rec1.tax_krw == 0.0
        assert rec1.tax_usd == 0.0

        # Scenario 2: Net gain exactly at threshold + 1 KRW (2,500,001 KRW)
        engine_2 = KoreanTaxEngine(enabled=True)
        engine_2.record_realized_trade(2024, gain_usd=1900.0, gain_krw=2_500_001.0)
        rec2 = engine_2.calculate_annual_tax(2024, year_end_fx=1300.0)
        assert rec2.taxable_base_krw == pytest.approx(1.0)
        assert rec2.tax_krw == pytest.approx(0.22)

        # Scenario 3: Large gain (10,000,000 KRW)
        engine_3 = KoreanTaxEngine(enabled=True)
        engine_3.record_realized_trade(2025, gain_usd=7500.0, gain_krw=10_000_000.0)
        rec3 = engine_3.calculate_annual_tax(2025, year_end_fx=1300.0)
        # Taxable base = 10,000,000 - 2,500,000 = 7,500,000
        assert rec3.taxable_base_krw == pytest.approx(7_500_000.0)
        # Tax = 7,500,000 * 0.22 = 1,650,000 KRW
        assert rec3.tax_krw == pytest.approx(1_650_000.0)
        assert rec3.tax_usd == pytest.approx(1_650_000.0 / 1300.0)

    def test_annual_tax_records_completeness_and_settlement_timing(self):
        """Expected: annual_tax_records contains complete calendar year history from 2001 to present."""
        sim_data = app.run_baseline_simulations()
        res_enh: BacktestResult = sim_data["res_enh"]
        tax_records = res_enh.annual_tax_records

        assert not tax_records.empty
        assert "Year" in tax_records.columns
        assert "Tax_KRW" in tax_records.columns
        assert "Tax_USD" in tax_records.columns
        assert "Year_End_FX" in tax_records.columns

        years = set(tax_records["Year"])
        assert 2001 in years
        assert 2026 in years
        assert len(years) == 26


# =============================================================================
# Pillar 5: Live Simulation Lab Extreme Parameter Sliders
# =============================================================================
class TestSimulationExtremeSliderInputs:
    """Stress-tests the live simulation lab with extreme parameters."""

    @pytest.fixture(scope="class")
    def market_data(self):
        return app.load_market_data()

    def test_zero_cash_extreme_100pct_equity_allocation(self, market_data):
        """
        Adversarial probe:
        Configure 0% cash buffer: QQQ 50% + SOXX 30% + Turnaround 20% = 100% Equity.
        Expected: Backtest completes cleanly without zero-division or margin debt errors.
        """
        prices_df, fx_series = market_data

        params = EnhancedStrategyParameters(
            w_qqq_base=0.50,
            w_soxx_base=0.30,
            w_turnaround_max=0.20,
            w_cash_buffer=0.00,
            max_active_stocks=3,
        )
        strategy = EnhancedStrategy(params=params, prices_df=prices_df)
        engine = BacktestEngine(initial_capital=100_000.0)

        res = engine.run(
            strategy=strategy,
            prices_df=prices_df,
            fx_rates=fx_series,
            tax_enabled=True,
            start_date="2001-07-10",
        )

        assert not res.daily_nav_usd.empty
        assert (res.daily_nav_usd > 0).all()
        assert np.isfinite(res.cagr_usd)
        assert np.isfinite(res.calmar_ratio_usd)

    def test_extreme_stop_loss_and_take_profit_bounds(self, market_data):
        """
        Adversarial probe:
        Test outer slider limits:
        - Hard stop-loss at maximum -25% vs tightest -5%.
        - Take-profit at maximum +80% vs lowest +15%.
        """
        prices_df, fx_series = market_data

        for stop_l, take_p in [(-0.25, 0.80), (-0.05, 0.15)]:
            params = EnhancedStrategyParameters(
                w_qqq_base=0.40,
                w_soxx_base=0.30,
                w_turnaround_max=0.20,
                stop_loss_pct=stop_l,
                profit_target_pct=take_p,
            )
            strategy = EnhancedStrategy(params=params, prices_df=prices_df)
            engine = BacktestEngine(initial_capital=100_000.0)

            res = engine.run(
                strategy=strategy,
                prices_df=prices_df,
                fx_rates=fx_series,
                tax_enabled=True,
                start_date="2001-07-10",
            )

            assert (res.daily_nav_usd > 0).all()
            assert res.cagr_usd > 0.0
            assert -1.0 <= res.max_annual_mdd_usd <= 0.0

    def test_extreme_holding_periods_and_capacity_bounds(self, market_data):
        """
        Adversarial probe:
        Holding period: 8 weeks (40 days) vs 52 weeks (260 days).
        Capacity: 1 stock vs 5 stocks.
        """
        prices_df, fx_series = market_data

        for weeks, cap in [(8, 1), (52, 5)]:
            params = EnhancedStrategyParameters(
                w_qqq_base=0.40,
                w_soxx_base=0.30,
                w_turnaround_max=0.20,
                max_active_stocks=cap,
                max_holding_weeks=weeks,
                max_holding_days=weeks * 5,
            )
            strategy = EnhancedStrategy(params=params, prices_df=prices_df)
            engine = BacktestEngine(initial_capital=100_000.0, max_stock_capacity=cap)

            res = engine.run(
                strategy=strategy,
                prices_df=prices_df,
                fx_rates=fx_series,
                tax_enabled=True,
                start_date="2001-07-10",
            )

            # Max stock holdings must never exceed cap
            if not res.allocation_history.empty:
                stock_cols = [c for c in res.allocation_history.columns if c not in ["QQQ", "SOXX", "Cash"]]
                active_count = (res.allocation_history[stock_cols] > 0.0).sum(axis=1)
                assert (active_count <= cap).all(), f"Holding count exceeded capacity {cap}"

    def test_regime_sma_and_momentum_window_extremes(self, market_data):
        """
        Adversarial probe:
        SMA window: 50 days (fast) vs 250 days (slow).
        Momentum lookback: 20 days (fast) vs 126 days (semi-annual).
        """
        prices_df, fx_series = market_data

        for sma_w, mom_w in [(50, 20), (250, 126)]:
            params = EnhancedStrategyParameters(
                sma_trend_window=sma_w,
                momentum_window=mom_w,
            )
            strategy = EnhancedStrategy(params=params, prices_df=prices_df)
            engine = BacktestEngine(initial_capital=100_000.0)

            res = engine.run(
                strategy=strategy,
                prices_df=prices_df,
                fx_rates=fx_series,
                tax_enabled=True,
                start_date="2001-07-10",
            )

            assert not res.daily_nav_usd.isna().any()
            assert res.calmar_ratio_usd > 0.0

    def test_slider_weights_exceeding_unity_graceful_handling(self):
        """
        Adversarial probe:
        If slider inputs sum to > 1.0 (e.g., QQQ 70% + SOXX 70% + Turnaround 30% = 170%),
        StrategyParameters raises ValueError, and the UI try/except catches it cleanly.
        """
        with pytest.raises(ValueError) as excinfo:
            StrategyParameters(
                w_qqq_base=0.70,
                w_soxx_base=0.70,
                w_turnaround_max=0.30,
            )
        assert "Total base weights exceed 1.0" in str(excinfo.value)

    def test_kpi_delta_display_robustness(self):
        """Expected: delta formatters handle positive, negative, and zero deltas without crashing."""
        for delta in [+5.25, -3.10, 0.0]:
            sub_str = f"Δ {delta:+.2f}% vs Enhanced"
            sub_type = "pos" if delta >= 0 else "neg"
            # render_metric_card should execute without error
            card_html = render_metric_card("Test Label", "100.0%", sub_str=sub_str, sub_type=sub_type)
            # Function internally calls st.markdown; in testing without Streamlit runtime it is captured or safely executed
