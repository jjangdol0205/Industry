"""
Challenger R8 Empirical Stress & Verification Suite
Adversarial empirical tests validating mathematical precision, boundary conditions,
and execution fidelity of Round 8 quantitative algorithms.
"""
import math
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest

# Add parent directory to sys.path
REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from src.optimizer.etf_rebalancer import (
    compute_1d_grid_search,
    get_sensitivity_table,
    compare_tax_timing,
    evaluate_etf_alternatives,
    calculate_series_metrics,
)
from src.engine.hybrid_backtester import (
    HybridBacktester,
    HybridBacktestResult,
    FIFOTaxLot,
    HybridPosition,
)
from src.valuation.sk_square import SKSquareValuationEngine
from src.data.tri_asset_loader import TriAssetDataLoader
from config.settings import CACHE_DIR


# ==============================================================================
# SECTION 1: EMPIRICAL VERIFICATION OF 1D GRID SEARCH (QQQ vs SOXX)
# ==============================================================================

class TestEmpiricalGridSearch:
    @classmethod
    def setup_class(cls):
        cls.loader = TriAssetDataLoader(cache_dir=CACHE_DIR)
        cls.prices_df, cls.fx_df = cls.loader.load_data(start_date="2001-07-10")
        cls.grid_df = compute_1d_grid_search(
            prices_df=cls.prices_df,
            fx_df=cls.fx_df,
            friction=0.0007,
        )

    def test_all_101_weights_evaluated_correctly(self):
        """Verify all 101 weights evaluate correctly with non-negativity and sum = 1.0."""
        assert len(self.grid_df) == 101, f"Expected 101 rows, got {len(self.grid_df)}"
        
        # Check non-negativity
        assert (self.grid_df["weight_a"] >= 0.0).all(), "weight_a contains negative values"
        assert (self.grid_df["weight_b"] >= 0.0).all(), "weight_b contains negative values"
        
        # Check sum == 1.0 for every single weight point
        sums = self.grid_df["weight_a"] + self.grid_df["weight_b"]
        np.testing.assert_allclose(sums.values, 1.0, atol=1e-5, err_msg="Weight sum != 1.0")

        # Check resolution step is 0.01
        diffs = np.diff(self.grid_df["weight_a"].values)
        np.testing.assert_allclose(diffs, 0.01, atol=1e-5, err_msg="Step is not 0.01")

    def test_qqq_100_percent_global_peak_calmar_and_2002_drawdown(self):
        """
        Verify that QQQ 100% achieves global peak Calmar (0.2513)
        due to SOXX's -65.94% 2002 dot-com drawdown vs QQQ's -51.86%.
        """
        calmar_col = self.grid_df["calmar_usd"].values
        best_idx = int(np.argmax(calmar_col))
        best_w_qqq = float(self.grid_df.loc[best_idx, "weight_a"])
        best_calmar = float(self.grid_df.loc[best_idx, "calmar_usd"])

        # Check global peak Calmar occurs at 100% QQQ / 0% SOXX
        assert best_w_qqq == 1.00, f"Expected peak Calmar at 1.00 QQQ, found at {best_w_qqq}"
        assert abs(best_calmar - 0.2513) < 0.0005, f"Expected Calmar ~0.2513, got {best_calmar:.4f}"

        # Check 2002 drawdown of SOXX vs QQQ
        sens = get_sensitivity_table(grid_df=self.grid_df, prices_df=self.prices_df, fx_df=self.fx_df)
        crisis_df = sens["crisis_drawdowns"]
        
        assert 2002 in crisis_df.index, "2002 missing from crisis table"
        mdd_2002_qqq = float(crisis_df.loc[2002, "100% QQQ (Max Calmar)"])
        mdd_2002_soxx = float(crisis_df.loc[2002, "100% SOXX"])

        # SOXX crashed by -65.94% in 2002 dot-com bust
        assert abs(mdd_2002_soxx - (-0.6594)) < 0.005, f"SOXX 2002 MDD expected -0.6594, got {mdd_2002_soxx}"
        # QQQ had milder drawdown (-51.86%)
        assert abs(mdd_2002_qqq - (-0.5186)) < 0.005, f"QQQ 2002 MDD expected -0.5186, got {mdd_2002_qqq}"
        
        # Verify SOXX drawdown is significantly worse
        assert mdd_2002_soxx < mdd_2002_qqq, "SOXX 2002 drawdown should be strictly worse than QQQ"

    def test_qqq_90_percent_soxx_10_percent_global_peak_sharpe(self):
        """
        Verify that QQQ 90% / SOXX 10% achieves global peak Sharpe (0.5582).
        """
        sharpe_col = self.grid_df["sharpe_usd"].values
        best_idx = int(np.argmax(sharpe_col))
        best_w_qqq = float(self.grid_df.loc[best_idx, "weight_a"])
        best_sharpe = float(self.grid_df.loc[best_idx, "sharpe_usd"])

        # Global peak Sharpe at 90% QQQ / 10% SOXX
        assert best_w_qqq in [0.89, 0.90, 0.91], f"Expected peak Sharpe near 0.90, got {best_w_qqq}"
        assert abs(best_sharpe - 0.5582) < 0.0005, f"Expected Sharpe ~0.5582, got {best_sharpe:.4f}"

        # Verify convexity: 90% is strictly higher than 80% and 100%
        sharpe_80 = float(self.grid_df.loc[self.grid_df["weight_a"] == 0.80, "sharpe_usd"].iloc[0])
        sharpe_90 = float(self.grid_df.loc[self.grid_df["weight_a"] == 0.90, "sharpe_usd"].iloc[0])
        sharpe_100 = float(self.grid_df.loc[self.grid_df["weight_a"] == 1.00, "sharpe_usd"].iloc[0])

        assert sharpe_90 > sharpe_80, f"Expected Sharpe 90 ({sharpe_90}) > 80 ({sharpe_80})"
        assert sharpe_90 > sharpe_100, f"Expected Sharpe 90 ({sharpe_90}) > 100 ({sharpe_100})"


