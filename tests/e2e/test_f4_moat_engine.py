"""
Tier 1: Feature 4 - 4-Stage Moat & Margin Engine (S_moat) Tests.
Covers 100-point quantitative scoring (market dominance, OPM, ROE, GPM, growth, D/E ratio)
and objective tier assignment (Core, Satellite, Watchlist, Standard).
"""

import unittest

class TestF4MoatEngine(unittest.TestCase):
    """E2E Test Suite for Feature 4 (4-Stage Moat & Margin Quantitative Engine)."""

    def setUp(self):
        try:
            import investment_engine
            self.engine = investment_engine
        except ImportError:
            self.engine = None

    def _require_engine(self):
        if self.engine is None:
            self.fail("Implementation missing: investment_engine.py does not exist yet")

    def test_f4_01_core_tier_classification(self):
        """
        [F4-01] Verifies that a high-moat, high-margin monopoly (e.g. NVDA, ASML:
        OPM >= 22%, ROE >= 15%, Dominance >= 18, S_moat >= 75) is classified as 'Core'.
        """
        self._require_engine()
        nvda_metrics = {
            "ticker": "NVDA",
            "name": "NVIDIA Corp",
            "op_margin_ttm": 0.55,       # 55% -> 25 pts
            "roe": 0.65,                 # 65% -> 20 pts
            "gross_margin_ttm": 0.75,    # 75% -> 10 pts
            "revenue_growth": 0.40,      # 40% -> 10 pts
            "debt_to_equity": 45.0,      # 45% -> 10 pts
            "market_dominance": 25,      # Monopoly -> 25 pts
        }
        tier, score = self.engine.evaluate_stock_tier(nvda_metrics)
        self.assertEqual(tier, "Core", f"Expected 'Core', got '{tier}'")
        self.assertGreaterEqual(score, 75.0, f"Expected Moat score >= 75, got {score}")
        self.assertLessEqual(score, 100.0)

    def test_f4_02_satellite_tier_classification(self):
        """
        [F4-02] Verifies that a high-growth alpha company (e.g. Vertiv / VRT:
        S_moat >= 60, Growth >= 15% or Dominance >= 18, OPM >= 12%) is classified as 'Satellite'.
        """
        self._require_engine()
        vrt_metrics = {
            "ticker": "VRT",
            "name": "Vertiv Holdings",
            "op_margin_ttm": 0.18,       # 18% -> 15 pts
            "roe": 0.22,                 # 22% -> 16 pts
            "gross_margin_ttm": 0.35,    # 35% -> 4 pts
            "revenue_growth": 0.26,      # 26% -> 10 pts
            "debt_to_equity": 90.0,      # 90% -> 7 pts
            "market_dominance": 18,      # Top 2-3 Oligopoly -> 18 pts
        }
        tier, score = self.engine.evaluate_stock_tier(vrt_metrics)
        self.assertEqual(tier, "Satellite", f"Expected 'Satellite', got '{tier}'")
        self.assertGreaterEqual(score, 60.0, f"Expected Moat score >= 60, got {score}")
        self.assertLess(score, 75.0, "Score should not trigger Core without meeting Core criteria")

    def test_f4_03_watchlist_tier_classification(self):
        """
        [F4-03] Verifies that an emerging niche stock with moderate moat (S_moat >= 50
        but not qualifying for Core or Satellite) is assigned to 'Watchlist'.
        """
        self._require_engine()
        niche_metrics = {
            "ticker": "NICHE",
            "name": "Emerging Niche Tech",
            "op_margin_ttm": 0.10,       # 10% -> 5 pts
            "roe": 0.10,                 # 10% -> 6 pts
            "gross_margin_ttm": 0.30,    # 30% -> 4 pts
            "revenue_growth": 0.12,      # 12% -> 3 pts
            "debt_to_equity": 60.0,      # 60% -> 7 pts
            "market_dominance": 25,      # High IP niche -> 25 pts
        }
        tier, score = self.engine.evaluate_stock_tier(niche_metrics)
        self.assertEqual(tier, "Watchlist", f"Expected 'Watchlist', got '{tier}'")
        self.assertGreaterEqual(score, 50.0)

    def test_f4_04_standard_tier_classification(self):
        """
        [F4-04] Verifies that standard commodity or low-margin competitors are classified as 'Standard'.
        """
        self._require_engine()
        commodity_metrics = {
            "ticker": "COMM",
            "name": "Commodity Parts Supplier",
            "op_margin_ttm": 0.04,       # 4% -> 0 pts
            "roe": 0.05,                 # 5% -> 0 pts
            "gross_margin_ttm": 0.15,    # 15% -> 0 pts
            "revenue_growth": 0.02,      # 2% -> 0 pts
            "debt_to_equity": 180.0,     # 180% -> 0 pts
            "market_dominance": 0,       # Commodity -> 0 pts
        }
        tier, score = self.engine.evaluate_stock_tier(commodity_metrics)
        self.assertEqual(tier, "Standard", f"Expected 'Standard', got '{tier}'")
        self.assertLess(score, 50.0)

    def test_f4_05_moat_score_components_summation(self):
        """
        [F4-05] Verifies exact sub-score breakdown summation:
        S_moat = S_market_dominance (25) + S_opm (25) + S_roe (20) + S_gpm (10) + S_growth (10) + S_fin (10).
        """
        self._require_engine()
        # Perfect 100 scenario
        perfect_metrics = {
            "op_margin_ttm": 0.40,       # >= 35% -> 25
            "roe": 0.35,                 # >= 30% -> 20
            "gross_margin_ttm": 0.60,    # >= 55% -> 10
            "revenue_growth": 0.30,      # >= 25% -> 10
            "debt_to_equity": 30.0,      # <= 50% -> 10
            "market_dominance": 25,      # Monopoly -> 25
        }
        tier, score = self.engine.evaluate_stock_tier(perfect_metrics)
        self.assertEqual(score, 100.0, f"Perfect metrics should sum to exactly 100, got {score}")
        self.assertEqual(tier, "Core")


if __name__ == "__main__":
    unittest.main()
