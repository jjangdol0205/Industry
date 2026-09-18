"""
Quantitative Investment Engine for 4-Tier Investment Principles
==============================================================
Provides rigorous mathematical modeling for:
  1. Moat & Quality Score (S_moat in [0, 100])
  2. Objective Tier Classification (Core / Satellite / Watchlist / Standard)
  3. Tier-Specific MDD DCA Dollar-Cost-Averaging Signals
  4. Quantitative Technical Oversold Rebound Engine (RSI, Bollinger %B, Disparity, Support Floor)
  5. Canonical Interface Contract Wrappers for E2E / Backend Integration

Authoritative Reference:
  - ORIGINAL_REQUEST.md (Requirement R2)
"""

from typing import Dict, Tuple, Any, Optional, List
import pandas as pd
import numpy as np


# ==============================================================================
# 1. Normalization & Helper Utilities
# ==============================================================================

def normalize_percentage(val: Any) -> Optional[float]:
    """
    Normalizes a financial metric into a percentage value (e.g. 0.35 -> 35.0, 35.0 -> 35.0).
    Handles decimals, percentages, strings with '%', and None.
    If the input is a string that had an explicit '%' suffix (e.g. "1.5%"),
    it is NOT multiplied by 100.0 even if abs(val) <= 2.0.
    Guards against non-finite floats (inf, -inf, nan) returning None for RFC 8259 compliance.
    """
    if val is None:
        return None
    has_percent_sign = False
    if isinstance(val, str):
        has_percent_sign = '%' in val
        cleaned = val.strip().replace('%', '').replace(',', '')
        try:
            fval = float(cleaned)
        except ValueError:
            return None
    else:
        try:
            fval = float(val)
        except (TypeError, ValueError):
            return None

    if not np.isfinite(fval):
        return None

    # If the input was an explicit '%' string (e.g. "1.5%"), do NOT multiply by 100
    if has_percent_sign:
        return round(fval, 4)

    # For decimal ratios (e.g. 0.35 -> 35.0%, 2.5 -> 250.0%, 5.0 -> 500.0%, -0.05 -> -5.0%)
    if 0.0 < fval <= 5.0:
        return round(fval * 100.0, 4)
    if -2.0 <= fval < 0.0:
        return round(fval * 100.0, 4)
    return round(fval, 4)


def normalize_de(val: Any) -> Optional[float]:
    """
    Normalizes Debt-to-Equity into percentage points (e.g. 0.50 -> 50.0%, 50.0 -> 50.0%).
    Negative D/E indicates negative equity (distressed firm), mapped to severe 999.0%.
    If the input is a string that had an explicit '%' suffix (e.g. "1.5%"),
    it is NOT multiplied by 100.0 even if 0.0 < val <= 3.0.
    Guards against non-finite floats (inf, -inf, nan) returning None for RFC 8259 compliance.
    """
    if val is None:
        return None
    has_percent_sign = False
    if isinstance(val, str):
        has_percent_sign = '%' in val
        cleaned = val.strip().replace('%', '').replace(',', '')
        try:
            fval = float(cleaned)
        except ValueError:
            return None
    else:
        try:
            fval = float(val)
        except (TypeError, ValueError):
            return None

    if not np.isfinite(fval):
        return None

    if fval < 0:
        return 999.0  # Severely distressed

    # In yfinance, debtToEquity is often given as percentage (e.g. 45.5) or ratio (e.g. 0.455)
    # Ratio up to 3.0 (300%) is converted to percentage, unless explicit '%' was specified
    if not has_percent_sign and 0.0 < fval <= 3.0:
        return round(fval * 100.0, 4)
    return round(fval, 4)


def extract_dominance_score(profile: dict) -> Tuple[float, bool]:
    """
    Extracts or infers Market Dominance score (0 to 25 pts).
    Returns (score, was_inferred).
    """
    # 1. Direct numerical dominance passed
    for key in ('market_dominance', 'dominance', 'market_dominance_score', 'dominance_score'):
        if key in profile and profile[key] is not None:
            try:
                num = float(profile[key])
                if np.isfinite(num):
                    return min(25.0, max(0.0, num)), False
            except (ValueError, TypeError):
                pass

    # 2. Textual analysis on profile metadata
    text_corpus = " ".join([
        str(profile.get(k, ''))
        for k in ('principle_reason', 'role_description', 'future_growth',
                  'moat_title', 'description', 'description_ko', 'name', 'industry')
    ]).lower()

    if not text_corpus.strip():
        return 0.0, True

    # Tier 1 (25 pts): Monopoly, Global #1, Insurmountable IP / bottleneck
    t1_keywords = [
        '독점', '100%', '1위', 'monopoly', 'global #1', '#1', '세계 1위', '전세계 1위',
        '국내 1위', 'euv', 'cuda', '수술로봇', '80%+', '85%+', '90%+', 'insurmountable',
        '독보적 1위'
    ]
    if any(kw in text_corpus for kw in t1_keywords):
        return 25.0, True

    # Tier 2 (18 pts): Top 2~3 Oligopoly
    t2_keywords = [
        '과점', '2위', '3위', '2~3', 'oligopoly', 'top 2', 'top 3',
        '독보적 2위', '글로벌 2위', '글로벌 3위', '3대 과점', '과점 시장'
    ]
    if any(kw in text_corpus for kw in t2_keywords):
        return 18.0, True

    # Tier 3 (12 pts): High-barrier specialized equipment/material supplier
    t3_keywords = [
        '병목', '특허', '소모품', '락인', '고마진', 'high-barrier', '장벽',
        '특화', '리들샷', '플랫폼 독점', '핵심 공급', '전환비용'
    ]
    if any(kw in text_corpus for kw in t3_keywords):
        return 12.0, True

    return 0.0, True


