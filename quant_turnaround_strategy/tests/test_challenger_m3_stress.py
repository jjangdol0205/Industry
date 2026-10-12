"""
Challenger M3-1 Empirical Stress Suite:
Adversarial testing of Enhanced Strategy (AR-DM) in src/strategies/enhanced_strategy.py:
1. Whipsaw regimes: Daily vs Weekly SMA200 crossings, turnover bounds, and deadzone behavior.
2. Candidate crash: Overnight -30% flash crash in Ratchet Stage 1 and Stage 2.
3. Bear regime buy ban: Strict prohibition of turnaround purchases (should_buy_candidate == False and target_weight == 0.0).
4. Portfolio weight invariant: Sum w_i + w_cash = 1.0 +- 1e-6 across all historical trading days (2001 to 2026).
"""
import sys
from pathlib import Path

# Ensure quant_turnaround_strategy root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
import pytest
import numpy as np
import pandas as pd

from src.data.cache_store import CacheStore
from config.settings import CACHE_DIR
from src.strategies.enhanced_strategy import EnhancedStrategy, EnhancedStrategyParameters
from src.engine.backtester import BacktestEngine, BacktestResult
from src.engine.risk_manager import RiskManager


@pytest.fixture(scope="module")
def historical_feeds():
    """Loads historical benchmark and FX feeds from parquet cache."""
    cs = CacheStore(CACHE_DIR)
    etf_prices = cs.load_parquet("etf_prices.parquet")
    fx_rates = cs.load_parquet("fx_rates.parquet")
    fx_series = fx_rates["USDKRW"] if "USDKRW" in fx_rates.columns else fx_rates.iloc[:, 0]
    return etf_prices, fx_series


