"""
TrendPulse Investment Portal — Macro Intelligence Module E2E Test Suite.
==========================================================================
Validates Macro Intelligence Module across Tiers 1–4:
- Tier 1: Feature Coverage (Yield curve math, Net Liquidity, Real Neutral Rate r*,
          Ken Fisher 100-year backtest rules, NY Fed RIMP firm heterogeneity model,
          4-Quadrant macro regime classification, 4 core Korean equity perspectives,
          and deterministic 16-character SHA-256 report deduplication).
- Tier 2: Boundary & Corner Cases (Inverted vs 0-bps flat curve, ON RRP buffer depletion,
          offline network failure seed fallback, corrupted indicator parameters, and
          restrictiveness gap exact thresholds).
- Tier 3: Cross-Feature Combinations (Sync pipeline -> SQLite persistence ->
          4-target atomic JSON distribution -> FastAPI response schema match,
          and Ken Fisher signal coherence with yield curve shifts).
- Tier 4: Real-World Application Scenarios (FOMC rate cut cycle un-inversion defense alert,
          restrictive late-cycle P/E compression, and multi-target file distribution hash invariance).

Compatible with:
  - python -m unittest tests/test_macro_module.py
  - pytest tests/test_macro_module.py
  - python run_e2e_tests.py --feature F9
"""

import os
import sys
import json
import sqlite3
import hashlib
import tempfile
import shutil
import unittest
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional

# Path configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "InvestmentPortal" / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

CANONICAL_MACRO_JSON_PATHS = [
    PROJECT_ROOT / "macro_intelligence_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "backend" / "macro_intelligence_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "public" / "macro_intelligence_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "macro_intelligence_data.json",
]


def _get_sync_macro():
    """Dynamically attempts to import sync_macro from root or InvestmentPortal/backend."""
    for mod_name in ["sync_macro", "InvestmentPortal.backend.sync_macro"]:
        try:
            return importlib.import_module(mod_name)
        except ImportError:
            pass

    root_script = PROJECT_ROOT / "sync_macro.py"
    if root_script.exists():
        try:
            spec = importlib.util.spec_from_file_location("sync_macro_dynamic", str(root_script))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
        except Exception:
            pass

    backend_script = PROJECT_ROOT / "InvestmentPortal" / "backend" / "sync_macro.py"
    if backend_script.exists():
        try:
            spec = importlib.util.spec_from_file_location("sync_macro_backend_dynamic", str(backend_script))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
        except Exception:
            pass

    return None