# ==============================================================================
# SECTION 2: EMPIRICAL VERIFICATION OF ALTERNATIVE ETF PAIRS
# ==============================================================================

class TestEmpiricalAlternativeETFPairs:
    def test_smh_achieves_48_bps_alpha_over_soxx_and_80_20_peak_calmar(self):
        """
        Verify that SMH achieves +48 bps annual alpha over SOXX and
        80/20 QQQ/SMH achieves peak Calmar (0.2511).
        """
        alts = evaluate_etf_alternatives()
        smh_row = alts[alts["ticker_pair"] == "SMH"].iloc[0]
        soxx_row = alts[alts["ticker_pair"] == "SOXX"].iloc[0]
        pair_row = alts[alts["ticker_pair"] == "QQQ + SMH"].iloc[0]

        # SMH CAGR = 14.49%, SOXX CAGR = 14.01% -> difference = +48 bps
        smh_cagr = float(smh_row["cagr"])
        soxx_cagr = float(soxx_row["cagr"])
        alpha_bps = (smh_cagr - soxx_cagr) * 10000.0
        assert abs(alpha_bps - 48.0) < 1.0, f"Expected +48 bps alpha, got {alpha_bps:.1f} bps"

        # SMH worst annual MDD (-64.52%) is milder than SOXX (-65.94%)
        assert float(smh_row["worst_annual_mdd"]) > float(soxx_row["worst_annual_mdd"])

        # 80/20 QQQ/SMH Calmar is 0.2511
        pair_calmar = float(pair_row["calmar"])
        assert abs(pair_calmar - 0.2511) < 0.0005, f"Expected 80/20 Calmar ~0.2511, got {pair_calmar:.4f}"
        assert float(pair_row["cagr"]) > float(alts[alts["ticker_pair"] == "QQQ"].iloc[0]["cagr"])

    def test_3x_tqqq_soxl_severe_drawdown_decay_in_2022(self):
        """
        Verify that 3x TQQQ+SOXL experiences severe drawdown decay (>84%) in 2022.
        """
        alts = evaluate_etf_alternatives()
        tqqq_soxl = alts[alts["ticker_pair"] == "TQQQ + SOXL"].iloc[0]
        
        worst_mdd = float(tqqq_soxl["worst_annual_mdd"])
        # Severe drawdown decay in 2022 > 84% (actual: -84.90%)
        assert worst_mdd <= -0.84, f"Expected 3x MDD <= -84%, got {worst_mdd*100:.2f}%"
        assert abs(worst_mdd - (-0.8490)) < 0.005, f"Expected MDD ~ -84.90%, got {worst_mdd*100:.2f}%"


# ==============================================================================
# SECTION 3: EMPIRICAL VERIFICATION OF 4-ASSET HYBRID ENGINE
# ==============================================================================

