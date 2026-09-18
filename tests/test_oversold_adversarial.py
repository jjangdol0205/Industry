"""
Adversarial Stress Test Suite for Technical Oversold Rebound Engine
===================================================================
Empirical challenger tests for calculate_oversold_rebound and related contracts in investment_engine.py.
Covers:
  1. Constant price series (zero volatility, std = 0)
  2. Monotonically crashing series (100% downward trend)
  3. Short series (< 14 days, < 20 days, 1 day, empty DataFrame, None)
  4. NaN / None / Inf values in close/high/low series
  5. Sudden spike / rebound series (verifying downside support buffer)
  6. Boundary verification: [0, 100] ranges, no zero division, NaN propagation checks
  7. Contract compliance: check existence of E2E wrapper functions
"""

import math
import pytest
import numpy as np
import pandas as pd

import investment_engine as ie


# ==============================================================================
# 1. Constant Price Series (Zero Volatility, std = 0)
# ==============================================================================

class TestConstantPriceSeries:
    def test_constant_series_std_zero(self):
        """
        Constant price series over 50 trading days:
        - std = 0 must NOT cause division by zero in Bollinger Bands %B.
        - %B should gracefully evaluate to 0.5 (neutral midpoint).
        - RSI should be 50.0 (zero gain, zero loss).
        - Disparity should be 100.0 (Close == MA).
        - Rebound score must be strictly in [0, 100].
        - Signal should be 'NEUTRAL'.
        """
        dates = pd.date_range('2026-01-01', periods=50)
        df = pd.DataFrame({
            'Close': [100.0] * 50,
            'Low': [100.0] * 50,
            'High': [100.0] * 50,
        }, index=dates)

        res = ie.calculate_oversold_rebound(df)

        assert res['rsi_14'] == 50.0
        assert res['bollinger_pct_b'] == 0.5
        assert res['disparity_20'] == 100.0
        assert res['disparity_60'] == 100.0
        assert 0.0 <= res['rebound_score'] <= 100.0
        assert res['rebound_signal'] == 'NEUTRAL'
        assert not math.isnan(res['rebound_score'])
        assert not math.isinf(res['rebound_score'])

    def test_constant_series_zero_price(self):
        """
        Constant zero price (0.0):
        Must not divide by zero anywhere.
        """
        dates = pd.date_range('2026-01-01', periods=30)
        df = pd.DataFrame({
            'Close': [0.0] * 30,
            'Low': [0.0] * 30,
            'High': [0.0] * 30,
        }, index=dates)

        res = ie.calculate_oversold_rebound(df)
        assert not math.isnan(res['rebound_score'])
        assert 0.0 <= res['rebound_score'] <= 100.0


# ==============================================================================
# 2. Monotonically Crashing Series (100% Downward Trend)
# ==============================================================================

class TestMonotonicallyCrashingSeries:
    def test_linear_crash(self):
        """
        Price drops monotonically by 2% each day for 40 days.
        - RSI should be deeply oversold (< 25).
        - Disparity should be low (< 88%).
        - Support buffer should be small (<= 3%).
        - Rebound score should indicate strong oversold.
        """
        dates = pd.date_range('2026-01-01', periods=40)
        prices = [100.0 * (0.98 ** i) for i in range(40)]
        df = pd.DataFrame({
            'Close': prices,
            'Low': [p * 0.99 for p in prices],
            'High': [p * 1.01 for p in prices],
        }, index=dates)

        res = ie.calculate_oversold_rebound(df)

        assert res['rsi_14'] < 25.0
        assert res['rsi_score'] == 35.0
        assert res['disparity_20'] <= 88.0
        assert res['disp_score'] == 20.0
        assert res['support_buffer_pct'] <= 3.0
        assert res['support_score'] == 20.0
        assert res['rebound_score'] >= 70.0
        assert res['rebound_signal'] in ('STRONG_REBOUND', 'MODERATE_REBOUND')

    def test_flash_crash_gap_down(self):
        """
        Steady market followed by a catastrophic flash crash gap down (-60% in 2 days).
        Should max out all 4 oversold scoring components to reach 100.0.
        """
        dates = pd.date_range('2026-01-01', periods=100)
        prices = [100.0] * 98 + [60.0, 35.0]
        df = pd.DataFrame({
            'Close': prices,
            'Low': [p * 0.98 for p in prices],
            'High': [p * 1.02 for p in prices],
        }, index=dates)

        res = ie.calculate_oversold_rebound(df)

        assert res['rsi_14'] < 25.0
        assert res['bollinger_pct_b'] <= 0.0
        assert res['disparity_20'] <= 88.0
        assert res['support_buffer_pct'] <= 3.0
        assert res['rebound_score'] == 100.0
        assert res['rebound_signal'] == 'STRONG_REBOUND'
        assert res['rebound_status_ko'] == '과매도 반등 강력 적기'


