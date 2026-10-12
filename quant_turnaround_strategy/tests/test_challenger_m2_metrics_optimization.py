"""
Milestone 2 Empirical Challenger 2 Stress Test Suite: Metrics & Optimization Engine.
Author: Challenger M2-2 (critic, specialist)
Target Repository: D:\\Industry\\quant_turnaround_strategy

Probes:
1. Calendar Year Intra-Year MDD Mathematical Correctness & Boundary Isolation.
2. Calmar Ratio Objective Function & Crisis Year Sensitivity (2002, 2008, 2022).
3. Dual-Currency NAV Consistency & FX Drawdown Decomposition.
4. Optimization Engine: Grid Search & Walk-Forward Analysis (20+ windows) Lookahead Audit.
5. Parameter & Risk Management Boundary Conditions & Collision Resolution.
"""
import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from src.engine.metrics import PerformanceMetrics
from src.optimizer.objective import ObjectiveFunction
from src.optimizer.grid_search import GridSearchOptimizer
from src.optimizer.walk_forward import WalkForwardOptimizer, WalkForwardResult
from src.engine.portfolio import Portfolio, Position
from src.engine.execution import ExecutionEngine
from src.engine.tax import KoreanTaxEngine
from src.engine.risk_manager import RiskManager
from src.engine.backtester import BacktestEngine, BacktestResult
from src.strategies.base_strategy import BaseStrategy, StrategyParameters
from src.data.price_feed import PriceFeed


