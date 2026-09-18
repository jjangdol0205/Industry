"""
Milestone 1 Iteration 2 Challenger Verification Test Suite
==========================================================
Codified adversarial challenges and empirical verification tests for:
  1. evaluate_company with null/missing/non-numeric prices (no TypeError)
  2. Non-finite float guards in normalizers & DCA (RFC 8259 JSON compliance)
  3. Percentage string normalization precision ("1.5%" -> 1.5, not 150.0)
  4. Oversold rebound calculation with all-NaN Low series and Inf values (no NaNs)
  5. Canonical E2E contract wrappers and tuple return types
  6. Backend and root engine parity verification

Author: Challenger (Milestone 1 Iteration 2)
"""

import sys
import os
import math
import pytest
import numpy as np
import pandas as pd

# Ensure workspace root is in sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import investment_engine as ie
import InvestmentPortal.backend.investment_engine as backend_ie


# ==============================================================================
# 1. Null / Non-Numeric Price Handling in evaluate_company
# ==============================================================================

class TestNullPriceHandlingInEvaluateCompany:
    """
    Challenge: When current_price and/or high_52w are None, non-numeric,
    or negative, evaluate_company must NOT raise TypeError or ValueError.
    """

    def test_both_prices_none(self):
        profile = {'ticker': 'TEST', 'current_price': None, 'high_52w': None}
        res = ie.evaluate_company(profile)
        assert res['portfolio_tier'] == 'Standard'
        assert res['dca_stage'] == 'STD_WAIT'
        assert res['korean_status'] == '관망'
        assert res['is_buy_ready'] is False

    def test_current_price_none_high_present(self):
        profile = {'ticker': 'TEST', 'current_price': None, 'high_52w': 150.0}
        res = ie.evaluate_company(profile)
        assert res['dca_stage'] == 'STD_WAIT'
        assert res['is_buy_ready'] is False

    def test_high_52w_none_current_present(self):
        profile = {'ticker': 'TEST', 'current_price': 100.0, 'high_52w': None}
        res = ie.evaluate_company(profile)
        assert res['dca_stage'] == 'STD_WAIT'
        assert res['is_buy_ready'] is False

    def test_string_na_prices(self):
        profile = {'ticker': 'TEST', 'current_price': 'N/A', 'high_52w': ''}
        res = ie.evaluate_company(profile)
        assert res['dca_stage'] == 'STD_WAIT'

    def test_zero_or_negative_high_52w(self):
        profile_zero = {'ticker': 'TEST', 'current_price': 50.0, 'high_52w': 0.0}
        res_zero = ie.evaluate_company(profile_zero)
        assert res_zero['dca_stage'] == 'STD_WAIT'

        profile_neg = {'ticker': 'TEST', 'current_price': 50.0, 'high_52w': -10.0}
        res_neg = ie.evaluate_company(profile_neg)
        assert res_neg['dca_stage'] == 'STD_WAIT'

    def test_valid_prices_produce_correct_mdd(self):
        profile = {'ticker': 'TEST', 'current_price': 80.0, 'high_52w': 100.0}
        res = ie.evaluate_company(profile)
        assert res['mdd_pct'] == -20.0
        # Standard tier with -20% MDD -> STD_WAIT (requires -40% for DEEP_DISCOUNT)
        assert res['dca_stage'] == 'STD_WAIT'


# ==============================================================================
# 2. Non-Finite Float Guards & RFC 8259 Compliance
# ==============================================================================