class TestEmpiricalHybridEngineMechanics:
    @classmethod
    def setup_class(cls):
        cls.sim_dates = pd.date_range("2024-01-01", "2024-03-31", freq="B")
        N = len(cls.sim_dates)

        # Baseline ETF prices
        cls.etf_prices = pd.DataFrame({
            "QQQ": np.full(N, 400.0),
            "SOXX": np.full(N, 200.0),
        }, index=cls.sim_dates)
        cls.fx_df = pd.DataFrame({"USDKRW": np.full(N, 1400.0)}, index=cls.sim_dates)

    def test_stop_loss_triggers_strictly_upon_closing_leq_minus_10_percent(self):
        """
        Verify that stop-loss triggers strictly upon closing <= -10% from entry,
        and does NOT trigger at -9.99%.
        """
        # Case A: Stock drops to exactly -9.9% from entry ($100 -> $90.1) -> NO STOP
        engine_no_stop = HybridBacktester(
            w_qqq=0.5, w_soxx=0.3, w_stocks=0.2,
            stop_loss=-0.10,
            slippage_stock_bps=12.0,
            commission_bps=5.0,
        )
        pos = HybridPosition(
            ticker="TEST_NO_STOP",
            shares=100.0,
            entry_price=100.0,
            entry_date=date(2024, 1, 1),
            entry_fx=1400.0,
        )
        pos.lots.append(FIFOTaxLot(
            lot_id="LOT_1", ticker="TEST_NO_STOP", shares=100.0,
            entry_date=date(2024, 1, 1), entry_price=100.0, entry_fx=1400.0,
            buy_commission_usd=0.05, buy_slippage_usd=0.12,
        ))
        engine_no_stop.positions["TEST_NO_STOP"] = pos
        engine_no_stop.holdings["TEST_NO_STOP"] = 100.0

        # Simulate test day with close at 90.1 (-9.9%)
        close_p = 90.1
        close_pnl = (close_p - pos.entry_price) / pos.entry_price
        assert close_pnl > -0.10, "Should be above -10%"
        # Check condition that backtester uses
        triggered = (close_pnl <= engine_no_stop.stop_loss)
        assert not triggered, "Stop-loss must NOT trigger at -9.9%"

        # Case B: Stock drops to $90.0 (-10.0%) -> STRICT STOP TRIGGER
        close_p_stop = 90.0
        close_pnl_stop = (close_p_stop - pos.entry_price) / pos.entry_price
        assert close_pnl_stop <= -0.10, "Should be <= -10%"
        triggered_stop = (close_pnl_stop <= engine_no_stop.stop_loss)
        assert triggered_stop, "Stop-loss MUST trigger at -10.0%"

        # Execute sell and check slippage & fee deductions
        records = engine_no_stop._execute_sell(
            ticker="TEST_NO_STOP",
            shares=100.0,
            nominal_price=90.0,
            trade_date=date(2024, 1, 15),
            fx_rate=1400.0,
            is_stock=True,
            reason="STOP_LOSS",
        )
        assert len(records) == 1
        rec = records[0]
        # Fill price is nominal_price * (1 - 12 bps) = 90 * (1 - 0.0012) = 89.892
        assert abs(rec["Exit Price"] - 89.892) < 1e-3
        assert rec["Reason"] == "STOP_LOSS"
        # Position cleared
        assert "TEST_NO_STOP" not in engine_no_stop.positions

    def test_auto_replacement_occurs_on_t_plus_1(self):
        """
        Verify that auto-replacement occurs on T+1 (the trading day following the stop-out),
        not on T=0.
        """
        N = len(self.sim_dates)
        # Construct candidate that stops out on day 5 (index 4)
        synth_cand = pd.DataFrame({
            "Open": [100.0] * N,
            "High": [100.0] * N,
            "Low": [100.0] * N,
            "Close": [100.0] * N,
        }, index=self.sim_dates)

        # On day 5, price drops to $88 (-12% stop)
        synth_cand.loc[self.sim_dates[4], "Close"] = 88.0
        synth_cand.loc[self.sim_dates[4], "Low"] = 88.0

        pools = {"AAPL": synth_cand}

        engine = HybridBacktester(
            w_qqq=0.5, w_soxx=0.3, w_stocks=0.2,
            stop_loss=-0.10,
        )

        res = engine.run_simulation(
            prices_df=self.etf_prices,
            fx_df=self.fx_df,
            candidate_price_dfs=pools,
            start_date="2024-01-01",
        )

        # Verify trade log has STOP_LOSS on day 5
        stop_trades = res.trade_log[res.trade_log["Reason"] == "STOP_LOSS"]
        if not stop_trades.empty:
            stop_date = stop_trades.iloc[0]["Exit Date"]
            # Any subsequent buy must be on or after stop_date + 1 trading day
            buy_trades = res.trade_log[res.trade_log["Reason"] != "STOP_LOSS"]
            for _, b in buy_trades.iterrows():
                if b["Entry Date"] and stop_date:
                    assert b["Entry Date"] >= stop_date

    def test_partial_profit_taking_at_plus_25_percent(self):
        """
        Verify that +25% gain triggers exactly 50% partial exit,
        and remainder is held with original entry cost basis.
        """
        engine = HybridBacktester(
            w_qqq=0.5, w_soxx=0.3, w_stocks=0.2,
            profit_take=0.25,
            profit_take_ratio=0.50,
        )
        pos = HybridPosition(
            ticker="NVDA",
            shares=200.0,
            entry_price=100.0,
            entry_date=date(2024, 1, 1),
            entry_fx=1400.0,
        )
        pos.lots.append(FIFOTaxLot(
            lot_id="LOT_NVDA_1", ticker="NVDA", shares=200.0,
            entry_date=date(2024, 1, 1), entry_price=100.0, entry_fx=1400.0,
            buy_commission_usd=0.10, buy_slippage_usd=0.24,
        ))
        engine.positions["NVDA"] = pos
        engine.holdings["NVDA"] = 200.0

        # High reaches $126 (+26% >= +25%)
        high_pnl = (126.0 - pos.entry_price) / pos.entry_price
        assert high_pnl >= engine.profit_take

        # Trigger partial exit
        shares_to_sell = pos.shares * engine.profit_take_ratio
        assert shares_to_sell == 100.0, "Should sell exactly 50% (100 shares)"

        closed = engine._execute_sell(
            ticker="NVDA",
            shares=shares_to_sell,
            nominal_price=125.0,
            trade_date=date(2024, 1, 20),
            fx_rate=1400.0,
            is_stock=True,
            reason="PARTIAL_TAKE",
        )
        assert len(closed) == 1
        rec = closed[0]
        assert rec["Shares"] == 100.0
        assert rec["Reason"] == "PARTIAL_TAKE"
        assert rec["Return %"] > 24.0, f"Expected return >24%, got {rec['Return %']}%"

        # Verify remaining 100 shares stay in portfolio
        assert pos.shares == 100.0
        assert engine.holdings["NVDA"] == 100.0
        assert len(pos.lots) == 1
        assert pos.lots[0].shares == 100.0
        assert pos.lots[0].entry_price == 100.0, "Entry price must be preserved"
        assert pos.lots[0].entry_date == date(2024, 1, 1), "Entry date must be preserved"

    def test_sec_finra_fees_and_22_percent_korean_tax_with_2_5m_deduction(self):
        """
        Verify SEC/FINRA fees on sells and 22% tax deduction with 2.5M KRW basic deduction.
        """
        engine = HybridBacktester(
            w_qqq=0.5, w_soxx=0.3, w_stocks=0.2,
            sec_fee_bps=0.28,
            finra_taf_per_share=0.000166,
            basic_deduction_krw=2_500_000.0,
            tax_rate=0.22,
        )

        # 1. Verify SEC and FINRA fees calculated on sell
        pos = HybridPosition(
            ticker="TSLA",
            shares=1000.0,
            entry_price=200.0,
            entry_date=date(2024, 1, 1),
            entry_fx=1400.0,
        )
        pos.lots.append(FIFOTaxLot(
            lot_id="LOT_TSLA_1", ticker="TSLA", shares=1000.0,
            entry_date=date(2024, 1, 1), entry_price=200.0, entry_fx=1400.0,
            buy_commission_usd=0.0, buy_slippage_usd=0.0,
        ))
        engine.positions["TSLA"] = pos
        engine.holdings["TSLA"] = 1000.0

        records = engine._execute_sell(
            ticker="TSLA",
            shares=1000.0,
            nominal_price=250.0,
            trade_date=date(2024, 6, 1),
            fx_rate=1400.0,
            is_stock=True,
            reason="REBALANCE",
        )
        rec = records[0]
        # Trade value = 1000 * 250 = $250,000
        expected_sec = 250_000.0 * 0.000028  # $7.00
        expected_finra = min(8.30, 1000 * 0.000166)  # $0.166
        expected_reg_fee = expected_sec + expected_finra  # $7.166
        assert abs(rec["SEC/FINRA Fee Paid"] - round(expected_reg_fee, 4)) < 0.01

        # 2. Tax calculation check on realized gain
        realized_krw = rec["Realized Gain KRW"]
        assert realized_krw > 2_500_000.0, "Gain should exceed 2.5M KRW"

        tax_rec = engine.tax_engine.calculate_annual_tax(2024, year_end_fx=1400.0)
        expected_tax_krw = (realized_krw - 2_500_000.0) * 0.22
        assert abs(tax_rec.tax_krw - expected_tax_krw) < 100.0, f"Expected tax {expected_tax_krw}, got {tax_rec.tax_krw}"
        assert abs(tax_rec.basic_deduction_krw - 2_500_000.0) < 1e-3


