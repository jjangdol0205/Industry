"""
Empirical Challenger Stress Test Harness for Milestone 1.
Probes Survivorship Bias, Lookahead Bias, Rolling 52-Week Low under Volatility Spikes,
and Discretionary Risk-Reward Exclusion Gates.
"""
import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

# Add repo to sys.path
REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from src.data.universe import UniverseManager, SECTOR_MAP
from src.screening.rolling_low import RollingLowScreener, calculate_rsi
from src.screening.exclusion_gates import ExclusionGates
from src.screening.turnaround_scorer import TurnaroundScorer, PITFundamentalStore
from src.screening.weekly_selector import WeeklySelector
from src.models.schemas import ExclusionReason


class TestSurvivorshipBiasEmpirical(unittest.TestCase):
    """Probes historical bankruptcies and delistings in point-in-time universe."""

    @classmethod
    def setUpClass(cls):
        cls.mgr = UniverseManager()

    def test_lehman_brothers_presence_and_absence(self):
        """LEH must be present during active tenure and absent after delisting."""
        # Active dates
        self.assertTrue(self.mgr.is_member_at("LEH", "2001-07-10"))
        self.assertTrue(self.mgr.is_member_at("LEH", "2005-01-01"))
        self.assertTrue(self.mgr.is_member_at("LEH", "2008-01-01"))
        self.assertTrue(self.mgr.is_member_at("LEH", "2008-09-17"))  # Exact end date

        # Post-bankruptcy / delisting dates
        self.assertFalse(self.mgr.is_member_at("LEH", "2008-09-18"))
        self.assertFalse(self.mgr.is_member_at("LEH", "2009-01-01"))
        self.assertFalse(self.mgr.is_member_at("LEH", "2020-01-01"))

    def test_aamrq_presence_and_absence(self):
        """AAMRQ must be present until March 2003 and absent thereafter."""
        self.assertTrue(self.mgr.is_member_at("AAMRQ", "2001-07-10"))
        self.assertTrue(self.mgr.is_member_at("AAMRQ", "2003-03-14"))  # Exact end date
        self.assertFalse(self.mgr.is_member_at("AAMRQ", "2003-03-15"))
        self.assertFalse(self.mgr.is_member_at("AAMRQ", "2005-01-01"))

    def test_enron_and_worldcom_delistings(self):
        """ENRNQ and WCOEQ presence during dot-com bust and absence after bankruptcy."""
        # Enron end date: 2001-11-30
        self.assertTrue(self.mgr.is_member_at("ENRNQ", "2001-07-10"))
        self.assertTrue(self.mgr.is_member_at("ENRNQ", "2001-11-30"))
        self.assertFalse(self.mgr.is_member_at("ENRNQ", "2001-12-01"))

        # WorldCom end date: 2002-05-15
        self.assertTrue(self.mgr.is_member_at("WCOEQ", "2001-07-10"))
        self.assertTrue(self.mgr.is_member_at("WCOEQ", "2002-05-15"))
        self.assertFalse(self.mgr.is_member_at("WCOEQ", "2002-05-16"))

    def test_bear_stearns_and_wamu(self):
        """BSC and WAMUQ presence during 2008 GFC and absence after takeover/failure."""
        # Bear Stearns end date: 2008-06-02
        self.assertTrue(self.mgr.is_member_at("BSC", "2008-01-01"))
        self.assertTrue(self.mgr.is_member_at("BSC", "2008-06-02"))
        self.assertFalse(self.mgr.is_member_at("BSC", "2008-06-03"))

        # Washington Mutual end date: 2008-09-30
        self.assertTrue(self.mgr.is_member_at("WAMUQ", "2008-01-01"))
        self.assertTrue(self.mgr.is_member_at("WAMUQ", "2008-09-30"))
        self.assertFalse(self.mgr.is_member_at("WAMUQ", "2008-10-01"))


