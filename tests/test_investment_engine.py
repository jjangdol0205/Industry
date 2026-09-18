"""
Comprehensive Unit Tests for Quantitative Investment Engine (Milestone 1: F4 & F5)
==================================================================================
Tests every mathematical formula, boundary condition, tier classification,
MDD DCA evaluation, oversold rebound calculation, and imputation logic.
"""

import pytest
import pandas as pd
import numpy as np

import sys
import os

# Ensure root is importable
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
# 1. Normalization & Utility Tests
# ==============================================================================

class TestNormalization:
    def test_normalize_percentage_decimal(self):
        assert normalize_percentage(0.35) == 35.0
        assert normalize_percentage(0.185) == 18.5
        assert normalize_percentage(-0.05) == -5.0
        assert normalize_percentage(0.0) == 0.0

    def test_normalize_percentage_whole(self):
        assert normalize_percentage(35.0) == 35.0
        assert normalize_percentage(18.5) == 18.5
        assert normalize_percentage(-5.0) == -5.0

    def test_normalize_percentage_string(self):
        assert normalize_percentage("25.5%") == 25.5
        assert normalize_percentage(" 42.0 ") == 42.0
        assert normalize_percentage("invalid") is None
        assert normalize_percentage(None) is None

    def test_normalize_de(self):
        assert normalize_de(0.50) == 50.0
        assert normalize_de(1.20) == 120.0
        assert normalize_de(50.0) == 50.0
        assert normalize_de(150.0) == 150.0
        assert normalize_de(0.0) == 0.0
        # Negative equity mapped to distressed
        assert normalize_de(-20.0) == 999.0
        assert normalize_de(None) is None


# ==============================================================================
# 2. Market Dominance Score Tests (Max 25 pts)
# ==============================================================================

class TestDominanceScore:
    def test_explicit_numerical_dominance(self):
        score, inferred = extract_dominance_score({'market_dominance': 25})
        assert score == 25.0
        assert not inferred

        score, inferred = extract_dominance_score({'dominance': 18})
        assert score == 18.0
        assert not inferred

        score, inferred = extract_dominance_score({'market_dominance': 35})
        assert score == 25.0  # Clamped to max 25

    def test_keyword_tier1_monopoly_25pts(self):
        profiles = [
            {'principle_reason': 'AI GPU 시장 80%+ 독점, CUDA 생태계 락인 (Core 2호)'},
            {'moat_title': 'EUV 노광장비 100% 독점'},
            {'role_description': '다빈치 수술로봇 독점, 글로벌 1위'},
            {'description': 'Global #1 provider of semiconductor metrology with insurmountable switching costs'},
        ]
        for p in profiles:
            score, inferred = extract_dominance_score(p)
            assert score == 25.0
            assert inferred

    def test_keyword_tier2_oligopoly_18pts(self):
        profiles = [
            {'principle_reason': 'HBM3E DRAM 3대 과점, AI 메모리 초고성장'},
            {'principle_reason': '소형 발사체 독보적 2위, 수주잔고 역대 최고치'},
            {'role_description': 'Global top 2 player in high-power cooling'},
        ]
        for p in profiles:
            score, inferred = extract_dominance_score(p)
            assert score == 18.0
            assert inferred

    def test_keyword_tier3_specialized_12pts(self):
        profiles = [
            {'principle_reason': '마이크로니들 리들샷 특허 병목 고마진'},
            {'role_description': '소모품 락인 기반 고마진 비즈니스 모델'},
        ]
        for p in profiles:
            score, inferred = extract_dominance_score(p)
            assert score == 12.0
            assert inferred

    def test_commodity_or_empty_0pts(self):
        score, _ = extract_dominance_score({'description': 'Standard commodity retail merchant'})
        assert score == 0.0


# ==============================================================================
# 3. Moat & Quality Score Boundary Tests (S_moat in [0, 100])
# ==============================================================================

