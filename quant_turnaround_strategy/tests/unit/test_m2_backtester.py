"""
Unit test suite for M2 Modular Backtester Simulator (src/engine/backtester.py).
Verifies:
- Event-driven daily simulation loop from July 10, 2001.
- Dynamic weekly rebalancing and order execution with friction.
- Cash interest accrual.
- Intra-week daily exit execution.
- Korean overseas capital gains tax deduction at year-end.
- Dual-currency (USD and KRW) NAV series and metric outputs.
- Gross vs Net after-tax returns comparison.
"""
from datetime import date
import pytest
import pandas as pd
import numpy as np

from src.engine.backtester import BacktestEngine, BacktestResult
from src.strategies.base_strategy import BaseStrategy, StrategyParameters


@pytest.fixture
def multi_year_market_data():
    """
    Synthetic market dataset spanning July 10, 2001 to December 31, 2003
    with MultiIndex columns for QQQ, SOXX, and turnaround stocks ABC, XYZ.
    """
    dates = pd.date_range("2001-07-10", "2003-12-31", freq="B")
    n = len(dates)

    np.random.seed(123)
    qqq_p = 40.0 * np.cumprod(1 + np.random.normal(0.0003, 0.012, n))
    soxx_p = 25.0 * np.cumprod(1 + np.random.normal(0.0004, 0.018, n))
    abc_p = 15.0 * np.cumprod(1 + np.random.normal(0.0002, 0.020, n))

    data = {
        ("Close", "QQQ"): qqq_p,
        ("Open", "QQQ"): qqq_p * 1.001,
        ("Close", "SOXX"): soxx_p,
        ("Open", "SOXX"): soxx_p * 1.001,
        ("Close", "ABC"): abc_p,
        ("Open", "ABC"): abc_p * 0.999,
    }
    df = pd.DataFrame(data, index=dates)
    df.columns = pd.MultiIndex.from_tuples(df.columns)

    # FX rates from 1200 to 1300
    fx = pd.Series(np.linspace(1200.0, 1300.0, n), index=dates, name="USDKRW")
    return df, fx