class TestNewEntrantLookaheadEmpirical(unittest.TestCase):
    """Probes future index additions to guarantee zero lookahead bias."""

    @classmethod
    def setUpClass(cls):
        cls.mgr = UniverseManager()

    def test_nvidia_entry_discipline(self):
        """NVDA added 2001-11-30: must be excluded prior and included from entry date."""
        self.assertFalse(self.mgr.is_member_at("NVDA", "2001-07-10"))
        self.assertFalse(self.mgr.is_member_at("NVDA", "2001-11-29"))
        self.assertTrue(self.mgr.is_member_at("NVDA", "2001-11-30"))
        self.assertTrue(self.mgr.is_member_at("NVDA", "2002-01-01"))

    def test_tesla_entry_discipline(self):
        """TSLA added 2020-12-21: must be absent throughout 2001-2020 Dec 20."""
        self.assertFalse(self.mgr.is_member_at("TSLA", "2001-07-10"))
        self.assertFalse(self.mgr.is_member_at("TSLA", "2015-01-01"))
        self.assertFalse(self.mgr.is_member_at("TSLA", "2020-12-20"))
        self.assertTrue(self.mgr.is_member_at("TSLA", "2020-12-21"))
        self.assertTrue(self.mgr.is_member_at("TSLA", "2021-01-01"))

    def test_google_meta_uber_entry_discipline(self):
        """Probes other notable historical additions."""
        # GOOGL entered 2006-04-03
        self.assertFalse(self.mgr.is_member_at("GOOGL", "2006-04-02"))
        self.assertTrue(self.mgr.is_member_at("GOOGL", "2006-04-03"))

        # FB entered 2013-12-23
        self.assertFalse(self.mgr.is_member_at("FB", "2013-12-22"))
        self.assertTrue(self.mgr.is_member_at("FB", "2013-12-23"))

        # UBER entered 2023-12-18
        self.assertFalse(self.mgr.is_member_at("UBER", "2023-12-17"))
        self.assertTrue(self.mgr.is_member_at("UBER", "2023-12-18"))

    def test_probe_timezone_aware_crash(self):
        """
        Adversarial probe: yfinance and pandas tz-aware timestamps.
        Verifies that UniverseManager handles tz-aware timestamp without TypeError.
        """
        tz_timestamp = pd.Timestamp("2020-12-21", tz="America/New_York")
        # TSLA added on 2020-12-21: must evaluate cleanly to True without TypeError
        is_member = self.mgr.is_member_at("TSLA", tz_timestamp)
        self.assertTrue(is_member)

    def test_probe_weekly_selector_fallback_lookahead_bypass(self):
        """
        Adversarial probe: Verifies that WeeklySelector does NOT evaluate non-constituents
        when candidates in price_pools are not in the point-in-time universe.
        """
        selector = WeeklySelector(universe_manager=self.mgr)
        dates = pd.date_range("2004-01-01", "2005-01-01", freq="B")
        df = pd.DataFrame({
            "Open": [10.0]*len(dates), "High": [10.0]*len(dates), "Low": [10.0]*len(dates),
            "Close": [10.0]*len(dates), "Volume": [50_000_000.0]*len(dates)
        }, index=dates)

        # On 2005-01-01, TSLA is NOT a constituent (entered 2020-12-21).
        # Passing TSLA in candidate_price_dfs:
        res = selector.screen_weekly_candidates(
            as_of_date="2005-01-01",
            current_holdings=[],
            candidate_price_dfs={"TSLA": df}
        )
        # Lookahead fallback removed: evaluated list must be empty
        self.assertEqual(len(res.all_evaluated_candidates), 0)


class TestRollingLowScreenerVolatilitySpikes(unittest.TestCase):
    """Probes 252-day rolling window math across flash crashes, volatility spikes, and halts."""

    @classmethod
    def setUpClass(cls):
        cls.screener = RollingLowScreener(
            window=252,
            proximity_threshold=0.05,
            min_history_days=252,
            min_rsi=20.0,
            min_5d_return=-0.05,
        )

    def test_rolling_window_expiration_spike(self):
        """
        Oracle test: At day T=252, low is at Day 1 ($50).
        At day T=253, Day 1 drops out of the 252-day window, causing low_52w to jump upward.
        """
        dates = pd.date_range("2020-01-01", periods=254, freq="B")
        prices = [100.0] * 254
        prices[1] = 50.0  # Day 1 is the spike low

        df = pd.DataFrame(
            {"Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": [1_000_000.0] * 254},
            index=dates,
        )

        indicators = self.screener.compute_indicators(df)
        
        # At day 252 (Day 1 is within window 1..252): low_52w MUST be $50
        self.assertEqual(indicators.iloc[252]["low_52w"], 50.0)
        
        # At day 253 (window is 2..253, Day 1 expired): low_52w MUST jump to $100
        self.assertEqual(indicators.iloc[253]["low_52w"], 100.0)
        self.assertEqual(indicators.iloc[253]["low_proximity"], 0.0)

    def test_active_freefall_rejection(self):
        """
        During panic freefall (COVID crash simulation), stock hitting 52w low
        MUST be rejected by stabilization filters.
        """
        dates = pd.date_range("2020-01-01", periods=270, freq="B")
        prices = [100.0] * 250
        for i in range(1, 8):
            prices.append(100.0 * (1.0 - 0.06 * i))  # drops to 58.0
        for j in range(1, 14):
            prices.append(58.0 + (j * 0.2))

        df = pd.DataFrame(
            {"Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": [20_000_000.0] * 270},
            index=dates,
        )

        # Freefall peak: Day 256
        qual_freefall, metrics_freefall = self.screener.evaluate_candidate(df, dates[256])
        self.assertFalse(qual_freefall)
        self.assertFalse(metrics_freefall["is_stabilized"])

    def test_post_crash_catch22_empty_set(self):
        """
        Empirical Discovery: After a severe crash (-40% in 10 days),
        the condition (low_proximity <= 0.05) and (rsi_14 >= 20.0) is an EMPTY SET.
        By the time RSI recovers to >= 20.0, price has bounced > 5% above the low.
        """
        base = [100.0] * 250
        crash = list(np.linspace(100.0, 60.0, 11))
        
        qualified_any = False
        for bounce_pct in [0.01, 0.02, 0.03, 0.04, 0.049]:
            for bounce_days in [5, 10, 14, 20]:
                prices = base + crash + list(np.linspace(60.0, 60.0 * (1.0 + bounce_pct), bounce_days))
                df = pd.DataFrame({
                    "Open": prices, "High": prices, "Low": prices, "Close": prices,
                    "Volume": [20_000_000.0] * len(prices)
                }, index=pd.date_range("2020-01-01", periods=len(prices), freq="B"))
                q, _ = self.screener.evaluate_candidate(df, df.index[-1])
                if q:
                    qualified_any = True
                    break
        print(f"\n[CONFIRMED FINDING #7] Severe crash Catch-22 (proximity <= 5% vs RSI >= 20): qualified={qualified_any}")
        self.assertFalse(qualified_any)

    def test_probe_flat_series_rsi_distortion(self):
        """
        Adversarial probe: When a stock is completely flat for 20+ days (e.g. trading halt),
        calculate_rsi must output neutral 50.0 instead of distorted 100.0.
        """
        flat_prices = pd.Series([50.0] * 30)
        rsi = calculate_rsi(flat_prices)
        val = rsi.iloc[-1]
        self.assertEqual(val, 50.0)  # Correct neutral RSI on flat series