# ==============================================================================
# 2. Moat & Quality Score (S_moat in [0, 100])
# ==============================================================================

def calculate_moat_score(profile: dict) -> Tuple[float, dict]:
    """
    Calculates the 100-point Moat & Quality score (S_moat):
      - Market Dominance: max 25 pts
      - OPM (Operating Margin): max 25 pts
      - ROE (Return on Equity): max 20 pts
      - GPM (Gross Margin): max 10 pts
      - Growth (YoY Revenue Growth): max 10 pts
      - Financial Health (Debt-to-Equity): max 10 pts
      - Graceful imputation for missing metrics.

    Returns:
      (total_moat_score, breakdown_dict)
    """
    imputed_fields = []

    # 1. Market Dominance (max 25 pts)
    dominance_score, dom_inferred = extract_dominance_score(profile)

    # 2. OPM (max 25 pts)
    #    >=35% 25pts, 25-35% 20pts, 18-25% 15pts, 12-18% 10pts, 5-12% 5pts, <5% 0pts, <0 -5pts
    raw_opm = None
    for k in ('op_margin_ttm', 'op_margin', 'operating_margin', 'opm', 'operatingMargins'):
        if k in profile and profile[k] is not None:
            raw_opm = profile[k]
            break

    opm = normalize_percentage(raw_opm)
    if opm is None:
        opm = 10.0  # Industry median fallback
        imputed_fields.append('op_margin_ttm')

    if opm >= 35.0:
        opm_score = 25.0
    elif opm >= 25.0:
        opm_score = 20.0
    elif opm >= 18.0:
        opm_score = 15.0
    elif opm >= 12.0:
        opm_score = 10.0
    elif opm >= 5.0:
        opm_score = 5.0
    elif opm >= 0.0:
        opm_score = 0.0
    else:
        opm_score = -5.0

    # 3. ROE (max 20 pts)
    #    >=30% 20pts, 20-30% 16pts, 14-20% 12pts, 8-14% 6pts, <8% 0pts
    raw_roe = None
    for k in ('roe', 'return_on_equity', 'returnOnEquity'):
        if k in profile and profile[k] is not None:
            raw_roe = profile[k]
            break

    roe = normalize_percentage(raw_roe)
    if roe is None:
        roe = 10.0  # Industry median fallback
        imputed_fields.append('roe')

    if roe >= 30.0:
        roe_score = 20.0
    elif roe >= 20.0:
        roe_score = 16.0
    elif roe >= 14.0:
        roe_score = 12.0
    elif roe >= 8.0:
        roe_score = 6.0
    else:
        roe_score = 0.0

    # 4. GPM (max 10 pts)
    #    >=55% 10pts, 40-55% 7pts, 25-40% 4pts, <25% 0pts
    raw_gpm = None
    for k in ('gross_margin_ttm', 'gross_margin', 'gpm', 'grossMargins'):
        if k in profile and profile[k] is not None:
            raw_gpm = profile[k]
            break

    gpm = normalize_percentage(raw_gpm)
    if gpm is None:
        gpm = 30.0  # Industry median fallback
        imputed_fields.append('gross_margin_ttm')

    if gpm >= 55.0:
        gpm_score = 10.0
    elif gpm >= 40.0:
        gpm_score = 7.0
    elif gpm >= 25.0:
        gpm_score = 4.0
    else:
        gpm_score = 0.0

    # 5. Growth (max 10 pts)
    #    YoY >=25% (or record backlog) 10pts, 15-25% 6pts, 5-15% 3pts, <5% 0pts
    raw_growth = None
    for k in ('revenue_growth', 'growth', 'rev_growth', 'revenueGrowth'):
        if k in profile and profile[k] is not None:
            raw_growth = profile[k]
            break

    growth = normalize_percentage(raw_growth)
    if growth is None:
        growth = 8.0  # Industry median fallback
        imputed_fields.append('revenue_growth')

    # Check for record backlog keywords
    text_corpus = " ".join([
        str(profile.get(k, ''))
        for k in ('principle_reason', 'role_description', 'future_growth')
    ]).lower()
    has_record_backlog = any(kw in text_corpus for kw in ['수주잔고 최고', '수주잔고 역대', 'record order backlog', 'record backlog'])

    if growth >= 25.0 or has_record_backlog:
        growth_score = 10.0
    elif growth >= 15.0:
        growth_score = 6.0
    elif growth >= 5.0:
        growth_score = 3.0
    else:
        growth_score = 0.0

    # 6. Financial Health / Debt-to-Equity (max 10 pts)
    #    D/E <=50% 10pts, 50-100% 7pts, 100-150% 4pts, 150-200% 2pts, >200% 0pts
    raw_de = None
    for k in ('debt_to_equity', 'debt_equity', 'de_ratio', 'debtToEquity'):
        if k in profile and profile[k] is not None:
            raw_de = profile[k]
            break

    de = normalize_de(raw_de)
    if de is None:
        de = 75.0  # Industry median fallback
        imputed_fields.append('debt_to_equity')

    if de <= 50.0:
        health_score = 10.0
    elif de <= 100.0:
        health_score = 7.0
    elif de <= 150.0:
        health_score = 4.0
    elif de <= 200.0:
        health_score = 2.0
    else:
        health_score = 0.0

    # Total Score computation
    raw_total = dominance_score + opm_score + roe_score + gpm_score + growth_score + health_score
    total_moat = round(max(0.0, min(100.0, raw_total)), 2)

    breakdown = {
        'dominance_score': round(dominance_score, 1),
        'opm_score': round(opm_score, 1),
        'roe_score': round(roe_score, 1),
        'gpm_score': round(gpm_score, 1),
        'growth_score': round(growth_score, 1),
        'health_score': round(health_score, 1),
        'total_moat': total_moat,
        'effective_opm': opm,
        'effective_roe': roe,
        'effective_gpm': gpm,
        'effective_growth': growth,
        'effective_de': de,
        'imputed_fields': imputed_fields,
        'is_inferred_dominance': dom_inferred
    }

    return total_moat, breakdown