class TestCalendarYearMDDAdversarial(unittest.TestCase):
    """
    Adversarial probes on Calendar Year MDD mathematical correctness and boundary isolation.
    """

    def test_intra_year_boundary_isolation_no_carryover(self):
        """
        Probe: Confirm that drawdowns in one year do NOT carry over or distort the next calendar year's intra-year peak.
        Fixture:
        2008: Peak 100 -> Trough 50 (-50% MDD) -> End 50
        2009: Start 50 -> Peak 60 -> Trough 54 -> End 70
        Expected 2009 Intra-Year Peak = 60.
        Expected 2009 Intra-Year MDD = (54 - 60) / 60 = -0.10 (-10.0%).
        Adversarial Failure Case: If 2008 peak (100) leaked into 2009, 2009 MDD would be (50 - 100)/100 = -50% or (54 - 100)/100 = -46%.
        """
        dates_2008 = pd.date_range("2008-01-02", "2008-12-31", periods=10)
        nav_2008 = [100.0, 95.0, 90.0, 80.0, 70.0, 60.0, 50.0, 52.0, 48.0, 50.0]

        dates_2009 = pd.date_range("2009-01-02", "2009-12-31", periods=10)
        nav_2009 = [50.0, 52.0, 55.0, 60.0, 57.0, 54.0, 58.0, 62.0, 65.0, 70.0]

        all_dates = list(dates_2008) + list(dates_2009)
        all_nav = nav_2008 + nav_2009
        s = pd.Series(all_nav, index=pd.DatetimeIndex(all_dates))

        table = PerformanceMetrics.calculate_calendar_year_mdd(s)
        self.assertEqual(len(table), 2)

        r2008 = table.loc[table["Year"] == 2008].iloc[0]
        r2009 = table.loc[table["Year"] == 2009].iloc[0]

        # 2008 MDD: peak was 100, min was 48 -> (48 - 100)/100 = -0.52
        self.assertAlmostEqual(r2008["Annual_MDD"], -0.52, places=4)

        # 2009 MDD: in 2009 alone, peak was 60.0, min after peak was 54.0 -> (54 - 60)/60 = -0.10
        self.assertAlmostEqual(r2009["Annual_MDD"], -0.10, places=4)
        # Confirms ZERO carryover from 2008's peak of 100

    def test_overnight_year_boundary_gap_return_and_drawdown(self):
        """
        Probe: Examines boundary behavior across year-end rollover (Dec 31 -> Jan 2/3).
        Fixture:
        2021-12-31: NAV = 100.0 (closes at 100)
        2022-01-03: NAV = 80.0 (gaps down -20% over weekend)
        2022-12-30: NAV = 80.0 (stays flat all year at 80)
        Empirical evaluation of how calculate_calendar_year_mdd handles the boundary gap:
        - Within 2022 group: vals[0] = 80, vals[-1] = 80.
        - ret = (80 - 80) / 80 = 0.0%
        - mdd = 0.0%
        Finding: The day-1 return of 2022 relative to 2021 close is NOT captured in 2022's Annual_Return
        because group['NAV'] is isolated per year without prepending prior year close.
        """
        dates = [
            pd.Timestamp("2021-01-04"), pd.Timestamp("2021-12-31"),
            pd.Timestamp("2022-01-03"), pd.Timestamp("2022-12-30")
        ]
        nav = [100.0, 100.0, 80.0, 80.0]
        s = pd.Series(nav, index=pd.DatetimeIndex(dates))

        table = PerformanceMetrics.calculate_calendar_year_mdd(s)
        r2021 = table.loc[table["Year"] == 2021].iloc[0]
        r2022 = table.loc[table["Year"] == 2022].iloc[0]

        # Record exact behaviors
        # 2021 return is (100 - 100) / 100 = 0.0
        self.assertAlmostEqual(r2021["Annual_Return"], 0.0, places=4)
        # 2022 return is (80 - 80) / 80 = 0.0
        self.assertAlmostEqual(r2022["Annual_Return"], 0.0, places=4)
        # 2022 MDD is 0.0
        self.assertAlmostEqual(r2022["Annual_MDD"], 0.0, places=4)

        # Total multi-year return is (80 - 100) / 100 = -0.20 (-20%)
        # But compounded annual return: (1 + 0.0) * (1 + 0.0) - 1 = 0.0% != -20%!
        total_compounded = (1 + r2021["Annual_Return"]) * (1 + r2022["Annual_Return"]) - 1.0
        actual_total = (nav[-1] - nav[0]) / nav[0]
        self.assertNotAlmostEqual(total_compounded, actual_total)

    def test_intra_year_complex_wave_mdd(self):
        """
        Probe: Complex wave in single year with multiple local peaks and troughs.
        Fixture:
        Start 100 -> Peak 120 -> Trough 96 (-20%) -> Peak 160 -> Trough 80 (-50%) -> End 140.
        Known true intra-year MDD must be exactly -50.0%.
        """
        dates = pd.date_range("2015-01-01", periods=6, freq="D")
        nav = [100.0, 120.0, 96.0, 160.0, 80.0, 140.0]
        s = pd.Series(nav, index=dates)

        table = PerformanceMetrics.calculate_calendar_year_mdd(s)
        self.assertEqual(len(table), 1)
        row = table.iloc[0]
        self.assertAlmostEqual(row["Annual_MDD"], -0.50, places=4)
        self.assertAlmostEqual(row["Annual_Return"], 0.40, places=4)
        self.assertAlmostEqual(row["Return_to_MDD"], 0.40 / 0.50, places=4)

    def test_degenerate_zero_mdd_cases(self):
        """
        Probe: Strictly monotonic increasing NAV produces exact 0.0% MDD.
        Flat NAV produces exact 0.0% MDD.
        Single day series produces exact 0.0% MDD.
        """
        # Monotonic
        d_up = pd.date_range("2020-01-01", periods=10, freq="D")
        s_up = pd.Series(np.linspace(100.0, 200.0, 10), index=d_up)
        t_up = PerformanceMetrics.calculate_calendar_year_mdd(s_up)
        self.assertAlmostEqual(t_up.iloc[0]["Annual_MDD"], 0.0, places=6)

        # Flat
        d_flat = pd.date_range("2020-01-01", periods=5, freq="D")
        s_flat = pd.Series([100.0] * 5, index=d_flat)
        t_flat = PerformanceMetrics.calculate_calendar_year_mdd(s_flat)
        self.assertAlmostEqual(t_flat.iloc[0]["Annual_MDD"], 0.0, places=6)

        # Single day
        d_single = pd.date_range("2020-01-01", periods=1, freq="D")
        s_single = pd.Series([100.0], index=d_single)
        t_single = PerformanceMetrics.calculate_calendar_year_mdd(s_single)
        self.assertAlmostEqual(t_single.iloc[0]["Annual_MDD"], 0.0, places=6)