class TestMoatScoreFormulas:
    def test_perfect_100_score(self):
        profile = {
            'market_dominance': 25,
            'op_margin_ttm': 0.40,      # >=35% -> 25 pts
            'roe': 0.35,                # >=30% -> 20 pts
            'gross_margin_ttm': 0.60,   # >=55% -> 10 pts
            'revenue_growth': 0.30,     # >=25% -> 10 pts
            'debt_to_equity': 0.40,     # <=50% -> 10 pts
        }
        score, bd = calculate_moat_score(profile)
        assert score == 100.0
        assert bd['dominance_score'] == 25.0
        assert bd['opm_score'] == 25.0
        assert bd['roe_score'] == 20.0
        assert bd['gpm_score'] == 10.0
        assert bd['growth_score'] == 10.0
        assert bd['health_score'] == 10.0
        assert len(bd['imputed_fields']) == 0

    def test_opm_brackets(self):
        # >=35% -> 25pts
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 35.0, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 25.0

        # 25-35% -> 20pts
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 25.0, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 20.0
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 34.9, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 20.0

        # 18-25% -> 15pts
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 18.0, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 15.0
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 24.9, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 15.0

        # 12-18% -> 10pts
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 12.0, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 10.0

        # 5-12% -> 5pts
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 5.0, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 5.0

        # 0-5% -> 0pts
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 0.0, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 0.0
        s, bd = calculate_moat_score({'dominance': 0, 'opm': 4.9, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == 0.0

        # <0 -> -5pts
        s, bd = calculate_moat_score({'dominance': 0, 'opm': -0.1, 'roe': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['opm_score'] == -5.0

    def test_roe_brackets(self):
        # >=30% -> 20pts
        _, bd = calculate_moat_score({'roe': 30.0, 'dominance': 0, 'opm': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['roe_score'] == 20.0

        # 20-30% -> 16pts
        _, bd = calculate_moat_score({'roe': 20.0, 'dominance': 0, 'opm': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['roe_score'] == 16.0
        _, bd = calculate_moat_score({'roe': 29.9, 'dominance': 0, 'opm': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['roe_score'] == 16.0

        # 14-20% -> 12pts
        _, bd = calculate_moat_score({'roe': 14.0, 'dominance': 0, 'opm': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['roe_score'] == 12.0

        # 8-14% -> 6pts
        _, bd = calculate_moat_score({'roe': 8.0, 'dominance': 0, 'opm': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['roe_score'] == 6.0

        # <8% -> 0pts
        _, bd = calculate_moat_score({'roe': 7.9, 'dominance': 0, 'opm': 0, 'gpm': 0, 'growth': 0, 'de': 300})
        assert bd['roe_score'] == 0.0

    def test_gpm_brackets(self):
        # >=55% -> 10pts
        _, bd = calculate_moat_score({'gpm': 55.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'growth': 0, 'de': 300})
        assert bd['gpm_score'] == 10.0

        # 40-55% -> 7pts
        _, bd = calculate_moat_score({'gpm': 40.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'growth': 0, 'de': 300})
        assert bd['gpm_score'] == 7.0

        # 25-40% -> 4pts
        _, bd = calculate_moat_score({'gpm': 25.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'growth': 0, 'de': 300})
        assert bd['gpm_score'] == 4.0

        # <25% -> 0pts
        _, bd = calculate_moat_score({'gpm': 24.9, 'dominance': 0, 'opm': 0, 'roe': 0, 'growth': 0, 'de': 300})
        assert bd['gpm_score'] == 0.0

    def test_growth_brackets(self):
        # >=25% -> 10pts
        _, bd = calculate_moat_score({'growth': 25.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'de': 300})
        assert bd['growth_score'] == 10.0

        # 15-25% -> 6pts
        _, bd = calculate_moat_score({'growth': 15.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'de': 300})
        assert bd['growth_score'] == 6.0

        # 5-15% -> 3pts
        _, bd = calculate_moat_score({'growth': 5.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'de': 300})
        assert bd['growth_score'] == 3.0

        # <5% -> 0pts
        _, bd = calculate_moat_score({'growth': 4.9, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'de': 300})
        assert bd['growth_score'] == 0.0

        # Record backlog overrides growth
        _, bd = calculate_moat_score({
            'growth': 0.0,
            'principle_reason': '수주잔고 최고치 경신, 역대급 수주',
            'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'de': 300
        })
        assert bd['growth_score'] == 10.0

    def test_health_brackets(self):
        # <=50% -> 10pts
        _, bd = calculate_moat_score({'de': 50.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'growth': 0})
        assert bd['health_score'] == 10.0

        # 50-100% -> 7pts
        _, bd = calculate_moat_score({'de': 100.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'growth': 0})
        assert bd['health_score'] == 7.0

        # 100-150% -> 4pts
        _, bd = calculate_moat_score({'de': 150.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'growth': 0})
        assert bd['health_score'] == 4.0

        # 150-200% -> 2pts
        _, bd = calculate_moat_score({'de': 200.0, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'growth': 0})
        assert bd['health_score'] == 2.0

        # >200% -> 0pts
        _, bd = calculate_moat_score({'de': 200.1, 'dominance': 0, 'opm': 0, 'roe': 0, 'gpm': 0, 'growth': 0})
        assert bd['health_score'] == 0.0

    def test_graceful_imputation_empty_profile(self):
        # When all metrics are missing (small cap fallback)
        score, bd = calculate_moat_score({})
        assert len(bd['imputed_fields']) == 5
        assert 'op_margin_ttm' in bd['imputed_fields']
        assert 'roe' in bd['imputed_fields']
        assert 'gross_margin_ttm' in bd['imputed_fields']
        assert 'revenue_growth' in bd['imputed_fields']
        assert 'debt_to_equity' in bd['imputed_fields']
        # Medians: opm=5, roe=6, gpm=4, growth=3, de=7 -> total = 25.0
        assert score == 25.0


# ==============================================================================
# 4. Objective Tier Classification Tests
# ==============================================================================

class TestTierClassification:
    def test_core_tier_qualification(self):
        profile = {
            'market_dominance': 25,
            'opm': 30.0,  # >=22%
            'roe': 20.0,  # >=15%
            'growth': 10.0
        }
        tier = classify_tier(profile, moat_score=80.0)
        assert tier == "Core"

    def test_core_disqualification_due_to_low_opm(self):
        profile = {
            'market_dominance': 25,
            'opm': 18.0,  # <22% -> cannot be Core, but qualifies for Satellite (Moat>=60, Dom>=18, OPM>=12)
            'roe': 20.0,
            'growth': 10.0
        }
        tier = classify_tier(profile, moat_score=76.0)
        assert tier == "Satellite"

    def test_core_disqualification_due_to_low_roe(self):
        profile = {
            'market_dominance': 25,
            'opm': 25.0,
            'roe': 12.0,  # <15% -> falls to Satellite
            'growth': 10.0
        }
        tier = classify_tier(profile, moat_score=76.0)
        assert tier == "Satellite"

    def test_satellite_qualification_via_growth(self):
        profile = {
            'market_dominance': 12,  # <18
            'opm': 15.0,             # >=12%
            'growth': 20.0,          # >=15%
            'roe': 10.0
        }
        tier = classify_tier(profile, moat_score=65.0)
        assert tier == "Satellite"

    def test_satellite_disqualification_to_watchlist(self):
        profile = {
            'market_dominance': 12,
            'opm': 10.0,             # <12% -> fails Satellite
            'growth': 20.0,
            'roe': 10.0
        }
        tier = classify_tier(profile, moat_score=55.0)
        assert tier == "Watchlist"

    def test_watchlist_via_emerging_niche(self):
        profile = {
            'market_dominance': 0,
            'opm': 8.0,
            'growth': 8.0,
            'is_emerging_niche': True
        }
        tier = classify_tier(profile, moat_score=40.0)
        assert tier == "Watchlist"

    def test_standard_tier(self):
        profile = {
            'market_dominance': 0,
            'opm': 5.0,
            'growth': 2.0,
            'roe': 4.0
        }
        tier = classify_tier(profile, moat_score=35.0)
        assert tier == "Standard"


# ==============================================================================
# 5. Tier-Specific MDD DCA Evaluation Tests
# ==============================================================================

class TestEvaluateMddDca:
    def test_core_mdd_thresholds(self):
        # 2차 분할매수: MDD <= -30.0%
        res = evaluate_mdd_dca("Core", -35.2)
        assert "BUY_READY (2차 분할매수 MDD -35.2%)" in res['buy_signal']
        assert res['stage'] == "CORE_DCA_2"
        assert res['korean_status'] == "2차 매수적기"
        assert res['is_buy_ready'] is True

        res = evaluate_mdd_dca("Core", -30.0)
        assert "BUY_READY (2차 분할매수 MDD -30.0%)" in res['buy_signal']
        assert res['stage'] == "CORE_DCA_2"

        # 1차 분할매수: -30.0% < MDD <= -20.0%
        res = evaluate_mdd_dca("Core", -29.9)
        assert "BUY_READY (1차 분할매수 MDD -29.9%)" in res['buy_signal']
        assert res['stage'] == "CORE_DCA_1"
        assert res['korean_status'] == "1차 매수적기"
        assert res['is_buy_ready'] is True

        res = evaluate_mdd_dca("Core", -20.0)
        assert "BUY_READY (1차 분할매수 MDD -20.0%)" in res['buy_signal']
        assert res['stage'] == "CORE_DCA_1"

        # 홀딩 / 관망: MDD > -20.0%
        res = evaluate_mdd_dca("Core", -19.9)
        assert "WAIT (고점 부근 MDD -19.9%)" in res['buy_signal']
        assert res['stage'] == "CORE_HOLD"
        assert res['korean_status'] == "홀딩"
        assert res['is_buy_ready'] is False

        res = evaluate_mdd_dca("Core", -5.2)
        assert "WAIT (고점 부근 MDD -5.2%)" in res['buy_signal']
        assert res['stage'] == "CORE_HOLD"

    def test_satellite_mdd_thresholds(self):
        # 2차 분할매수: MDD <= -35.0%
        res = evaluate_mdd_dca("Satellite", -35.0)
        assert "BUY_READY (2차 분할매수 MDD -35.0%)" in res['buy_signal']
        assert res['stage'] == "SAT_DCA_2"
        assert res['korean_status'] == "2차 매수적기"
        assert res['is_buy_ready'] is True

        # 1차 분할매수: -35.0% < MDD <= -25.0%
        res = evaluate_mdd_dca("Satellite", -34.9)
        assert "BUY_READY (1차 분할매수 MDD -34.9%)" in res['buy_signal']
        assert res['stage'] == "SAT_DCA_1"

        res = evaluate_mdd_dca("Satellite", -25.0)
        assert "BUY_READY (1차 분할매수 MDD -25.0%)" in res['buy_signal']
        assert res['stage'] == "SAT_DCA_1"
        assert res['korean_status'] == "1차 매수적기"

        # 홀딩: MDD > -25.0%
        res = evaluate_mdd_dca("Satellite", -24.9)
        assert "WAIT (고점 부근 MDD -24.9%)" in res['buy_signal']
        assert res['stage'] == "SAT_HOLD"
        assert res['korean_status'] == "홀딩"
        assert res['is_buy_ready'] is False

    def test_watchlist_mdd_thresholds(self):
        # 극단 폭락 진입검토: MDD <= -35.0%
        res = evaluate_mdd_dca("Watchlist", -35.0)
        assert "BUY_READY (극단폭락 진입검토 MDD -35.0%)" in res['buy_signal']
        assert res['stage'] == "WATCH_DEEP"
        assert res['korean_status'] == "1차 매수적기"
        assert res['is_buy_ready'] is True

        # 대기: MDD > -35.0%
        res = evaluate_mdd_dca("Watchlist", -34.9)
        assert "WAIT (폭락대기 MDD -34.9%)" in res['buy_signal']
        assert res['stage'] == "WATCH_WAIT"
        assert res['korean_status'] == "관망"
        assert res['is_buy_ready'] is False

    def test_standard_mdd_thresholds(self):
        # 일반 폭락: MDD <= -40.0%
        res = evaluate_mdd_dca("Standard", -42.5)
        assert "DEEP_DISCOUNT (일반 폭락 MDD -42.5%)" in res['buy_signal']
        assert res['stage'] == "STD_DISCOUNT"
        assert res['korean_status'] == "1차 매수적기"
        assert res['is_buy_ready'] is True

        # 일반 관망: MDD > -40.0%
        res = evaluate_mdd_dca("Standard", -39.9)
        assert "WAIT (일반 관망 MDD -39.9%)" in res['buy_signal']
        assert res['stage'] == "STD_WAIT"
        assert res['korean_status'] == "관망"
        assert res['is_buy_ready'] is False


# ==============================================================================
# 6. Quantitative Oversold Rebound Engine Tests
# ==============================================================================

class TestOversoldRebound:
    def test_extreme_oversold_signal(self):
        """
        Creates synthetic data where price crashes abruptly
        causing extreme oversold across all 4 dimensions:
          - RSI < 25 (35 pts)
          - Bollinger %B <= 0 (25 pts)
          - Disparity Disp20 <= 88% (20 pts)
          - Buffer <= 3% (20 pts)
        Total Rebound Score should be 100.0 with 'STRONG_REBOUND'.
        """
        dates = pd.date_range(end='2026-09-18', periods=100)
        # 80 days steady around 90.0
        prices = [90.0 for _ in range(80)]
        # 18 days steady at 90.0
        for _ in range(18):
            prices.append(90.0)
        # Last 2 days: massive crash gap down
        prices.append(70.0)
        prices.append(48.0)

        # Lows: equal or slightly lower
        lows = [p * 0.99 for p in prices]
        highs = [p * 1.01 for p in prices]

        df = pd.DataFrame({
            'Close': prices,
            'Low': lows,
            'High': highs,
        }, index=dates)

        res = calculate_oversold_rebound(df)
        assert res['rsi_14'] < 25.0
        assert res['rsi_score'] == 35.0
        assert res['bollinger_pct_b'] <= 0.0
        assert res['bb_score'] == 25.0
        assert res['disparity_20'] <= 88.0
        assert res['disp_score'] == 20.0
        assert res['support_buffer_pct'] <= 3.0
        assert res['support_score'] == 20.0
        assert res['rebound_score'] == 100.0
        assert res['rebound_signal'] == 'STRONG_REBOUND'
        assert res['rebound_status_ko'] == '과매도 반등 강력 적기'

    def test_neutral_signal_steady_uptrend(self):
        """
        Steady uptrend has high RSI and high %B, scoring 0 pts -> 'NEUTRAL'.
        """
        dates = pd.date_range(end='2026-09-18', periods=100)
        prices = [50.0 + i * 0.5 for i in range(100)]

        df = pd.DataFrame({
            'Close': prices,
            'Low': [p * 0.99 for p in prices],
            'High': [p * 1.01 for p in prices],
        }, index=dates)

        res = calculate_oversold_rebound(df)
        assert res['rsi_14'] > 50.0
        assert res['rebound_score'] < 30.0
        assert res['rebound_signal'] == 'NEUTRAL'
        assert res['rebound_status_ko'] == '중립'

    def test_empty_or_malformed_dataframe(self):
        res = calculate_oversold_rebound(None)
        assert res['rebound_signal'] == 'NEUTRAL'
        assert res['rebound_score'] == 0.0

        res = calculate_oversold_rebound(pd.DataFrame())
        assert res['rebound_signal'] == 'NEUTRAL'


# ==============================================================================
# 7. End-to-End Comprehensive Company Evaluator Tests
# ==============================================================================

class TestEvaluateCompanyPipeline:
    def test_nvda_evaluation(self):
        nvda_profile = {
            'ticker': 'NVDA',
            'name': 'NVIDIA Corporation',
            'market_dominance': 25,
            'op_margin_ttm': 0.64,
            'roe': 1.10,
            'gross_margin_ttm': 0.75,
            'revenue_growth': 0.88,
            'debt_to_equity': 0.20,
            'current_price': 223.96,
            'high_52w': 236.26,
            'mdd_pct': -5.21
        }
        res = evaluate_company(nvda_profile)
        assert res['portfolio_tier'] == 'Core'
        assert res['moat_score'] == 100.0
        assert res['dca_stage'] == 'CORE_HOLD'
        assert 'WAIT (고점 부근 MDD -5.2%)' in res['buy_signal']
        assert res['is_buy_ready'] is False

    def test_qcom_deep_discount_evaluation(self):
        qcom_profile = {
            'ticker': 'QCOM',
            'name': 'Qualcomm',
            'principle_reason': '5G/모바일 AP 특허 독점, ROE 35%, SDV 확장 (Core)',
            'op_margin_ttm': 0.28,
            'roe': 0.35,
            'gross_margin_ttm': 0.56,
            'revenue_growth': 0.12,
            'debt_to_equity': 0.70,
            'current_price': 167.86,
            'high_52w': 258.96,
            'mdd_pct': -35.18
        }
        res = evaluate_company(qcom_profile)
        assert res['portfolio_tier'] == 'Core'
        assert res['moat_score'] >= 75.0
        assert res['dca_stage'] == 'CORE_DCA_2'
        assert 'BUY_READY (2차 분할매수 MDD -35.2%)' in res['buy_signal']
        assert res['is_buy_ready'] is True

    def test_rklb_satellite_evaluation(self):
        rklb_profile = {
            'ticker': 'RKLB',
            'name': 'Rocket Lab USA',
            'principle_reason': '소형 발사체 독보적 2위, 수주잔고 역대 최고치',
            'op_margin_ttm': 0.14,
            'roe': 0.10,
            'gross_margin_ttm': 0.32,
            'revenue_growth': 0.35,
            'debt_to_equity': 0.45,
            'current_price': 20.0,
            'high_52w': 30.0,
            'mdd_pct': -33.33
        }
        res = evaluate_company(rklb_profile)
        assert res['portfolio_tier'] == 'Satellite'
        assert res['moat_score'] >= 60.0
        assert res['dca_stage'] == 'SAT_DCA_1'
        assert 'BUY_READY (1차 분할매수 MDD -33.3%)' in res['buy_signal']
        assert res['is_buy_ready'] is True


if __name__ == '__main__':
    pytest.main(['-v', __file__])