class TestBacktestEngineSimulation:
    def test_backtest_execution_and_result_schema(self, multi_year_market_data):
        prices_df, fx_series = multi_year_market_data
        engine = BacktestEngine(
            initial_capital=100_000.0,
            commission_bps=5.0,
            slippage_etf_bps=2.0,
            slippage_stock_bps=10.0,
        )
        strategy = BaseStrategy(StrategyParameters(
            w_qqq_base=0.50,
            w_soxx_base=0.30,
            w_turnaround_max=0.20,
            turnaround_idle_policy="etf_sweep",
        ))

        # First Friday of backtest has candidate ABC
        first_friday = prices_df.index[prices_df.index.dayofweek == 4][0].date()
        candidate_map = {first_friday: "ABC"}

        res = engine.run(
            strategy=strategy,
            prices_df=prices_df,
            candidate_selections=candidate_map,
            fx_rates=fx_series,
            tax_enabled=True,
            start_date="2001-07-10",
        )

        assert isinstance(res, BacktestResult)
        assert len(res.daily_nav_usd) == len(prices_df)
        assert len(res.daily_nav_krw) == len(prices_df)
        assert res.daily_nav_usd.iloc[0] == pytest.approx(100_000.0, rel=1e-3)
        assert res.daily_nav_krw.iloc[0] == pytest.approx(100_000.0 * 1200.0, rel=1e-3)

        # Check annual metrics tables
        assert not res.annual_metrics_usd.empty
        assert not res.annual_metrics_krw.empty
        years = list(res.annual_metrics_usd["Year"])
        assert 2001 in years
        assert 2002 in years
        assert 2003 in years

        # Check Calmar ratios
        assert isinstance(res.calmar_ratio_usd, float)
        assert isinstance(res.calmar_ratio_krw, float)

        # Check trade log
        assert not res.trade_log.empty
        assert "friction" in res.trade_log.columns
        assert "action" in res.trade_log.columns
        assert "ticker" in res.trade_log.columns

    def test_tax_enabled_vs_tax_disabled_nav_comparison(self, multi_year_market_data):
        prices_df, fx_series = multi_year_market_data

        # Run with tax enabled
        engine_tax = BacktestEngine(initial_capital=100_000.0)
        res_tax = engine_tax.run(
            prices_df=prices_df,
            fx_rates=fx_series,
            tax_enabled=True,
            start_date="2001-07-10",
        )

        # Run with tax disabled
        engine_notax = BacktestEngine(initial_capital=100_000.0)
        res_notax = engine_notax.run(
            prices_df=prices_df,
            fx_rates=fx_series,
            tax_enabled=False,
            start_date="2001-07-10",
        )

        # After-tax NAV must be <= Gross NAV
        assert res_tax.after_tax_nav_usd.iloc[-1] <= res_tax.gross_nav_usd.iloc[-1]
        assert res_notax.after_tax_nav_usd.iloc[-1] == res_notax.gross_nav_usd.iloc[-1]

    def test_cash_interest_accrues_on_uninvested_capital(self):
        # 100 days of flat prices, 100% Cash strategy
        dates = pd.date_range("2001-07-10", periods=100, freq="B")
        prices = pd.DataFrame({
            ("Close", "QQQ"): [100.0] * 100,
            ("Open", "QQQ"): [100.0] * 100,
            ("Close", "SOXX"): [50.0] * 100,
            ("Open", "SOXX"): [50.0] * 100,
        }, index=dates)
        prices.columns = pd.MultiIndex.from_tuples(prices.columns)

        engine = BacktestEngine(
            initial_capital=100_000.0,
            rf_rate_annual=0.0504,  # ~5% annual interest
        )
        # Strategy with 100% Cash buffer
        strategy = BaseStrategy(StrategyParameters(
            w_qqq_base=0.0,
            w_soxx_base=0.0,
            w_turnaround_max=0.0,
            w_cash_buffer=1.0,
            turnaround_idle_policy="cash_buffer",
        ))

        res = engine.run(strategy=strategy, prices_df=prices, tax_enabled=False)
        # NAV should grow purely through interest
        final_nav = res.daily_nav_usd.iloc[-1]
        assert final_nav > 100_000.0
        # Over 100 days at 5% / 252 ≈ +2%
        assert final_nav == pytest.approx(100_000.0 * (1 + 0.0504/252)**100, rel=1e-3)

    def test_rebalance_sell_orders_execute_before_buy_orders(self):
        dates = pd.date_range("2021-01-01", periods=15, freq="B")
        prices = pd.DataFrame({
            ("Close", "QQQ"): [100.0] * 15,
            ("Close", "SOXX"): [100.0] * 15,
            ("Close", "ABC"): [10.0] * 15,
        }, index=dates)
        prices.columns = pd.MultiIndex.from_tuples(prices.columns)
        strat = BaseStrategy(turnaround_idle_policy="etf_sweep")
        engine = BacktestEngine(initial_capital=100_000.0)
        cand = {dates[5].date(): "ABC"}
        res = engine.run(strategy=strat, prices_df=prices, candidate_selections=cand)

        abc_trades = res.trade_log[res.trade_log["ticker"] == "ABC"]
        # Candidate ABC must be fully funded and bought in 1 trade via liberated ETF cash
        assert len(abc_trades) == 1
        assert abc_trades["shares"].iloc[0] > 600.0

    def test_tax_deduction_full_accounting_without_clamping(self):
        dates = pd.date_range("2021-12-01", "2022-01-10", freq="B")
        prices = pd.DataFrame({
            ("Close", "QQQ"): [100.0] * len(dates),
            ("Close", "SOXX"): [100.0] * len(dates),
            ("Close", "ABC"): [10.0] * len(dates),
        }, index=dates)
        prices.columns = pd.MultiIndex.from_tuples(prices.columns)
        prices.loc["2021-12-10":, ("Close", "ABC")] = 20.0
        strat = BaseStrategy(turnaround_idle_policy="etf_sweep")
        engine = BacktestEngine(initial_capital=100_000.0)
        cand = {pd.Timestamp("2021-12-03").date(): "ABC"}
        res = engine.run(strategy=strat, prices_df=prices, candidate_selections=cand)

        tax_usd = res.annual_tax_records.loc[res.annual_tax_records["Year"] == 2021, "Tax_USD"].values[0]
        assert tax_usd > 500.0
        nav_drop = res.daily_nav_usd.loc["2021-12-31"] - res.daily_nav_usd.loc["2022-01-03"]
        # NAV drop at rollover must reflect the full tax liability without cash-clamping leakage
        assert abs(nav_drop - tax_usd) < 5.0

    def test_position_tracking_on_partial_sells(self):
        engine = BacktestEngine()
        # Initial buy 100 @ 10
        engine.execute_trade("QQQ", 100, 10.0, is_stock=False)
        assert engine.positions["QQQ"].shares == 100.0
        assert engine.positions["QQQ"].entry_price == 10.0

        # Partial sell 50 @ 20
        engine.execute_trade("QQQ", -50, 20.0, is_stock=False)
        assert engine.positions["QQQ"].shares == 50.0
        assert engine.holdings["QQQ"] == 50.0
        assert engine.positions["QQQ"].entry_price == 10.0

        # Subsequent buy 50 @ 30 -> average entry price should be (50*10 + 50*30)/100 = 20.0
        engine.execute_trade("QQQ", 50, 30.0, is_stock=False)
        assert engine.positions["QQQ"].shares == 100.0
        assert abs(engine.positions["QQQ"].entry_price - 20.0) < 1e-4

    def test_final_simulation_day_tax_settlement(self):
        dates = pd.date_range("2021-01-01", "2021-12-31", freq="B")
        prices = pd.DataFrame({
            ("Close", "QQQ"): [100.0] * len(dates),
            ("Close", "SOXX"): [100.0] * len(dates),
            ("Close", "ABC"): [10.0] * len(dates),
        }, index=dates)
        prices.columns = pd.MultiIndex.from_tuples(prices.columns)
        prices.loc["2021-06-01":, ("Close", "ABC")] = 20.0
        strat = BaseStrategy(StrategyParameters(profit_target_pct=0.35, turnaround_idle_policy="etf_sweep"))
        engine = BacktestEngine(initial_capital=100_000.0)
        cand = {dates[0].date(): "ABC"}
        res = engine.run(strategy=strat, prices_df=prices, candidate_selections=cand)

        total_tax = res.annual_tax_records["Tax_USD"].sum()
        assert total_tax > 0.0
        # Final day Net NAV must settle tax, ensuring Gross - Net NAV equals cumulative tax paid
        gross_net_diff = res.gross_nav_usd.iloc[-1] - res.daily_nav_usd.iloc[-1]
        assert abs(gross_net_diff - total_tax) < 1e-4