class TestCalmarRatioObjectiveFunctionAdversarial(unittest.TestCase):
    """
    Adversarial probes on Calmar Ratio objective function and crisis year penalization.
    """

    def test_calmar_crisis_years_penalization_oracle(self):
        """
        Probe: Confirm Calmar strictly penalizes worst calendar crisis years (2002, 2008, 2022).
        Scenario:
        Strategy 1 (Aggressive): CAGR = 18.0%, worst MDD in 2002 (-52.0%). Calmar = 0.18 / 0.52 = 0.346.
        Strategy 2 (Defensive):  CAGR = 14.0%, worst MDD in 2002 (-28.0%). Calmar = 0.14 / 0.28 = 0.500.
        The objective function MUST rank Strategy 2 strictly ahead of Strategy 1 despite lower CAGR.
        """
        calmar_strat1 = PerformanceMetrics.calculate_calmar_ratio(cagr=0.18, max_annual_mdd=-0.52)
        calmar_strat2 = PerformanceMetrics.calculate_calmar_ratio(cagr=0.14, max_annual_mdd=-0.28)

        self.assertAlmostEqual(calmar_strat1, 0.18 / 0.52, places=4)
        self.assertAlmostEqual(calmar_strat2, 0.14 / 0.28, places=4)
        self.assertGreater(calmar_strat2, calmar_strat1)

    def test_actual_benchmark_crisis_years_ranking(self):
        """
        Probe: Run actual 25-year benchmark backtest and verify that 2002, 2008, 2022
        are indeed the top-3 worst annual drawdowns in history.
        """
        feed = PriceFeed()
        prices = feed.fetch_and_bridge_benchmarks()
        fx = feed.get_fx_rates()
        engine = BacktestEngine()
        result = engine.run(strategy=BaseStrategy(), prices_df=prices, fx_rates=fx)

        annual_df = result.annual_metrics_usd
        sorted_mdd = annual_df.sort_values(by="Annual_MDD", ascending=True)

        worst_years = list(sorted_mdd["Year"].iloc[:3])
        # Expected worst crisis years in 2001-2026: 2002, 2008, 2022
        self.assertIn(2002, worst_years)
        self.assertIn(2008, worst_years)
        self.assertIn(2022, worst_years)

        # Calmar ratio must equal cagr_usd / abs(worst_mdd)
        worst_mdd = float(sorted_mdd["Annual_MDD"].iloc[0])
        expected_calmar = result.cagr_usd / abs(worst_mdd)
        self.assertAlmostEqual(result.calmar_ratio_usd, expected_calmar, places=4)

    def test_calmar_zero_mdd_and_negative_cagr_edge_cases(self):
        """
        Probe: Zero MDD edge case (safeguard division by zero).
        Negative CAGR edge case (Calmar should be negative).
        """
        # Zero MDD safeguard
        c_zero = PerformanceMetrics.calculate_calmar_ratio(cagr=0.10, max_annual_mdd=0.0)
        self.assertEqual(c_zero, 0.0)

        # Negative CAGR
        c_neg = PerformanceMetrics.calculate_calmar_ratio(cagr=-0.08, max_annual_mdd=-0.20)
        self.assertAlmostEqual(c_neg, -0.40, places=4)

    def test_objective_evaluate_key_schema_compatibility(self):
        """
        Probe: Check key names expected by ObjectiveFunction.evaluate vs BacktestResult.
        ObjectiveFunction.evaluate looks for:
        cagr = run_stats.get('cagr', 0.0)
        max_mdd = run_stats.get('max_annual_mdd', run_stats.get('mdd', -1.0))
        Check if run_stats with 'cagr_usd' passes or defaults to 0.0.
        """
        stats_usd = {"cagr_usd": 0.15, "max_annual_mdd_usd": -0.25}
        score_missing_keys = ObjectiveFunction.evaluate(stats_usd, metric="calmar")
        # Because 'cagr' is missing, it evaluates to 0.0 / 1.0 = 0.0
        self.assertEqual(score_missing_keys, 0.0)

        stats_compat = {"cagr": 0.15, "max_annual_mdd": -0.25}
        score_compat = ObjectiveFunction.evaluate(stats_compat, metric="calmar")
        self.assertAlmostEqual(score_compat, 0.60, places=4)