# ==============================================================================
# 3. Short Series Handling (< 14 days, < 20 days, 1 day, empty)
# ==============================================================================

class TestShortSeries:
    def test_none_dataframe(self):
        res = ie.calculate_oversold_rebound(None)
        assert res['rebound_signal'] == 'NEUTRAL'
        assert res['rebound_score'] == 0.0
        assert res['rsi_14'] == 50.0

    def test_empty_dataframe(self):
        res = ie.calculate_oversold_rebound(pd.DataFrame())
        assert res['rebound_signal'] == 'NEUTRAL'
        assert res['rebound_score'] == 0.0

    def test_one_day_series(self):
        df = pd.DataFrame({'Close': [100.0], 'Low': [99.0], 'High': [101.0]})
        res = ie.calculate_oversold_rebound(df)
        assert res['rebound_signal'] == 'NEUTRAL'
        assert res['rebound_score'] == 0.0

    def test_four_day_series_below_five_day_minimum(self):
        df = pd.DataFrame({'Close': [100.0, 98.0, 95.0, 90.0]})
        res = ie.calculate_oversold_rebound(df)
        assert res['rebound_signal'] == 'NEUTRAL'
        assert res['rebound_score'] == 0.0

    def test_five_day_series_minimum_threshold(self):
        """5 days is the minimum length for technical calculation."""
        df = pd.DataFrame({'Close': [100.0, 98.0, 95.0, 90.0, 85.0]})
        res = ie.calculate_oversold_rebound(df)
        assert isinstance(res['rebound_score'], float)
        assert 0.0 <= res['rebound_score'] <= 100.0
        assert not math.isnan(res['rebound_score'])

    def test_ten_day_series_sub_14_and_sub_20(self):
        """
        10 days is < 14 (sub-RSI window) and < 20 (sub-BB window).
        Must fallback to simple mean RSI and adaptive window BB without crashing.
        """
        prices = [100.0 - i * 3.0 for i in range(10)]
        df = pd.DataFrame({'Close': prices, 'Low': prices})
        res = ie.calculate_oversold_rebound(df)
        assert 0.0 <= res['rsi_14'] <= 100.0
        assert 0.0 <= res['rebound_score'] <= 100.0
        assert not math.isnan(res['rsi_14'])
        assert not math.isnan(res['bollinger_pct_b'])


# ==============================================================================
# 4. NaN / None / Inf Adversarial Injections
# ==============================================================================

class TestAdversarialValues:
    def test_interspersed_nans_in_close(self):
        """Close series has random NaNs and Nones that must be dropped cleanly."""
        raw_prices = [100.0, np.nan, 95.0, None, 92.0, np.nan, 88.0, 85.0, 80.0, 75.0]
        df = pd.DataFrame({'Close': raw_prices})
        res = ie.calculate_oversold_rebound(df)
        assert not math.isnan(res['rebound_score'])
        assert 0.0 <= res['rebound_score'] <= 100.0

    def test_all_nans_in_close(self):
        """Entire Close series is NaN -> must return default_res cleanly."""
        df = pd.DataFrame({'Close': [np.nan] * 20})
        res = ie.calculate_oversold_rebound(df)
        assert res['rebound_signal'] == 'NEUTRAL'
        assert res['rebound_score'] == 0.0

    def test_low_column_entirely_nan(self):
        """
        VULNERABILITY CHALLENGE:
        When 'Low' column is present in DataFrame but contains entirely NaNs,
        low_s becomes empty.
        Verify if support_price or support_buffer_pct propagates NaN!
        """
        df = pd.DataFrame({
            'Close': [100.0 - i * 2.0 for i in range(25)],
            'Low': [np.nan] * 25
        })
        res = ie.calculate_oversold_rebound(df)
        # Bug check: If support_price or support_buffer_pct is NaN, this asserts failure
        assert not math.isnan(res['support_price']), "Bug: support_price is NaN when Low column is all NaN"
        assert not math.isnan(res['support_buffer_pct']), "Bug: support_buffer_pct is NaN when Low column is all NaN"
        assert not math.isnan(res['rebound_score'])

    def test_inf_values_in_close(self):
        """
        VULNERABILITY CHALLENGE:
        Close series contains np.inf or -np.inf.
        dropna() does not drop inf by default in pandas.
        Verify if inf causes NaN/Inf propagation into scores.
        """
        df = pd.DataFrame({
            'Close': [100.0] * 20 + [np.inf]
        })
        res = ie.calculate_oversold_rebound(df)
        assert not math.isnan(res['rebound_score']), "Bug: rebound_score is NaN when Close contains inf"
        assert not math.isinf(res['rebound_score']), "Bug: rebound_score is Inf when Close contains inf"


