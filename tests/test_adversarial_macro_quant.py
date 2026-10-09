"""
TrendPulse Macro Intelligence — Adversarial Stress Test Suite (tests/test_adversarial_macro_quant.py)
=====================================================================================================
Adversarial stress testing of quantitative math, extreme inputs, boundary conditions,
corrupted data resilience, and combinatorial stability in sync_macro.py.

Targeted areas:
1. Inverted curve transitions (S = 0.000%, S = -0.0001%, S = +0.0001%, sub-basis point shifts).
2. Extreme yields (negative rates, yields > 20%, 0.0% yields, Volcker-era rates).
3. Liquidity & balance sheet corner cases (zero TGA, zero ON RRP, negative Net Liquidity, Fed assets auto-scaling).
4. Policy restrictiveness, inflation spikes, deflation, and NY Fed RIMP model boundaries.
5. High-dimensional combinatorial grid testing (7,700 synthetic market states) for regime classification.
6. Factor allocation invariants (sum == 100.0%) and sector sensitivity matrix completeness (6 sectors).
7. SQLite persistence and round-trip fidelity under extreme numerical bounds.
8. Data corruption & malformed JSON resilience (fallback behavior on broken JSON in DB).
9. Validation bounds (-1.0 to 1.0 sentiment score, mandatory fields, invalid enums).
10. Backend mirror (`InvestmentPortal/backend/sync_macro.py`) parity and dynamic import verification.
"""

import os
import sys
import json
import math
import sqlite3
import tempfile
import shutil
import unittest
import importlib
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "InvestmentPortal" / "backend"))

import sync_macro as m