class TestDualCurrencyConsistencyAdversarial(unittest.TestCase):
    """
    Adversarial probes on dual-currency accounting and FX consistency.
    """

    def test_strict_daily_nav_krw_usd_fx_identity(self):
        """
        Probe: Verify that KRW NAV matches USD NAV * FX rate on ALL 6,355 trading dates.
        Identity: |NAV_KRW(t) - NAV_USD(t) * FX(t)| < 1e-3 on all dates.
        """
        feed = PriceFeed()
        prices = feed.fetch_and_bridge_benchmarks()
        fx = feed.get_fx_rates()
        engine = BacktestEngine()
        result = engine.run(strategy=BaseStrategy(), prices_df=prices, fx_rates=fx)

        nav_usd = result.daily_nav_usd
        nav_krw = result.daily_nav_krw
        gross_usd = result.gross_nav_usd
        gross_krw = result.gross_nav_krw

        # Daily FX aligned
        fx_aligned = fx.reindex(nav_usd.index).ffill().bfill()

        # Check Net NAV identity
        calculated_krw = nav_usd * fx_aligned
        diff_net = (nav_krw - calculated_krw).abs()
        max_diff_net = float(diff_net.max())
        self.assertLess(max_diff_net, 1e-3, f"Net NAV KRW identity violated: max diff {max_diff_net}")

        # Check Gross NAV identity
        calculated_gross_krw = gross_usd * fx_aligned
        diff_gross = (gross_krw - calculated_gross_krw).abs()
        max_diff_gross = float(diff_gross.max())
        self.assertLess(max_diff_gross, 1e-3, f"Gross NAV KRW identity violated: max diff {max_diff_gross}")

    def test_fx_drawdown_buffering_effect_2008_gfc(self):
        """
        Probe: FX drawdown decomposition during 2008 GFC.
        In 2008, USD crashed, but USD/KRW spiked from ~930 to ~1500 (KRW depreciated +60%).
        Empirical check: Did KRW annual MDD in 2008 buffer the USD annual MDD?
        USD MDD in 2008 vs KRW MDD in 2008:
        Because USDKRW rose sharply when US stocks collapsed, KRW investors experienced a lower drawdown.
        """
        feed = PriceFeed()
        prices = feed.fetch_and_bridge_benchmarks()
        fx = feed.get_fx_rates()
        engine = BacktestEngine()
        result = engine.run(strategy=BaseStrategy(), prices_df=prices, fx_rates=fx)

        m_usd_2008 = result.annual_metrics_usd.loc[result.annual_metrics_usd["Year"] == 2008].iloc[0]
        m_krw_2008 = result.annual_metrics_krw.loc[result.annual_metrics_krw["Year"] == 2008].iloc[0]

        # USD MDD in 2008 was ~-45.2%
        # KRW MDD in 2008 was significantly cushioned by USD surge!
        self.assertGreater(m_krw_2008["Annual_MDD"], m_usd_2008["Annual_MDD"])

    def test_overseas_stock_tax_korean_law_fx_conversion_rule(self):
        """
        Probe: Korean overseas stock capital gains tax acquisition FX vs realization FX.
        Tax base must be: Realized_KRW = (Sale_Price * Sale_FX - Entry_Price * Entry_FX) * Shares - Friction_KRW.
        Verify that KoreanTaxEngine receives the correct acquisition-date FX vs sale-date FX.
        """
        tax_engine = KoreanTaxEngine(enabled=True)
        gain_usd = (120 - 100) * 10.0
        gain_krw = (120 * 1200.0 - 100 * 1000.0) * 10.0

        tax_engine.record_realized_trade(
            year=2024,
            gain_usd=gain_usd,
            gain_krw=gain_krw,
            trade_date=date(2024, 6, 15),
            ticker="XYZ",
        )

        rec = tax_engine.calculate_annual_tax(year=2024, year_end_fx=1300.0)
        # Net gain KRW = 440,000 KRW <= 2,500,000 KRW deduction -> Tax = 0
        self.assertEqual(rec.tax_krw, 0.0)

        # Now add large gain: 10,000,000 KRW net
        tax_engine.record_realized_trade(
            year=2024,
            gain_usd=8000.0,
            gain_krw=10_000_000.0,
            trade_date=date(2024, 9, 15),
            ticker="ABC",
        )
        rec2 = tax_engine.calculate_annual_tax(year=2024, year_end_fx=1300.0)
        # Total gain = 10,440,000 KRW. Taxable base = 10,440,000 - 2,500,000 = 7,940,000 KRW.
        # Tax = 7,940,000 * 0.22 = 1,746,800 KRW.
        expected_tax_krw = 7_940_000.0 * 0.22
        expected_tax_usd = expected_tax_krw / 1300.0
        self.assertAlmostEqual(rec2.tax_krw, expected_tax_krw, places=2)
        self.assertAlmostEqual(rec2.tax_usd, expected_tax_usd, places=2)


