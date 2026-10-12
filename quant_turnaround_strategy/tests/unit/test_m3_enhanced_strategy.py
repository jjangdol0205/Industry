"""
Unit test suite for M3 Enhanced Strategy (AR-DM) (src/strategies/enhanced_strategy.py).
Verifies:
- Parameter configuration and validation.
- Macro-Trend 200-day SMA regime classification (Bull, Transition, Bear).
- Dual-Momentum relative strength tilt between QQQ and SOXX.
- Asymmetric 3-stage profit ratchet logic.
- Target portfolio weights under all regimes and idle policies.
- Turnaround stock buy freeze during Bear regimes.
- Integration compatibility with BacktestEngine producing dual-currency results.
"""
from datetime import date
import pytest
import pandas as pd
import numpy as np

from src.strategies.enhanced_strategy import (
    EnhancedStrategy,
    EnhancedStrategyParameters,
    AdaptiveRegimeDualMomentum,
    ExitReason,
)
from src.engine.backtester import BacktestEngine, BacktestResult
from src.engine.portfolio import Position


class TestEnhancedStrategyAR_DM:
    """Tests for Adaptive Regime-Switching Dual-Momentum strategy logic."""

    def test_default_parameters_and_invariants(self):
        strat = EnhancedStrategy()
        assert strat.params.sma_trend_window == 200
        assert strat.params.sma_fast_window == 50
        assert strat.params.bear_cash == 0.85
        assert strat.params.transition_cash == 0.40
        assert strat.params.bull_leader_weight == 0.55
        assert strat.params.bull_laggard_weight == 0.30
        assert strat.params.bull_turnaround_max == 0.15
        assert strat.params.breakeven_gain_pct == 0.20
        assert strat.params.trailing_gain_pct == 0.40

    def test_regime_classification_boundaries(self):
        strat = EnhancedStrategy()
        # BULL: price >= sma200 and sma50 > sma200
        assert strat.classify_regime(price=110.0, sma200=100.0, sma50=105.0) == "BULL"

        # TRANSITION: price >= sma200 but sma50 <= sma200
        assert strat.classify_regime(price=105.0, sma200=100.0, sma50=98.0) == "TRANSITION"
        assert strat.classify_regime(price=100.0, sma200=100.0, sma50=100.0) == "TRANSITION"

        # BEAR: price < sma200
        assert strat.classify_regime(price=99.9, sma200=100.0, sma50=105.0) == "BEAR"
        assert strat.classify_regime(price=70.0, sma200=100.0, sma50=80.0) == "BEAR"

    def test_determine_regime_allocation_constraints(self):
        strat = EnhancedStrategy()

        bear_alloc = strat.determine_regime_allocation("BEAR")
        assert bear_alloc["cash_min"] >= 0.85
        assert bear_alloc["allow_turnaround_buy"] is False

        trans_alloc = strat.determine_regime_allocation("TRANSITION")
        assert trans_alloc["cash_min"] == 0.40
        assert trans_alloc["equity_max"] == 0.60
        assert trans_alloc["allow_turnaround_buy"] is True

        bull_alloc = strat.determine_regime_allocation("BULL")
        assert bull_alloc["cash_min"] == 0.0
        assert bull_alloc["equity_max"] == 1.0
        assert bull_alloc["allow_turnaround_buy"] is True

    def test_dual_momentum_relative_strength_tilt(self):
        strat = EnhancedStrategy()

        # SOXX momentum (+25%) > QQQ momentum (+10%)
        soxx_leads = strat.compute_dual_momentum_tilt(qqq_mom=0.10, soxx_mom=0.25)
        assert soxx_leads["SOXX"] == 0.55
        assert soxx_leads["QQQ"] == 0.30
        assert soxx_leads["Turnaround"] == 0.15

        # QQQ momentum (+18%) > SOXX momentum (+5%)
        qqq_leads = strat.compute_dual_momentum_tilt(qqq_mom=0.18, soxx_mom=0.05)
        assert qqq_leads["QQQ"] == 0.55
        assert qqq_leads["SOXX"] == 0.30
        assert qqq_leads["Turnaround"] == 0.15

    def test_asymmetric_profit_ratchet_three_stages(self):
        strat = EnhancedStrategy()
        entry = 100.0

        # Stage 1: gain < +20% -> -10% hard stop
        stop1, stage1 = strat.evaluate_profit_ratchet(entry_price=entry, current_price=110.0, peak_price=115.0)
        assert stage1 == "STAGE_1_HARD"
        assert stop1 == pytest.approx(90.0, abs=1e-4)

        # Stage 2: gain in [+20%, +40%) -> break-even stop at entry ($100.0)
        stop2, stage2 = strat.evaluate_profit_ratchet(entry_price=entry, current_price=122.0, peak_price=125.0)
        assert stage2 == "STAGE_2_BREAKEVEN"
        assert stop2 == pytest.approx(100.0, abs=1e-4)

        # Stage 3: gain >= +40% -> 8% trailing stop from peak ($150 * 0.92 = $138.0)
        stop3, stage3 = strat.evaluate_profit_ratchet(entry_price=entry, current_price=145.0, peak_price=150.0)
        assert stage3 == "STAGE_3_TRAILING"
        assert stop3 == pytest.approx(138.0, abs=1e-4)

    def test_target_weights_in_bear_regime_freezes_turnaround(self):
        strat = EnhancedStrategy()

        # In Bear regime, turnaround stocks get 0.0 weight
        w = strat.compute_target_weights(
            active_turnaround_stocks=["STK1", "STK2"],
            regime="BEAR",
        )
        assert w["STK1"] == 0.0
        assert w["STK2"] == 0.0
        assert w["Cash"] == pytest.approx(0.85, abs=1e-4)
        assert pytest.approx(sum(w.values()), abs=1e-6) == 1.0

    def test_target_weights_in_bull_regime_etf_sweep_vs_cash_buffer(self):
        strat = EnhancedStrategy()

        # 0 turnaround stocks, SOXX leads (sm > qm)
        w_sweep = strat.compute_target_weights(
            active_turnaround_stocks=[],
            idle_policy="etf_sweep",
            regime="BULL",
            qqq_mom=0.05,
            soxx_mom=0.20,
        )
        # Unallocated 15% turnaround capacity swept into SOXX and QQQ (55:30 ratio)
        assert w_sweep["SOXX"] > 0.55
        assert w_sweep["QQQ"] > 0.30
        assert pytest.approx(w_sweep["Cash"], abs=1e-6) == 0.0
        assert pytest.approx(sum(w_sweep.values()), abs=1e-6) == 1.0

        w_cash = strat.compute_target_weights(
            active_turnaround_stocks=[],
            idle_policy="cash_buffer",
            regime="BULL",
            qqq_mom=0.05,
            soxx_mom=0.20,
        )
        assert w_cash["SOXX"] == pytest.approx(0.55, abs=1e-4)
        assert w_cash["QQQ"] == pytest.approx(0.30, abs=1e-4)
        assert w_cash["Cash"] == pytest.approx(0.15, abs=1e-4)
        assert pytest.approx(sum(w_cash.values()), abs=1e-6) == 1.0

    def test_target_weights_with_active_turnaround_stocks(self):
        strat = EnhancedStrategy()

        # 2 turnaround stocks in Bull regime
        w = strat.compute_target_weights(
            active_turnaround_stocks=["AAPL", "INTC"],
            idle_policy="etf_sweep",
            regime="BULL",
            qqq_mom=0.15,
            soxx_mom=0.05,  # QQQ leads
        )
        assert "AAPL" in w and "INTC" in w
        assert w["AAPL"] == pytest.approx(0.05, abs=1e-4)
        assert w["INTC"] == pytest.approx(0.05, abs=1e-4)
        assert w["QQQ"] > w["SOXX"]
        assert pytest.approx(sum(w.values()), abs=1e-6) == 1.0

    def test_should_buy_candidate_respects_bear_freeze(self):
        strat = EnhancedStrategy()

        # In Bear regime: candidate purchase MUST be rejected
        can_buy_bear = strat.should_buy_candidate(
            candidate_score=95.0,
            low_proximity=0.01,
            current_holdings_count=0,
            regime="BEAR",
        )
        assert can_buy_bear is False

        # In Bull regime: candidate purchase accepted
        can_buy_bull = strat.should_buy_candidate(
            candidate_score=95.0,
            low_proximity=0.01,
            current_holdings_count=0,
            regime="BULL",
        )
        assert can_buy_bull is True

    def test_backtest_engine_integration_with_enhanced_strategy(self):
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        prices = pd.DataFrame({
            ("Close", "QQQ"): np.linspace(100.0, 150.0, 100),
            ("Open", "QQQ"): np.linspace(100.0, 150.0, 100),
            ("Close", "SOXX"): np.linspace(50.0, 80.0, 100),
            ("Open", "SOXX"): np.linspace(50.0, 80.0, 100),
        }, index=dates)
        prices.columns = pd.MultiIndex.from_tuples(prices.columns)

        strat = EnhancedStrategy(prices_df=prices)
        engine = BacktestEngine(initial_capital=100_000.0)
        res = engine.run(strategy=strat, prices_df=prices, start_date="2020-01-01")

        assert isinstance(res, BacktestResult)
        assert len(res.daily_nav_usd) == 100
        assert res.daily_nav_usd.iloc[-1] > 100_000.0
        assert res.calmar_ratio_usd >= 0.0

    def test_consecutive_backtest_runs_are_idempotent(self):
        """Verifies running BacktestEngine.run twice consecutively yields identical Calmar ratio."""
        from src.data.cache_store import CacheStore
        from config.settings import CACHE_DIR

        cs = CacheStore(CACHE_DIR)
        prices = cs.load_parquet("etf_prices.parquet")
        fx_df = cs.load_parquet("fx_rates.parquet")
        fx_series = fx_df["USDKRW"] if "USDKRW" in fx_df.columns else fx_df.iloc[:, 0]

        strat = EnhancedStrategy(prices_df=prices)
        engine = BacktestEngine(100_000.0)

        res1 = engine.run(strategy=strat, prices_df=prices, fx_rates=fx_series, start_date="2001-07-10")
        res2 = engine.run(strategy=strat, prices_df=prices, fx_rates=fx_series, start_date="2001-07-10")

        assert abs(res1.calmar_ratio_usd - res2.calmar_ratio_usd) < 1e-6
        assert res1.calmar_ratio_usd > 0.42

    def test_slice_backtest_respects_slice_regime(self):
        """Verifies sub-slice backtests starting in 2020 look up the 2020 Bull regime indicators."""
        from src.data.cache_store import CacheStore
        from config.settings import CACHE_DIR

        cs = CacheStore(CACHE_DIR)
        prices = cs.load_parquet("etf_prices.parquet")

        strat = EnhancedStrategy(prices_df=prices)
        engine = BacktestEngine(100_000.0)

        res = engine.run(strategy=strat, prices_df=prices, start_date="2020-01-01")
        cash_weight = res.allocation_history.loc["2020-01-03", "Cash"]
        assert cash_weight <= 0.15

    def test_evaluate_daily_exit_stages_and_holding_duration(self):
        """Verifies evaluate_daily_exit across all 3 profit ratchet stages and max holding period."""
        strat = EnhancedStrategy()

        # Stage 1: Hard stop-loss (-10%)
        pos1 = Position(
            ticker="TEST", shares=10.0, entry_price=100.0, entry_date=date(2020, 1, 1),
            current_price=89.0, peak_price=100.0, days_held=5,
        )
        r1 = strat.evaluate_daily_exit(pos1, current_price=89.0, high_price=95.0, low_price=89.0, days_held=5)
        assert r1 == ExitReason.STOP_LOSS

        # Stage 2: Breakeven stop (+25% peak gain, price drops below entry $100)
        pos2 = Position(
            ticker="TEST", shares=10.0, entry_price=100.0, entry_date=date(2020, 1, 1),
            current_price=99.0, peak_price=125.0, days_held=20,
        )
        r2 = strat.evaluate_daily_exit(pos2, current_price=99.0, high_price=105.0, low_price=99.0, days_held=20)
        assert r2 == ExitReason.BREAKEVEN_STOP

        # Stage 3: Trailing stop (+50% peak gain, 8% trailing stop from $150 = $138)
        pos3 = Position(
            ticker="TEST", shares=10.0, entry_price=100.0, entry_date=date(2020, 1, 1),
            current_price=137.0, peak_price=150.0, days_held=40,
        )
        r3 = strat.evaluate_daily_exit(pos3, current_price=137.0, high_price=145.0, low_price=137.0, days_held=40)
        assert r3 == ExitReason.TRAILING_STOP

        # Time stop: max holding duration (130 days)
        pos4 = Position(
            ticker="TEST", shares=10.0, entry_price=100.0, entry_date=date(2020, 1, 1),
            current_price=110.0, peak_price=115.0, days_held=130,
        )
        r4 = strat.evaluate_daily_exit(pos4, current_price=110.0, high_price=112.0, low_price=108.0, days_held=130)
        assert r4 == ExitReason.TIME_STOP

        # Normal holding: no exit triggered
        pos5 = Position(
            ticker="TEST", shares=10.0, entry_price=100.0, entry_date=date(2020, 1, 1),
            current_price=115.0, peak_price=118.0, days_held=10,
        )
        r5 = strat.evaluate_daily_exit(pos5, current_price=115.0, high_price=118.0, low_price=112.0, days_held=10)
        assert r5 == ExitReason.NONE

    def test_profit_ratchet_actively_protects_turnaround_positions_in_backtest(self):
        """Verifies evaluate_profit_ratchet is actively invoked during backtest daily monitoring."""
        dates = pd.date_range("2020-01-01", periods=50, freq="B")
        prices = pd.DataFrame({
            ("Close", "QQQ"): np.linspace(100.0, 150.0, 50),
            ("Open", "QQQ"): np.linspace(100.0, 150.0, 50),
            ("Close", "SOXX"): np.linspace(50.0, 80.0, 50),
            ("Open", "SOXX"): np.linspace(50.0, 80.0, 50),
            ("Close", "TRND"): [100.0] * 10 + [125.0] * 10 + [150.0] * 10 + [135.0] * 20,
            ("Open", "TRND"): [100.0] * 10 + [125.0] * 10 + [150.0] * 10 + [135.0] * 20,
            ("High", "TRND"): [102.0] * 10 + [128.0] * 10 + [155.0] * 10 + [138.0] * 20,
            ("Low", "TRND"): [98.0] * 10 + [122.0] * 10 + [148.0] * 10 + [134.0] * 20,
        }, index=dates)
        prices.columns = pd.MultiIndex.from_tuples(prices.columns)

        strat = EnhancedStrategy(prices_df=prices)
        engine = BacktestEngine(100_000.0)

        ratchet_calls = 0
        original_eval = strat.evaluate_profit_ratchet

        def spy_ratchet(*args, **kwargs):
            nonlocal ratchet_calls
            ratchet_calls += 1
            return original_eval(*args, **kwargs)

        strat.evaluate_profit_ratchet = spy_ratchet

        friday_dt = [d for d in dates if d.dayofweek == 4][0].date()
        cands = {friday_dt: "TRND"}

        res = engine.run(strategy=strat, prices_df=prices, candidate_selections=cands)
        assert ratchet_calls > 0, "evaluate_profit_ratchet was not invoked during daily exit monitoring"

        # Position should have triggered a trailing stop exit when falling from $155 peak to $135
        sell_orders = [t for t in res.trade_log.to_dict("records") if t["ticker"] == "TRND" and t["action"] == "SELL"]
        assert len(sell_orders) > 0
        assert sell_orders[-1]["reason"] in ("TRAILING_STOP", ExitReason.TRAILING_STOP)