class TestExclusionGatesEmpirical(unittest.TestCase):
    """Probes liquidity gate ($20M), solvency gate, and sector concentration limits."""

    @classmethod
    def setUpClass(cls):
        cls.gates = ExclusionGates(
            min_dollar_volume=20_000_000.0,
            min_solvency_score=0.40,
            max_stocks_per_sector=1,
        )
        cls.mgr = UniverseManager()

    def test_probe_liquidity_gate_zero_dollar_volume_bypass(self):
        """
        Adversarial probe: Stock with $0.0 daily volume (halted or zero trading).
        Gate logic: `if avg_dv < min_dollar_volume:` properly rejects $0 volume as ILLIQUID.
        """
        passed, reasons = self.gates.evaluate_gates(
            ticker="DEAD",
            sector="Industrials",
            current_holdings=[],
            current_holding_sectors=[],
            metrics={"avg_dollar_volume_20d": 0.0, "solvency_score": 0.8, "turnaround_score": 0.8},
        )
        self.assertFalse(passed)
        self.assertIn(ExclusionReason.ILLIQUID, reasons)

    def test_solvency_gate_seeded_vs_unseeded_bankruptcies(self):
        """
        LEH has financial statement with solvency 0.10 -> properly rejected.
        AAMRQ has NO financial statements in pit_fundamentals.json -> defaults to 0.50 -> PASSES!
        """
        scorer = TurnaroundScorer()
        
        # LEH 2008 (seeded)
        s_leh, bd_leh = scorer.score_candidate("LEH", "2008-08-01")
        p_leh, r_leh = self.gates.evaluate_gates(
            "LEH", "Financials", [], [],
            {"avg_dollar_volume_20d": 50_000_000.0, "solvency_score": bd_leh["pillar3_solvency"], "turnaround_score": s_leh}
        )
        self.assertFalse(p_leh)
        self.assertIn(ExclusionReason.SOLVENCY_RISK, r_leh)

        # AAMRQ 2002 (unseeded)
        s_aamrq, bd_aamrq = scorer.score_candidate("AAMRQ", "2002-12-01")
        p_aamrq, r_aamrq = self.gates.evaluate_gates(
            "AAMRQ", "Industrials", [], [],
            {"avg_dollar_volume_20d": 50_000_000.0, "solvency_score": bd_aamrq["pillar3_solvency"], "turnaround_score": s_aamrq}
        )
        self.assertTrue(p_aamrq)
        self.assertNotIn(ExclusionReason.SOLVENCY_RISK, r_aamrq)
        self.assertEqual(bd_aamrq["pillar3_solvency"], 0.50)

    def test_probe_sector_mapping_starvation(self):
        """
        Adversarial probe: UniverseManager provides comprehensive GICS sector mapping.
        Holding AAPL (Information Technology) does NOT block buying non-tech companies like Ford (Consumer Discretionary).
        """
        holding_sectors = [self.mgr.get_sector("AAPL")]  # ["Information Technology"]
        self.assertEqual(holding_sectors[0], "Information Technology")

        ford_sector = self.mgr.get_sector("F")
        self.assertEqual(ford_sector, "Consumer Discretionary")

        passed_f, reasons_f = self.gates.evaluate_gates(
            ticker="F",
            sector=ford_sector,
            current_holdings=["AAPL"],
            current_holding_sectors=holding_sectors,
            metrics={"avg_dollar_volume_20d": 50_000_000.0, "solvency_score": 0.8, "turnaround_score": 0.8},
        )
        self.assertTrue(passed_f)
        self.assertNotIn(ExclusionReason.SECTOR_CAPACITY, reasons_f)


if __name__ == "__main__":
    unittest.main()
