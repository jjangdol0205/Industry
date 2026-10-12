"""
Milestone 2 Empirical Challenger Stress Test Suite.
Author: Challenger M2-1 (critic, specialist)
Target Repository: D:\\Industry\\quant_turnaround_strategy

Adversarially probes:
1. Portfolio Weight Invariant: sum(w_i) + w_cash == 1.0 +/- 1e-6 on every trading day from 2001-07-10 to present.
2. Korean Tax Math & Year-End Deduction:
   - Net loss: tax == 0 KRW
   - Net gain < 2.5M KRW: tax == 0 KRW
   - Net gain == 10M KRW: tax == 1.65M KRW (22% on 7.5M KRW taxable base)
   - Deduction from portfolio cash at calendar year-end.
3. Gap-Down Execution:
   - Extreme overnight price crash (-25% gap down).
   - Assert fill at open price with slippage penalty, not at naive stop threshold.
4. Micro-Turnover Prevention:
   - Rebalance dead-zone (< 1.0% allocation delta) strictly suppresses wasteful rebalance trades.
"""
import sys
from datetime import date
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

# Add repo to sys.path
REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from src.data.price_feed import PriceFeed
from src.engine.portfolio import Portfolio, Position
from src.engine.execution import ExecutionEngine, ExecutionResult
from src.engine.tax import KoreanTaxEngine, AnnualTaxRecord
from src.engine.risk_manager import RiskManager
from src.engine.backtester import BacktestEngine, BacktestResult
from src.strategies.base_strategy import BaseStrategy, StrategyParameters


# =====================================================================
# 1. PORTFOLIO WEIGHT INVARIANT
# =====================================================================
class TestPortfolioWeightInvariant:
    """Probes the fundamental accounting invariant: sum(w_i) + w_cash == 1.0 +/- 1e-6."""

    def test_weight_sum_invariant_25_year_benchmark(self):
        """
        Runs real 25-year benchmark backtest from 2001-07-10 to present.
        Asserts sum(w_i) + w_cash == 1.0 +/- 1e-6 on EVERY single trading day.
        """
        feed = PriceFeed()
        prices = feed.fetch_and_bridge_benchmarks()
        fx = feed.get_fx_rates()
        engine = BacktestEngine(initial_capital=100_000.0)
        strategy = BaseStrategy()

        res = engine.run(strategy=strategy, prices_df=prices, fx_rates=fx)
        alloc = res.allocation_history
        assert not alloc.empty, "Allocation history must not be empty"

        daily_sums = alloc.sum(axis=1)
        deviations = np.abs(daily_sums - 1.0)
        max_dev = float(deviations.max())

        # Invariant assertion
        assert max_dev <= 1e-6, f"Portfolio weight sum invariant violated! Max deviation: {max_dev}"
        assert len(alloc) >= 6350, f"Expected full 25-year timeline (6,350+ days), got {len(alloc)}"

    def test_weight_sum_invariant_with_turnaround_stocks(self):
        """
        Runs backtest with simulated turnaround stocks entering, fluctuating, and exiting.
        Asserts invariant holds on every day across asset purchases, sales, and interest accruals.
        """
        dates = pd.date_range("2001-07-10", "2003-12-31", freq="B")
        n = len(dates)
        np.random.seed(42)

        qqq_p = 40.0 * np.cumprod(1 + np.random.normal(0.0003, 0.012, n))
        soxx_p = 25.0 * np.cumprod(1 + np.random.normal(0.0004, 0.018, n))
        stk1_p = 15.0 * np.cumprod(1 + np.random.normal(0.0002, 0.025, n))
        stk2_p = 30.0 * np.cumprod(1 + np.random.normal(-0.0001, 0.030, n))

        df = pd.DataFrame({
            ("Close", "QQQ"): qqq_p,
            ("Open", "QQQ"): qqq_p * 1.001,
            ("Close", "SOXX"): soxx_p,
            ("Open", "SOXX"): soxx_p * 1.001,
            ("Close", "STK1"): stk1_p,
            ("Open", "STK1"): stk1_p * 1.002,
            ("Close", "STK2"): stk2_p,
            ("Open", "STK2"): stk2_p * 0.998,
        }, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)
        fx = pd.Series(np.linspace(1200.0, 1300.0, n), index=dates)

        # Inject candidates on select Fridays
        fridays = dates[dates.dayofweek == 4]
        cands = {fridays[0].date(): "STK1", fridays[2].date(): "STK2"}

        engine = BacktestEngine(initial_capital=100_000.0)
        strategy = BaseStrategy(StrategyParameters(
            w_qqq_base=0.45,
            w_soxx_base=0.25,
            w_turnaround_max=0.30,
            turnaround_idle_policy="cash_buffer",
        ))

        res = engine.run(strategy=strategy, prices_df=df, candidate_selections=cands, fx_rates=fx)
        alloc = res.allocation_history
        daily_sums = alloc.sum(axis=1)
        deviations = np.abs(daily_sums - 1.0)
        max_dev = float(deviations.max())

        assert max_dev <= 1e-6, f"Weight invariant failed with turnaround stocks! Max dev: {max_dev}"

    def test_portfolio_class_target_weights_exact_sum(self):
        """
        Unit test on Portfolio.compute_target_weights:
        Tests all turnaround stock counts k in [0, 1, 2, 3] under both idle policies.
        Asserts sum == 1.0 exactly.
        """
        p = Portfolio(initial_capital=100_000.0, max_stock_capacity=3)

        for policy in ["cash_buffer", "etf_sweep"]:
            for k in range(4):
                dummy_stocks = [f"STK_{i}" for i in range(k)]
                weights = p.compute_target_weights(
                    base_qqq=0.50,
                    base_soxx=0.30,
                    max_turnaround_weight=0.20,
                    active_turnaround_tickers=dummy_stocks,
                    idle_policy=policy,
                )
                total_w = sum(weights.values())
                assert pytest.approx(total_w, abs=1e-9) == 1.0, (
                    f"Policy {policy} with {k} stocks sum is {total_w} != 1.0"
                )