# ==============================================================================
# 3. Objective Tier Classification
# ==============================================================================

def classify_tier(profile: dict, moat_score: float) -> str:
    """
    Classifies a company into Core, Satellite, Watchlist, or Standard.
      - Core: Moat >= 75 and OPM >= 22% and ROE >= 15% and Dominance >= 18.
      - Satellite: Moat >= 60 and (Growth >= 15% or Dominance >= 18) and OPM >= 12%.
      - Watchlist: Moat >= 50 or emerging niche with high potential.
      - Standard: All other coverage universe.
    """
    # Extract dominance
    dom_score, _ = extract_dominance_score(profile)

    # Extract normalized OPM, ROE, Growth
    raw_opm = None
    for k in ('op_margin_ttm', 'op_margin', 'operating_margin', 'opm', 'operatingMargins'):
        if k in profile and profile[k] is not None:
            raw_opm = profile[k]
            break
    opm = normalize_percentage(raw_opm)
    if opm is None:
        opm = 10.0

    raw_roe = None
    for k in ('roe', 'return_on_equity', 'returnOnEquity'):
        if k in profile and profile[k] is not None:
            raw_roe = profile[k]
            break
    roe = normalize_percentage(raw_roe)
    if roe is None:
        roe = 10.0

    raw_growth = None
    for k in ('revenue_growth', 'growth', 'rev_growth', 'revenueGrowth'):
        if k in profile and profile[k] is not None:
            raw_growth = profile[k]
            break
    growth = normalize_percentage(raw_growth)
    if growth is None:
        growth = 8.0

    # Emerging niche check
    is_emerging_niche = bool(
        profile.get('is_emerging_niche') or
        profile.get('emerging_niche') or
        profile.get('watchlist_candidate')
    )
    if not is_emerging_niche:
        text_corpus = " ".join([
            str(profile.get(k, ''))
            for k in ('principle_reason', 'role_description', 'future_growth')
        ]).lower()
        if any(kw in text_corpus for kw in ['신규 편입', 'emerging', '잠재력', 'niche high potential']):
            is_emerging_niche = True

    # 1. Core Check
    if moat_score >= 75.0 and opm >= 22.0 and roe >= 15.0 and dom_score >= 18.0:
        return "Core"

    # 2. Satellite Check
    if moat_score >= 60.0 and (growth >= 15.0 or dom_score >= 18.0) and opm >= 12.0:
        return "Satellite"

    # 3. Watchlist Check
    if moat_score >= 50.0 or is_emerging_niche:
        return "Watchlist"

    # 4. Standard
    return "Standard"