class TestNonFiniteFloatGuardsAndRFC8259:
    """
    Challenge: Inf, -Inf, and NaN must never propagate to output dictionaries,
    guaranteeing strict RFC 8259 JSON serialization safety.
    """

    def test_normalize_percentage_non_finite(self):
        assert ie.normalize_percentage(float('inf')) is None
        assert ie.normalize_percentage(float('-inf')) is None
        assert ie.normalize_percentage(float('nan')) is None
        assert ie.normalize_percentage("inf") is None
        assert ie.normalize_percentage("-infinity") is None

    def test_normalize_de_non_finite(self):
        assert ie.normalize_de(float('inf')) is None
        assert ie.normalize_de(float('-inf')) is None
        assert ie.normalize_de(float('nan')) is None
        assert ie.normalize_de("Infinity") is None

    def test_evaluate_mdd_dca_non_finite(self):
        for bad_mdd in [float('inf'), float('-inf'), float('nan')]:
            res = ie.evaluate_mdd_dca("Core", bad_mdd)
            assert res['mdd_pct'] == 0.0
            assert res['stage'] == 'CORE_HOLD'
            assert not math.isinf(res['mdd_pct'])
            assert not math.isnan(res['mdd_pct'])
            assert "inf" not in res['buy_signal'].lower()
            assert "nan" not in res['buy_signal'].lower()

    def test_moat_score_with_inf_metrics(self):
        profile = {
            'opm': float('inf'),
            'roe': float('-inf'),
            'debt_to_equity': float('inf'),
            'revenue_growth': float('nan')
        }
        score, bd = ie.calculate_moat_score(profile)
        assert math.isfinite(score)
        for k, v in bd.items():
            if isinstance(v, (int, float)):
                assert math.isfinite(v), f"Key {k} has non-finite value: {v}"


# ==============================================================================
# 3. Percentage String Normalization Precision
# ==============================================================================

class TestPercentageStringNormalizationPrecision:
    """
    Challenge: Explicit '%' strings must preserve their nominal percentage value
    and never suffer from 100x ratio multiplication inflation.
    """

    def test_small_positive_percentage_string(self):
        assert ie.normalize_percentage("1.5%") == 1.5
        assert ie.normalize_percentage("0.5%") == 0.5
        assert ie.normalize_percentage("2.0%") == 2.0
        assert ie.normalize_percentage("0.0%") == 0.0

    def test_small_negative_percentage_string(self):
        assert ie.normalize_percentage("-0.8%") == -0.8
        assert ie.normalize_percentage("-1.5%") == -1.5
        assert ie.normalize_percentage("-2.0%") == -2.0

    def test_large_percentage_string(self):
        assert ie.normalize_percentage("25.5%") == 25.5
        assert ie.normalize_percentage("150.0%") == 150.0

    def test_numeric_decimal_ratios_still_converted(self):
        # Numeric decimals in [-2.0, 2.0] without '%' are ratios -> scaled x100
        assert ie.normalize_percentage(0.015) == 1.5
        assert ie.normalize_percentage(0.35) == 35.0
        assert ie.normalize_percentage(-0.05) == -5.0

    def test_normalize_de_percentage_string(self):
        assert ie.normalize_de("1.5%") == 1.5
        assert ie.normalize_de("50.0%") == 50.0
        # Decimal without % <= 3.0 converted to percentage
        assert ie.normalize_de(0.50) == 50.0


# ==============================================================================
# 4. Oversold Rebound All-NaN Low Series & Inf Resilience
# ==============================================================================

class TestOversoldAllNaNLowSeriesAndInfResilience:
    """
    Challenge: Missing or corrupted Low column or infinite prices must never
    cause calculate_oversold_rebound to output NaNs.
    """

    def test_low_column_entirely_nan(self):
        n = 30
        dates = pd.date_range('2026-01-01', periods=n)
        df = pd.DataFrame({
            'Close': [100.0 - i * 1.5 for i in range(n)],
            'Low': [np.nan] * n
        }, index=dates)

        res = ie.calculate_oversold_rebound(df)

        assert not math.isnan(res['support_price'])
        assert not math.isnan(res['support_buffer_pct'])
        assert not math.isnan(res['rebound_score'])
        assert res['support_price'] > 0.0
        assert 0.0 <= res['rebound_score'] <= 100.0

    def test_low_column_missing_entirely(self):
        n = 30
        dates = pd.date_range('2026-01-01', periods=n)
        df = pd.DataFrame({
            'Close': [100.0 - i * 1.5 for i in range(n)]
        }, index=dates)

        res = ie.calculate_oversold_rebound(df)

        assert not math.isnan(res['support_price'])
        assert not math.isnan(res['support_buffer_pct'])
        assert not math.isnan(res['rebound_score'])

    def test_inf_and_nan_in_close_series(self):
        raw_close = [100.0] * 20 + [float('inf'), float('-inf'), np.nan] + [90.0, 85.0, 80.0]
        df = pd.DataFrame({'Close': raw_close})

        res = ie.calculate_oversold_rebound(df)

        assert math.isfinite(res['rsi_14'])
        assert math.isfinite(res['bollinger_pct_b'])
        assert math.isfinite(res['disparity_20'])
        assert math.isfinite(res['support_price'])
        assert math.isfinite(res['support_buffer_pct'])
        assert math.isfinite(res['rebound_score'])
        assert 0.0 <= res['rebound_score'] <= 100.0