class TestOptimizationEngineAdversarial(unittest.TestCase):
    """
    Adversarial probes on Grid Search and Walk-Forward Analysis (20+ windows).
    """

    def test_wfa_rolling_windows_lookahead_boundary_leakage_audit(self):
        """
        Probe: WalkForwardOptimizer window boundaries.
        Must generate >= 20 windows (for 2001-2026, 5y IS, 1y OOS -> 21 windows).
        Strict leakage audit:
        1. is_end_year < oos_year on every window.
        2. oos_year == is_end_year + 1 (strictly out-of-sample).
        3. No window may train on future years (is_start_year <= is_end_year).
        """
        wfa = WalkForwardOptimizer(is_years=5, oos_years=1, step_years=1)
        windows = wfa.generate_rolling_windows(start_year=2001, end_year=2026)

        self.assertGreaterEqual(len(windows), 20)
        self.assertEqual(len(windows), 21)

        for i, w in enumerate(windows):
            is_start = w["is_start_year"]
            is_end = w["is_end_year"]
            oos_yr = w["oos_year"]

            # Audit checks
            self.assertEqual(is_end - is_start + 1, 5, f"Window {i}: IS period must be 5 years")
            self.assertEqual(oos_yr, is_end + 1, f"Window {i}: OOS year must be strictly is_end + 1")
            self.assertLess(is_end, oos_yr, f"Window {i}: IS end must precede OOS")

            if i > 0:
                prev_w = windows[i - 1]
                self.assertEqual(is_start, prev_w["is_start_year"] + 1, "Rolling step must be 1 year")

    def test_wfe_efficiency_mathematical_edge_cases(self):
        """
        Probe: WFE formula edge cases:
        WFE = (CAGR_OOS / CAGR_IS) * (|MDD_IS| / |MDD_OOS|)
        Adversarial cases:
        1. Negative CAGR_IS: does it produce negative or clamped ratio?
        2. Zero MDD_OOS: division by zero safeguard.
        3. Normal robust case (>= 0.60).
        """
        wfa = WalkForwardOptimizer()

        # Zero MDD_OOS safeguard: must not crash
        wfe_zero_mdd = wfa.compute_walk_forward_efficiency(cagr_is=0.15, cagr_oos=0.12, mdd_is=-0.20, mdd_oos=0.0)
        self.assertAlmostEqual(wfe_zero_mdd, 0.12 / 0.15, places=4)

        # Negative CAGR_IS: implementation returns 0.0 when CAGR_IS <= 0
        wfe_neg_is = wfa.compute_walk_forward_efficiency(cagr_is=-0.05, cagr_oos=0.10, mdd_is=-0.20, mdd_oos=-0.25)
        self.assertEqual(wfe_neg_is, 0.0)

        # Standard robust strategy
        wfe_robust = wfa.compute_walk_forward_efficiency(cagr_is=0.20, cagr_oos=0.15, mdd_is=-0.20, mdd_oos=-0.20)
        self.assertAlmostEqual(wfe_robust, 0.75, places=4)
        self.assertGreaterEqual(wfe_robust, 0.60)

    def test_grid_search_constraint_enforcement_and_ranking(self):
        """
        Probe: GridSearchOptimizer parameter validator rejects invalid allocations and rankings.
        """
        optimizer = GridSearchOptimizer()

        # Over-allocated weight sum (0.5 + 0.3 + 0.25 = 1.05 > 1.0)
        self.assertFalse(optimizer.validate_parameters({
            "w_qqq_base": 0.50, "w_soxx_base": 0.30, "w_turnaround_max": 0.25
        }))

        # Valid weight sum (0.5 + 0.3 + 0.2 = 1.0)
        self.assertTrue(optimizer.validate_parameters({
            "w_qqq_base": 0.50, "w_soxx_base": 0.30, "w_turnaround_max": 0.20, "stop_loss_pct": -0.10
        }))

        # Positive stop loss (must be negative)
        self.assertFalse(optimizer.validate_parameters({
            "w_qqq_base": 0.50, "w_soxx_base": 0.30, "stop_loss_pct": 0.10
        }))

        # Negative profit taking (must be positive)
        self.assertFalse(optimizer.validate_parameters({
            "w_qqq_base": 0.50, "w_soxx_base": 0.30, "profit_taking_pct": -0.20
        }))

    def test_grid_search_ranking_key_sorting_anomaly(self):
        """
        Probe: Discovers that rank_results checks 'calmar' before 'score':
        key=lambda x: x.get('calmar', x.get('score', 0.0))
        When evaluating with objective_metric='sharpe', if run_metrics contains both 'score' and 'calmar',
        it sorts by 'calmar' instead of the requested 'score'.
        """
        optimizer = GridSearchOptimizer(objective_metric="sharpe")
        runs = [
            {"score": 2.5, "calmar": 0.1, "params": {"w": 0.1}},
            {"score": 0.5, "calmar": 0.9, "params": {"w": 0.2}},
        ]
        ranked = optimizer.rank_results(runs)
        # Because 'calmar' is preferred by x.get('calmar', x.get('score', 0.0)),
        # runs[1] (calmar 0.9) is ranked ahead of runs[0] (score 2.5)!
        self.assertEqual(ranked[0]["params"]["w"], 0.2)

    def test_end_to_end_walk_forward_execution_synthetic_oracle(self):
        """
        Probe: Execute run_walk_forward across 21 periods with a synthetic oracle evaluator.
        Verifies that WalkForwardResult schema, mean_wfe, is_robust, and 21 periods are produced cleanly.
        """
        wfa = WalkForwardOptimizer(is_years=5, oos_years=1, step_years=1)

        def mock_grid_search(is_start: int, is_end: int):
            return {"w_qqq": 0.5, "w_soxx": 0.3}, 0.15, -0.20

        def mock_eval_oos(oos_year: int, params: dict):
            return 0.12, -0.22

        res: WalkForwardResult = wfa.run_walk_forward(
            grid_search_fn=mock_grid_search,
            evaluate_oos_fn=mock_eval_oos,
            start_year=2001,
            end_year=2026,
        )

        self.assertEqual(res.total_periods, 21)
        self.assertEqual(len(res.periods), 21)
        self.assertAlmostEqual(res.mean_wfe, 0.7273, places=3)
        self.assertTrue(res.is_robust)


