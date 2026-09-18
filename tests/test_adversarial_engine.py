"""
Adversarial Stress Testing & Boundary Verification Suite for Quantitative Investment Engine
============================================================================================
Author: Challenger 1 (Milestone 1)
Target: investment_engine.py

Verifies:
  1. Exact boundary MDD behavior across all 4 tiers (Core, Satellite, Watchlist, Standard)
  2. Extreme financial metrics (OPM > 100%, OPM < -100%, ROE > 1000%, ROE < -500%, D/E = 0, D/E < 0)
  3. Non-finite values (NaN, Inf, -Inf) and graceful degradation
  4. Missing keys, None values, and malformed inputs in evaluate_company
  5. Technical oversold rebound engine edge cases (flat price, zero price, short series)
"""

import sys
import os
import math
import pytest
import pandas as pd
import numpy as np

# Ensure root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from investment_engine import (
    calculate_moat_score,
    classify_tier,
    evaluate_mdd_dca,
    calculate_oversold_rebound,
    evaluate_company,
    normalize_percentage,
    normalize_de,
    extract_dominance_score,
)


# ==============================================================================
# 1. Extreme MDD Boundary Tests
# ==============================================================================

class TestExtremeMddBoundaries:
    """
    Tests exact boundary conditions for MDD:
      0.0%, -19.99%, -20.0%, -29.99%, -30.0%, -34.99%, -35.0%, -39.99%, -40.0%, -99.9%
    across all portfolio tiers.
    """

    # --- Core Tier Boundaries ---
    def test_core_mdd_zero(self):
        res = evaluate_mdd_dca("Core", 0.0)
        assert res['stage'] == "CORE_HOLD"
        assert res['korean_status'] == "홀딩"
        assert res['is_buy_ready'] is False

    def test_core_mdd_just_above_threshold_1(self):
        # -19.99% is not yet -20.0% -> HOLD
        res = evaluate_mdd_dca("Core", -19.99)
        assert res['stage'] == "CORE_HOLD"
        assert res['korean_status'] == "홀딩"
        assert res['is_buy_ready'] is False

    def test_core_mdd_exact_threshold_1(self):
        # -20.0% exact trigger for DCA 1
        res = evaluate_mdd_dca("Core", -20.0)
        assert res['stage'] == "CORE_DCA_1"
        assert res['korean_status'] == "1차 매수적기"
        assert res['is_buy_ready'] is True
        assert "1차 분할매수" in res['buy_signal']

    def test_core_mdd_just_above_threshold_2(self):
        # -29.99% is DCA 1, not yet DCA 2
        res = evaluate_mdd_dca("Core", -29.99)
        assert res['stage'] == "CORE_DCA_1"
        assert res['korean_status'] == "1차 매수적기"
        assert res['is_buy_ready'] is True

    def test_core_mdd_exact_threshold_2(self):
        # -30.0% exact trigger for DCA 2
        res = evaluate_mdd_dca("Core", -30.0)
        assert res['stage'] == "CORE_DCA_2"
        assert res['korean_status'] == "2차 매수적기"
        assert res['is_buy_ready'] is True
        assert "2차 분할매수" in res['buy_signal']

    def test_core_mdd_deep_crashes(self):
        for mdd in [-34.99, -35.0, -39.99, -40.0, -99.9]:
            res = evaluate_mdd_dca("Core", mdd)
            assert res['stage'] == "CORE_DCA_2"
            assert res['korean_status'] == "2차 매수적기"
            assert res['is_buy_ready'] is True

    # --- Satellite Tier Boundaries ---
    def test_satellite_mdd_boundaries(self):
        # Above -25.0% -> HOLD
        for mdd in [0.0, -19.99, -20.0, -24.99]:
            res = evaluate_mdd_dca("Satellite", mdd)
            assert res['stage'] == "SAT_HOLD"
            assert res['korean_status'] == "홀딩"
            assert res['is_buy_ready'] is False

        # -25.0% to -34.99% -> DCA 1
        for mdd in [-25.0, -29.99, -30.0, -34.99]:
            res = evaluate_mdd_dca("Satellite", mdd)
            assert res['stage'] == "SAT_DCA_1"
            assert res['korean_status'] == "1차 매수적기"
            assert res['is_buy_ready'] is True

        # -35.0% and deeper -> DCA 2
        for mdd in [-35.0, -39.99, -40.0, -99.9]:
            res = evaluate_mdd_dca("Satellite", mdd)
            assert res['stage'] == "SAT_DCA_2"
            assert res['korean_status'] == "2차 매수적기"
            assert res['is_buy_ready'] is True

    # --- Watchlist Tier Boundaries ---
    def test_watchlist_mdd_boundaries(self):
        # Above -35.0% -> WAIT
        for mdd in [0.0, -19.99, -20.0, -29.99, -30.0, -34.99]:
            res = evaluate_mdd_dca("Watchlist", mdd)
            assert res['stage'] == "WATCH_WAIT"
            assert res['korean_status'] == "관망"
            assert res['is_buy_ready'] is False

        # -35.0% and deeper -> DEEP
        for mdd in [-35.0, -39.99, -40.0, -99.9]:
            res = evaluate_mdd_dca("Watchlist", mdd)
            assert res['stage'] == "WATCH_DEEP"
            assert res['korean_status'] == "1차 매수적기"
            assert res['is_buy_ready'] is True

    # --- Standard Tier Boundaries ---
    def test_standard_mdd_boundaries(self):
        # Above -40.0% -> WAIT
        for mdd in [0.0, -19.99, -20.0, -29.99, -30.0, -34.99, -35.0, -39.99]:
            res = evaluate_mdd_dca("Standard", mdd)
            assert res['stage'] == "STD_WAIT"
            assert res['korean_status'] == "관망"
            assert res['is_buy_ready'] is False

        # -40.0% and deeper -> DISCOUNT
        for mdd in [-40.0, -99.9]:
            res = evaluate_mdd_dca("Standard", mdd)
            assert res['stage'] == "STD_DISCOUNT"
            assert res['korean_status'] == "1차 매수적기"
            assert res['is_buy_ready'] is True