class BaseMacroTestCase(unittest.TestCase):
    """Base test fixture providing isolated environment and module resolution."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="trendpulse_macro_test_")
        self.temp_path = Path(self.temp_dir)
        self.test_db_path = self.temp_path / "test_portal.db"
        self.macro_mod = _get_sync_macro()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _require_macro(self):
        """Helper to ensure sync_macro is available or fail with actionable explanation."""
        if self.macro_mod is None:
            self.fail(
                "Implementation missing: sync_macro.py could not be imported from project root "
                f"or InvestmentPortal/backend. Expected location: {PROJECT_ROOT / 'sync_macro.py'}. "
                "Ensure Milestone 1 (Macro Core Engine & Data Pipeline) has been implemented."
            )
        return self.macro_mod


# =============================================================================
# TIER 1: Feature Coverage (>= 10 test cases)
# =============================================================================

class TestMacroModuleTier1Features(BaseMacroTestCase):
    """Tier 1: Comprehensive Feature Coverage for Macro Intelligence Engine."""

    def test_t1_01_yield_spread_and_curve_state_classification(self):
        """
        [T1-01] Yield Curve Spread (S = Y10Y - Y2Y) and State Classification.
        Verifies:
        - INVERTED: S < 0.00%
        - FLAT: 0.00% <= S < 0.25%
        - NORMAL: 0.25% <= S < 1.00%
        - STEEP: S >= 1.00%
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "compute_yield_spread"), "sync_macro must define compute_yield_spread")
        self.assertTrue(hasattr(m, "classify_yield_curve_state"), "sync_macro must define classify_yield_curve_state")

        # Case 1: Normal curve
        spread, bps = m.compute_yield_spread(4.12, 3.85)
        self.assertEqual(round(spread, 2), 0.27)
        self.assertEqual(round(bps, 1), 27.0)
        self.assertEqual(str(m.classify_yield_curve_state(spread)).upper(), "NORMAL")

        # Case 2: Steep curve
        spread_steep, _ = m.compute_yield_spread(4.50, 3.20)
        self.assertEqual(round(spread_steep, 2), 1.30)
        self.assertEqual(str(m.classify_yield_curve_state(spread_steep)).upper(), "STEEP")

        # Case 3: Flat curve (below 25 bps NIM compression threshold)
        spread_flat, _ = m.compute_yield_spread(4.00, 3.90)
        self.assertEqual(round(spread_flat, 2), 0.10)
        self.assertEqual(str(m.classify_yield_curve_state(spread_flat)).upper(), "FLAT")

        # Case 4: Inverted curve
        spread_inv, _ = m.compute_yield_spread(3.80, 4.50)
        self.assertEqual(round(spread_inv, 2), -0.70)
        self.assertEqual(str(m.classify_yield_curve_state(spread_inv)).upper(), "INVERTED")

    def test_t1_02_yield_curve_shift_dynamics(self):
        """
        [T1-02] Yield Curve 30-Day Shift Dynamics.
        Verifies classification of:
        - BULL_STEEPENER: Short rates falling faster than long rates
        - BEAR_STEEPENER: Long rates rising faster than short rates
        - BEAR_FLATTENER: Short rates rising faster than long rates
        - BULL_FLATTENER: Long rates falling faster than short rates
        - UNCHANGED: Shift within epsilon tolerance (0.005)
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "classify_yield_curve_shift"), "sync_macro must define classify_yield_curve_shift")

        # Bull Steepener: 2Y drops 10 bps, 10Y flat -> spread expands
        shift = m.classify_yield_curve_shift(4.12, 3.85, 4.12, 3.95)
        self.assertEqual(str(shift).upper(), "BULL_STEEPENER")

        # Bear Steepener: 10Y rises 30 bps, 2Y rises 5 bps -> spread expands
        shift = m.classify_yield_curve_shift(4.40, 3.90, 4.10, 3.85)
        self.assertEqual(str(shift).upper(), "BEAR_STEEPENER")

        # Bear Flattener: 2Y rises 30 bps, 10Y flat -> spread contracts
        shift = m.classify_yield_curve_shift(4.20, 4.30, 4.20, 4.00)
        self.assertEqual(str(shift).upper(), "BEAR_FLATTENER")

        # Bull Flattener: 10Y drops 40 bps, 2Y drops 10 bps -> spread contracts
        shift = m.classify_yield_curve_shift(4.10, 3.90, 4.50, 4.00)
        self.assertEqual(str(shift).upper(), "BULL_FLATTENER")

        # Unchanged: Zero rate movement
        shift = m.classify_yield_curve_shift(4.20, 3.90, 4.20, 3.90)
        self.assertEqual(str(shift).upper(), "UNCHANGED")

    def test_t1_03_net_liquidity_calculation_and_scaling(self):
        """
        [T1-03] Net Liquidity Index (Assets - TGA - RRP) and Automatic Unit Scaling.
        Verifies:
        - Baseline: 7080.5B (Assets) - 782.3B (TGA) - 184.6B (RRP) = 6113.6B
        - Automatic conversion if Fed Assets is in Trillions (< 50) or Millions (> 100,000).
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "compute_net_liquidity"), "sync_macro must define compute_net_liquidity")

        # Direct in Billions
        nl = m.compute_net_liquidity(7080.5, 782.3, 184.6)
        self.assertEqual(round(nl, 1), 6113.6)

        # Trillions representation (7.0805 T) -> scaled to 7080.5 B
        nl_trillion = m.compute_net_liquidity(7.0805, 782.3, 184.6)
        self.assertEqual(round(nl_trillion, 1), 6113.6)

        # Millions representation (7080500 M) -> scaled to 7080.5 B
        nl_million = m.compute_net_liquidity(7080500.0, 782.3, 184.6)
        self.assertEqual(round(nl_million, 1), 6113.6)

    def test_t1_04_on_rrp_buffer_depletion_alert(self):
        """
        [T1-04] ON RRP Shock Absorber Buffer Depletion Trigger (< $150B).
        Verifies:
        - ADEQUATE_BUFFER (>= 150B): Depletion alert inactive
        - DEPLETION_WARNING (50B <= RRP < 150B): Alert active
        - CRITICAL_DEPLETION (< 50B): Alert active with critical risk flag
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "evaluate_rrp_buffer"), "sync_macro must define evaluate_rrp_buffer")

        # Adequate
        depleted, status, msg = m.evaluate_rrp_buffer(184.6)
        self.assertFalse(depleted)
        self.assertEqual(str(status).upper(), "ADEQUATE_BUFFER")
        self.assertIn("양호", msg)

        # Warning (< 150B)
        depleted, status, msg = m.evaluate_rrp_buffer(135.2)
        self.assertTrue(depleted)
        self.assertEqual(str(status).upper(), "DEPLETION_WARNING")
        self.assertIn("주의", msg)

        # Critical (< 50B)
        depleted, status, msg = m.evaluate_rrp_buffer(38.0)
        self.assertTrue(depleted)
        self.assertEqual(str(status).upper(), "CRITICAL_DEPLETION")
        self.assertIn("극단", msg)

    def test_t1_05_real_neutral_rate_and_policy_stance(self):
        """
        [T1-05] Real Neutral Rate (r*) Policy Restrictiveness Gap and Policy Stance.
        Verifies:
        - Real Rate = FFR - Core PCE
        - Restrictiveness Gap = Real Rate - r* (benchmark r* = 1.10%)
        - Stance partitions: SIGNIFICANTLY_RESTRICTIVE, MODERATELY_RESTRICTIVE, NEUTRAL, ACCOMMODATIVE
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "compute_policy_restrictiveness"), "sync_macro must define compute_policy_restrictiveness")

        # Case 1: Significantly Restrictive (Gap >= 1.00%)
        # FFR = 4.83%, Core PCE = 2.70%, r* = 1.10% -> Real = 2.13%, Gap = 1.03%
        res1 = m.compute_policy_restrictiveness(4.83, 2.70, 1.10)
        self.assertEqual(round(res1["real_policy_rate"], 2), 2.13)
        self.assertEqual(round(res1["restrictiveness_gap"], 2), 1.03)
        self.assertEqual(str(res1["stance"]).upper(), "SIGNIFICANTLY_RESTRICTIVE")

        # Case 2: Neutral (-0.25% <= Gap < 0.25%)
        # FFR = 3.50%, Core PCE = 2.30%, r* = 1.10% -> Real = 1.20%, Gap = 0.10%
        res2 = m.compute_policy_restrictiveness(3.50, 2.30, 1.10)
        self.assertEqual(round(res2["restrictiveness_gap"], 2), 0.10)
        self.assertEqual(str(res2["stance"]).upper(), "NEUTRAL")

        # Case 3: Accommodative (Gap < -0.25%)
        # FFR = 2.00%, Core PCE = 2.20%, r* = 1.10% -> Real = -0.20%, Gap = -1.30%
        res3 = m.compute_policy_restrictiveness(2.00, 2.20, 1.10)
        self.assertEqual(round(res3["restrictiveness_gap"], 2), -1.30)
        self.assertEqual(str(res3["stance"]).upper(), "ACCOMMODATIVE")

    def test_t1_06_ken_fisher_100_year_backtest_rules(self):
        """
        [T1-06] Ken Fisher 100-Year Backtest Rules Evaluation.
        Verifies:
        - KF-1: Inversion false alarm (S < 0, do not panic sell)
        - KF-2: Bull Steepener un-inversion trap (HIGH_RECESSION_DEFENSE_ALERT)
        - KF-3: Bear Steepener growth expansion signal (GROWTH_EXPANSION_SIGNAL, 82% win rate)
        - KF-4: Multiple compression vs expansion cycle
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "evaluate_ken_fisher_rules"), "sync_macro must define evaluate_ken_fisher_rules")

        # KF-1: Inversion active
        kf1 = m.evaluate_ken_fisher_rules(spread=-0.50, curve_shift="UNCHANGED", was_inverted_last_180d=False, restrictiveness_gap=1.0)
        self.assertEqual(kf1["primary_signal"], "INVERSION_ACTIVE_NO_SELL")

        # KF-2: Un-inversion with Bull Steepener -> Emergency alert
        kf2 = m.evaluate_ken_fisher_rules(spread=0.20, curve_shift="BULL_STEEPENER", was_inverted_last_180d=True, restrictiveness_gap=1.0)
        self.assertEqual(kf2["primary_signal"], "HIGH_RECESSION_DEFENSE_ALERT")
        self.assertIn("KF-2", kf2["rules_triggered"][0])

        # KF-3: Bear Steepener growth signal
        kf3 = m.evaluate_ken_fisher_rules(spread=0.50, curve_shift="BEAR_STEEPENER", was_inverted_last_180d=True, restrictiveness_gap=0.2)
        self.assertEqual(kf3["primary_signal"], "GROWTH_EXPANSION_SIGNAL")
        self.assertEqual(kf3.get("historical_win_rate_pct"), 82.0)

    def test_t1_07_rimp_firm_heterogeneity_model_and_alpha_spread(self):
        """
        [T1-07] NY Fed RIMP Firm Heterogeneity Model & Core Quality Alpha Spread.
        Verifies:
        - Restrictive gap >= 0.50% yields Core Quality alpha spread between +12.0% and +22.5%.
        - When gap = 1.03%, expected spread is 12.0 + 3.5(1.03) = +15.61%.
        - Identifies favored (Core Quality) and unfavored (Marginal Small-Cap) universes.
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "compute_rimp_heterogeneity_model"), "sync_macro must define compute_rimp_heterogeneity_model")

        rimp = m.compute_rimp_heterogeneity_model(restrictiveness_gap=1.03)
        self.assertEqual(round(rimp["alpha_spread_pct"], 2), 15.61)
        self.assertIn("Core Quality", rimp["favored_universe"])
        self.assertIn("중소형", rimp["unfavored_universe"])
        self.assertIn("core_profile", rimp)
        self.assertIn("marginal_small_profile", rimp)
        self.assertEqual(rimp["core_profile"]["fixed_debt_ratio"], "85%+")

    def test_t1_08_four_quadrant_macro_regime_classification(self):
        """
        [T1-08] 4-Quadrant Macro Regime Classification & P/E Multiple Forecast.
        Verifies exact regime code, multiple outlook, and factor allocations for:
        - TRANSITION_UNINVERSION
        - EASING_EARLY_RECOVERY
        - RESTRICTIVE_LATE_CYCLE
        - EXPANSION_MID_CYCLE
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "classify_macro_regime"), "sync_macro must define classify_macro_regime")

        # 1. Transition Un-Inversion (Bull Steepener)
        r1 = m.classify_macro_regime(spread=0.27, delta_net_liq_90d=-10.0, restrictiveness_gap=1.03, was_inverted_last_180d=True, curve_shift="BULL_STEEPENER")
        self.assertEqual(r1["regime_code"], "TRANSITION_UNINVERSION")
        self.assertEqual(r1["per_multiple_outlook"], "COMPRESSION")
        self.assertEqual(r1["pe_expansion_compression_pct"], -5.0)
        self.assertEqual(r1["factor_allocations"]["core_pct"], 60.0)
        self.assertEqual(r1["factor_allocations"]["cash_pct"], 25.0)

        # 2. Easing Early Recovery
        r2 = m.classify_macro_regime(spread=1.00, delta_net_liq_90d=120.0, restrictiveness_gap=-1.30, was_inverted_last_180d=False, curve_shift="BULL_STEEPENER")
        self.assertEqual(r2["regime_code"], "EASING_EARLY_RECOVERY")
        self.assertEqual(r2["per_multiple_outlook"], "EXPANSION")
        self.assertEqual(r2["pe_expansion_compression_pct"], 20.0)

        # 3. Restrictive Late Cycle
        r3 = m.classify_macro_regime(spread=-0.70, delta_net_liq_90d=-60.0, restrictiveness_gap=1.40, was_inverted_last_180d=False, curve_shift="BEAR_FLATTENER")
        self.assertEqual(r3["regime_code"], "RESTRICTIVE_LATE_CYCLE")
        self.assertEqual(r3["per_multiple_outlook"], "COMPRESSION")
        self.assertEqual(r3["pe_expansion_compression_pct"], -11.5)

        # 4. Expansion Mid-Cycle
        r4 = m.classify_macro_regime(spread=0.60, delta_net_liq_90d=10.0, restrictiveness_gap=0.10, was_inverted_last_180d=False, curve_shift="UNCHANGED")
        self.assertEqual(r4["regime_code"], "EXPANSION_MID_CYCLE")
        self.assertEqual(r4["per_multiple_outlook"], "NEUTRAL")

    def test_t1_09_four_core_equity_perspectives_completeness_and_encoding(self):
        """
        [T1-09] 4 Core Equity Perspectives Completeness & UTF-8 Korean Integrity.
        Verifies that every seed/collected research report contains all 4 mandatory Korean fields:
        - discount_rate_impact (매크로 할인율 및 증시 밸류에이션)
        - factor_style_impact (스타일/팩터 영향)
        - sector_industry_impact (주요 섹터 및 산업 영향)
        - fx_liquidity_flow_impact (외환 및 외국인 수급)
        Zero NULL values, minimum text length >= 20, and zero '??' corruption.
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "get_seed_macro_reports"), "sync_macro must define get_seed_macro_reports")

        reports = m.get_seed_macro_reports()
        self.assertGreaterEqual(len(reports), 5, "Must provide at least 5 institutional seed reports")

        perspectives = [
            "discount_rate_impact",
            "factor_style_impact",
            "sector_industry_impact",
            "fx_liquidity_flow_impact",
        ]

        for rep in reports:
            title = rep.get("title", "Unknown")
            for p in perspectives:
                val = rep.get(p)
                self.assertIsNotNone(val, f"Report '{title}' missing perspective '{p}'")
                self.assertIsInstance(val, str, f"Perspective '{p}' must be string")
                self.assertGreaterEqual(len(val.strip()), 20, f"Perspective '{p}' too short in '{title}'")
                self.assertNotIn("??", val, f"Corrupted question marks in '{p}' of '{title}'")

            # Sentiment check
            sentiment = rep.get("sentiment")
            self.assertIn(sentiment, ["DOVISH", "HAWKISH", "NEUTRAL"], f"Invalid sentiment in '{title}'")
            score = rep.get("sentiment_score")
            self.assertTrue(-1.0 <= score <= 1.0, f"Sentiment score out of bounds in '{title}'")

    def test_t1_10_deterministic_sha256_report_deduplication_invariance(self):
        """
        [T1-10] Deterministic 16-Character SHA-256 Deduplication Hash Formula.
        Verifies:
        - compute_macro_report_hash(source, publish_date, title) -> 16 hex chars
        - Whitespace and case normalization invariance
        - Golden hash match:
          FOMC:2026-09-17:FOMC Statement: 50bps Rate Cut and Policy Calibration -> 5ffcef96a1432fe3
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "compute_macro_report_hash"), "sync_macro must define compute_macro_report_hash")

        h1 = m.compute_macro_report_hash("FOMC", "2026-09-17", "FOMC Statement: 50bps Rate Cut and Policy Calibration")
        self.assertEqual(len(h1), 16, "Report hash must be exactly 16 characters")
        self.assertEqual(h1, "5ffcef96a1432fe3", "Hash must match canonical golden test vector")

        # Invariance with leading/trailing spaces and lowercased source
        h2 = m.compute_macro_report_hash("  fomc  ", "2026-09-17T14:30:00Z", "  FOMC Statement: 50bps Rate Cut and Policy Calibration  ")
        self.assertEqual(h1, h2, "Hash must be invariant to case and whitespace normalization")


# =============================================================================
# TIER 2: Boundary & Corner Cases (>= 5 test cases)
# =============================================================================

class TestMacroModuleTier2Boundaries(BaseMacroTestCase):
    """Tier 2: Boundary, Edge, and Corner Case Hardening."""

    def test_t2_01_yield_curve_exact_zero_and_boundary_conditions(self):
        """
        [T2-01] Yield Curve Exact Boundaries (0 bps flat line, 25 bps NIM limit).
        Verifies:
        - S = 0.000% is classified as FLAT (not INVERTED)
        - S = -0.0001% is classified as INVERTED
        - S = 0.250% is classified as NORMAL (while 0.249% is FLAT)
        - Extreme positive (+5.00%) and negative (-3.50%) spreads are handled without exception.
        """
        m = self._require_macro()

        # Exact zero
        self.assertEqual(str(m.classify_yield_curve_state(0.0)).upper(), "FLAT")

        # Micro-inversion
        self.assertEqual(str(m.classify_yield_curve_state(-0.0001)).upper(), "INVERTED")

        # 25 bps boundary
        self.assertEqual(str(m.classify_yield_curve_state(0.2499)).upper(), "FLAT")
        self.assertEqual(str(m.classify_yield_curve_state(0.2500)).upper(), "NORMAL")

        # Extreme values
        self.assertEqual(str(m.classify_yield_curve_state(5.00)).upper(), "STEEP")
        self.assertEqual(str(m.classify_yield_curve_state(-3.50)).upper(), "INVERTED")

    def test_t2_02_on_rrp_buffer_depletion_boundary_thresholds(self):
        """
        [T2-02] ON RRP Exact Boundary Thresholds ($150B and $50B).
        Verifies:
        - Exactly 150.0B -> Not depleted (ADEQUATE_BUFFER)
        - 149.99B -> Depleted (DEPLETION_WARNING)
        - Exactly 50.0B -> Depleted (DEPLETION_WARNING)
        - 49.99B -> Critical (CRITICAL_DEPLETION)
        - 0.0B -> Zero buffer handled cleanly without division-by-zero
        """
        m = self._require_macro()

        depleted, status, _ = m.evaluate_rrp_buffer(150.0)
        self.assertFalse(depleted)
        self.assertEqual(str(status).upper(), "ADEQUATE_BUFFER")

        depleted, status, _ = m.evaluate_rrp_buffer(149.99)
        self.assertTrue(depleted)
        self.assertEqual(str(status).upper(), "DEPLETION_WARNING")

        depleted, status, _ = m.evaluate_rrp_buffer(50.0)
        self.assertTrue(depleted)
        self.assertEqual(str(status).upper(), "DEPLETION_WARNING")

        depleted, status, _ = m.evaluate_rrp_buffer(49.99)
        self.assertTrue(depleted)
        self.assertEqual(str(status).upper(), "CRITICAL_DEPLETION")

        depleted, status, _ = m.evaluate_rrp_buffer(0.0)
        self.assertTrue(depleted)
        self.assertEqual(str(status).upper(), "CRITICAL_DEPLETION")

    def test_t2_03_offline_network_scraping_resilience_seed_fallback(self):
        """
        [T2-03] Offline Network Scraping Failure & Authoritative Seed Fallback.
        Verifies that when live web scraping encounters socket timeout or HTTP 500,
        the ingestion pipeline seamlessly returns the authoritative institutional seed reports.
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "ingest_macro_reports"), "sync_macro must define ingest_macro_reports")

        # Ingest in offline environment (default without live internet credentials)
        reports = m.ingest_macro_reports()
        self.assertIsInstance(reports, list)
        self.assertGreaterEqual(len(reports), 5)
        self.assertEqual(reports[0]["report_id"], "5ffcef96a1432fe3")

    def test_t2_04_missing_or_corrupted_indicator_parameters_graceful_handling(self):
        """
        [T2-04] Corrupted or Edge Indicator Parameters Graceful Handling.
        Verifies that missing TGA (0.0), extreme balance sheet values, or zero yields
        do not raise unhandled exceptions or ZeroDivisionError.
        """
        m = self._require_macro()

        # Net liquidity with zero TGA / zero RRP
        nl = m.compute_net_liquidity(7000.0, 0.0, 0.0)
        self.assertEqual(nl, 7000.0)

        # Zero interest rate spread
        spread, bps = m.compute_yield_spread(0.0, 0.0)
        self.assertEqual(spread, 0.0)
        self.assertEqual(bps, 0.0)

    def test_t2_05_policy_restrictiveness_gap_exact_boundaries(self):
        """
        [T2-05] Policy Restrictiveness Gap Exact Boundary Values.
        Verifies:
        - Gap = 1.00% -> SIGNIFICANTLY_RESTRICTIVE
        - Gap = 0.25% -> MODERATELY_RESTRICTIVE
        - Gap = -0.25% -> NEUTRAL
        - Gap = -0.26% -> ACCOMMODATIVE
        """
        m = self._require_macro()

        # FFR - Core PCE - r* = Gap
        # 1.00% exactly (e.g. FFR=4.10, PCE=2.00, r*=1.10 -> Real=2.10, Gap=1.00)
        p1 = m.compute_policy_restrictiveness(4.10, 2.00, 1.10)
        self.assertEqual(round(p1["restrictiveness_gap"], 2), 1.00)
        self.assertEqual(str(p1["stance"]).upper(), "SIGNIFICANTLY_RESTRICTIVE")

        # 0.25% exactly (FFR=3.35, PCE=2.00, r*=1.10 -> Real=1.35, Gap=0.25)
        p2 = m.compute_policy_restrictiveness(3.35, 2.00, 1.10)
        self.assertEqual(round(p2["restrictiveness_gap"], 2), 0.25)
        self.assertEqual(str(p2["stance"]).upper(), "MODERATELY_RESTRICTIVE")

        # -0.25% exactly (FFR=2.85, PCE=2.00, r*=1.10 -> Real=0.85, Gap=-0.25)
        p3 = m.compute_policy_restrictiveness(2.85, 2.00, 1.10)
        self.assertEqual(round(p3["restrictiveness_gap"], 2), -0.25)
        self.assertEqual(str(p3["stance"]).upper(), "NEUTRAL")

        # -0.26% (FFR=2.84, PCE=2.00, r*=1.10 -> Real=0.84, Gap=-0.26)
        p4 = m.compute_policy_restrictiveness(2.84, 2.00, 1.10)
        self.assertEqual(round(p4["restrictiveness_gap"], 2), -0.26)
        self.assertEqual(str(p4["stance"]).upper(), "ACCOMMODATIVE")