# ==============================================================================
# 5. Sudden Spike / Rebound Series (Downside Support Floor Buffer)
# ==============================================================================

class TestSuddenSpikeSupportBuffer:
    def test_sharp_rebound_kills_oversold_signal(self):
        """
        Stock falls from 100 to 20 (oversold), but on day 41 spikes +50% to 30.
        The downside support floor is 20.
        Current price 30 is (30 - 20)/30 = 33.3% above floor.
        Buffer > 7% must give support_score = 0.0.
        Total rebound score should drop sharply, demonstrating support floor defense.
        """
        dates = pd.date_range('2026-01-01', periods=42)
        # 40 days drop to 20
        prices = [100.0 - 2.0 * i for i in range(41)]  # ends at 20.0
        # Day 41: sudden spike to 30.0
        prices.append(30.0)

        df = pd.DataFrame({
            'Close': prices,
            'Low': prices
        }, index=dates)

        res = ie.calculate_oversold_rebound(df)

        assert res['support_price'] <= 21.0
        assert res['support_buffer_pct'] > 7.0
        assert res['support_score'] == 0.0
        # Rebound score should be demoted from STRONG_REBOUND
        assert res['rebound_score'] < 70.0


# ==============================================================================
# 6. Boundary & Range Verification [0, 100]
# ==============================================================================

class TestRangeAndBounds:
    def test_random_walks_range_invariance(self):
        """
        Stress test 50 randomized price series with drift, volatility, and jumps.
        Verify that:
          - rsi_score in [0, 35]
          - bb_score in [0, 25]
          - disp_score in [0, 20]
          - support_score in [0, 20]
          - rebound_score in [0.0, 100.0]
          - rsi_14 in [0.0, 100.0]
          - No division by zero or NaN propagation.
        """
        np.random.seed(42)
        for i in range(50):
            n = np.random.randint(5, 300)
            returns = np.random.normal(loc=0.0002, scale=0.04, size=n)
            price = 100.0 * np.exp(np.cumsum(returns))
            # clamp price to positive
            price = np.maximum(price, 0.01)

            df = pd.DataFrame({
                'Close': price,
                'Low': price * np.random.uniform(0.95, 1.0, size=n),
                'High': price * np.random.uniform(1.0, 1.05, size=n)
            })

            res = ie.calculate_oversold_rebound(df)

            assert 0.0 <= res['rsi_14'] <= 100.0
            assert 0.0 <= res['rsi_score'] <= 35.0
            assert 0.0 <= res['bb_score'] <= 25.0
            assert 0.0 <= res['disp_score'] <= 20.0
            assert 0.0 <= res['support_score'] <= 20.0
            assert 0.0 <= res['rebound_score'] <= 100.0
            assert not math.isnan(res['rebound_score'])
            assert res['rebound_signal'] in ('STRONG_REBOUND', 'MODERATE_REBOUND', 'CONSOLIDATING', 'NEUTRAL')


# ==============================================================================
# 7. E2E Contract Wrapper Existence Checks
# ==============================================================================

class TestContractInterfaceCompliance:
    def test_e2e_contract_wrappers_present(self):
        """
        Checks whether investment_engine.py exports the wrappers required
        by tests/e2e/test_f4_moat_engine.py and test_f5_mdd_rebound.py:
          - evaluate_stock_tier(metrics)
          - compute_dca_signal(tier, mdd)
          - compute_rebound_score(history_df)
          - classify_rebound_signal(score)
        """
        missing_wrappers = []
        for fn in ('evaluate_stock_tier', 'compute_dca_signal', 'compute_rebound_score', 'classify_rebound_signal'):
            if not hasattr(ie, fn):
                missing_wrappers.append(fn)

        assert len(missing_wrappers) == 0, (
            f"investment_engine.py is missing required E2E contract functions: {missing_wrappers}"
        )