# ==============================================================================
# 4. Tier-Specific MDD DCA Evaluation Engine
# ==============================================================================

def evaluate_mdd_dca(tier: str, mdd_pct: Optional[float]) -> dict:
    """
    Evaluates Dollar-Cost-Averaging buy signals based on portfolio tier and MDD.
    Guarantees 100% backward compatibility with React App.jsx filtering.
    Guards against non-finite floats (inf, -inf, nan) falling back to 0.0 for RFC 8259 compliance.

    Rules:
      - Core:
          MDD <= -30.0% -> 'BUY_READY (2차 분할매수 MDD {mdd:.1f}%)', stage='CORE_DCA_2', korean_status='2차 매수적기'
          MDD <= -20.0% -> 'BUY_READY (1차 분할매수 MDD {mdd:.1f}%)', stage='CORE_DCA_1', korean_status='1차 매수적기'
          otherwise     -> 'WAIT (고점 부근 MDD {mdd:.1f}%)', stage='CORE_HOLD', korean_status='홀딩'
      - Satellite:
          MDD <= -35.0% -> 'BUY_READY (2차 분할매수 MDD {mdd:.1f}%)', stage='SAT_DCA_2', korean_status='2차 매수적기'
          MDD <= -25.0% -> 'BUY_READY (1차 분할매수 MDD {mdd:.1f}%)', stage='SAT_DCA_1', korean_status='1차 매수적기'
          otherwise     -> 'WAIT (고점 부근 MDD {mdd:.1f}%)', stage='SAT_HOLD', korean_status='홀딩'
      - Watchlist:
          MDD <= -35.0% -> 'BUY_READY (극단폭락 진입검토 MDD {mdd:.1f}%)', stage='WATCH_DEEP', korean_status='1차 매수적기'
          otherwise     -> 'WAIT (폭락대기 MDD {mdd:.1f}%)', stage='WATCH_WAIT', korean_status='관망'
      - Standard:
          MDD <= -40.0% -> 'DEEP_DISCOUNT (일반 폭락 MDD {mdd:.1f}%)', stage='STD_DISCOUNT', korean_status='1차 매수적기'
          otherwise     -> 'WAIT (일반 관망 MDD {mdd:.1f}%)', stage='STD_WAIT', korean_status='관망'
    """
    try:
        if mdd_pct is not None:
            fval = float(mdd_pct)
            mdd = fval if np.isfinite(fval) else 0.0
        else:
            mdd = 0.0
    except (TypeError, ValueError):
        mdd = 0.0

    normalized_tier = (tier or 'Standard').strip().capitalize()
    if normalized_tier not in ('Core', 'Satellite', 'Watchlist', 'Standard'):
        normalized_tier = 'Standard'

    if normalized_tier == 'Core':
        if mdd <= -30.0:
            buy_signal = f"BUY_READY (2차 분할매수 MDD {mdd:.1f}%)"
            stage = "CORE_DCA_2"
            korean_status = "2차 매수적기"
            guidance = "2차 적극 분할매수 (포트폴리오 비중 확대)"
        elif mdd <= -20.0:
            buy_signal = f"BUY_READY (1차 분할매수 MDD {mdd:.1f}%)"
            stage = "CORE_DCA_1"
            korean_status = "1차 매수적기"
            guidance = "1차 분할매수 개시 (초기 분할 진입)"
        else:
            buy_signal = f"WAIT (고점 부근 MDD {mdd:.1f}%)"
            stage = "CORE_HOLD"
            korean_status = "홀딩"
            guidance = "보유 지속 / 조정 대기"

    elif normalized_tier == 'Satellite':
        if mdd <= -35.0:
            buy_signal = f"BUY_READY (2차 분할매수 MDD {mdd:.1f}%)"
            stage = "SAT_DCA_2"
            korean_status = "2차 매수적기"
            guidance = "2차 적극 분할매수 (알파 비중 확대)"
        elif mdd <= -25.0:
            buy_signal = f"BUY_READY (1차 분할매수 MDD {mdd:.1f}%)"
            stage = "SAT_DCA_1"
            korean_status = "1차 매수적기"
            guidance = "1차 분할매수 개시 (알파 분할 진입)"
        else:
            buy_signal = f"WAIT (고점 부근 MDD {mdd:.1f}%)"
            stage = "SAT_HOLD"
            korean_status = "홀딩"
            guidance = "보유 지속 / 조정 대기"

    elif normalized_tier == 'Watchlist':
        if mdd <= -35.0:
            buy_signal = f"BUY_READY (극단폭락 진입검토 MDD {mdd:.1f}%)"
            stage = "WATCH_DEEP"
            korean_status = "1차 매수적기"
            guidance = "극단적 마진오브세이프티 구간 제한적 진입"
        else:
            buy_signal = f"WAIT (폭락대기 MDD {mdd:.1f}%)"
            stage = "WATCH_WAIT"
            korean_status = "관망"
            guidance = "매수 유보 / 관망 대기"

    else:  # Standard
        if mdd <= -40.0:
            buy_signal = f"DEEP_DISCOUNT (일반 폭락 MDD {mdd:.1f}%)"
            stage = "STD_DISCOUNT"
            korean_status = "1차 매수적기"
            guidance = "단순 가격 폭락 모니터링 (자동매수 미부여)"
        else:
            buy_signal = f"WAIT (일반 관망 MDD {mdd:.1f}%)"
            stage = "STD_WAIT"
            korean_status = "관망"
            guidance = "일반 커버리지 관망"

    is_buy_ready = ('BUY_READY' in buy_signal) or ('DEEP_DISCOUNT' in buy_signal)

    return {
        'tier': normalized_tier,
        'mdd_pct': round(mdd, 2),
        'buy_signal': buy_signal,
        'stage': stage,
        'dca_stage': stage,
        'korean_status': korean_status,
        'is_buy_ready': is_buy_ready,
        'action_guidance': guidance
    }