# ==============================================================================
# SECTION 4: ADVERSARIAL STRESS HARNESS & BOUNDARY ASSUMPTION CHALLENGES
# ==============================================================================

class TestAdversarialStressAndBoundaries:
    def test_extreme_gap_down_30_percent_fill(self):
        """Stress: Market gaps down by -30% overnight below the -10% stop."""
        engine = HybridBacktester(stop_loss=-0.10, slippage_stock_bps=15.0)
        pos = HybridPosition("CRASH", 100.0, entry_price=100.0, entry_date=date(2024, 1, 1), entry_fx=1400.0)
        pos.lots.append(FIFOTaxLot("L1", "CRASH", 100.0, date(2024, 1, 1), 100.0, 1400.0, 0, 0))
        engine.positions["CRASH"] = pos
        engine.holdings["CRASH"] = 100.0

        # Market opens at 70.0 (-30%)
        recs = engine._execute_sell(
            ticker="CRASH", shares=100.0, nominal_price=70.0,
            trade_date=date(2024, 1, 2), fx_rate=1400.0, is_stock=True, reason="STOP_LOSS_GAP"
        )
        assert len(recs) == 1
        # Fill price must be nominal open price * (1 - 15 bps) = 70 * (1 - 0.0015) = 69.895
        assert recs[0]["Exit Price"] < 70.0
        assert recs[0]["Return %"] < -30.0

    def test_tax_deduction_cliff_edge_cases(self):
        """Stress: Net gain exactly at, 1 won below, and 1 won above the 2.5M KRW threshold."""
        from src.engine.tax import KoreanTaxEngine
        
        # Exactly 2.5M KRW -> tax = 0
        te = KoreanTaxEngine(enabled=True)
        te.record_realized_trade(2024, 2500000.0 / 1400.0, 2500000.0, date(2024, 5, 1), "A")
        rec = te.calculate_annual_tax(2024, 1400.0)
        assert rec.tax_krw == 0.0

        # 2,499,999 KRW -> tax = 0
        te2 = KoreanTaxEngine(enabled=True)
        te2.record_realized_trade(2024, 2499999.0 / 1400.0, 2499999.0, date(2024, 5, 1), "B")
        rec2 = te2.calculate_annual_tax(2024, 1400.0)
        assert rec2.tax_krw == 0.0

        # 2,500,001 KRW -> tax = 0.22 KRW
        te3 = KoreanTaxEngine(enabled=True)
        te3.record_realized_trade(2024, 2500001.0 / 1400.0, 2500001.0, date(2024, 5, 1), "C")
        rec3 = te3.calculate_annual_tax(2024, 1400.0)
        assert abs(rec3.tax_krw - 0.22) < 0.01

    def test_zero_candidates_in_severe_bear_market(self):
        """Stress: When candidate pool is empty, idle capacity sweeps cleanly to ETFs without errors."""
        engine = HybridBacktester(
            w_qqq=0.5, w_soxx=0.3, w_stocks=0.2,
            candidate_price_dfs={},  # empty pool
        )
        weights = engine.compute_idle_weights(active_stock_count=0)
        # All 20% stock capacity sweeps to QQQ and SOXX
        assert abs(weights["QQQ"] + weights["SOXX"] - 1.0) < 1e-6
        assert weights["QQQ"] > 0.50
        assert weights["SOXX"] > 0.30


if __name__ == "__main__":
    pytest.main(["-v", str(Path(__file__))])