class TestMacroAdversarialTransitions(unittest.TestCase):
    """Adversarial stress testing on yield curve inversion transitions and boundaries."""

    def test_adv_01_exact_zero_and_micro_spread_transitions(self):
        """Tests micro-spreads around zero: -0.0001%, 0.0000%, +0.0001%."""
        test_cases = [
            (-0.0001, -0.01, m.YieldCurveState.INVERTED),
            (0.0000, 0.0, m.YieldCurveState.FLAT),
            (0.0001, 0.01, m.YieldCurveState.FLAT),
            (0.2499, 24.99, m.YieldCurveState.FLAT),
            (0.2500, 25.0, m.YieldCurveState.NORMAL),
            (0.9999, 99.99, m.YieldCurveState.NORMAL),
            (1.0000, 100.0, m.YieldCurveState.STEEP),
        ]
        for spread_input, exp_bps, exp_state in test_cases:
            spread, bps = m.compute_yield_spread(3.0 + spread_input, 3.0)
            self.assertAlmostEqual(spread, spread_input, places=4)
            self.assertAlmostEqual(bps, exp_bps, places=2)
            state = m.classify_yield_curve_state(spread)
            self.assertEqual(state, exp_state, f"Failed state at spread {spread_input}")

    def test_adv_02_curve_shift_epsilon_boundaries(self):
        """Tests 30-day shift dynamics at exact epsilon (0.005) boundaries."""
        eps = m.CURVE_SHIFT_EPSILON  # 0.005

        # Exactly at +epsilon -> UNCHANGED
        shift = m.classify_yield_curve_shift(
            current_10y=4.0 + eps, current_2y=4.0,
            prior_30d_10y=4.0, prior_30d_2y=4.0
        )
        self.assertEqual(shift, m.CurveShiftType.UNCHANGED)

        # Just above +epsilon with delta_2y <= 0 -> BULL_STEEPENER
        shift = m.classify_yield_curve_shift(
            current_10y=4.0 + eps + 0.001, current_2y=4.0,
            prior_30d_10y=4.0, prior_30d_2y=4.0
        )
        self.assertEqual(shift, m.CurveShiftType.BULL_STEEPENER)

        # Just above +epsilon with delta_2y > 0 -> BEAR_STEEPENER
        shift = m.classify_yield_curve_shift(
            current_10y=4.0 + eps + 0.005, current_2y=4.002,
            prior_30d_10y=4.0, prior_30d_2y=4.0
        )
        self.assertEqual(shift, m.CurveShiftType.BEAR_STEEPENER)

        # Exactly at -epsilon -> UNCHANGED
        shift = m.classify_yield_curve_shift(
            current_10y=4.0 - eps, current_2y=4.0,
            prior_30d_10y=4.0, prior_30d_2y=4.0
        )
        self.assertEqual(shift, m.CurveShiftType.UNCHANGED)

        # Just below -epsilon with delta_2y >= 0 -> BEAR_FLATTENER
        shift = m.classify_yield_curve_shift(
            current_10y=4.0 - eps - 0.001, current_2y=4.0,
            prior_30d_10y=4.0, prior_30d_2y=4.0
        )
        self.assertEqual(shift, m.CurveShiftType.BEAR_FLATTENER)

        # Just below -epsilon with delta_2y < 0 -> BULL_FLATTENER
        shift = m.classify_yield_curve_shift(
            current_10y=4.0 - eps - 0.005, current_2y=3.998,
            prior_30d_10y=4.0, prior_30d_2y=4.0
        )
        self.assertEqual(shift, m.CurveShiftType.BULL_FLATTENER)

    def test_adv_03_ken_fisher_rules_zero_spread_edge(self):
        """Tests Ken Fisher backtest signals exactly at inversion boundary (S=0.0)."""
        # Spread exactly 0.0 with prior inversion and Bull Steepener -> KF-2 Alert
        kf_res = m.evaluate_ken_fisher_rules(
            spread=0.0000,
            curve_shift=m.CurveShiftType.BULL_STEEPENER,
            was_inverted_last_180d=True,
            restrictiveness_gap=0.50
        )
        self.assertEqual(kf_res["primary_signal"], m.KenFisherSignal.HIGH_RECESSION_DEFENSE_ALERT.value)
        self.assertTrue(any("KF-2" in r for r in kf_res["rules_triggered"]))

        # Spread negative (-0.0001) -> KF-1 No Sell
        kf_res_inv = m.evaluate_ken_fisher_rules(
            spread=-0.0001,
            curve_shift=m.CurveShiftType.BULL_STEEPENER,
            was_inverted_last_180d=True,
            restrictiveness_gap=0.50
        )
        self.assertEqual(kf_res_inv["primary_signal"], m.KenFisherSignal.INVERSION_ACTIVE_NO_SELL.value)
        self.assertTrue(any("KF-1" in r for r in kf_res_inv["rules_triggered"]))


class TestMacroAdversarialExtremeYields(unittest.TestCase):
    """Stress tests covering extreme yields: negative, 0%, Volcker era, hyperinflation."""

    def test_adv_04_negative_yields_regime(self):
        """Tests European/Japanese negative yield scenarios (e.g. 10Y = -0.50%, 2Y = -0.80%)."""
        spread, bps = m.compute_yield_spread(-0.50, -0.80)
        self.assertEqual(spread, 0.30)
        self.assertEqual(bps, 30.0)
        self.assertEqual(m.classify_yield_curve_state(spread), m.YieldCurveState.NORMAL)

        # Inverted negative yields
        spread_inv, _ = m.compute_yield_spread(-0.80, -0.50)
        self.assertEqual(spread_inv, -0.30)
        self.assertEqual(m.classify_yield_curve_state(spread_inv), m.YieldCurveState.INVERTED)

    def test_adv_05_zero_and_extreme_high_yields(self):
        """Tests 0.00% yields and extreme yields (20%+, 100%)."""
        # Exactly 0.00% yields
        s_zero, bps_zero = m.compute_yield_spread(0.0, 0.0)
        self.assertEqual(s_zero, 0.0)
        self.assertEqual(bps_zero, 0.0)
        self.assertEqual(m.classify_yield_curve_state(s_zero), m.YieldCurveState.FLAT)

        # Volcker-era rates (1981): 10Y = 15.84%, 2Y = 16.50%
        s_volcker, _ = m.compute_yield_spread(15.84, 16.50)
        self.assertEqual(round(s_volcker, 2), -0.66)
        self.assertEqual(m.classify_yield_curve_state(s_volcker), m.YieldCurveState.INVERTED)

        # Hyper-inflation rates (100% vs 95%)
        s_hyper, bps_hyper = m.compute_yield_spread(100.0, 95.0)
        self.assertEqual(s_hyper, 5.0)
        self.assertEqual(bps_hyper, 500.0)
        self.assertEqual(m.classify_yield_curve_state(s_hyper), m.YieldCurveState.STEEP)


