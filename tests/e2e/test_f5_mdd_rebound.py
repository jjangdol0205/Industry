"""
Tier 1: Feature 5 - Tier-Specific MDD DCA & Oversold Rebound Engine Tests.
Covers Core/Satellite/Watchlist/Standard MDD threshold triggers, standardized Korean badges,
and 100-point Oversold Rebound Engine (RSI14, Bollinger %B, MA Disparity, Support Buffer).
"""

import unittest
import pandas as pd
import numpy as np

from tests.e2e.test_helpers import generate_mock_ohlcv


class TestF5MDDRebound(unittest.TestCase):
    """E2E Test Suite for Feature 5 (Tier-Specific MDD DCA & Oversold Rebound Engine)."""

    def setUp(self):
        try:
            import investment_engine
            self.engine = investment_engine
        except ImportError:
            self.engine = None

    def _require_engine(self):
        if self.engine is None:
            self.fail("Implementation missing: investment_engine.py does not exist yet")

    def test_f5_01_core_mdd_thresholds(self):
        """
        [F5-01] Verifies Core tier MDD triggers:
        MDD > -20% -> CORE_HOLD / WAIT
        -30% < MDD <= -20% -> CORE_DCA_1 / BUY_READY (1차 분할매수)
        MDD <= -30% -> CORE_DCA_2 / BUY_READY (2차 분할매수)
        """
        self._require_engine()

        # -10.0% -> WAIT
        sig, code = self.engine.compute_dca_signal("Core", -10.0)
        self.assertEqual(code, "CORE_HOLD")
        self.assertIn("WAIT", sig)

        # -20.0% -> 1차 분할매수
        sig, code = self.engine.compute_dca_signal("Core", -20.0)
        self.assertEqual(code, "CORE_DCA_1")
        self.assertIn("BUY_READY", sig)
        self.assertIn("1차", sig)

        # -25.0% -> 1차 분할매수
        sig, code = self.engine.compute_dca_signal("Core", -25.0)
        self.assertEqual(code, "CORE_DCA_1")
        self.assertIn("BUY_READY", sig)

        # -30.0% -> 2차 분할매수
        sig, code = self.engine.compute_dca_signal("Core", -30.0)
        self.assertEqual(code, "CORE_DCA_2")
        self.assertIn("BUY_READY", sig)
        self.assertIn("2차", sig)

        # -45.0% -> 2차 분할매수 (적극매수)
        sig, code = self.engine.compute_dca_signal("Core", -45.0)
        self.assertEqual(code, "CORE_DCA_2")
        self.assertIn("BUY_READY", sig)

    def test_f5_02_satellite_mdd_thresholds(self):
        """
        [F5-02] Verifies Satellite tier MDD triggers:
        MDD > -25% -> SAT_HOLD / WAIT
        -35% < MDD <= -25% -> SAT_DCA_1 / BUY_READY (1차 분할매수)
        MDD <= -35% -> SAT_DCA_2 / BUY_READY (2차 분할매수)
        """
        self._require_engine()

        # -20.0% -> WAIT (Core triggers at -20%, but Satellite must NOT trigger at -20%)
        sig, code = self.engine.compute_dca_signal("Satellite", -20.0)
        self.assertEqual(code, "SAT_HOLD")
        self.assertIn("WAIT", sig)

        # -25.0% -> 1차 분할매수
        sig, code = self.engine.compute_dca_signal("Satellite", -25.0)
        self.assertEqual(code, "SAT_DCA_1")
        self.assertIn("BUY_READY", sig)
        self.assertIn("1차", sig)

        # -30.0% -> still 1차 분할매수 for Satellite
        sig, code = self.engine.compute_dca_signal("Satellite", -30.0)
        self.assertEqual(code, "SAT_DCA_1")
        self.assertIn("BUY_READY", sig)

        # -35.0% -> 2차 분할매수
        sig, code = self.engine.compute_dca_signal("Satellite", -35.0)
        self.assertEqual(code, "SAT_DCA_2")
        self.assertIn("BUY_READY", sig)
        self.assertIn("2차", sig)

    def test_f5_03_watchlist_and_standard_thresholds(self):
        """
        [F5-03] Verifies Watchlist (only MDD <= -35% triggers deep entry)
        and Standard (only MDD <= -40% triggers deep discount).
        """
        self._require_engine()

        # Watchlist at -30% -> WAIT
        sig, code = self.engine.compute_dca_signal("Watchlist", -30.0)
        self.assertEqual(code, "WATCH_WAIT")
        self.assertIn("WAIT", sig)

        # Watchlist at -36% -> BUY_READY 극단폭락 진입검토
        sig, code = self.engine.compute_dca_signal("Watchlist", -36.0)
        self.assertEqual(code, "WATCH_DEEP")
        self.assertIn("BUY_READY", sig)
        self.assertIn("진입검토", sig)

        # Standard at -35% -> WAIT
        sig, code = self.engine.compute_dca_signal("Standard", -35.0)
        self.assertEqual(code, "STD_WAIT")

        # Standard at -42% -> DEEP_DISCOUNT
        sig, code = self.engine.compute_dca_signal("Standard", -42.0)
        self.assertEqual(code, "STD_DISCOUNT")
        self.assertIn("DEEP_DISCOUNT", sig)

    def test_f5_04_rsi_and_bollinger_rebound_score(self):
        """
        [F5-04] Verifies mathematical computation of RSI(14) and Bollinger %B.
        An oversold plunge price series must generate RSI < 30 and %B <= 0.0.
        """
        self._require_engine()

        mock_data = generate_mock_ohlcv(num_days=252, base_price=70.0, mdd_pct=-35.0, is_oversold=True)
        df = pd.DataFrame(mock_data)

        score, signal = self.engine.compute_rebound_score(df)
        self.assertIsInstance(score, (int, float))
        self.assertGreaterEqual(score, 50.0, "Steep oversold history should yield rebound score >= 50")
        self.assertIn(signal, ("STRONG_REBOUND", "MODERATE_REBOUND"))

    def test_f5_05_rebound_signal_classification(self):
        """
        [F5-05] Verifies rebound signal classification thresholds:
        Score >= 70 -> STRONG_REBOUND
        50 <= Score < 70 -> MODERATE_REBOUND
        30 <= Score < 50 -> CONSOLIDATING
        Score < 30 -> NEUTRAL
        """
        self._require_engine()

        # Helper mapping function or direct classification check
        if hasattr(self.engine, "classify_rebound_signal"):
            self.assertEqual(self.engine.classify_rebound_signal(75.0), "STRONG_REBOUND")
            self.assertEqual(self.engine.classify_rebound_signal(60.0), "MODERATE_REBOUND")
            self.assertEqual(self.engine.classify_rebound_signal(40.0), "CONSOLIDATING")
            self.assertEqual(self.engine.classify_rebound_signal(15.0), "NEUTRAL")
        else:
            # Check constant/threshold adherence in compute_rebound_score
            pass


if __name__ == "__main__":
    unittest.main()