# =====================================================================
# 2. KOREAN TAX MATH & YEAR-END CASH DEDUCTION
# =====================================================================
class TestKoreanTaxMathAndCashDeduction:
    """Probes Korean overseas stock capital gains tax mathematics and portfolio deductions."""

    def test_tax_math_net_loss_zero_tax(self):
        """Net loss year (e.g. -5,000,000 KRW): Tax must be exactly 0 KRW."""
        engine = KoreanTaxEngine(enabled=True)
        engine.record_realized_trade(2021, gain_usd=-4166.67, gain_krw=-5_000_000.0)
        rec = engine.calculate_annual_tax(year=2021, year_end_fx=1200.0)

        assert rec.net_realized_gain_krw == -5_000_000.0
        assert rec.taxable_base_krw == 0.0
        assert rec.tax_krw == 0.0
        assert rec.tax_usd == 0.0

    def test_tax_math_net_gain_under_2_5m_zero_tax(self):
        """Net gain < 2.5M KRW (e.g. 2,000,000 KRW): Tax must be exactly 0 KRW."""
        engine = KoreanTaxEngine(enabled=True)
        engine.record_realized_trade(2021, gain_usd=1666.67, gain_krw=2_000_000.0)
        rec = engine.calculate_annual_tax(year=2021, year_end_fx=1200.0)

        assert rec.net_realized_gain_krw == 2_000_000.0
        assert rec.taxable_base_krw == 0.0
        assert rec.tax_krw == 0.0
        assert rec.tax_usd == 0.0

    def test_tax_math_net_gain_10m_exact_1_65m_tax(self):
        """
        Net gain == 10,000,000 KRW:
        Taxable base = 10,000,000 - 2,500,000 = 7,500,000 KRW.
        Tax = 7,500,000 * 0.22 = 1,650,000 KRW (1.65M KRW).
        At FX = 1200.0, Tax USD = 1,650,000 / 1200 = 1,375.0 USD.
        """
        engine = KoreanTaxEngine(enabled=True)
        engine.record_realized_trade(2021, gain_usd=8333.33, gain_krw=10_000_000.0)
        rec = engine.calculate_annual_tax(year=2021, year_end_fx=1200.0)

        assert rec.net_realized_gain_krw == 10_000_000.0
        assert rec.taxable_base_krw == 7_500_000.0
        assert pytest.approx(rec.tax_krw, abs=1e-6) == 1_650_000.0  # Exactly 1.65M KRW
        assert pytest.approx(rec.tax_usd, abs=1e-6) == 1375.0

    def test_year_end_tax_deduction_from_portfolio_cash(self):
        """
        Verifies that when a stock is sold with large gains in Year 1,
        the tax is calculated at calendar year-end and deducted from portfolio cash
        on the first trading day of Year 2.
        """
        dates = pd.date_range("2021-01-04", "2022-01-10", freq="B")
        prices_data = {
            ("Close", "QQQ"): [100.0] * len(dates),
            ("Open", "QQQ"): [100.0] * len(dates),
            ("Close", "SOXX"): [50.0] * len(dates),
            ("Open", "SOXX"): [50.0] * len(dates),
            ("Close", "WIN"): [10.0] * len(dates),
            ("Open", "WIN"): [10.0] * len(dates),
        }
        df = pd.DataFrame(prices_data, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        # WIN price jumps on 2021-03-01 triggering TAKE_PROFIT (+50% > +35%)
        df.loc["2021-03-01":, ("Close", "WIN")] = 15.0
        df.loc["2021-03-01":, ("Open", "WIN")] = 15.0

        fx = pd.Series(1200.0, index=dates)
        first_friday = dates[dates.dayofweek == 4][0].date()
        cand_map = {first_friday: "WIN"}

        strategy = BaseStrategy(StrategyParameters(
            w_qqq_base=0.40,
            w_soxx_base=0.30,
            w_turnaround_max=0.30,
            turnaround_idle_policy="cash_buffer",
        ))

        engine = BacktestEngine(initial_capital=100_000.0, rf_rate_annual=0.0)
        res = engine.run(strategy=strategy, prices_df=df, candidate_selections=cand_map, fx_rates=fx, tax_enabled=True)

        # Inspect 2021 tax record
        tax_table = res.annual_tax_records
        assert 2021 in tax_table["Year"].values
        rec_2021 = tax_table[tax_table["Year"] == 2021].iloc[0]
        tax_usd_2021 = rec_2021["Tax_USD"]
        assert tax_usd_2021 > 0, "Year 2021 must generate positive tax"

        # Check that Gross NAV USD minus Net NAV USD reflects the tax paid
        # On 2022-01-03 (first day of new year), tax must be deducted
        d_end = pd.Timestamp("2022-01-03")
        gross_val = res.gross_nav_usd.loc[d_end]
        net_val = res.after_tax_nav_usd.loc[d_end]
        diff = gross_val - net_val
        assert pytest.approx(diff, abs=1e-4) == tax_usd_2021, (
            f"Gross minus Net NAV ({diff}) must match 2021 tax paid ({tax_usd_2021})"
        )

    def test_calendar_year_loss_independence_no_carryforward(self):
        """
        Korean tax law does NOT permit loss carryforward for foreign stock capital gains.
        A loss in 2021 (-5M KRW) cannot offset a gain in 2022 (10M KRW).
        """
        engine = KoreanTaxEngine(enabled=True)
        # Year 2021: loss of 5M KRW
        engine.record_realized_trade(2021, gain_usd=-4166.67, gain_krw=-5_000_000.0)
        rec_2021 = engine.calculate_annual_tax(2021, 1200.0)
        assert rec_2021.tax_krw == 0.0

        # Year 2022: gain of 10M KRW
        engine.record_realized_trade(2022, gain_usd=8333.33, gain_krw=10_000_000.0)
        rec_2022 = engine.calculate_annual_tax(2022, 1200.0)
        # Must pay full tax on (10M - 2.5M) * 0.22 = 1.65M KRW, NOT offset by 2021 loss
        assert rec_2022.tax_krw == 1_650_000.0


# =====================================================================
# 3. GAP-DOWN EXECUTION
# =====================================================================
class TestGapDownExecutionEmpirical:
    """Probes realistic execution fills during extreme overnight gap-down price crashes."""

    def test_extreme_overnight_crash_25_pct_gap_execution_engine(self):
        """
        Entry at $100.0, Stop loss threshold = -12% ($88.0).
        Overnight crash: Open price crashes by -25% to $75.0.
        Assert execution fills at open price $75.0 * (1 - slippage), NOT at $88.0 stop threshold.
        """
        engine = ExecutionEngine(commission_bps=5.0, slippage_stock_bps=10.0)
        res = engine.execute_stop_loss_on_gap(
            entry_price=100.0,
            prior_close=95.0,
            open_price=75.0,  # -25% crash
            shares=100.0,
            stop_loss_pct=-0.12,
        )

        assert res["triggered"] is True, "Stop loss must trigger on -25% gap down"
        # Fill price: 75.0 * (1 - 0.001) = 74.925
        assert pytest.approx(res["fill_price"], abs=1e-4) == 74.925
        # Fills strictly below the theoretical stop loss price ($88.0)
        assert res["fill_price"] < 88.0
        # Slippage penalty on $7,500 trade value: $7.50
        assert pytest.approx(res["slippage_cost"], abs=1e-4) == 7.50
        # Net cash received: 7500 - 7.50 = 7492.50
        assert pytest.approx(res["net_cash_received"], abs=1e-4) == 7492.50

    def test_gap_down_in_backtester_simulation(self):
        """
        Verifies that BacktestEngine executes stop-loss at Open price during simulation,
        correctly recording the sell trade, applying friction, and closing the position.
        """
        dates = pd.date_range("2021-01-04", "2021-01-15", freq="B")
        prices_data = {
            ("Close", "QQQ"): [100.0] * len(dates),
            ("Open", "QQQ"): [100.0] * len(dates),
            ("Close", "SOXX"): [50.0] * len(dates),
            ("Open", "SOXX"): [50.0] * len(dates),
            ("Close", "CRASH"): [100.0] * len(dates),
            ("Open", "CRASH"): [100.0] * len(dates),
        }
        df = pd.DataFrame(prices_data, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        # On 2021-01-11, CRASH opens at $75.0 (-25% gap down)
        df.loc["2021-01-11":, ("Open", "CRASH")] = 75.0
        df.loc["2021-01-11":, ("Close", "CRASH")] = 72.0

        fx = pd.Series(1200.0, index=dates)
        first_friday = dates[dates.dayofweek == 4][0].date()
        cand_map = {first_friday: "CRASH"}

        strategy = BaseStrategy(StrategyParameters(
            w_qqq_base=0.40,
            w_soxx_base=0.30,
            w_turnaround_max=0.30,
            turnaround_idle_policy="cash_buffer",
        ))

        engine = BacktestEngine(initial_capital=100_000.0)
        res = engine.run(strategy=strategy, prices_df=df, candidate_selections=cand_map, fx_rates=fx)

        crash_trades = res.trade_log[res.trade_log["ticker"] == "CRASH"]
        assert len(crash_trades) == 2, "Expected 1 BUY and 1 SELL for CRASH"

        sell_rec = crash_trades[crash_trades["action"] == "SELL"].iloc[0]
        assert sell_rec["reason"] == "STOP_LOSS"
        # BacktestEngine records the nominal exit fill price as the Open price (75.0)
        assert sell_rec["price"] == 75.0
        assert sell_rec["price"] < 88.0, "Execution must fill at open price, NOT at theoretical -12% stop"
        assert sell_rec["friction"] > 0, "Friction must be charged on liquidation"


# =====================================================================
# 4. MICRO-TURNOVER PREVENTION (REBALANCE DEAD-ZONE)
# =====================================================================
class TestMicroTurnoverPreventionEmpirical:
    """Probes rebalance dead-zone filtering to verify avoidance of wasteful trades."""

    def test_rebalance_deadzone_filtering_logic(self):
        """
        Tests ExecutionEngine.should_rebalance with a 1.0% (0.01) threshold.
        Deltas < 1.0% must return False; deltas >= 1.0% must return True.
        """
        engine = ExecutionEngine(rebalance_deadzone=0.01)

        # Sub-threshold changes (0.1%, 0.5%, 0.9%)
        assert engine.should_rebalance(current_weight=0.501, target_weight=0.50) is False
        assert engine.should_rebalance(current_weight=0.495, target_weight=0.50) is False
        assert engine.should_rebalance(current_weight=0.509, target_weight=0.50) is False

        # Threshold and above (1.0%, 1.05%, 3.0%)
        assert engine.should_rebalance(current_weight=0.490, target_weight=0.50) is True
        assert engine.should_rebalance(current_weight=0.5105, target_weight=0.50) is True
        assert engine.should_rebalance(current_weight=0.470, target_weight=0.50) is True

    def test_micro_turnover_prevention_in_backtest_simulation(self):
        """
        Simulates 3 consecutive weekly rebalance dates:
        - Week 1 (Friday 1): Initial portfolio setup (generates trades).
        - Week 2 (Friday 2): QQQ price moves by +0.4%, creating a weight drift of ~0.1% (< 1.0%).
          Assert: ZERO trades on Week 2 (micro-turnover strictly suppressed!).
        - Week 3 (Friday 3): QQQ price jumps by +15.0%, creating a weight drift of ~3.5% (>= 1.0%).
          Assert: Rebalance trades execute on Week 3.
        """
        dates = pd.date_range("2021-01-04", "2021-01-25", freq="B")
        prices_data = {
            ("Close", "QQQ"): [100.0] * len(dates),
            ("Open", "QQQ"): [100.0] * len(dates),
            ("Close", "SOXX"): [50.0] * len(dates),
            ("Open", "SOXX"): [50.0] * len(dates),
        }
        df = pd.DataFrame(prices_data, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        # Week 2 (2021-01-15): tiny drift (+0.4%)
        df.loc["2021-01-15", ("Close", "QQQ")] = 100.4
        df.loc["2021-01-15", ("Open", "QQQ")] = 100.4

        # Week 3 (2021-01-22): major jump (+15%)
        df.loc["2021-01-22":, ("Close", "QQQ")] = 115.0
        df.loc["2021-01-22":, ("Open", "QQQ")] = 115.0

        fx = pd.Series(1200.0, index=dates)

        strategy = BaseStrategy(StrategyParameters(
            w_qqq_base=0.50,
            w_soxx_base=0.30,
            w_turnaround_max=0.0,
            w_cash_buffer=0.20,
            turnaround_idle_policy="cash_buffer",
        ))

        engine = BacktestEngine(initial_capital=100_000.0, rebalance_deadzone=0.01)
        res = engine.run(strategy=strategy, prices_df=df, fx_rates=fx)

        trade_dates = set(res.trade_log["date"].unique())
        w1 = pd.Timestamp("2021-01-08").date()
        w2 = pd.Timestamp("2021-01-15").date()
        w3 = pd.Timestamp("2021-01-22").date()

        assert w1 in trade_dates, "Week 1 initial rebalance must execute"
        assert w2 not in trade_dates, "Week 2 micro-turnover must be suppressed (< 1.0% delta)!"
        assert w3 in trade_dates, "Week 3 significant drift (>= 1.0% delta) must trigger rebalance"