# ==============================================================================
# 5. Canonical Interface Contract Wrappers & Exact Tuples
# ==============================================================================

class TestCanonicalInterfaceContractWrappers:
    """
    Challenge: Wrappers must exist and return exact expected types and values:
      - evaluate_stock_tier: Tuple[str, float]
      - compute_dca_signal: Tuple[str, str]
      - compute_rebound_score: Tuple[float, str]
      - classify_rebound_signal: str
      - calculate_mdd: float
    """

    def test_evaluate_stock_tier_contract(self):
        metrics = {
            'market_dominance': 25,
            'opm': 35.0,
            'roe': 25.0,
            'gross_margin_ttm': 60.0,
            'revenue_growth': 20.0,
            'debt_to_equity': 40.0
        }
        res = ie.evaluate_stock_tier(metrics)
        assert isinstance(res, tuple)
        assert len(res) == 2
        tier, score = res
        assert isinstance(tier, str)
        assert isinstance(score, float)
        assert tier == 'Core'
        assert score >= 80.0

    def test_compute_dca_signal_contract(self):
        res = ie.compute_dca_signal("Core", -22.5)
        assert isinstance(res, tuple)
        assert len(res) == 2
        buy_signal, stage = res
        assert isinstance(buy_signal, str)
        assert isinstance(stage, str)
        assert stage == 'CORE_DCA_1'
        assert 'BUY_READY' in buy_signal

    def test_compute_rebound_score_contract(self):
        n = 30
        dates = pd.date_range('2026-01-01', periods=n)
        df = pd.DataFrame({'Close': [100.0 - i * 2.0 for i in range(n)]}, index=dates)

        res = ie.compute_rebound_score(df)
        assert isinstance(res, tuple)
        assert len(res) == 2
        score, signal = res
        assert isinstance(score, float)
        assert isinstance(signal, str)
        assert 0.0 <= score <= 100.0
        assert signal in ('STRONG_REBOUND', 'MODERATE_REBOUND', 'CONSOLIDATING', 'NEUTRAL')

    def test_classify_rebound_signal_contract(self):
        assert ie.classify_rebound_signal(75.0) == 'STRONG_REBOUND'
        assert ie.classify_rebound_signal(55.0) == 'MODERATE_REBOUND'
        assert ie.classify_rebound_signal(35.0) == 'CONSOLIDATING'
        assert ie.classify_rebound_signal(20.0) == 'NEUTRAL'

    def test_calculate_mdd_contract(self):
        assert ie.calculate_mdd(80.0, 100.0) == -20.0
        assert ie.calculate_mdd(100.0, 100.0) == 0.0
        assert ie.calculate_mdd(110.0, 100.0) == 0.0  # New high
        assert ie.calculate_mdd(50.0, 0.0) == 0.0    # Zero high
        assert ie.calculate_mdd(None, 100.0) == 0.0  # None price


# ==============================================================================
# 6. Root Engine vs Backend Engine Parity
# ==============================================================================

class TestCrossFileEngineParity:
    """
    Challenge: Both root investment_engine.py and InvestmentPortal/backend/investment_engine.py
    must export the exact same functions and return identical outputs.
    """

    def test_all_exports_match(self):
        assert set(ie.__all__) == set(backend_ie.__all__)

    def test_identical_evaluations(self):
        profile = {
            'ticker': 'NVDA',
            'current_price': 120.0,
            'high_52w': 140.0,
            'opm': 0.60,
            'roe': 0.70,
            'debt_to_equity': 0.30
        }
        res_root = ie.evaluate_company(profile)
        res_backend = backend_ie.evaluate_company(profile)

        assert res_root['portfolio_tier'] == res_backend['portfolio_tier']
        assert res_root['moat_score'] == res_backend['moat_score']
        assert res_root['dca_stage'] == res_backend['dca_stage']
        assert res_root['mdd_pct'] == res_backend['mdd_pct']