class TestMacroAdversarialLiquidityAndBalances(unittest.TestCase):
    """Stress tests on liquidity balances: zero TGA, zero ON RRP, negative Net Liquidity, auto-scaling."""

    def test_adv_06_zero_and_extreme_on_rrp_buffer(self):
        """Tests ON RRP at $0.0B, $49.99B, $50.0B, $149.99B, $150.0B, $2500B."""
        # Exact $0.0B drain
        depleted, status, msg = m.evaluate_rrp_buffer(0.0)
        self.assertTrue(depleted)
        self.assertEqual(status, m.RRPBufferStatus.CRITICAL_DEPLETION)
        self.assertIn("$0.0B < $50B", msg)

        # Just below $50B
        depleted, status, _ = m.evaluate_rrp_buffer(49.99)
        self.assertTrue(depleted)
        self.assertEqual(status, m.RRPBufferStatus.CRITICAL_DEPLETION)

        # Exactly at $50B
        depleted, status, _ = m.evaluate_rrp_buffer(50.0)
        self.assertTrue(depleted)
        self.assertEqual(status, m.RRPBufferStatus.DEPLETION_WARNING)

        # Just below $150B
        depleted, status, _ = m.evaluate_rrp_buffer(149.99)
        self.assertTrue(depleted)
        self.assertEqual(status, m.RRPBufferStatus.DEPLETION_WARNING)

        # Exactly at $150B
        depleted, status, _ = m.evaluate_rrp_buffer(150.0)
        self.assertFalse(depleted)
        self.assertEqual(status, m.RRPBufferStatus.ADEQUATE_BUFFER)

        # Massive buffer ($2500B)
        depleted, status, _ = m.evaluate_rrp_buffer(2500.0)
        self.assertFalse(depleted)
        self.assertEqual(status, m.RRPBufferStatus.ADEQUATE_BUFFER)

    def test_adv_07_zero_tga_and_negative_net_liquidity(self):
        """Tests zero TGA balance and negative Net Liquidity calculation."""
        # Zero TGA balance
        net_liq = m.compute_net_liquidity(fed_assets_b=7080.0, tga_b=0.0, on_rrp_b=184.6)
        self.assertEqual(net_liq, 6895.4)

        # Both TGA and RRP zero
        net_liq_pure = m.compute_net_liquidity(fed_assets_b=7080.0, tga_b=0.0, on_rrp_b=0.0)
        self.assertEqual(net_liq_pure, 7080.0)

        # Negative Net Liquidity (TGA + RRP exceeds Assets)
        net_liq_neg = m.compute_net_liquidity(fed_assets_b=500.0, tga_b=400.0, on_rrp_b=300.0)
        self.assertEqual(net_liq_neg, -200.0)
        self.assertIsInstance(net_liq_neg, float)

    def test_adv_08_fed_assets_scaling_boundaries(self):
        """Tests auto-scaling of Fed Assets: Trillions (< 50), Billions (50 - 100k), Millions (> 100k)."""
        # Trillions: 7.08 -> 7080.0B
        liq_t = m.compute_net_liquidity(7.08, 500.0, 100.0)
        # Billions: 7080.0 -> 7080.0B
        liq_b = m.compute_net_liquidity(7080.0, 500.0, 100.0)
        # Millions: 7,080,000.0 -> 7080.0B
        liq_m = m.compute_net_liquidity(7080000.0, 500.0, 100.0)

        self.assertEqual(liq_t, 6480.0)
        self.assertEqual(liq_b, 6480.0)
        self.assertEqual(liq_m, 6480.0)