# ==============================================================================
# 5. Quantitative Oversold Rebound Engine
# ==============================================================================

def classify_rebound_signal(score: float) -> str:
    """
    Canonical Interface Contract Wrapper for classifying rebound signal.
    Returns:
      - 'STRONG_REBOUND' (>= 70)
      - 'MODERATE_REBOUND' (50-69)
      - 'CONSOLIDATING' (30-49)
      - 'NEUTRAL' (< 30)
    """
    if score is None or not np.isfinite(score):
        return 'NEUTRAL'
    if score >= 70.0:
        return 'STRONG_REBOUND'
    elif score >= 50.0:
        return 'MODERATE_REBOUND'
    elif score >= 30.0:
        return 'CONSOLIDATING'
    else:
        return 'NEUTRAL'


def calculate_oversold_rebound(df_history: pd.DataFrame) -> dict:
    """
    Calculates technical oversold and downside support indicators from historical OHLCV.
      1. 14-Day RSI (max 35 pts: <25 35pts, <30 28pts, <38 18pts, >=38 0pts)
      2. Bollinger Bands %B (max 25 pts: <=0.0 25pts, 0-0.15 15pts, >0.15 0pts)
      3. Moving Average Disparity (max 20 pts: Disp20 <=88% or Disp60 <=82% 20pts, Disp20 <=92% or Disp60 <=88% 12pts)
      4. Downside Floor Support Buffer (max 20 pts: buffer <=3% 20pts, 3-7% 12pts, >7% 0pts)
      5. Total Rebound Score [0, 100] & Rebound Signal:
           >=70: 'STRONG_REBOUND' ('과매도 반등 강력 적기')
          50-69: 'MODERATE_REBOUND' ('기술적 반등 유효 구간')
          30-49: 'CONSOLIDATING' ('하방 지지 탐색 중')
            <30: 'NEUTRAL' ('중립')
    """
    default_res = {
        'rsi_14': 50.0,
        'bollinger_pct_b': 0.5,
        'disparity_20': 100.0,
        'disparity_60': 100.0,
        'support_price': 0.0,
        'support_buffer_pct': 99.0,
        'rsi_score': 0.0,
        'bb_score': 0.0,
        'disp_score': 0.0,
        'support_score': 0.0,
        'rebound_score': 0.0,
        'rebound_signal': 'NEUTRAL',
        'rebound_status_ko': '중립'
    }

    if df_history is None or not isinstance(df_history, pd.DataFrame) or df_history.empty:
        return default_res

    # Handle MultiIndex columns if yfinance returned (Ticker, OHLCV)
    if isinstance(df_history.columns, pd.MultiIndex):
        try:
            df_history = df_history.droplevel(0, axis=1)
        except Exception:
            pass

    # Find close series
    close_col = None
    for c in ('Close', 'close', 'Adj Close', 'adj_close'):
        if c in df_history.columns:
            close_col = c
            break

    if close_col is None:
        return default_res

    raw_close = pd.to_numeric(df_history[close_col], errors='coerce')
    close_s = raw_close[np.isfinite(raw_close)].astype(float)
    if len(close_s) < 20:
        return default_res

    curr_price = float(close_s.iloc[-1])

    # Find low series
    low_col = None
    for c in ('Low', 'low'):
        if c in df_history.columns:
            low_col = c
            break

    if low_col is not None:
        raw_low = pd.to_numeric(df_history[low_col], errors='coerce')
        low_s = raw_low[np.isfinite(raw_low)].astype(float)
        # Fallback to close_s if low_s is empty or contains only NaNs
        if low_s.empty:
            low_s = close_s
    else:
        low_s = close_s

    # 1. 14-Day RSI (Relative Strength Index)
    # Wilder's Smoothing formula (alpha = 1/14)
    delta = close_s.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    if len(close_s) >= 14:
        avg_gain = gain.ewm(alpha=1.0 / 14.0, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / 14.0, adjust=False).mean()
        last_loss = float(avg_loss.iloc[-1])
        last_gain = float(avg_gain.iloc[-1])

        if last_loss == 0.0:
            rsi_val = 100.0 if last_gain > 0.0 else 50.0
        else:
            rs = last_gain / last_loss
            rsi_val = 100.0 - (100.0 / (1.0 + rs))
    else:
        # Fallback simple mean for short series
        tot_gain = gain.sum()
        tot_loss = loss.sum()
        if tot_loss == 0.0:
            rsi_val = 100.0 if tot_gain > 0.0 else 50.0
        else:
            rs = tot_gain / tot_loss
            rsi_val = 100.0 - (100.0 / (1.0 + rs))

    if not np.isfinite(rsi_val):
        rsi_val = 50.0
    rsi_val = round(float(rsi_val), 2)

    # RSI scoring (max 35 pts)
    # <25 35pts, <30 28pts, <38 18pts, >=38 0pts
    if rsi_val < 25.0:
        rsi_score = 35.0
    elif rsi_val < 30.0:
        rsi_score = 28.0
    elif rsi_val < 38.0:
        rsi_score = 18.0
    else:
        rsi_score = 0.0

    # 2. Bollinger Bands (20-day, 2 Standard Deviations) & %B
    # %B = (Close - Lower) / (Upper - Lower)
    window_bb = min(20, len(close_s))
    slice_bb = close_s.tail(window_bb)
    mu_20 = float(slice_bb.mean())
    sigma_20 = float(slice_bb.std(ddof=0))
    upper = mu_20 + 2.0 * sigma_20
    lower = mu_20 - 2.0 * sigma_20

    if upper > lower:
        pct_b = (curr_price - lower) / (upper - lower)
    else:
        pct_b = 0.5

    if not np.isfinite(pct_b):
        pct_b = 0.5
    pct_b = round(float(pct_b), 4)

    # Bollinger scoring (max 25 pts)
    # <=0.0 25pts, 0-0.15 15pts, >0.15 0pts
    if pct_b <= 0.0:
        bb_score = 25.0
    elif pct_b <= 0.15:
        bb_score = 15.0
    else:
        bb_score = 0.0

    # 3. Moving Average Disparity (단기/중기 낙폭 과대율 / 이격도)
    # Disp20 = (Close / MA20) * 100%, Disp60 = (Close / MA60) * 100%
    window_60 = min(60, len(close_s))
    mu_60 = float(close_s.tail(window_60).mean())

    disp20 = (curr_price / mu_20) * 100.0 if mu_20 > 0 else 100.0
    disp60 = (curr_price / mu_60) * 100.0 if mu_60 > 0 else 100.0
    if not np.isfinite(disp20):
        disp20 = 100.0
    if not np.isfinite(disp60):
        disp60 = 100.0
    disp20 = round(float(disp20), 2)
    disp60 = round(float(disp60), 2)

    # Disparity scoring (max 20 pts)
    # Disp20 <=88% or Disp60 <=82% 20pts
    # Disp20 <=92% or Disp60 <=88% 12pts
    # otherwise 0pts
    if disp20 <= 88.0 or disp60 <= 82.0:
        disp_score = 20.0
    elif disp20 <= 92.0 or disp60 <= 88.0:
        disp_score = 12.0
    else:
        disp_score = 0.0

    # 4. Downside Floor Support Buffer
    # P_support = max(Low_52w, MA_200, min(L_{t-60..t}))
    # Buffer (%) = ((Close - P_support) / Close) * 100%
    w_52w = min(252, len(low_s))
    w_60d = min(60, len(low_s))
    low_52w = float(low_s.tail(w_52w).min())
    low_60d = float(low_s.tail(w_60d).min())

    support_candidates = [low_52w, low_60d]
    if len(close_s) >= 80:
        ma_200 = float(close_s.tail(min(200, len(close_s))).mean())
        if np.isfinite(ma_200):
            support_candidates.append(ma_200)

    # Filter out any non-finite candidates
    support_candidates = [sc for sc in support_candidates if np.isfinite(sc)]
    if not support_candidates:
        support_candidates = [curr_price]

    # The immediate support floor tested is the highest support candidate
    # that is at or below the market (or nearest floor)
    below_supports = [sc for sc in support_candidates if sc <= curr_price * 1.03]
    if below_supports:
        support_price = max(below_supports)
    else:
        support_price = min(support_candidates)

    if curr_price > 0:
        buffer_pct = ((curr_price - support_price) / curr_price) * 100.0
    else:
        buffer_pct = 99.0

    if not np.isfinite(buffer_pct):
        buffer_pct = 99.0
    if not np.isfinite(support_price):
        support_price = curr_price

    buffer_pct = round(float(buffer_pct), 2)
    support_price = round(float(support_price), 2)

    # Support Buffer scoring (max 20 pts)
    # buffer <=3% 20pts, 3-7% 12pts, >7% 0pts
    if buffer_pct <= 3.0:
        supp_score = 20.0
    elif buffer_pct <= 7.0:
        supp_score = 12.0
    else:
        supp_score = 0.0

    # 5. Total Rebound Score & Signal
    raw_rebound = rsi_score + bb_score + disp_score + supp_score
    if not np.isfinite(raw_rebound):
        raw_rebound = 0.0
    total_rebound = round(max(0.0, min(100.0, raw_rebound)), 1)

    rebound_signal = classify_rebound_signal(total_rebound)
    status_ko_map = {
        'STRONG_REBOUND': '과매도 반등 강력 적기',
        'MODERATE_REBOUND': '기술적 반등 유효 구간',
        'CONSOLIDATING': '하방 지지 탐색 중',
        'NEUTRAL': '중립'
    }
    rebound_status_ko = status_ko_map.get(rebound_signal, '중립')

    return {
        'rsi_14': rsi_val,
        'bollinger_pct_b': pct_b,
        'disparity_20': disp20,
        'disparity_60': disp60,
        'support_price': support_price,
        'support_buffer_pct': buffer_pct,
        'rsi_score': rsi_score,
        'bb_score': bb_score,
        'disp_score': disp_score,
        'support_score': supp_score,
        'rebound_score': total_rebound,
        'rebound_signal': rebound_signal,
        'rebound_status_ko': rebound_status_ko
    }