# ==============================================================================
# 2. Extreme Financial Metrics & Stress Testing
# ==============================================================================

class TestExtremeFinancialMetrics:
    """
    Tests extreme metrics:
      - OPM > 100%, OPM < -100%
      - ROE > 1000%, ROE < -500%
      - D/E = 0, D/E < 0 (negative equity), D/E > 200%
    """

    def test_extreme_high_opm(self):
        # OPM = 150.0% (e.g. extreme patent licensing windfall)
        score, bd = calculate_moat_score({'opm': 150.0, 'dominance': 0, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 25.0
        assert bd['effective_opm'] == 150.0

    def test_extreme_low_opm(self):
        # OPM = -150.0% (severe pre-revenue biotech or turnaround)
        score, bd = calculate_moat_score({'opm': -150.0, 'dominance': 0, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == -5.0
        assert bd['effective_opm'] == -150.0

    def test_extreme_high_roe(self):
        # ROE = 1200.0% (e.g. asset-light firm with high share buybacks)
        score, bd = calculate_moat_score({'roe': 1200.0, 'dominance': 0, 'opm': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['roe_score'] == 20.0
        assert bd['effective_roe'] == 1200.0

    def test_extreme_low_roe(self):
        # ROE = -600.0% (massive net loss eroding equity)
        score, bd = calculate_moat_score({'roe': -600.0, 'dominance': 0, 'opm': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['roe_score'] == 0.0
        assert bd['effective_roe'] == -600.0

    def test_de_zero(self):
        # Zero debt firm
        score, bd = calculate_moat_score({'de': 0.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'growth': 0})
        assert bd['health_score'] == 10.0
        assert bd['effective_de'] == 0.0

    def test_de_negative_equity(self):
        # Negative equity -> severe distress mapping to 999.0% -> 0 pts
        score, bd = calculate_moat_score({'de': -50.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'growth': 0})
        assert bd['health_score'] == 0.0
        assert bd['effective_de'] == 999.0

    def test_de_extreme_high(self):
        # D/E = 500.0% -> 0 pts
        score, bd = calculate_moat_score({'de': 500.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'growth': 0})
        assert bd['health_score'] == 0.0
        assert bd['effective_de'] == 500.0


# ==============================================================================
# 3. Non-Finite Values (Inf, -Inf, NaN) & Missing Keys
# ==============================================================================

class TestNonFiniteAndMalformedInputs:
    """
    Empirically exposes how the engine behaves on:
      - float('inf'), float('-inf'), float('nan')
      - Missing keys, empty dicts, None values
    """

    def test_nan_metrics_trigger_graceful_imputation(self):
        profile = {
            'opm': float('nan'),
            'roe': float('nan'),
            'gross_margin_ttm': float('nan'),
            'revenue_growth': float('nan'),
            'debt_to_equity': float('nan'),
        }
        score, bd = calculate_moat_score(profile)
        # All 5 fields should be imputed with industry medians
        assert len(bd['imputed_fields']) == 5
        assert bd['effective_opm'] == 10.0
        assert bd['effective_roe'] == 10.0
        assert bd['effective_gpm'] == 30.0
        assert bd['effective_growth'] == 8.0
        assert bd['effective_de'] == 75.0
        assert score == 25.0

    def test_none_metrics_trigger_graceful_imputation(self):
        profile = {
            'opm': None,
            'roe': None,
            'gross_margin_ttm': None,
            'revenue_growth': None,
            'debt_to_equity': None,
        }
        score, bd = calculate_moat_score(profile)
        assert len(bd['imputed_fields']) == 5
        assert score == 25.0

    def test_empty_profile(self):
        score, bd = calculate_moat_score({})
        assert score == 25.0
        assert bd['dominance_score'] == 0.0

    def test_mdd_none_and_nan(self):
        # When mdd_pct is None or NaN, evaluate_mdd_dca should fallback to 0.0
        res_none = evaluate_mdd_dca("Core", None)
        assert res_none['mdd_pct'] == 0.0
        assert res_none['stage'] == "CORE_HOLD"

        res_nan = evaluate_mdd_dca("Core", float('nan'))
        assert res_nan['mdd_pct'] == 0.0
        assert res_nan['stage'] == "CORE_HOLD"

    def test_evaluate_company_with_empty_dict(self):
        # Empty dict should evaluate cleanly to Standard tier
        res = evaluate_company({})
        assert res['portfolio_tier'] == "Standard"
        assert res['moat_score'] == 25.0
        assert res['dca_stage'] == "STD_WAIT"

    def test_evaluate_company_null_prices_bug_investigation(self):
        """
        Adversarial challenge:
        When current_price and high_52w are present in profile but set to None or non-numeric,
        evaluate_company previously failed if not guarded by try-except.
        """
        profile = {
            'ticker': 'TEST',
            'current_price': None,
            'high_52w': None,
        }
        # If this raises an unhandled TypeError, the engine has a critical bug.
        try:
            res = evaluate_company(profile)
            assert res['dca_stage'] in ('STD_WAIT', 'CORE_HOLD')
        except TypeError as e:
            pytest.fail(f"CRITICAL BUG: evaluate_company raised unhandled TypeError on None prices: {e}")


# ==============================================================================
# 4. Percentage String Normalization Edge Cases
# ==============================================================================

class TestPercentageNormalizationPitfalls:
    """
    Tests edge cases where decimal ratios vs percentage numbers are ambiguous.
    """

    def test_explicit_percent_strings(self):
        assert normalize_percentage("25.0%") == 25.0
        assert normalize_percentage("5.5%") == 5.5

    def test_small_percent_string_distortion(self):
        """
        Adversarial test:
        A company with 1.5% margin passed as "1.5%".
        If normalize_percentage strips '%' and sees abs(1.5) <= 2.0,
        it multiplies by 100 to 150.0%, creating a 100x distortion!
        """
        val = normalize_percentage("1.5%")
        # A correct parser must return 1.5, NOT 150.0
        assert val == 1.5, f"Expected 1.5 but got {val} (100x distortion!)"


# ==============================================================================
# 5. Technical Rebound Engine Edge Cases
# ==============================================================================

class TestOversoldReboundEdgeCases:
    """
    Tests technical oversold rebound under extreme market data regimes.
    """

    def test_flat_price_series_no_divide_by_zero(self):
        # Stock halted or fixed price for 50 days
        dates = pd.date_range(end='2026-09-18', periods=50)
        df = pd.DataFrame({'Close': [100.0] * 50, 'Low': [100.0] * 50}, index=dates)
        res = calculate_oversold_rebound(df)
        assert math.isfinite(res['rsi_14'])
        assert math.isfinite(res['bollinger_pct_b'])
        assert math.isfinite(res['rebound_score'])
        assert res['rebound_signal'] == 'NEUTRAL'

    def test_zero_price_series(self):
        dates = pd.date_range(end='2026-09-18', periods=20)
        df = pd.DataFrame({'Close': [0.0] * 20, 'Low': [0.0] * 20}, index=dates)
        res = calculate_oversold_rebound(df)
        assert math.isfinite(res['rebound_score'])

    def test_series_shorter_than_5_rows(self):
        dates = pd.date_range(end='2026-09-18', periods=4)
        df = pd.DataFrame({'Close': [10.0, 11.0, 12.0, 13.0]}, index=dates)
        res = calculate_oversold_rebound(df)
        assert res['rebound_score'] == 0.0
        assert res['rebound_signal'] == 'NEUTRAL'


if __name__ == '__main__':
    pytest.main(['-v', __file__])