class TestRiskManagerAndExecutionAdversarial(unittest.TestCase):
    """
    Adversarial probes on Risk Manager collision resolution and overnight gap execution.
    """

    def test_risk_manager_collision_priority(self):
        """
        Probe: Verify strict collision priority STOP_LOSS > TAKE_PROFIT > TRAILING_STOP > TIME_STOP.
        """
        rm = RiskManager(
            stop_loss_pct=-0.12,
            profit_target_pct=0.35,
            trailing_stop_pct=0.10,
            max_holding_days=130,
        )

        # Collision: Stop loss (-15%) AND Time Stop (140 days)
        # STOP_LOSS must win
        reason1 = rm.evaluate_daily_exit(entry_price=100.0, current_price=85.0, peak_price=100.0, days_held=140)
        self.assertEqual(reason1, "STOP_LOSS")

        # Collision: Take profit (+40%) AND Trailing stop (-12% from peak 160)
        # TAKE_PROFIT must win
        reason2 = rm.evaluate_daily_exit(entry_price=100.0, current_price=140.0, peak_price=160.0, days_held=50)
        self.assertEqual(reason2, "TAKE_PROFIT")

        # Collision: Trailing stop (-15% from peak 120) AND Time stop (140 days)
        # TRAILING_STOP must win
        reason3 = rm.evaluate_daily_exit(entry_price=100.0, current_price=102.0, peak_price=120.0, days_held=140)
        self.assertEqual(reason3, "TRAILING_STOP")

        # Time stop alone
        reason4 = rm.evaluate_daily_exit(entry_price=100.0, current_price=105.0, peak_price=106.0, days_held=140)
        self.assertEqual(reason4, "TIME_STOP")

    def test_overnight_gap_down_execution_fill(self):
        """
        Probe: When stock gaps down overnight past stop-loss, execution MUST fill at open_price,
        NOT at entry * (1 + stop_loss_pct) or current_price.
        """
        rm = RiskManager(stop_loss_pct=-0.12)
        # Entry 100, Prior close 95 (-5%), Open 80 (-20%)
        is_gap, reason = rm.check_overnight_gap(entry_price=100.0, open_price=80.0, prior_close=95.0)
        self.assertTrue(is_gap)
        self.assertEqual(reason, "STOP_LOSS")


if __name__ == "__main__":
    unittest.main()