class TestMacroAdversarialPolicyAndRIMP(unittest.TestCase):
    """Stress tests on policy restrictiveness, inflation spikes, deflation, and RIMP model."""

    def test_adv_09_inflation_spikes_and_deflation(self):
        """Tests inflation spike (15%) and deflation (-3%) scenarios."""
        # 1. Inflation spike: Core PCE = 15.0%, FFR = 5.0%
        # real rate = 5 - 15 = -10.0%, gap = -10 - 1.10 = -11.10% -> Accommodative
        res_spike = m.compute_policy_restrictiveness(ffr=5.0, core_pce=15.0, r_star=1.10)
        self.assertEqual(res_spike["real_policy_rate"], -10.0)
        self.assertEqual(res_spike["restrictiveness_gap"], -11.10)
        self.assertEqual(res_spike["stance"], m.PolicyStance.ACCOMMODATIVE.value)

        # 2. Severe Deflation: Core PCE = -3.0%, FFR = 2.0%
        # real rate = 2 - (-3) = 5.0%, gap = 5 - 1.10 = 3.90% -> Significantly Restrictive
        res_def = m.compute_policy_restrictiveness(ffr=2.0, core_pce=-3.0, r_star=1.10)
        self.assertEqual(res_def["real_policy_rate"], 5.0)
        self.assertEqual(res_def["restrictiveness_gap"], 3.90)
        self.assertEqual(res_def["stance"], m.PolicyStance.SIGNIFICANTLY_RESTRICTIVE.value)

        # 3. ZIRP with deflation: Core PCE = -1.0%, FFR = 0.0%
        # real rate = 0 - (-1) = 1.0%, gap = 1 - 1.10 = -0.10% -> Neutral
        res_zirp = m.compute_policy_restrictiveness(ffr=0.0, core_pce=-1.0, r_star=1.10)
        self.assertEqual(res_zirp["real_policy_rate"], 1.0)
        self.assertEqual(res_zirp["restrictiveness_gap"], -0.10)
        self.assertEqual(res_zirp["stance"], m.PolicyStance.NEUTRAL.value)

    def test_adv_10_policy_stance_exact_boundaries(self):
        """Tests restrictiveness gap boundary thresholds: 1.00, 0.25, -0.25."""
        # Gap = 1.00 -> SIGNIFICANTLY_RESTRICTIVE
        r1 = m.compute_policy_restrictiveness(ffr=3.10, core_pce=1.00, r_star=1.10)
        self.assertEqual(r1["restrictiveness_gap"], 1.00)
        self.assertEqual(r1["stance"], m.PolicyStance.SIGNIFICANTLY_RESTRICTIVE.value)

        # Gap = 0.99 -> MODERATELY_RESTRICTIVE
        r2 = m.compute_policy_restrictiveness(ffr=3.09, core_pce=1.00, r_star=1.10)
        self.assertEqual(r2["restrictiveness_gap"], 0.99)
        self.assertEqual(r2["stance"], m.PolicyStance.MODERATELY_RESTRICTIVE.value)

        # Gap = 0.25 -> MODERATELY_RESTRICTIVE
        r3 = m.compute_policy_restrictiveness(ffr=2.35, core_pce=1.00, r_star=1.10)
        self.assertEqual(r3["restrictiveness_gap"], 0.25)
        self.assertEqual(r3["stance"], m.PolicyStance.MODERATELY_RESTRICTIVE.value)

        # Gap = 0.24 -> NEUTRAL
        r4 = m.compute_policy_restrictiveness(ffr=2.34, core_pce=1.00, r_star=1.10)
        self.assertEqual(r4["restrictiveness_gap"], 0.24)
        self.assertEqual(r4["stance"], m.PolicyStance.NEUTRAL.value)

        # Gap = -0.25 -> NEUTRAL
        r5 = m.compute_policy_restrictiveness(ffr=1.85, core_pce=1.00, r_star=1.10)
        self.assertEqual(r5["restrictiveness_gap"], -0.25)
        self.assertEqual(r5["stance"], m.PolicyStance.NEUTRAL.value)

        # Gap = -0.26 -> ACCOMMODATIVE
        r6 = m.compute_policy_restrictiveness(ffr=1.84, core_pce=1.00, r_star=1.10)
        self.assertEqual(r6["restrictiveness_gap"], -0.26)
        self.assertEqual(r6["stance"], m.PolicyStance.ACCOMMODATIVE.value)

    def test_adv_11_rimp_model_extreme_spread_capping(self):
        """Tests RIMP model under extreme positive and negative gaps."""
        # Extreme tight: gap = +10.0%p -> capped at 22.50%
        rimp_extreme_tight = m.compute_rimp_heterogeneity_model(10.0)
        self.assertEqual(rimp_extreme_tight["alpha_spread_pct"], 22.50)
        self.assertIn("우량 대형주", rimp_extreme_tight["favored_universe"])

        # Boundary at 0.50%p
        rimp_050 = m.compute_rimp_heterogeneity_model(0.50)
        self.assertEqual(rimp_050["alpha_spread_pct"], 13.75)

        # Neutral 0.00%p
        rimp_zero = m.compute_rimp_heterogeneity_model(0.00)
        self.assertEqual(rimp_zero["alpha_spread_pct"], 5.00)

        # Extreme accommodative: gap = -10.0%p
        # alpha_spread = -(8.0 + 2.0 * 10) = -28.00%
        rimp_extreme_easy = m.compute_rimp_heterogeneity_model(-10.0)
        self.assertEqual(rimp_extreme_easy["alpha_spread_pct"], -28.00)
        self.assertIn("중소형", rimp_extreme_easy["favored_universe"])


