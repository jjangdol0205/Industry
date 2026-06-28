import os
import datetime
import json
import math
from sqlalchemy.orm import Session
import google.generativeai as genai
import models

# Configure Gemini
api_key = os.environ.get("GOOGLE_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

def get_gemini_response(prompt: str, fallback_content: str) -> str:
    if not api_key:
        return fallback_content
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return fallback_content

def safe_float(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except:
        return None

def fmt_b(v, ticker=''):
    v = safe_float(v)
    if v is None: return "N/A"
    if ticker.endswith('.KS') or ticker.endswith('.KQ'):
        return f"₩{v/1e8:,.0f}억"
    return f"${v/1e9:.2f}B"

def fmt_pct(v):
    v = safe_float(v)
    return f"{v:.1f}%" if v is not None else "N/A"

def fmt_pct_ratio(v):
    v = safe_float(v)
    return f"{v*100:.1f}%" if v is not None else "N/A"

def fmt_x(v):
    v = safe_float(v)
    return f"{v:.1f}x" if v is not None else "N/A"

def fmt_n(v):
    v = safe_float(v)
    return f"{v:.2f}" if v is not None else "N/A"


# ─────────────────────────────────────────────────────────
# Score Engine 1: Quant Score (재무 건전성)
# ─────────────────────────────────────────────────────────
def calc_quant_score(profile, fin_annual):
    score = 50
    signals = []

    gm = safe_float(getattr(profile, 'gross_margin_ttm', None))
    nm = safe_float(getattr(profile, 'net_margin_ttm', None))
    if gm is not None:
        if gm > 0.5:   score += 10; signals.append(f"✅ 높은 매출총이익률 {gm*100:.0f}%")
        elif gm > 0.3: score += 5;  signals.append(f"🟡 적정 매출총이익률 {gm*100:.0f}%")
        else:          score -= 5;  signals.append(f"⚠️ 낮은 매출총이익률 {gm*100:.0f}%")
    if nm is not None:
        if nm > 0.15:   score += 10; signals.append(f"✅ 높은 순이익률 {nm*100:.0f}%")
        elif nm > 0.05: score += 5;  signals.append(f"🟡 적정 순이익률 {nm*100:.0f}%")
        elif nm < 0:    score -= 10; signals.append(f"🔴 적자 (순이익률 {nm*100:.0f}%)")

    rg = safe_float(getattr(profile, 'revenue_growth', None))
    if rg is not None:
        if rg > 0.3:   score += 15; signals.append(f"✅ 고성장 매출성장률 {rg*100:.0f}%")
        elif rg > 0.1: score += 8;  signals.append(f"🟡 성장 매출성장률 {rg*100:.0f}%")
        elif rg > 0:   score += 3;  signals.append(f"🟡 완만한 성장 {rg*100:.0f}%")
        else:          score -= 10; signals.append(f"🔴 매출 역성장 {rg*100:.0f}%")

    pe = safe_float(getattr(profile, 'pe_ratio', None))
    if pe is not None and pe > 0:
        if pe < 15:    score += 15; signals.append(f"✅ 저평가 PER {pe:.1f}x")
        elif pe < 30:  score += 8;  signals.append(f"🟡 적정 PER {pe:.1f}x")
        elif pe < 60:  score += 3;  signals.append(f"🟡 다소 고평가 PER {pe:.1f}x")
        else:          score -= 5;  signals.append(f"⚠️ 고평가 PER {pe:.1f}x")

    de = safe_float(getattr(profile, 'debt_to_equity', None))
    cr = safe_float(getattr(profile, 'current_ratio', None))
    if de is not None:
        if de < 50:    score += 8;  signals.append(f"✅ 낮은 부채비율 {de:.0f}%")
        elif de < 150: score += 3;  signals.append(f"🟡 적정 부채비율 {de:.0f}%")
        else:          score -= 8;  signals.append(f"⚠️ 높은 부채비율 {de:.0f}%")
    if cr is not None:
        if cr > 2:     score += 7;  signals.append(f"✅ 양호한 유동비율 {cr:.1f}x")
        elif cr > 1:   score += 3;  signals.append(f"🟡 적정 유동비율 {cr:.1f}x")
        else:          score -= 7;  signals.append(f"🔴 유동성 위험 {cr:.1f}x")

    roe = safe_float(getattr(profile, 'roe', None))
    if roe is not None:
        if roe > 0.2:   score += 10; signals.append(f"✅ 우수한 ROE {roe*100:.0f}%")
        elif roe > 0.1: score += 5;  signals.append(f"🟡 적정 ROE {roe*100:.0f}%")
        elif roe < 0:   score -= 8;  signals.append(f"🔴 마이너스 ROE {roe*100:.0f}%")

    score = max(0, min(100, score))
    if score >= 75:   grade = "BUY ⭐"
    elif score >= 55: grade = "HOLD 🟡"
    elif score >= 35: grade = "WATCH ⚠️"
    else:             grade = "AVOID 🔴"

    return score, grade, signals


# ─────────────────────────────────────────────────────────
# Score Engine 2: Growth Score (5~10년 성장성)
# ─────────────────────────────────────────────────────────
def calc_growth_score(company, profile, fin_annual):
    """
    TAM 확장성 + 매출 성장률 + FCF 창출력 + 독점적 시장 지위 기반 성장 잠재력 (0~100점)
    현재 실적이 아닌 5~10년 후 성장 가능성을 평가
    """
    score = 40

    # 1. 매출 성장률 YoY (35점 배점)
    rg = safe_float(getattr(profile, 'revenue_growth', None))
    if rg is not None:
        if rg > 0.5:    score += 35
        elif rg > 0.3:  score += 28
        elif rg > 0.15: score += 18
        elif rg > 0.05: score += 8
        elif rg > 0:    score += 2
        else:           score -= 20

    # 2. FCF 창출력 (25점 배점)
    if fin_annual:
        latest_fin = fin_annual[-1]
        fcf = safe_float(latest_fin.free_cash_flow)
        rev = safe_float(latest_fin.revenue)
        if fcf is not None and rev is not None and rev > 0:
            fcf_margin = fcf / rev
            if fcf_margin > 0.25:   score += 25
            elif fcf_margin > 0.15: score += 16
            elif fcf_margin > 0.05: score += 7
            elif fcf_margin > 0:    score += 2
            else:                   score -= 10
        elif fcf is not None and fcf < 0 and rev and rev > 0:
            # 적자 FCF지만 매출이 있으면 소폭 감점
            score -= 8

    # 3. 시장 지위 / 해자 강도 (20점 배점)
    desc = (company.role_description or '').lower()
    fg   = (company.future_growth or '').lower()
    combined = desc + ' ' + fg

    if any(kw in combined for kw in ['독점', 'monopoly', '유일한', 'only u.s.', 'sole']):
        score += 20
    elif any(kw in combined for kw in ['지배', 'dominant', '1위', 'leader', '선두']):
        score += 13
    elif any(kw in combined for kw in ['강자', 'established', 'major player', '대표']):
        score += 6

    # 4. 미래 TAM 키워드 매칭 (20점 배점)
    tam_keywords = [
        ('smr', 8), ('haleu', 8), ('ai', 5), ('데이터센터', 5), ('llm', 5),
        ('자율주행', 5), ('로봇', 5), ('휴머노이드', 8), ('우주', 5), ('ppa', 6),
        ('빅테크', 5), ('반감기', 6), ('etf', 5), ('triso', 8), ('nrc', 7),
        ('인허가', 6), ('수주잔고', 7), ('backlog', 7), ('take-or-pay', 8),
        ('cost-plus', 6), ('behind the meter', 8), ('btm', 7),
    ]
    tam_score = 0
    for kw, pts in tam_keywords:
        if kw in combined:
            tam_score += pts
            if tam_score >= 20:
                break
    score += min(20, tam_score)

    return max(0, min(100, score))


# ─────────────────────────────────────────────────────────
# Score Engine 3: Upside Score (현재 주가 대비 업사이드)
# ─────────────────────────────────────────────────────────
def calc_upside_score(company, profile, fin_annual):
    """
    현재 주가 대비 5~10년 내재 가치 업사이드 갭 (0~100점)
    낮은 PEG + 낮은 EV/Sales + 소형주 프리미엄 = 높은 업사이드 잠재력
    """
    score = 45

    pe = safe_float(getattr(profile, 'pe_ratio', None))
    rg = safe_float(getattr(profile, 'revenue_growth', None))
    ev_ebitda = safe_float(getattr(profile, 'ev_ebitda', None))
    market_cap = safe_float(getattr(profile, 'market_cap', None))
    pb = safe_float(getattr(profile, 'pb_ratio', None))

    # 1. PEG 분석 - 성장 대비 밸류에이션 (40점)
    if pe and pe > 0 and rg and rg > 0:
        peg = pe / (rg * 100)
        if peg < 0.5:   score += 38   # 극저평가 대비 성장
        elif peg < 1.0: score += 28   # 저평가
        elif peg < 1.5: score += 14   # 적정
        elif peg < 2.5: score -= 5    # 다소 고평가
        else:           score -= 18   # 고평가
    elif (not pe or pe <= 0) and rg and rg > 0.5:
        # 적자지만 초고성장 → 옵션가치 인정 (NuScale, Oklo 등)
        score += 18
    elif (not pe or pe <= 0) and rg and rg > 0.2:
        score += 8
    elif (not pe or pe <= 0) and (not rg or rg <= 0):
        score -= 20  # 적자 + 역성장 → 업사이드 없음

    # 2. EV/EBITDA (20점)
    if ev_ebitda and ev_ebitda > 0:
        if ev_ebitda < 8:    score += 20
        elif ev_ebitda < 15: score += 12
        elif ev_ebitda < 25: score += 4
        elif ev_ebitda < 40: score -= 4
        else:                score -= 12

    # 3. 시가총액 구간 프리미엄 (20점)
    # 소형주: 더 많은 성장 여력, 대형주: 제한적 업사이드
    if market_cap:
        # 한국 주식인 경우 원화(KRW)를 달러(USD)로 환산 (약 1350원 = 1달러 기준)
        ticker = getattr(company, 'ticker', '')
        adjusted_mc = market_cap / 1350 if ticker.endswith('.KS') or ticker.endswith('.KQ') else market_cap

        if adjusted_mc < 2e9:     score += 20   # Small cap (<$2B): 폭발적 성장 가능
        elif adjusted_mc < 10e9:  score += 14   # Mid cap (<$10B)
        elif adjusted_mc < 50e9:  score += 6    # Large cap
        elif adjusted_mc < 200e9: score += 0    # Mega
        else:                     score -= 10   # Ultra-mega (>$200B): 제한적

    # 4. PBR 역발상 (없으면 0)
    if pb and pb > 0:
        if pb < 1.5:   score += 10   # 장부가 이하 → 자산 저평가
        elif pb < 3:   score += 4
        elif pb > 20:  score -= 8

    return max(0, min(100, score))


# ─────────────────────────────────────────────────────────
# 목표 주가 & CAGR 추정
# ─────────────────────────────────────────────────────────
def estimate_target_and_cagr(profile, fin_annual):
    """
    5년 목표주가 & CAGR 추정 (단순 모델)
    - 매출성장률 기반 주가 성장률 추정
    - 밸류에이션 배수 프리미엄/디스카운트 반영
    """
    current_price = safe_float(getattr(profile, 'current_price', None)) or 0
    if current_price <= 0:
        return None, None, None

    rg = safe_float(getattr(profile, 'revenue_growth', None)) or 0
    pe = safe_float(getattr(profile, 'pe_ratio', None))
    market_cap = safe_float(getattr(profile, 'market_cap', None))

    # Base CAGR 추정
    if rg > 0.5:    base_cagr = 0.30
    elif rg > 0.35: base_cagr = 0.25
    elif rg > 0.2:  base_cagr = 0.20
    elif rg > 0.1:  base_cagr = 0.15
    elif rg > 0.03: base_cagr = 0.10
    elif rg >= 0:   base_cagr = 0.07
    else:           base_cagr = 0.04

    # 밸류에이션 조정 (고PER = 배수 압축 리스크)
    if pe and pe > 200:  base_cagr *= 0.72
    elif pe and pe > 100: base_cagr *= 0.85
    elif pe and pe > 50:  base_cagr *= 0.94
    elif pe and pe < 12 and pe > 0: base_cagr *= 1.18
    elif pe and pe < 20 and pe > 0: base_cagr *= 1.08

    # 소형주 프리미엄 (소형주는 더 높은 성장 기대)
    if market_cap and market_cap < 5e9:   base_cagr *= 1.15
    elif market_cap and market_cap < 15e9: base_cagr *= 1.06

    target_5y   = round(current_price * (1 + base_cagr) ** 5, 2)
    cagr_pct    = round(base_cagr * 100, 1)
    total_return = round(((target_5y / current_price) - 1) * 100, 1) if current_price > 0 else 0

    return target_5y, cagr_pct, total_return


# ─────────────────────────────────────────────────────────
# 포트폴리오 비중 배분 (확신도 비례 차등)
# ─────────────────────────────────────────────────────────
def assign_weights(scores):
    """
    상위 5개 종목 점수 기반 차등 비중 배분
    - 1.8제곱으로 차이를 증폭 (확신 있는 종목에 더 높은 비중)
    - 합계 정확히 100%
    """
    if not scores:
        return []
    powered = [s ** 1.8 for s in scores]
    total = sum(powered)
    if total == 0:
        n = len(scores)
        return [round(100 / n, 1)] * n

    weights = [round(p / total * 100, 1) for p in powered]
    # 반올림 오차 보정
    diff = round(100.0 - sum(weights), 1)
    weights[0] = round(weights[0] + diff, 1)
    return weights


# ─────────────────────────────────────────────────────────
# 에이전트 초기화
# ─────────────────────────────────────────────────────────
def initialize_agents(db: Session):
    """포트폴리오 매니저용 에이전트 초기화"""

    def ensure_agent(name, role, agent_type):
        agent = db.query(models.Agent).filter(models.Agent.name == name).first()
        if not agent:
            agent = models.Agent(name=name, role=role, type=agent_type)
            db.add(agent)
        return agent

    ensure_agent(
        "Alpha Orchestrator",
        "Chief Portfolio Strategist — 전 산업 리스크 조정 수익률 최적화 및 집중 포트폴리오 구성 총괄",
        "orchestrator"
    )
    ensure_agent(
        "Growth Screener Agent",
        "5~10년 성장 잠재력 스크리닝 — TAM 확장성, 매출 성장률, FCF 창출력, 시장 지위 분석",
        "quant"
    )
    ensure_agent(
        "Valuation Gap Agent",
        "현재 주가 대비 내재가치 갭 분석 — PEG Ratio, EV/EBITDA, 시가총액 구간별 업사이드 산출",
        "quant"
    )
    ensure_agent(
        "Portfolio Strategist",
        "최종 5종목 선발 및 비중 배분 — 확신도 비례 차등 가중, 시나리오별 수익률 시뮬레이션",
        "orchestrator"
    )
    ensure_agent(
        "Quant Signal Agent",
        "재무지표 기반 정량 스코어링 — PER, ROE, 부채비율, 마진 등 복합 재무 건전성 평가",
        "quant"
    )

    # 산업 에이전트
    reports = db.query(models.IndustryReport).all()
    for report in reports:
        ensure_agent(
            f"{report.tag} Analyst",
            f"{report.tag} 산업 수석 애널리스트 — 밸류체인 분석 및 산업 내 최선호주 선정",
            "industry"
        )

    # 기업 에이전트
    companies = db.query(models.Company).all()
    for company in companies:
        ensure_agent(
            f"{company.name} Tracker",
            f"{company.name} ({company.ticker}) 주식 전담 — 재무·전략·성장성·밸류에이션 모니터링",
            "company"
        )

    db.commit()


# ─────────────────────────────────────────────────────────
# 메인: 포트폴리오 구성 실행
# ─────────────────────────────────────────────────────────
def run_portfolio_construction(db: Session):
    """
    AI 포트폴리오 매니저 — 5종목 집중 투자 포트폴리오 구성
    
    단계:
    1. 전 산업 × 전 기업 3단계 스크리닝
       - Quant Score (재무 건전성, 0.30 가중)
       - Growth Score (5~10년 성장 잠재력, 0.40 가중)
       - Upside Score (현재 주가 대비 업사이드, 0.30 가중)
    2. 상위 5개 종목 선발
    3. 확신도 비례 차등 비중 배분 (합계 100%)
    4. Gemini로 각 종목 투자 근거 생성
    5. 최종 포트폴리오 JSON 저장
    """
    initialize_agents(db)
    db.query(models.AgentMessage).delete()
    db.commit()

    print("[Portfolio] 포트폴리오 구성 시작...")

    all_industries = db.query(models.IndustryReport).all()
    all_companies  = db.query(models.Company).all()

    print(f"[Portfolio] 대상: {len(all_industries)}개 산업, {len(all_companies)}개 기업")

    # ── Step 1: 전 기업 3단계 스코어링 ──────────────────────
    company_scores = {}   # company_id → {quant, growth, upside, portfolio, profile, fin_annual}

    for company in all_companies:
        profile = db.query(models.CompanyProfile).filter(
            models.CompanyProfile.company_id == company.id
        ).first()

        fin_all     = db.query(models.FinancialData).filter(
            models.FinancialData.company_id == company.id
        ).all()
        fin_annual  = sorted([f for f in fin_all if f.period_type == "annual"],  key=lambda x: x.date)

        # 1-a. Quant Score
        if profile:
            quant_score, quant_grade, _ = calc_quant_score(profile, fin_annual)
        else:
            quant_score, quant_grade = 40, "WATCH ⚠️"

        # 1-b. Growth Score
        growth_score = calc_growth_score(company, profile, fin_annual) if profile else 35

        # 1-c. Upside Score
        upside_score = calc_upside_score(company, profile, fin_annual) if profile else 40

        # 1-d. Portfolio Score (가중 합산)
        portfolio_score = round(
            0.30 * quant_score +
            0.40 * growth_score +
            0.30 * upside_score,
            2
        )

        company_scores[company.id] = {
            "company":         company,
            "profile":         profile,
            "fin_annual":      fin_annual,
            "quant_score":     quant_score,
            "quant_grade":     quant_grade,
            "growth_score":    growth_score,
            "upside_score":    upside_score,
            "portfolio_score": portfolio_score,
        }

    print(f"[Portfolio] 스코어링 완료. 상위 5개 선발 중...")

    # ── Step 2: 상위 5개 선발 (ticker 중복 제거) ─────────────
    ranked = sorted(
        company_scores.values(),
        key=lambda x: x["portfolio_score"],
        reverse=True
    )
    seen_tickers = set()
    top5 = []
    for item in ranked:
        ticker = item["company"].ticker
        if ticker not in seen_tickers:
            seen_tickers.add(ticker)
            top5.append(item)
        if len(top5) == 5:
            break

    # ── Step 3: 비중 배분 ────────────────────────────────────
    top5_scores  = [x["portfolio_score"] for x in top5]
    weights      = assign_weights(top5_scores)

    print(f"[Portfolio] Top 5 선발 완료: {[x['company'].ticker for x in top5]}")
    print(f"[Portfolio] 비중 배분: {weights}")

    # ── Step 4: 각 종목 투자 근거 생성 ──────────────────────────
    portfolio_items = []

    for i, (data, weight) in enumerate(zip(top5, weights)):
        company  = data["company"]
        profile  = data["profile"]
        fin_a    = data["fin_annual"]

        # 목표 주가 & CAGR 추정
        current_price = safe_float(getattr(profile, 'current_price', None)) if profile else None
        target_5y, cagr_5y, total_return_5y = estimate_target_and_cagr(profile, fin_a) if profile else (None, None, None)

        # 산업명 조회
        industry = db.query(models.IndustryReport).filter(
            models.IndustryReport.id == company.industry_id
        ).first()
        industry_name = industry.tag if industry else "기타"

        # ─── 핵심 재무 메트릭 추출 ────────────────────────────
        rg    = safe_float(getattr(profile, 'revenue_growth', None)) if profile else None
        nm    = safe_float(getattr(profile, 'net_margin_ttm', None)) if profile else None
        gm    = safe_float(getattr(profile, 'gross_margin_ttm', None)) if profile else None
        pe    = safe_float(getattr(profile, 'pe_ratio', None)) if profile else None
        roe   = safe_float(getattr(profile, 'roe', None)) if profile else None
        de    = safe_float(getattr(profile, 'debt_to_equity', None)) if profile else None
        cap   = safe_float(getattr(profile, 'market_cap', None)) if profile else None
        cr    = safe_float(getattr(profile, 'current_ratio', None)) if profile else None
        ev_eb = safe_float(getattr(profile, 'ev_ebitda', None)) if profile else None

        fcf_val = None
        rev_val = None
        if fin_a:
            latest = fin_a[-1]
            fcf_val = safe_float(latest.free_cash_flow)
            rev_val = safe_float(latest.revenue)

        rg_str  = f"{rg*100:.0f}%" if rg is not None else "N/A"
        pe_str  = fmt_x(pe)
        cap_str = fmt_b(cap, company.ticker)
        nm_str  = f"{nm*100:.1f}%" if nm is not None else "N/A"
        gm_str  = f"{gm*100:.1f}%" if gm is not None else "N/A"
        roe_str = f"{roe*100:.1f}%" if roe is not None else "N/A"
        de_str  = f"{de:.0f}%" if de is not None else "N/A"
        cr_str  = f"{cr:.1f}x" if cr is not None else "N/A"
        fcf_str = fmt_b(fcf_val, company.ticker) if fcf_val else "N/A"
        rev_str = fmt_b(rev_val, company.ticker) if rev_val else "N/A"
        is_krw = company.ticker.endswith('.KS') or company.ticker.endswith('.KQ')
        target_str = (f"₩{target_5y:,.0f}" if is_krw else f"${target_5y:.2f}") if target_5y else "N/A"
        upside_str = f"+{total_return_5y:.0f}%" if total_return_5y else "N/A"
        cagr_str   = f"{cagr_5y:.1f}%/yr" if cagr_5y else "N/A"

        # ─── 데이터 기반 투자 논거 생성 (Fallback) ───────────
        thesis_points = []
        risk_points   = []

        # 논거 1: 밸류에이션 업사이드 (현재가 → 목표가)
        if current_price and target_5y and total_return_5y:
            peg_desc = ""
            if pe and rg and rg > 0:
                peg = pe / (rg * 100)
                if peg < 1.0:
                    peg_desc = f" PEG {peg:.2f}x로 성장 대비 현저히 저평가,"
                elif peg < 1.5:
                    peg_desc = f" PEG {peg:.2f}x 적정 수준,"
            thesis_points.append(
                f"현재가 ${current_price:.2f} → 5년 목표가 {target_str}으로 업사이드 {upside_str}(CAGR {cagr_str}) 예상.{peg_desc} 현재 시가총액 {cap_str}은 {industry_name} 내 핵심 밸류체인 포지션 대비 저평가 구간."
            )
        elif company.role_description:
            thesis_points.append(
                f"{industry_name} 밸류체인 내 {company.role_description[:80]}의 핵심 포지션 확보. 산업 구조적 성장에 따른 장기 업사이드 기대."
            )

        # 논거 2: 성장 모멘텀 (매출성장률 + FCF)
        growth_desc = []
        if rg is not None:
            if rg > 0.5:
                growth_desc.append(f"매출성장률 {rg_str}(고성장 구간)")
            elif rg > 0.2:
                growth_desc.append(f"매출성장률 {rg_str}(업계 상위권)")
            elif rg > 0.05:
                growth_desc.append(f"매출성장률 {rg_str}(안정 성장)")
            elif rg < 0:
                growth_desc.append(f"매출 역성장({rg_str}) 국면이나 구조적 전환 중")
        if fcf_val and rev_val and rev_val > 0:
            fcf_margin = fcf_val / rev_val
            if fcf_margin > 0.15:
                growth_desc.append(f"FCF 마진 {fcf_margin*100:.0f}%(강력한 현금 창출력)")
            elif fcf_margin > 0.05:
                growth_desc.append(f"FCF 마진 {fcf_margin*100:.0f}%(플러스 FCF)")
            elif fcf_val < 0:
                growth_desc.append("현재 FCF 음수이나 스케일업 단계")
        if gm is not None and gm > 0.4:
            growth_desc.append(f"매출총이익률 {gm_str}(소프트웨어급 해자)")
        if not growth_desc:
            growth_desc.append(f"{company.future_growth[:80]}")

        thesis_points.append(
            f"{', '.join(growth_desc[:3])}. " +
            (f"ROE {roe_str}의 자본 효율성이 5~10년 복리 수익을 뒷받침." if roe and roe > 0.1 else
             f"{company.future_growth[80:160] if len(company.future_growth) > 80 else company.future_growth[:80]}")
        )

        # 논거 3: 구조적 촉매 (역할 + 경쟁 해자)
        role_text = company.role_description[:200] if company.role_description else ""
        future_text = company.future_growth[:200] if company.future_growth else ""
        moat_desc = ""
        if any(kw in (role_text + future_text).lower() for kw in ['독점', 'sole', 'only u.s.', '유일', 'monopoly']):
            moat_desc = "국내 유일 혹은 독점적 기술 포지션으로 경쟁자 진입장벽 최고 수준."
        elif any(kw in (role_text + future_text).lower() for kw in ['1위', 'leader', 'dominant', '지배', 'largest']):
            moat_desc = "해당 세그먼트 시장 지배자로 점유율 확대 및 프라이싱 파워 보유."
        elif any(kw in (role_text + future_text).lower() for kw in ['ppa', 'take-or-pay', 'backlog', '수주잔고', 'contract']):
            moat_desc = "장기 계약(PPA·수주잔고) 기반 예측 가능한 수익 구조로 하방 리스크 제한."
        else:
            moat_desc = f"{role_text[:120]} 포지션에서 수혜 집중."

        thesis_points.append(
            f"{moat_desc} " +
            (f"부채비율 {de_str}, 유동비율 {cr_str}의 건전한 재무구조가 장기 투자 안전마진을 제공." if de is not None and cr is not None else
             f"5~10년 구조적 성장 수혜주로 중장기 포트폴리오 핵심 편입 논거.")
        )

        # ─── 리스크 요인 생성 (구체적 2개) ──────────────────
        # Risk 1: 밸류에이션 / 실적 리스크
        if pe and pe > 100:
            risk_points.append(f"PER {pe:.0f}x의 과도한 밸류에이션은 실적 미달 시 30~50% 급락 위험. 성장 기대치 충족 실패가 최대 리스크.")
        elif pe and pe > 50:
            risk_points.append(f"PER {pe:.0f}x로 이미 성장이 선반영된 상태. 매출성장률 둔화 시 멀티플 압축으로 주가 하방 압력 불가피.")
        elif rg is not None and rg < 0:
            risk_points.append(f"현재 역성장({rg_str}) 국면. 사업 구조 전환 실패 시 추가 매출 감소 및 수익성 악화 가능.")
        elif fcf_val is not None and fcf_val < 0:
            risk_points.append(f"FCF 적자 지속. 자금 조달 여건 악화(금리 상승·투자 심리 위축) 시 유동성 위기 및 지분 희석 위험.")
        else:
            risk_points.append(f"예상 성장률({rg_str}) 둔화 시 현재 밸류에이션 정당성 약화. 경기침체·금리 상승 환경에서 성장주 멀티플 압축 리스크.")

        # Risk 2: 사업/산업/규제 리스크
        role_lower = (role_text + future_text).lower()
        if any(kw in role_lower for kw in ['nrc', '인허가', 'faa', 'regulation', '규제', 'license']):
            risk_points.append(f"규제 인허가 지연이 사업화 타임라인을 2~4년 연장할 수 있어 현재가 기준 업사이드 시나리오의 최대 불확실성.")
        elif any(kw in role_lower for kw in ['경쟁', 'competitor', 'competition', 'rival', 'against']):
            risk_points.append(f"빅테크·후발주자의 공격적 투자로 시장점유율 잠식 가능. 가격 경쟁 심화 시 마진 압박 현실화.")
        elif any(kw in role_lower for kw in ['china', '중국', 'geopolit', '지정학', 'tariff', '관세']):
            risk_points.append(f"미중 무역 갈등 및 지정학적 리스크로 공급망 비용 상승·시장 접근 제한 가능. 관세 정책 변화가 핵심 변수.")
        elif de is not None and de > 200:
            risk_points.append(f"부채비율 {de_str}의 높은 레버리지. 금리 상승 환경에서 이자 부담 급증 및 리파이낸싱 리스크 존재.")
        else:
            risk_points.append(f"거시 경기 침체 시 기업 IT/인프라 투자 감축으로 수요 위축 가능. 핵심 고객 집중도가 높을 경우 개별 리스크도 존재.")

        # ─── Gemini로 논거 보강 (API 있는 경우) ─────────────
        fallback_thesis_list = thesis_points
        fallback_risk_list   = risk_points

        gemini_prompt = f"""당신은 헤지펀드 포트폴리오 매니저입니다. 다음 기업의 5~10년 투자 논거를 한국어로 작성하세요.

기업: {company.name}({company.ticker}) | 산업: {industry_name}
현재가: ${f'{current_price:.2f}' if current_price else 'N/A'} → 5년 목표가: {target_str} (업사이드 {upside_str}, CAGR {cagr_str})
시가총액: {cap_str} | 매출성장률: {rg_str} | 순이익률: {nm_str} | ROE: {roe_str}
PER: {pe_str} | EV/EBITDA: {fmt_x(ev_eb)} | 부채비율: {de_str} | 유동비율: {cr_str}
매출: {rev_str} | FCF: {fcf_str}
밸류체인 역할: {role_text[:200]}
성장 스토리: {future_text[:200]}

출력 형식 (반드시 JSON):
{{
  "thesis": ["논거1(현재가 대비 업사이드 수치 필수 포함)", "논거2(성장 모멘텀, 구체 수치)", "논거3(해자 또는 구조적 촉매)"],
  "risks": ["리스크1(밸류에이션/실적)", "리스크2(사업/규제/경쟁)"]
}}

규칙: 수치 없는 추상적 문장 금지. 각 항목 2문장 이내. "AI 수혜" 같은 진부한 표현 금지."""

        # Gemini 호출
        gemini_raw = get_gemini_response(gemini_prompt, "")
        thesis_list = fallback_thesis_list
        risk_list   = fallback_risk_list

        if gemini_raw:
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', gemini_raw)
                if json_match:
                    parsed = json.loads(json_match.group())
                    th = parsed.get('thesis', [])
                    ri = parsed.get('risks', [])
                    if len(th) >= 2 and len(ri) >= 1:
                        thesis_list = th[:3]
                        risk_list   = ri[:2]
            except Exception as e:
                print(f"[Portfolio] Gemini 파싱 실패 ({company.ticker}): {e}")

        portfolio_items.append({
            "rank":            i + 1,
            "name":            company.name,
            "ticker":          company.ticker,
            "industry":        industry_name,
            "weight":          weight,
            "current_price":   round(current_price, 2) if current_price else None,
            "target_price_5y": target_5y,
            "cagr_5y":         cagr_5y,
            "total_return_5y": total_return_5y,
            "upside_str":      upside_str,
            "portfolio_score": round(data["portfolio_score"], 1),
            "quant_score":     data["quant_score"],
            "growth_score":    data["growth_score"],
            "upside_score":    data["upside_score"],
            "quant_grade":     data["quant_grade"],
            # 구조화된 논거 (리스트)
            "thesis":          thesis_list,
            "risks":           risk_list,
            # 하위 호환
            "selection_reason": " | ".join(thesis_list),
            "key_risk":        " | ".join(risk_list),
            # 재무 메트릭 요약 (UI 표시용)
            "metrics": {
                "revenue_growth": rg_str,
                "net_margin":     nm_str,
                "gross_margin":   gm_str,
                "roe":            roe_str,
                "pe_ratio":       pe_str,
                "ev_ebitda":      fmt_x(ev_eb),
                "debt_to_equity": de_str,
                "market_cap":     cap_str,
                "fcf":            fcf_str,
            }
        })

        print(f"[Portfolio] #{i+1} {company.ticker}: 비중 {weight}%, 스코어 {data['portfolio_score']:.1f}")


    # ── Step 5: 포트폴리오 시나리오 & 최종 출력 ──────────────
    # 가중 평균 CAGR
    weighted_cagr = sum(
        (item["cagr_5y"] or 0) * item["weight"] / 100
        for item in portfolio_items
    )

    scenario_prompt = f"""다음 포트폴리오의 5년 시나리오를 한국어로 작성하세요.

포트폴리오: {', '.join([f"{x['ticker']}({x['weight']}%)" for x in portfolio_items])}
가중평균 추정 CAGR: {weighted_cagr:.1f}%/yr
투자 산업: {', '.join(set([x['industry'] for x in portfolio_items]))}

3가지 시나리오를 JSON으로 출력하세요:
{{
  "bull": {{"return_pct": [숫자], "cagr": [숫자], "probability": 30, "trigger": "[트리거 한 문장]"}},
  "base": {{"return_pct": [숫자], "cagr": [숫자], "probability": 45, "trigger": "[트리거 한 문장]"}},
  "bear": {{"return_pct": [숫자], "cagr": [숫자], "probability": 25, "trigger": "[트리거 한 문장]"}}
}}

bull return_pct는 base의 1.8~2.5배, bear는 base의 -0.3~0.3배로 설정."""

    base_return = round(weighted_cagr * 5 * 1.2, 0)  # 단순 추정
    fallback_scenario = {
        "bull": {
            "return_pct": round(base_return * 2.2, 0),
            "cagr": round(weighted_cagr * 2.0, 1),
            "probability": 30,
            "trigger": "AI 전력 수요 폭증 + SMR 인허가 조기 획득 + 금리 인하로 성장주 프리미엄 확대"
        },
        "base": {
            "return_pct": round(base_return, 0),
            "cagr": round(weighted_cagr, 1),
            "probability": 45,
            "trigger": "현 성장 트렌드 지속 + 점진적 규제 명확화 + PPA/수주잔고 확대"
        },
        "bear": {
            "return_pct": round(base_return * 0.15, 0),
            "cagr": round(weighted_cagr * 0.2, 1),
            "probability": 25,
            "trigger": "경기침체 + 규제 지연 + 경쟁 심화로 성장 모멘텀 약화"
        }
    }

    scenario = fallback_scenario
    try:
        scenario_text = get_gemini_response(scenario_prompt, json.dumps(fallback_scenario, ensure_ascii=False))
        # JSON 추출
        import re
        json_match = re.search(r'\{[\s\S]*\}', scenario_text)
        if json_match:
            parsed = json.loads(json_match.group())
            if "bull" in parsed and "base" in parsed and "bear" in parsed:
                scenario = parsed
    except Exception as e:
        print(f"[Portfolio] 시나리오 파싱 실패: {e}")

    # ── 최종 포트폴리오 JSON 저장 ───────────────────────────
    portfolio_json = {
        "type":               "portfolio",
        "created_at":         datetime.datetime.now().strftime("%Y-%m-%d"),
        "investment_horizon": "5~10년",
        "total_companies_screened": len(all_companies),
        "total_industries_analyzed": len(all_industries),
        "portfolio":          portfolio_items,
        "scenario":           scenario,
        "scoring_weights": {
            "quant":  "30% — 재무 건전성 (PER·ROE·부채비율·마진)",
            "growth": "40% — 5~10년 성장 잠재력 (TAM·FCF·시장지위)",
            "upside": "30% — 현재주가 대비 업사이드 (PEG·EV/EBITDA·시가총액)"
        }
    }

    # DB 저장 (기존 OrchestrationReport 테이블 재사용)
    db.query(models.OrchestrationReport).delete()
    report_obj = models.OrchestrationReport(
        title=f"AI 최적 포트폴리오 — {len(all_industries)}개 산업 {len(all_companies)}개 기업 스크리닝",
        content=json.dumps(portfolio_json, ensure_ascii=False),
        created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(report_obj)
    db.commit()

    print(f"[Portfolio] 완료! 상위 5종목: {[x['ticker'] for x in portfolio_items]}")
    print(f"[Portfolio] 비중 합계: {sum(x['weight'] for x in portfolio_items):.1f}%")


# ─────────────────────────────────────────────────────────
# 하위 호환성 (main.py에서 기존 이름으로 호출하는 경우)
# ─────────────────────────────────────────────────────────
def run_agent_simulation(db: Session):
    """하위 호환 래퍼 — 포트폴리오 구성으로 리다이렉트"""
    run_portfolio_construction(db)