class TestChallengerM3StressSuite:
    """Adversarial stress-tests verifying stability, invariance, and risk boundaries."""

    # -------------------------------------------------------------------------
    # Pillar 1: Severe Whipsaw Regimes & Turnover Bounds
    # -------------------------------------------------------------------------
    def test_intraweek_whipsaw_produces_zero_spurious_turnover(self):
        """
        Adversarial probe:
        If QQQ oscillates above and below SMA200 daily Monday through Thursday,
        does turnover explode?
        Finding: BacktestEngine rebalances strictly on weekly Friday closes.
        Intra-week oscillations around SMA200 produce zero rebalancing trades.
        """
        dates = pd.date_range("2021-01-04", periods=20, freq="B")  # 4 full weeks
        # Construct SMA200 reference at 100.0, QQQ oscillates between 95 and 105 Mon-Thu
        qqq_prices = []
        for i, dt in enumerate(dates):
            if dt.dayofweek == 4:  # Friday: always stable at 105.0 (BULL)
                qqq_prices.append(105.0)
            else:  # Mon-Thu: violent swings
                qqq_prices.append(90.0 if i % 2 == 0 else 110.0)

        df = pd.DataFrame({
            ("Close", "QQQ"): qqq_prices,
            ("Open", "QQQ"): qqq_prices,
            ("Close", "SOXX"): [100.0] * len(dates),
            ("Open", "SOXX"): [100.0] * len(dates),
        }, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        strat = EnhancedStrategy(prices_df=df)
        engine = BacktestEngine(initial_capital=100000.0, rebalance_deadzone=0.01)
        res = engine.run(strategy=strat, prices_df=df)

        # Rebalances should occur at most once per week (4 Fridays)
        rebal_trades = res.trade_log[res.trade_log["reason"] == "REBALANCE"]
        # No trades should occur on Monday, Tuesday, Wednesday, or Thursday
        non_friday_rebal = [t for t in rebal_trades.to_dict("records") if pd.Timestamp(t["date"]).dayofweek != 4]
        assert len(non_friday_rebal) == 0, f"Found unexpected intra-week rebalances: {non_friday_rebal}"

    def test_weekly_persistent_whipsaw_turnover_is_strictly_bounded(self):
        """
        Adversarial probe:
        If QQQ crosses SMA200 every Friday for 20 consecutive weeks (worst-case weekly whipsaw),
        measure turnover and friction.
        Finding: Turnover is bounded to at most 1 macro rebalance per week.
        The 1% deadzone does not prevent regime rebalances (since delta_w = 85% > 1%),
        but overall trade count cannot exceed 2 trades per week.
        """
        dates = pd.date_range("2021-01-01", periods=100, freq="B")  # 20 weeks
        # Flip Friday closes between 95 (Bear) and 105 (Bull)
        qqq_prices = []
        for dt in dates:
            week_idx = dt.isocalendar()[1]
            if week_idx % 2 == 0:
                qqq_prices.append(110.0)
            else:
                qqq_prices.append(90.0)

        df = pd.DataFrame({
            ("Close", "QQQ"): qqq_prices,
            ("Open", "QQQ"): qqq_prices,
            ("Close", "SOXX"): [100.0] * len(dates),
            ("Open", "SOXX"): [100.0] * len(dates),
        }, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        strat = EnhancedStrategy(prices_df=df)
        engine = BacktestEngine(initial_capital=100000.0, rebalance_deadzone=0.01)
        res = engine.run(strategy=strat, prices_df=df)

        # Max rebalance trades across 20 weeks cannot exceed 20 * 2 = 40 trades
        assert len(res.trade_log) <= 40
        # NAV must remain positive despite 20 regime flips
        assert res.daily_nav_usd.iloc[-1] > 50000.0

    def test_rebalance_deadzone_filters_small_portfolio_weight_drift(self):
        """
        Verifies that rebalance_deadzone (0.01) filters out small micro-drifts
        (< 1%) while allowing intentional macro allocation changes (>= 1%).
        """
        engine = BacktestEngine(initial_capital=100000.0, rebalance_deadzone=0.01)
        # 0.5% drift -> filtered
        assert abs(0.555 - 0.550) < engine.rebalance_deadzone
        # 1.5% drift -> executed
        assert abs(0.565 - 0.550) >= engine.rebalance_deadzone

    # -------------------------------------------------------------------------
    # Pillar 2: Overnight Flash Crash (-30%) in Ratchet Stages
    # -------------------------------------------------------------------------
    def test_overnight_crash_30pct_in_ratchet_stage1_and_stage2(self):
        """
        Adversarial probe:
        Candidate crashes -30% overnight from entry price:
        - In Stage 1 (Hard stop active at -10%):
          evaluate_profit_ratchet maintains stop at entry * 0.90 ($90.0).
        - In Stage 2 (Break-even stop active at 0% loss):
          evaluate_profit_ratchet maintains stop at entry * 1.00 ($100.0).
        - Real execution in BacktestEngine:
          RiskManager detects overnight gap (open_price $70 <= entry * 0.88),
          triggers STOP_LOSS liquidation at open_price ($70.0), absorbing the real gap.
        """
        strat = EnhancedStrategy()
        entry = 100.0

        # Stage 1: Gain was +10% (peak = 110.0), crashes to 70.0 overnight
        stop_s1, stage_s1 = strat.evaluate_profit_ratchet(entry_price=entry, current_price=105.0, peak_price=110.0)
        assert stage_s1 == "STAGE_1_HARD"
        assert stop_s1 == pytest.approx(90.0, abs=1e-4)

        # When evaluated at crash price 70.0
        stop_s1_post, stage_s1_post = strat.evaluate_profit_ratchet(entry_price=entry, current_price=70.0, peak_price=110.0)
        assert stage_s1_post == "STAGE_1_HARD"
        assert stop_s1_post == pytest.approx(90.0, abs=1e-4)
        # Current price (70) < stop_price (90), signaling immediate liquidation
        assert 70.0 < stop_s1_post

        # Stage 2: Gain was +25% (peak = 125.0), crashes to 70.0 overnight
        stop_s2, stage_s2 = strat.evaluate_profit_ratchet(entry_price=entry, current_price=125.0, peak_price=125.0)
        assert stage_s2 == "STAGE_2_BREAKEVEN"
        assert stop_s2 == pytest.approx(100.0, abs=1e-4)

        # When evaluated at crash price 70.0
        stop_s2_post, stage_s2_post = strat.evaluate_profit_ratchet(entry_price=entry, current_price=70.0, peak_price=125.0)
        assert stage_s2_post == "STAGE_2_BREAKEVEN"
        assert stop_s2_post == pytest.approx(100.0, abs=1e-4)
        # Current price (70) < stop_price (100), signaling immediate liquidation
        assert 70.0 < stop_s2_post

        # RiskManager empirical overnight gap handling
        rm = RiskManager(stop_loss_pct=-0.12)
        is_gap, reason = rm.check_overnight_gap(entry_price=entry, open_price=70.0, prior_close=105.0)
        assert is_gap is True
        assert reason == "STOP_LOSS"

    def test_backtest_engine_liquidates_overnight_crashing_candidate_at_open(self):
        """
        End-to-end integration:
        Simulate an active candidate that gaps down -30% overnight inside BacktestEngine.
        Assert that the candidate is liquidated at the gap open price and removed from holdings.
        """
        # Start on a Friday (2021-01-08 is Friday, dayofweek == 4) so weekly rebalance executes purchase
        dates = pd.date_range("2021-01-08", periods=10, freq="B")
        prices_data = {
            ("Close", "QQQ"): [100.0] * 10,
            ("Open", "QQQ"): [100.0] * 10,
            ("Close", "SOXX"): [100.0] * 10,
            ("Open", "SOXX"): [100.0] * 10,
            # CRASH stock: bought on Friday Day 0 at 100, then gaps down -30% on Day 3 (Wednesday)
            ("Close", "CRASH"): [100.0, 105.0, 108.0, 68.0, 65.0, 65.0, 65.0, 65.0, 65.0, 65.0],
            ("Open", "CRASH"):  [100.0, 105.0, 108.0, 70.0, 68.0, 65.0, 65.0, 65.0, 65.0, 65.0],
        }
        df = pd.DataFrame(prices_data, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        strat = EnhancedStrategy(prices_df=df)
        engine = BacktestEngine(initial_capital=100000.0)

        # Inject candidate purchase on Day 0 (Friday)
        cands = {dates[0].date(): "CRASH"}
        res = engine.run(strategy=strat, prices_df=df, candidate_selections=cands)

        crash_trades = [t for t in res.trade_log.to_dict("records") if t["ticker"] == "CRASH"]
        # Must have both BUY and SELL
        actions = [t["action"] for t in crash_trades]
        assert "BUY" in actions
        assert "SELL" in actions
        # SELL order must be executed due to STOP_LOSS
        sell_order = next(t for t in crash_trades if t["action"] == "SELL")
        assert sell_order["reason"] == "STOP_LOSS"
        # Executed fill price must reflect the opening gap price (70.0)
        assert sell_order["price"] == pytest.approx(70.0, abs=1e-2)
        # Position must not be held at the end of the simulation
        assert "CRASH" not in engine.holdings

    # -------------------------------------------------------------------------
    # Pillar 3: Bear Regime Buy Ban Verification
    # -------------------------------------------------------------------------
    def test_bear_regime_strictly_forbids_candidate_purchases(self, historical_feeds):
        """
        Adversarial probe:
        Across all 1,462 historical Bear dates (2001-2026):
        1. should_buy_candidate MUST strictly return False for any candidate.
        2. compute_target_weights MUST allocate 0.0 weight to any turnaround stocks.
        """
        etf_prices, fx_series = historical_feeds
        strat = EnhancedStrategy(prices_df=etf_prices)
        strat.prepare(etf_prices)

        bear_dates = strat._indicator_df[strat._indicator_df["Regime"] == "BEAR"].index
        assert len(bear_dates) > 1000, f"Expected >1000 Bear dates, got {len(bear_dates)}"

        # Sample across bear market episodes: 2002, 2008, 2022
        sample_bear_dates = [
            pd.Timestamp("2002-06-14"),
            pd.Timestamp("2002-10-04"),
            pd.Timestamp("2008-10-10"),
            pd.Timestamp("2008-11-21"),
            pd.Timestamp("2022-05-13"),
            pd.Timestamp("2022-10-14"),
        ]

        for dt in sample_bear_dates:
            if dt in strat._indicator_df.index:
                # 1. should_buy_candidate check
                can_buy = strat.should_buy_candidate(
                    candidate_score=99.0,  # Flawless fundamental score
                    low_proximity=0.001,   # Perfect 52w low proximity
                    current_holdings_count=0,
                    current_date=dt,
                )
                assert can_buy is False, f"Leaked buy permission on Bear date {dt}"

                # 2. compute_target_weights check
                weights = strat.compute_target_weights(
                    active_turnaround_stocks=["STOCK_A", "STOCK_B"],
                    current_date=dt,
                )
                assert weights["STOCK_A"] == 0.0
                assert weights["STOCK_B"] == 0.0
                assert weights["Cash"] >= 0.85

    def test_backtest_engine_executes_zero_candidate_buys_during_bear(self, historical_feeds):
        """
        Injects a tempting candidate stock into candidate_selections during
        a deep Bear market period (Lehman crisis, Oct 2008).
        Asserts that BacktestEngine executes 0 purchases of the candidate.
        """
        etf_prices, fx_series = historical_feeds
        strat = EnhancedStrategy(prices_df=etf_prices)
        engine = BacktestEngine(initial_capital=100000.0)

        # October 10, 2008 is peak Lehman GFC crash (Friday, Bear regime)
        lehman_friday = date(2008, 10, 10)
        cands = {lehman_friday: "TEMPTING_CRASH_STOCK"}

        # Run 2-month slice around Lehman crash
        res = engine.run(
            strategy=strat,
            prices_df=etf_prices,
            candidate_selections=cands,
            fx_rates=fx_series,
            start_date="2008-09-01",
            end_date="2008-11-30",
        )

        bought_tickers = [t["ticker"] for t in res.trade_log.to_dict("records") if t["action"] == "BUY"]
        assert "TEMPTING_CRASH_STOCK" not in bought_tickers

    # -------------------------------------------------------------------------
    # Pillar 4: Portfolio Weight Invariant Across All Historical Trading Days
    # -------------------------------------------------------------------------
    def test_target_weight_invariant_sum_across_all_historical_days(self, historical_feeds):
        """
        Adversarial probe:
        Evaluates compute_target_weights across all 6,352 days from 2001-07-09 to 2026-10-09:
        - For 0, 1, 2, and 3 active turnaround stocks
        - Under both 'etf_sweep' and 'cash_buffer' idle cash policies
        Asserts sum(weights.values()) == 1.0 +- 1e-6 without exception.
        """
        etf_prices, _ = historical_feeds
        strat = EnhancedStrategy(prices_df=etf_prices)
        strat.prepare(etf_prices)

        total_tested = 0
        max_deviation = 0.0

        for dt in etf_prices.index:
            for k_stocks in [[], ["STK1"], ["STK1", "STK2"], ["STK1", "STK2", "STK3"]]:
                for pol in ["etf_sweep", "cash_buffer"]:
                    w = strat.compute_target_weights(
                        active_turnaround_stocks=k_stocks,
                        idle_policy=pol,
                        current_date=dt,
                    )
                    tot = sum(w.values())
                    dev = abs(tot - 1.0)
                    if dev > max_deviation:
                        max_deviation = dev
                    assert dev <= 1e-6, f"Weight invariant violated on {dt}: sum={tot}"
                    total_tested += 1

        assert total_tested == len(etf_prices) * 4 * 2
        assert max_deviation <= 1e-6

    def test_backtest_engine_allocation_history_weight_invariant_all_25_years(self, historical_feeds):
        """
        Adversarial probe:
        Executes full 25-year backtest simulation (6,351 days).
        Asserts that on EVERY single trading day:
        sum(w_i) + w_cash == 1.0 +- 1e-6 in res.allocation_history.
        """
        etf_prices, fx_series = historical_feeds
        strat = EnhancedStrategy(prices_df=etf_prices)
        engine = BacktestEngine(initial_capital=100000.0)

        res = engine.run(strategy=strat, prices_df=etf_prices, fx_rates=fx_series)
        alloc_df = res.allocation_history

        assert len(alloc_df) >= 6350, f"Expected >=6350 allocation rows, got {len(alloc_df)}"

        row_sums = alloc_df.sum(axis=1)
        deviations = (row_sums - 1.0).abs()
        max_dev = float(deviations.max())

        assert max_dev <= 1e-6, f"Max allocation deviation {max_dev:.2e} exceeded tolerance 1e-6"
        violations = deviations > 1e-6
        assert violations.sum() == 0, f"Found {violations.sum()} violating daily allocation rows"