class TestMacroAdversarialCombinatorialStress(unittest.TestCase):
    """Combinatorial grid stress testing (7,700 synthetic market states) across regime engine."""

    def test_adv_12_combinatorial_grid_stability(self):
        """
        Executes a dense Cartesian product across all regime dimensions:
        - spread: [-1.50, -0.50, -0.01, 0.0, 0.10, 0.15, 0.16, 0.27, 0.50, 1.20, 3.0]
        - delta_net_liq: [-500.0, -50.0, 0.0, 10.0, 50.0, 50.1, 200.0]
        - restrictiveness_gap: [-5.0, -1.0, -0.26, -0.25, 0.0, 0.24, 0.25, 0.50, 1.0, 3.5]
        - was_inverted: [True, False]
        - curve_shift: [BULL_STEEPENER, BEAR_STEEPENER, BULL_FLATTENER, BEAR_FLATTENER, UNCHANGED]

        Total combinations: 11 * 7 * 10 * 2 * 5 = 7,700 states!
        Verifies:
        1. No unhandled exception or NaN.
        2. Regime code is one of the 4 valid MacroRegimeCode values.
        3. P/E multiple outlook is valid enum.
        4. Factor allocations always sum to exactly 100.0%.
        5. Sector matrix always has exactly 6 sectors with non-empty ratings and rationales.
        6. JSON serialization is 100% compliant without error.
        """
        spreads = [-1.50, -0.50, -0.01, 0.0, 0.10, 0.15, 0.16, 0.27, 0.50, 1.20, 3.0]
        liq_deltas = [-500.0, -50.0, 0.0, 10.0, 50.0, 50.1, 200.0]
        gaps = [-5.0, -1.0, -0.26, -0.25, 0.0, 0.24, 0.25, 0.50, 1.0, 3.5]
        inversions = [True, False]
        shifts = list(m.CurveShiftType)

        valid_regime_codes = {c.value for c in m.MacroRegimeCode}
        valid_outlooks = {o.value for o in m.MultipleOutlook}

        evaluated_count = 0
        for s in spreads:
            for dl in liq_deltas:
                for gap in gaps:
                    for inv in inversions:
                        for shift in shifts:
                            evaluated_count += 1
                            regime = m.classify_macro_regime(
                                spread=s,
                                delta_net_liq_90d=dl,
                                restrictiveness_gap=gap,
                                was_inverted_last_180d=inv,
                                curve_shift=shift
                            )

                            # 1. Regime code validity
                            self.assertIn(regime["regime_code"], valid_regime_codes)

                            # 2. Outlook validity
                            self.assertIn(regime["per_multiple_outlook"], valid_outlooks)

                            # 3. Allocation sum invariant == 100.0%
                            alloc = regime["factor_allocations"]
                            tot = alloc["core_pct"] + alloc["satellite_pct"] + alloc["cash_pct"]
                            self.assertAlmostEqual(tot, 100.0, places=3)

                            # 4. Sector matrix validity
                            sec_mat = m.get_sector_sensitivity_matrix(regime["regime_code"])
                            self.assertEqual(len(sec_mat), 6, f"Expected 6 sectors for {regime['regime_code']}")
                            for sec in sec_mat:
                                self.assertTrue(sec["sector"])
                                self.assertTrue(sec["rating"])
                                self.assertTrue(sec["rationale"])

                            # 5. JSON serializability
                            json_str = json.dumps(regime, ensure_ascii=False)
                            self.assertTrue(len(json_str) > 0)

        self.assertEqual(evaluated_count, 7700)

    def test_adv_13_sqlite_extreme_values_persistence(self):
        """Verifies SQLite persistence round-trip when storing extreme numerical inputs."""
        temp_dir = tempfile.mkdtemp(prefix="adv_db_test_")
        temp_db = Path(temp_dir) / "adv_test.db"
        try:
            m.ensure_tables_and_seed(temp_db)
            conn = m.get_db_connection(temp_db)
            cur = conn.cursor()

            # Insert an extreme boundary record into macro_indicators
            extreme_record = {
                "indicator_date": "2099-12-31",
                "us_10y_yield": 25.5,
                "us_2y_yield": -0.75,
                "yield_spread_10y_2y": 26.25,
                "yield_curve_state": "STEEP",
                "curve_shift_type": "BEAR_STEEPENER",
                "fed_funds_rate": 30.0,
                "real_neutral_rate_r_star": -1.5,
                "core_pce_inflation": -5.0,
                "policy_restrictiveness_gap": 36.5,
                "tga_balance_billion": 0.0,
                "on_rrp_balance_billion": 0.0,
                "fed_total_assets_trillion": 0.5,
                "net_liquidity_billion": 500.0,
                "net_liquidity_change_30d": -250.0,
                "net_liquidity_change_90d": -500.0,
                "dxy_index": 160.0,
                "usdkrw_exchange_rate": 1900.0,
                "vix_index": 85.0,
                "recorded_at": "2099-12-31T09:00:00",
                "updated_at": "2099-12-31T09:00:00"
            }

            cols = list(extreme_record.keys())
            placeholders = ", ".join(["?"] * len(cols))
            sql = f"INSERT INTO macro_indicators ({', '.join(cols)}) VALUES ({placeholders})"
            cur.execute(sql, [extreme_record[c] for c in cols])
            conn.commit()

            # Retrieve and verify round-trip fidelity
            cur.execute("SELECT * FROM macro_indicators WHERE indicator_date = '2099-12-31'")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["us_10y_yield"], 25.5)
            self.assertEqual(row["us_2y_yield"], -0.75)
            self.assertEqual(row["tga_balance_billion"], 0.0)
            self.assertEqual(row["on_rrp_balance_billion"], 0.0)
            self.assertEqual(row["policy_restrictiveness_gap"], 36.5)

            conn.close()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMacroAdversarialValidationAndCorruption(unittest.TestCase):
    """Stress tests on report schema validation, corrupted DB data, and hash stability."""

    def test_adv_14_report_validation_boundaries(self):
        """Verifies report validation constraints and boundary enforcement."""
        base_rep = dict(m.SEED_MACRO_REPORTS[0])

        # Exact valid bounds for sentiment_score: -1.0 and 1.0
        base_rep["sentiment_score"] = -1.0
        m.validate_macro_report(base_rep)
        base_rep["sentiment_score"] = 1.0
        m.validate_macro_report(base_rep)

        # Out-of-bounds sentiment_score -> raises ValueError
        base_rep["sentiment_score"] = 1.0001
        with self.assertRaises(ValueError):
            m.validate_macro_report(base_rep)

        base_rep["sentiment_score"] = -1.0001
        with self.assertRaises(ValueError):
            m.validate_macro_report(base_rep)

        # Invalid sentiment string
        base_rep["sentiment_score"] = 0.0
        base_rep["sentiment"] = "SUPER_BULLISH"
        with self.assertRaises(ValueError):
            m.validate_macro_report(base_rep)

        # Empty string in mandatory field
        base_rep["sentiment"] = "DOVISH"
        base_rep["summary"] = "   "
        with self.assertRaises(ValueError):
            m.validate_macro_report(base_rep)

        # None in mandatory field
        base_rep["summary"] = None
        with self.assertRaises(ValueError):
            m.validate_macro_report(base_rep)

    def test_adv_15_corrupted_json_in_db_graceful_recovery(self):
        """Verifies that get_all_macro_data recovers gracefully if DB JSON columns are corrupt."""
        temp_dir = tempfile.mkdtemp(prefix="adv_corrupt_")
        temp_db = Path(temp_dir) / "corrupt_test.db"
        try:
            m.ensure_tables_and_seed(temp_db)
            conn = m.get_db_connection(temp_db)
            cur = conn.cursor()

            # Corrupt factor_allocations_json and sector_matrix_json in macro_regime
            cur.execute("""
                UPDATE macro_regime
                SET factor_allocations_json = '{corrupted_not_json: true',
                    sector_matrix_json = 'INVALID_ARRAY'
                WHERE regime_id = 'CURRENT'
            """)
            conn.commit()

            # 1. When passed an open Connection, get_all_macro_data catches the JSONDecodeError
            # and gracefully falls back to empty dict/list without throwing an exception.
            data_from_conn = m.get_all_macro_data(conn)
            self.assertEqual(data_from_conn["status"], "success")
            self.assertEqual(data_from_conn["regime"]["factor_allocations"], {})
            self.assertEqual(data_from_conn["regime"]["sector_matrix"], [])
            conn.close()

            # 2. When passed a file path, get_all_macro_data triggers ensure_tables_and_seed,
            # which actively self-heals corrupted records via ON CONFLICT DO UPDATE.
            data_from_path = m.get_all_macro_data(temp_db)
            self.assertEqual(data_from_path["status"], "success")
            self.assertIn("core_pct", data_from_path["regime"]["factor_allocations"])
            self.assertEqual(len(data_from_path["regime"]["sector_matrix"]), 6)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_adv_16_backend_mirror_parity(self):
        """Verifies backend mirror exports identical quant math symbols and passes functions."""
        backend_mirror = importlib.import_module("InvestmentPortal.backend.sync_macro")
        quant_symbols = [
            "compute_yield_spread",
            "classify_yield_curve_state",
            "classify_yield_curve_shift",
            "compute_net_liquidity",
            "evaluate_rrp_buffer",
            "compute_policy_restrictiveness",
            "compute_rimp_heterogeneity_model",
            "evaluate_ken_fisher_rules",
            "classify_macro_regime",
            "get_sector_sensitivity_matrix",
            "compute_macro_report_hash",
            "validate_macro_report",
            "run_sync",
            "get_all_macro_data",
        ]
        for sym in quant_symbols:
            self.assertTrue(hasattr(backend_mirror, sym), f"Backend mirror missing {sym}")
            # Ensure callable points to valid implementation
            fn = getattr(backend_mirror, sym)
            self.assertTrue(callable(fn), f"Symbol {sym} is not callable in backend mirror")


if __name__ == "__main__":
    unittest.main()