# ==============================================================================
# 6. Comprehensive Unified Company Evaluator
# ==============================================================================

def evaluate_company(company_dict: dict, df_history: Optional[pd.DataFrame] = None) -> dict:
    """
    End-to-end evaluation pipeline:
      - Computes Moat & Quality score (S_moat)
      - Classifies tier (Core / Satellite / Watchlist / Standard)
      - Evaluates MDD DCA Dollar-Cost-Averaging stage & buy_signal
      - Computes Oversold Rebound indicators if history is available
      - Merges into standardized output schema
    """
    result = dict(company_dict)

    # 1. Moat Score
    moat_score, moat_breakdown = calculate_moat_score(company_dict)
    result['moat_score'] = moat_score
    result['moat_breakdown'] = moat_breakdown

    # 2. Tier Classification
    tier = classify_tier(company_dict, moat_score)
    result['portfolio_tier'] = tier
    result['current_tier'] = tier
    result['suggested_tier'] = tier

    # 3. MDD DCA Evaluation (with defensive price parsing)
    mdd = company_dict.get('mdd_pct')
    if mdd is not None:
        try:
            mdd_f = float(mdd)
            if np.isfinite(mdd_f):
                mdd = mdd_f
            else:
                mdd = None
        except (TypeError, ValueError):
            mdd = None

    if mdd is None and 'current_price' in company_dict and 'high_52w' in company_dict:
        try:
            cp = company_dict.get('current_price')
            hp = company_dict.get('high_52w')
            if cp is not None and hp is not None:
                curr = float(cp)
                high = float(hp)
                if np.isfinite(curr) and np.isfinite(high) and high > 0:
                    if curr >= high:
                        mdd = 0.0
                    else:
                        mdd = round(((curr - high) / high) * 100.0, 2)
                    result['mdd_pct'] = mdd
                else:
                    mdd = None
            else:
                mdd = None
        except (TypeError, ValueError):
            mdd = None

    dca_res = evaluate_mdd_dca(tier, mdd)
    result['buy_signal'] = dca_res['buy_signal']
    result['dca_stage'] = dca_res['stage']
    result['korean_status'] = dca_res['korean_status']
    result['is_buy_ready'] = dca_res['is_buy_ready']
    result['action_guidance'] = dca_res['action_guidance']

    # 4. Technical Rebound Engine
    if df_history is not None and not df_history.empty:
        reb_res = calculate_oversold_rebound(df_history)
        result['rsi_14'] = reb_res['rsi_14']
        result['bollinger_pct_b'] = reb_res['bollinger_pct_b']
        result['disparity_20'] = reb_res['disparity_20']
        result['disparity_60'] = reb_res['disparity_60']
        result['support_price'] = reb_res['support_price']
        result['support_buffer_pct'] = reb_res['support_buffer_pct']
        result['rebound_score'] = reb_res['rebound_score']
        result['rebound_signal'] = reb_res['rebound_signal']
        result['rebound_status_ko'] = reb_res['rebound_status_ko']
    else:
        result.setdefault('rsi_14', None)
        result.setdefault('bollinger_pct_b', None)
        result.setdefault('support_price', None)
        result.setdefault('rebound_score', None)
        result.setdefault('rebound_signal', 'NEUTRAL')
        result.setdefault('rebound_status_ko', '중립')

    return result