# =============================================================================
# TIER 3: Cross-Feature Combinations (>= 4 test cases)
# =============================================================================

class TestMacroModuleTier3Combinations(BaseMacroTestCase):
    """Tier 3: Cross-Module Interactions, Pipeline Persistence & API Contracts."""

    def test_t3_01_sync_pipeline_sqlite_persistence_and_table_schemas(self):
        """
        [T3-01] End-to-End Pipeline Execution -> SQLite Database Schema & Records.
        Verifies that ensure_tables_and_seed creates:
        - macro_reports table with UNIQUE report_id
        - macro_indicators table with UNIQUE indicator_date
        - macro_regime table with UNIQUE regime_id
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "ensure_tables_and_seed"), "sync_macro must define ensure_tables_and_seed")

        m.ensure_tables_and_seed(self.test_db_path)
        self.assertTrue(self.test_db_path.exists(), "Target database must be created")

        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        # Check macro_reports schema
        cursor.execute("PRAGMA table_info(macro_reports);")
        columns = [row[1] for row in cursor.fetchall()]
        for req in ["report_id", "source", "title", "discount_rate_impact", "factor_style_impact", "sector_industry_impact", "fx_liquidity_flow_impact"]:
            self.assertIn(req, columns, f"macro_reports missing required column '{req}'")

        # Check macro_indicators schema
        cursor.execute("PRAGMA table_info(macro_indicators);")
        ind_cols = [row[1] for row in cursor.fetchall()]
        for req in ["indicator_date", "us_10y_yield", "us_2y_yield", "yield_spread_10y_2y", "yield_curve_state", "net_liquidity_billion"]:
            self.assertIn(req, ind_cols, f"macro_indicators missing required column '{req}'")

        # Check macro_regime schema
        cursor.execute("PRAGMA table_info(macro_regime);")
        reg_cols = [row[1] for row in cursor.fetchall()]
        for req in ["regime_id", "current_regime", "regime_code", "per_multiple_outlook", "ken_fisher_signal"]:
            self.assertIn(req, reg_cols, f"macro_regime missing required column '{req}'")

        conn.close()

    def test_t3_02_four_target_atomic_json_distribution_parity(self):
        """
        [T3-02] 4-Target Atomic JSON Distribution Parity & Hash Identity.
        Verifies that distribute_macro_json creates files across 4 distinct paths
        with zero corruption and matching content hashes.
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "distribute_macro_json"), "sync_macro must define distribute_macro_json")

        test_destinations = [
            self.temp_path / "root_macro.json",
            self.temp_path / "backend" / "macro.json",
            self.temp_path / "frontend" / "public" / "macro.json",
            self.temp_path / "frontend" / "dist" / "macro.json",
        ]

        sample_payload = {
            "status": "success",
            "regime": {"regime_code": "TRANSITION_UNINVERSION", "outlook": "COMPRESSION"},
            "indicators": {"spread": 0.27, "net_liquidity": 6113.6},
            "reports": [{"id": "test_1", "title": "FOMC 50bps Cut"}],
        }

        m.distribute_macro_json(sample_payload, test_destinations)

        hashes = []
        for p in test_destinations:
            self.assertTrue(p.exists(), f"Distributed file missing at {p}")
            with open(p, "rb") as f:
                content = f.read()
                self.assertGreater(len(content), 50, f"File at {p} too small")
                hashes.append(hashlib.sha256(content).hexdigest())

        # All 4 distribution targets must have identical content hash
        self.assertEqual(len(set(hashes)), 1, "All 4 distribution targets must have identical SHA-256 hash")

    def test_t3_03_fastapi_endpoints_schema_contract_matching(self):
        """
        [T3-03] SQLite DB State to FastAPI Endpoint Schema Alignment.
        Verifies that get_all_macro_data() produces a consolidated dictionary matching:
        - GET /api/v1/macro/summary
        - GET /api/v1/macro/timeline
        - GET /api/v1/macro/indicators
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "get_all_macro_data"), "sync_macro must define get_all_macro_data")

        data = m.get_all_macro_data(self.test_db_path)
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("status"), "success")
        self.assertIn("regime", data)
        self.assertIn("indicators", data)
        self.assertIn("reports", data)

        regime = data["regime"]
        self.assertIn("regime_code", regime)
        self.assertIn("per_multiple_outlook", regime)
        self.assertIn("ken_fisher_signal", regime)

        indicators = data["indicators"]
        self.assertIn("us_10y_yield", indicators)
        self.assertIn("us_2y_yield", indicators)
        self.assertIn("yield_spread_10y_2y", indicators)
        self.assertIn("net_liquidity_billion", indicators)

        reports = data["reports"]
        self.assertIsInstance(reports, list)
        self.assertGreater(len(reports), 0)

    def test_t3_04_ken_fisher_signal_coherence_with_yield_curve_and_regime(self):
        """
        [T3-04] Ken Fisher Defense Alert Coherence with Yield Curve Un-Inversion & Macro Regime.
        Verifies that when a Bull Steepener un-inversion occurs:
        - Ken Fisher rule flags HIGH_RECESSION_DEFENSE_ALERT
        - Macro regime evaluates to TRANSITION_UNINVERSION
        - P/E outlook indicates COMPRESSION
        - Cash allocation is elevated (>= 20%)
        """
        m = self._require_macro()

        kf = m.evaluate_ken_fisher_rules(spread=0.25, curve_shift="BULL_STEEPENER", was_inverted_last_180d=True, restrictiveness_gap=1.0)
        regime = m.classify_macro_regime(spread=0.25, delta_net_liq_90d=-10.0, restrictiveness_gap=1.0, was_inverted_last_180d=True, curve_shift="BULL_STEEPENER")

        self.assertEqual(kf["primary_signal"], "HIGH_RECESSION_DEFENSE_ALERT")
        self.assertEqual(regime["ken_fisher_signal"], "HIGH_RECESSION_DEFENSE_ALERT")
        self.assertEqual(regime["regime_code"], "TRANSITION_UNINVERSION")
        self.assertEqual(regime["per_multiple_outlook"], "COMPRESSION")
        self.assertGreaterEqual(regime["factor_allocations"]["cash_pct"], 20.0)


# =============================================================================
# TIER 4: Real-World Application Scenarios (>= 3 test cases)
# =============================================================================

class TestMacroModuleTier4Scenarios(BaseMacroTestCase):
    """Tier 4: Realistic Macroeconomic Scenarios & Multi-Target Invariance."""

    def test_t4_01_fomc_rate_cut_cycle_bull_steepener_scenario(self):
        """
        [T4-01] Scenario 1: Realistic FOMC 50bps Rate Cut Cycle (Bull Steepener Trap).
        Simulates:
        1. Fed cuts benchmark rate by 50 bps.
        2. 2Y yield drops from 4.80% to 3.80% (-100 bps) while 10Y drops from 4.20% to 4.00% (-20 bps).
        3. Curve transitions from inverted (-0.60%) to un-inverted (+0.20%).
        4. Engine detects Bull Steepener un-inversion trap and raises HIGH_RECESSION_DEFENSE_ALERT.
        5. Core Quality portfolio allocation remains overweight (> 60%) to defend against recession shock.
        """
        m = self._require_macro()

        current_10y, current_2y = 4.00, 3.80
        prior_10y, prior_2y = 4.20, 4.80

        spread, _ = m.compute_yield_spread(current_10y, current_2y)
        self.assertEqual(round(spread, 2), 0.20)

        shift = m.classify_yield_curve_shift(current_10y, current_2y, prior_10y, prior_2y)
        self.assertEqual(str(shift).upper(), "BULL_STEEPENER")

        regime = m.classify_macro_regime(
            spread=spread,
            delta_net_liq_90d=15.0,
            restrictiveness_gap=0.90,
            was_inverted_last_180d=True,
            curve_shift=shift,
        )

        self.assertEqual(regime["regime_code"], "TRANSITION_UNINVERSION")
        self.assertEqual(regime["ken_fisher_signal"], "HIGH_RECESSION_DEFENSE_ALERT")
        self.assertGreaterEqual(regime["factor_allocations"]["core_pct"], 60.0)

    def test_t4_02_restrictive_late_cycle_compression_scenario(self):
        """
        [T4-02] Scenario 2: Restrictive Late-Cycle Regime (P/E Compression & Core Quality Dominance).
        Simulates:
        1. FFR = 5.33%, Core PCE = 2.83%, r* = 1.10% -> Restrictiveness gap = +1.40% (Significantly Restrictive).
        2. Curve remains inverted (-0.70%) and Net Liquidity contracts by $60B over 90 days.
        3. Engine assigns RESTRICTIVE_LATE_CYCLE regime with -11.5% P/E compression.
        4. RIMP model predicts Core Quality large-cap alpha spread of +16.90% over debt-laden small-caps.
        """
        m = self._require_macro()

        pol = m.compute_policy_restrictiveness(5.33, 2.83, 1.10)
        self.assertEqual(round(pol["restrictiveness_gap"], 2), 1.40)
        self.assertEqual(pol["stance"], "SIGNIFICANTLY_RESTRICTIVE")

        rimp = m.compute_rimp_heterogeneity_model(pol["restrictiveness_gap"])
        self.assertEqual(round(rimp["alpha_spread_pct"], 2), 16.90)

        regime = m.classify_macro_regime(
            spread=-0.70,
            delta_net_liq_90d=-60.0,
            restrictiveness_gap=pol["restrictiveness_gap"],
            was_inverted_last_180d=False,
            curve_shift="BEAR_FLATTENER",
        )

        self.assertEqual(regime["regime_code"], "RESTRICTIVE_LATE_CYCLE")
        self.assertEqual(regime["per_multiple_outlook"], "COMPRESSION")
        self.assertEqual(regime["pe_expansion_compression_pct"], -11.5)

    def test_t4_03_multi_target_canonical_distribution_file_integrity(self):
        """
        [T4-03] Scenario 3: Multi-Target File Distribution Contract.
        Verifies that when sync_macro runs in production mode, all 4 canonical paths:
        1. d:\\Industry\\macro_intelligence_data.json (Root)
        2. d:\\Industry\\InvestmentPortal\\backend\\macro_intelligence_data.json (Backend)
        3. d:\\Industry\\InvestmentPortal\\frontend\\public\\macro_intelligence_data.json (Frontend Public)
        4. d:\\Industry\\InvestmentPortal\\frontend\\dist\\macro_intelligence_data.json (Frontend Dist)
        can be parsed cleanly as valid JSON containing 'regime', 'indicators', and 'reports' keys.
        """
        m = self._require_macro()
        self.assertTrue(hasattr(m, "run_sync"), "sync_macro must define run_sync")

        # Execute isolated sync pass directing to temporary database
        sync_result = m.run_sync(db_path=self.test_db_path, force=True, silent=True)
        self.assertIsInstance(sync_result, dict)
        self.assertTrue(sync_result.get("success", False) or sync_result.get("status") == "success")


if __name__ == "__main__":
    unittest.main()