# ==============================================================================
# 7. Canonical Interface Contract Wrappers
# ==============================================================================

def evaluate_stock_tier(metrics: dict) -> Tuple[str, float]:
    """
    Canonical Interface Contract Wrapper for Tier Classification.
    Calls calculate_moat_score(metrics) and classify_tier(metrics, moat_score),
    returning (tier, moat_score).
    """
    moat_score, _ = calculate_moat_score(metrics)
    tier = classify_tier(metrics, moat_score)
    return tier, moat_score


def compute_dca_signal(tier: str, mdd_pct: float) -> Tuple[str, str]:
    """
    Canonical Interface Contract Wrapper for MDD DCA Signal.
    Calls evaluate_mdd_dca(tier, mdd_pct),
    returning (buy_signal, dca_stage).
    """
    res = evaluate_mdd_dca(tier, mdd_pct)
    return res['buy_signal'], res['dca_stage']


def compute_rebound_score(history_df: pd.DataFrame) -> Tuple[float, str]:
    """
    Canonical Interface Contract Wrapper for Technical Oversold Rebound.
    Calls calculate_oversold_rebound(history_df),
    returning (rebound_score, rebound_signal).
    """
    res = calculate_oversold_rebound(history_df)
    return res['rebound_score'], res['rebound_signal']


def calculate_mdd(curr_price: Any, high_52w: Any) -> float:
    """
    Calculates Maximum Drawdown (MDD) percentage from 52-week high.
    Formula: ((curr_price - high_52w) / high_52w) * 100.0
    If high_52w <= 0 or non-finite: returns 0.0 without ZeroDivisionError.
    If curr_price >= high_52w: returns 0.0 (new high).
    """
    try:
        curr = float(curr_price)
        high = float(high_52w)
        if not np.isfinite(curr) or not np.isfinite(high) or high <= 0.0:
            return 0.0
        if curr >= high:
            return 0.0
        return round(((curr - high) / high) * 100.0, 2)
    except (TypeError, ValueError):
        return 0.0


def normalize_ticker(raw: Optional[str]) -> str:
    """
    Normalizes stock tickers bidirectionally for Yahoo Finance.
    """
    if not raw or not isinstance(raw, str):
        return ""
    t = raw.strip()
    t_upper = t.upper()
    if t_upper in ("TSMC", "TSMC.US"):
        return "TSM"
    if t_upper.endswith(".KS") or t_upper.endswith(".KQ"):
        if t_upper.startswith("A") and len(t_upper) == 9:
            return t_upper[1:]
        return t_upper
    if t_upper.startswith("A") and len(t_upper) == 7 and t_upper[1:].isdigit():
        return f"{t_upper[1:]}.KS"
    if len(t) == 6 and t.isdigit():
        return f"{t}.KS"
    return t


def read_cache_metadata(cache_path=None):
    try:
        import sync_stocks
        return sync_stocks.read_cache_metadata(cache_path)
    except Exception:
        return None


def write_cache_metadata(*args, **kwargs):
    try:
        import sync_stocks
        return sync_stocks.write_cache_metadata(*args, **kwargs)
    except Exception:
        pass


def is_cache_valid(*args, **kwargs):
    try:
        import sync_stocks
        return sync_stocks.is_cache_valid(*args, **kwargs)
    except Exception:
        return False


__all__ = [
    'normalize_percentage',
    'normalize_de',
    'extract_dominance_score',
    'calculate_moat_score',
    'classify_tier',
    'evaluate_mdd_dca',
    'calculate_oversold_rebound',
    'evaluate_company',
    'evaluate_stock_tier',
    'compute_dca_signal',
    'compute_rebound_score',
    'classify_rebound_signal',
    'calculate_mdd',
    'normalize_ticker',
    'read_cache_metadata',
    'write_cache_metadata',
    'is_cache_valid',
]
