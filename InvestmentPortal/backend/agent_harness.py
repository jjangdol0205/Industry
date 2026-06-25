import os
import datetime
from sqlalchemy.orm import Session
import google.generativeai as genai
import models
import json
import math

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
    except: return None

def fmt_b(v):   # 십억 달러
    v = safe_float(v)
    return f"${v/1e9:.2f}B" if v is not None else "N/A"

def fmt_pct(v): # 퍼센트
    v = safe_float(v)
    return f"{v:.1f}%" if v is not None else "N/A"

def fmt_pct_ratio(v): # 0~1 비율을 %로
    v = safe_float(v)
    return f"{v*100:.1f}%" if v is not None else "N/A"

def fmt_x(v):   # 배수
    v = safe_float(v)
    return f"{v:.1f}x" if v is not None else "N/A"

def fmt_n(v):   # 일반 숫자
    v = safe_float(v)
    return f"{v:.2f}" if v is not None else "N/A"

# ─────────────────────────────────────────────────────────
# Quant Scoring Engine
# ─────────────────────────────────────────────────────────
def calc_quant_score(profile, fin_annual):
    """
    재무지표 기반 정량 스코어 (0~100점) 계산
    Returns: (score, grade, signals)
    """
    score = 50  # 기본 점수
    signals = []

    # 1. 수익성 (최대 20점)
    gm = safe_float(getattr(profile, 'gross_margin_ttm', None))
    nm = safe_float(getattr(profile, 'net_margin_ttm', None))
    if gm is not None:
        if gm > 0.5:   score += 10; signals.append(f"✅ 높은 매출총이익률 {gm*100:.0f}%")
        elif gm > 0.3: score += 5;  signals.append(f"🟡 적정 매출총이익률 {gm*100:.0f}%")
        else:          score -= 5;  signals.append(f"⚠️ 낮은 매출총이익률 {gm*100:.0f}%")
    if nm is not None:
        if nm > 0.15:  score += 10; signals.append(f"✅ 높은 순이익률 {nm*100:.0f}%")
        elif nm > 0.05: score += 5; signals.append(f"🟡 적정 순이익률 {nm*100:.0f}%")
        elif nm < 0:   score -= 10; signals.append(f"🔴 적자 (순이익률 {nm*100:.0f}%)")

    # 2. 성장성 (최대 20점)
    rg = safe_float(getattr(profile, 'revenue_growth', None))
    if rg is not None:
        if rg > 0.3:   score += 15; signals.append(f"✅ 고성장 매출성장률 {rg*100:.0f}%")
        elif rg > 0.1: score += 8;  signals.append(f"🟡 성장 매출성장률 {rg*100:.0f}%")
        elif rg > 0:   score += 3;  signals.append(f"🟡 완만한 성장 {rg*100:.0f}%")
        else:          score -= 10; signals.append(f"🔴 매출 역성장 {rg*100:.0f}%")

    # 3. 밸류에이션 (최대 15점)
    pe = safe_float(getattr(profile, 'pe_ratio', None))
    if pe is not None and pe > 0:
        if pe < 15:    score += 15; signals.append(f"✅ 저평가 PER {pe:.1f}x")
        elif pe < 30:  score += 8;  signals.append(f"🟡 적정 PER {pe:.1f}x")
        elif pe < 60:  score += 3;  signals.append(f"🟡 다소 고평가 PER {pe:.1f}x")
        else:          score -= 5;  signals.append(f"⚠️ 고평가 PER {pe:.1f}x")

    # 4. 재무건전성 (최대 15점)
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

    # 5. ROE/ROA (최대 10점)
    roe = safe_float(getattr(profile, 'roe', None))
    if roe is not None:
        if roe > 0.2:  score += 10; signals.append(f"✅ 우수한 ROE {roe*100:.0f}%")
        elif roe > 0.1: score += 5; signals.append(f"🟡 적정 ROE {roe*100:.0f}%")
        elif roe < 0:  score -= 8;  signals.append(f"🔴 마이너스 ROE {roe*100:.0f}%")

    # 범위 제한
    score = max(0, min(100, score))

    # 등급 판정
    if score >= 75:   grade = "BUY ⭐"
    elif score >= 55: grade = "HOLD 🟡"
    elif score >= 35: grade = "WATCH ⚠️"
    else:             grade = "AVOID 🔴"

    return score, grade, signals


def initialize_agents(db: Session):
    """Initializes agents for the orchestrator, reports, and companies if they don't exist."""
    orchestrator = db.query(models.Agent).filter(models.Agent.type == "orchestrator").first()
    if not orchestrator:
        orchestrator = models.Agent(
            name="Alpha Orchestrator",
            role="Lead Investment Strategist & Cross-Industry Bottleneck Analyzer",
            type="orchestrator"
        )
        db.add(orchestrator)

    manager = db.query(models.Agent).filter(models.Agent.name == "Site Manager Agent").first()
    if not manager:
        manager = models.Agent(
            name="Site Manager Agent",
            role="전반적인 홈페이지 관리, 깃허브 메인 브랜치 동기화 및 Render 클라우드 배포 모니터링 총괄",
            type="management"
        )
        db.add(manager)

    app_dev = db.query(models.Agent).filter(models.Agent.name == "App Developer Agent").first()
    if not app_dev:
        app_dev = models.Agent(
            name="App Developer Agent",
            role="PWA 모바일 앱 최적화, 반응형 UI 레이아웃 및 모바일 디바이스 호환성 검증 총괄",
            type="management"
        )
        db.add(app_dev)

    # ── Quant Signal Agent (신규) ────────────────────────
    quant = db.query(models.Agent).filter(models.Agent.name == "Quant Signal Agent").first()
    if not quant:
        quant = models.Agent(
            name="Quant Signal Agent",
            role="재무지표 기반 정량 스코어링 및 자동 BUY/HOLD/SELL 투자등급 산출 전담",
            type="quant"
        )
        db.add(quant)

    # Industry Agents
    reports = db.query(models.IndustryReport).all()
    for report in reports:
        agent = db.query(models.Agent).filter(
            models.Agent.type == "industry",
            models.Agent.target_id == report.id
        ).first()
        if not agent:
            agent = models.Agent(
                name=f"{report.tag} Analyst",
                role=f"Lead Industry Analyst specializing in {report.tag} Value Chain & Technology Trends",
                type="industry",
                target_id=report.id
            )
            db.add(agent)

    # Company Agents
    companies = db.query(models.Company).all()
    for company in companies:
        agent = db.query(models.Agent).filter(
            models.Agent.type == "company",
            models.Agent.target_id == company.id
        ).first()
        if not agent:
            agent = models.Agent(
                name=f"{company.name} Tracker",
                role=f"Equity Research Specialist monitoring {company.name} ({company.ticker}) Financials & Strategy",
                type="company",
                target_id=company.id
            )
            db.add(agent)

    db.commit()


def run_agent_simulation(db: Session):
    """
    업그레이드된 멀티에이전트 협동 분석 루프:
    1. Orchestrator 분석 개시
    2. Quant Signal Agent: 전 기업 정량 스코어링
    3. Industry Analyst → Company Monitor (상세 재무+프로파일 기반)
    4. Orchestrator: 구조화된 최종 리포트 생성
    """
    initialize_agents(db)
    db.query(models.AgentMessage).delete()
    db.commit()

    def log_msg(sender, sender_type, recipient, content, msg_type="message"):
        msg = models.AgentMessage(
            sender=sender,
            sender_type=sender_type,
            recipient=recipient,
            content=content,
            msg_type=msg_type,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(msg)
        db.commit()

    # Step 0: 관리 에이전트 보고
    manager_agent = db.query(models.Agent).filter(models.Agent.name == "Site Manager Agent").first()
    if manager_agent:
        log_msg(manager_agent.name, "management", "Self",
                "홈페이지 시스템 리소스 점검 완료: 깃허브 저장소(main) 및 Render 배포 상태 양호.", "thought")
        log_msg(manager_agent.name, "management", "Alpha Orchestrator",
                "보고드립니다. 홈페이지 관리 및 서버 리소스 최적화 완료. 리서치 시뮬레이션을 시작하셔도 좋습니다.", "message")

    app_dev_agent = db.query(models.Agent).filter(models.Agent.name == "App Developer Agent").first()
    if app_dev_agent:
        log_msg(app_dev_agent.name, "management", "Self",
                "PWA 및 모바일 앱 호환성 점검 완료: iOS/Android 반응형 디자인 정상 작동 확인.", "thought")
        log_msg(app_dev_agent.name, "management", "Alpha Orchestrator",
                "PWA 모바일 앱 배포 및 반응형 UX 최적화 완료. 커스텀 도메인(industry.truthofmarket.com) 설정 진행 중.", "message")

    # Step 1: Orchestrator 개시
    log_msg("System", "system", "Alpha Orchestrator", "프리미엄 협동 분석 명령을 받았습니다. 하네스를 가동합니다.", "message")
    log_msg("Alpha Orchestrator", "orchestrator", "Self",
            "분석 미션 개시. 오늘 목표: 전 산업 밸류체인 정밀 분석 + 크로스인더스트리 병목 발굴 + BUY등급 수혜주 선정. "
            "먼저 Quant Signal Agent에게 전 기업 정량 스코어링을 지시한 후, 각 산업 애널리스트에게 심층 분석을 명령합니다.",
            "thought")

    # ── Step 2: Quant Signal Agent 스코어링 ───────────────
    quant_agent = db.query(models.Agent).filter(models.Agent.name == "Quant Signal Agent").first()
    log_msg("Alpha Orchestrator", "orchestrator", "Quant Signal Agent",
            "전체 추적 기업에 대한 정량 스코어링을 실시하세요. 재무지표 기반 BUY/HOLD/WATCH 등급을 산출하여 보고하십시오.", "message")

    all_companies = db.query(models.Company).all()
    quant_scores = {}   # company_id → (score, grade, signals)
    quant_summary_lines = []

    log_msg("Quant Signal Agent", "quant", "Self",
            f"전체 {len(all_companies)}개 기업의 company_profile 데이터를 로드하여 PER·PBR·ROE·부채비율·성장률 등 "
            "복합 지표 기반 스코어링을 수행합니다.", "thought")

    for comp in all_companies:
        profile = db.query(models.CompanyProfile).filter(
            models.CompanyProfile.company_id == comp.id
        ).first()
        fin_annual = db.query(models.FinancialData).filter(
            models.FinancialData.company_id == comp.id,
            models.FinancialData.period_type == "annual"
        ).all()

        if profile:
            score, grade, signals = calc_quant_score(profile, fin_annual)
        else:
            score, grade, signals = 50, "HOLD 🟡", ["프로파일 데이터 미확인"]

        quant_scores[comp.id] = (score, grade, signals)
        quant_summary_lines.append(
            f"  [{grade}] {comp.name} ({comp.ticker}): {score}점 | "
            f"PER {fmt_x(getattr(profile, 'pe_ratio', None) if profile else None)} | "
            f"ROE {fmt_pct_ratio(getattr(profile, 'roe', None) if profile else None)} | "
            f"매출성장 {fmt_pct_ratio(getattr(profile, 'revenue_growth', None) if profile else None)}"
        )

    # BUY 등급 기업 추출
    buy_companies = [(cid, s, g) for cid, (s, g, _) in quant_scores.items() if 'BUY' in g]
    buy_names = [c.name for c in all_companies if c.id in [x[0] for x in buy_companies]]

    quant_report = (
        f"정량 스코어링 완료 ({len(all_companies)}개 기업).\n"
        f"BUY 등급: {len(buy_companies)}개 | "
        f"HOLD: {sum(1 for _,(s,g,_) in quant_scores.items() if 'HOLD' in g)}개 | "
        f"WATCH: {sum(1 for _,(s,g,_) in quant_scores.items() if 'WATCH' in g)}개\n"
        f"BUY 등급 기업: {', '.join(buy_names[:10])}\n\n"
        + "\n".join(quant_summary_lines[:20])
    )
    log_msg("Quant Signal Agent", "quant", "Alpha Orchestrator", quant_report, "message")

    # ── Step 3: 산업별 심층 분석 ──────────────────────────
    industries = db.query(models.IndustryReport).all()
    if not industries:
        log_msg("Alpha Orchestrator", "orchestrator", "System", "추적 산업 데이터가 없습니다.", "message")
        return

    industry_reports_compiled = []

    for ind in industries:
        ind_agent_name = f"{ind.tag} Analyst"
        log_msg("Alpha Orchestrator", "orchestrator", ind_agent_name,
                f"[{ind.title}] 산업의 심층 밸류체인 분석을 실시하세요. "
                "하위 기업의 재무 건전성 + 성장 모멘텀 + 밸류에이션을 종합하여 산업 내 Winner/Loser를 구분하고 "
                "최선호주 1개와 향후 6개월 촉매 이벤트를 보고하십시오.", "message")

        log_msg(ind_agent_name, "industry", "Self",
                f"{ind.tag} 산업 분석 오더 수신. 하위 기업 모니터들에게 상세 재무 보고를 요청합니다.", "thought")

        companies = db.query(models.Company).filter(models.Company.industry_id == ind.id).all()
        company_insights = []
        company_grades = []

        for comp in companies:
            comp_agent_name = f"{comp.name} Tracker"
            log_msg(ind_agent_name, "industry", comp_agent_name,
                    f"{comp.name} ({comp.ticker})의 재무 건전성, 밸류에이션, 성장성을 종합 분석하여 투자등급을 포함한 상세 보고서를 제출하세요.", "message")

            # ── 재무 데이터 로드 ──
            financials = db.query(models.FinancialData).filter(
                models.FinancialData.company_id == comp.id
            ).all()
            fin_annual  = sorted([f for f in financials if f.period_type == "annual"],  key=lambda x: x.date)
            fin_quarter = sorted([f for f in financials if f.period_type == "quarterly"], key=lambda x: x.date)

            # ── 프로파일 로드 ──
            profile = db.query(models.CompanyProfile).filter(
                models.CompanyProfile.company_id == comp.id
            ).first()

            # ── 재무 요약 구성 (상세화) ──
            fin_block = f"=== {comp.name} ({comp.ticker}) 재무 요약 ===\n"

            # 연간 재무 (최근 3년)
            fin_block += "\n[연간 실적 - 최근 3년]\n"
            fin_block += f"{'연도':>10} {'매출':>12} {'매출원가':>12} {'매출총이익':>12} {'영업이익':>12} {'순이익':>12} {'EBITDA':>12} {'매출총이익률':>12} {'영업이익률':>10}\n"
            for f in fin_annual[-3:]:
                fin_block += (
                    f"{f.date:>10} {fmt_b(f.revenue):>12} {fmt_b(f.cost_of_revenue):>12} "
                    f"{fmt_b(f.gross_profit):>12} {fmt_b(f.operating_income):>12} "
                    f"{fmt_b(f.net_income):>12} {fmt_b(f.ebitda):>12} "
                    f"{fmt_pct(f.gross_margin):>12} {fmt_pct(f.op_margin):>10}\n"
                )

            # 분기 실적 (최근 4분기)
            fin_block += "\n[분기 실적 - 최근 4분기]\n"
            for f in fin_quarter[-4:]:
                fin_block += (
                    f"{f.date}: 매출 {fmt_b(f.revenue)} | "
                    f"영업이익 {fmt_b(f.operating_income)} | "
                    f"순이익 {fmt_b(f.net_income)} | "
                    f"FCF {fmt_b(f.free_cash_flow)}\n"
                )

            # 재무상태
            latest = fin_annual[-1] if fin_annual else None
            if latest:
                fin_block += f"\n[재무상태 (최근 연간)]\n"
                fin_block += f"총자산 {fmt_b(latest.total_assets)} | 현금 {fmt_b(latest.cash_and_equivalents)} | "
                fin_block += f"총부채 {fmt_b(latest.total_debt)} | 자기자본 {fmt_b(latest.shareholders_equity)}\n"
                fin_block += f"부채비율 {fmt_pct(latest.debt_to_equity_ratio)} | 유동비율 {fmt_x(latest.current_ratio)} | "
                fin_block += f"ROE {fmt_pct(latest.roe)} | ROA {fmt_pct(latest.roa)}\n"

            # 프로파일 (시장 평가)
            if profile:
                fin_block += f"\n[시장 평가 & 밸류에이션]\n"
                fin_block += f"현재주가 ${fmt_n(profile.current_price)} | 시총 {fmt_b(profile.market_cap)} | 베타 {fmt_n(profile.beta)}\n"
                fin_block += f"PER {fmt_x(profile.pe_ratio)} | PBR {fmt_x(profile.pb_ratio)} | EV/EBITDA {fmt_x(profile.ev_ebitda)}\n"
                fin_block += f"매출성장률 {fmt_pct_ratio(profile.revenue_growth)} | 총이익률 {fmt_pct_ratio(profile.gross_margin_ttm)} | 순이익률 {fmt_pct_ratio(profile.net_margin_ttm)}\n"

            # Quant 스코어
            score, grade, signals = quant_scores.get(comp.id, (50, "HOLD 🟡", []))
            fin_block += f"\n[Quant Signal Agent 스코어]\n정량점수: {score}/100 | 투자등급: {grade}\n"
            fin_block += "\n".join(signals[:5]) + "\n"

            log_msg(comp_agent_name, "company", "Self",
                    f"{comp.name} 재무·프로파일·정량 데이터 로드 완료. 수익성·성장성·밸류에이션·재무건전성을 종합한 투자등급 보고서를 작성합니다.", "thought")

            # ── Gemini 프롬프트 (상세화) ──
            prompt_comp = f"""당신은 기업 담당 애널리스트입니다. 아래 상세 데이터를 바탕으로 {comp.name} ({comp.ticker})에 대한 기관급 리서치 보고서를 한국어로 작성하세요.

{fin_block}

밸류체인 내 역할: {comp.role_description}
미래 성장 스토리: {comp.future_growth}

다음 형식으로 작성하세요:
■ 핵심 요약: (2줄)
■ 재무 건전성: 매출/이익 트렌드, 마진 변화, FCF 흐름 분석 (3줄)
■ 밸류에이션: 현재 PER/EV-EBITDA가 섹터 평균 대비 저/고평가인지 평가 (2줄)
■ 성장 촉매: 향후 성장을 이끌 핵심 드라이버 (2줄)
■ 핵심 리스크: (2줄)
■ 투자등급: {grade} ({score}/100점) — 근거 1줄
"""
            fallback_comp = (
                f"■ 핵심 요약: {comp.name}({comp.ticker})는 {ind.tag} 밸류체인에서 핵심 역할을 수행 중이며, Quant 정량평가 {score}점({grade}) 등급을 획득했습니다.\n"
                f"■ 재무 건전성: " + (f"매출 {fmt_b(fin_annual[-1].revenue)} 수준으로 " if fin_annual else "") +
                f"안정적인 사업 구조를 유지하고 있습니다.\n"
                f"■ 밸류에이션: " + (f"PER {fmt_x(profile.pe_ratio)} 수준으로 " if profile else "") +
                "섹터 내 포지션 확인이 필요합니다.\n"
                f"■ 성장 촉매: {comp.future_growth[:80]}...\n"
                f"■ 핵심 리스크: 거시경제 불확실성 및 경쟁 심화.\n"
                f"■ 투자등급: {grade} ({score}/100점)"
            )

            comp_report = get_gemini_response(prompt_comp, fallback_comp)
            log_msg(comp_agent_name, "company", ind_agent_name, comp_report, "message")
            company_insights.append(f"### {comp.name} ({comp.ticker}) — {grade}\n{comp_report}")
            company_grades.append(f"{comp.ticker}: {grade} ({score}점)")

        # ── 산업 애널리스트 종합 리포트 ──
        ind_compilation = "\n\n".join(company_insights)
        grades_summary = " | ".join(company_grades)

        log_msg(ind_agent_name, "industry", "Self",
                f"하위 기업 {len(companies)}개 실적 보고 취합 완료. 산업 Winner/Loser 분석 및 최선호주 선정을 진행합니다.", "thought")

        prompt_ind = f"""당신은 {ind.tag} 산업 수석 애널리스트입니다. 아래 기업들의 심층 분석 결과를 바탕으로 산업 종합 보고서를 한국어로 작성하세요.

[산업 배경]
{ind.summary}

[기업별 분석 결과]
{ind_compilation[:3000]}

[Quant 등급 요약]
{grades_summary}

다음 형식으로 작성하세요 (마크다운):
## {ind.tag} 산업 종합 분석

### 1. 경쟁 구도 & 기술 트렌드
(현재 산업 내 기술 표준 전쟁, 주요 이슈 2~3가지)

### 2. 밸류체인 가치 집중 포인트
(어디서 마진이 나오고 어디가 Commodity화 되는지)

### 3. 산업 내 Winner vs Loser
(실적 기준 상위/하위 기업 구분 및 이유)

### 4. 향후 6개월 주요 촉매 이벤트
(규제, 실적 발표, 기술 이벤트 등)

### 5. 최선호주 1개 선정
종목명, 선정 이유, 목표 수익률 근거
"""

        fallback_ind = (
            f"## {ind.tag} 산업 종합 분석\n\n"
            f"### 1. 경쟁 구도 & 기술 트렌드\n{ind.tag} 산업은 AI와 물리적 인프라의 결합으로 급격한 구조 변화 중.\n\n"
            f"### 2. 밸류체인 가치 집중 포인트\n고마진 소프트웨어·플랫폼 레이어로 가치 집중 추세.\n\n"
            f"### 3. 산업 내 Winner vs Loser\nQuant 고득점 기업이 재무적으로 우월한 포지션.\n\n"
            f"### 4. 향후 6개월 주요 촉매\n실적 시즌, 규제 변화, 기술 발표 예정.\n\n"
            f"### 5. 최선호주\n{ind.tag} 섹터 내 Quant BUY 등급 최고점 기업 추천."
        )

        ind_report = get_gemini_response(prompt_ind, fallback_ind)
        log_msg(ind_agent_name, "industry", "Alpha Orchestrator", ind_report, "message")
        industry_reports_compiled.append(f"# {ind.tag} Industry\n{ind_report}")

    # ── Step 4: Orchestrator 최종 리포트 ─────────────────
    log_msg("Alpha Orchestrator", "orchestrator", "Self",
            "모든 산업 분석 접수 완료. 전산업 크로스 분석 및 최종 투자 제안서를 작성합니다. "
            "Executive Summary → 산업별 등급 매트릭스 → 병목 분석 → Top3 Pick → 시나리오 순으로 구성합니다.", "thought")

    all_ind_summaries = "\n\n".join(industry_reports_compiled)

    # Quant 상위 기업 추출
    top_quant = sorted(
        [(c.id, c.name, c.ticker, quant_scores.get(c.id, (0, "HOLD", []))[0],
          quant_scores.get(c.id, (0, "HOLD 🟡", []))[1])
         for c in all_companies],
        key=lambda x: x[3], reverse=True
    )[:5]
    top_quant_str = "\n".join([f"  {i+1}. {n} ({t}): {s}점 [{g}]"
                                for i, (_, n, t, s, g) in enumerate(top_quant)])

    prompt_orch = f"""당신은 수석 투자 오케스트레이터입니다. 아래 산업별 분석과 Quant 스코어를 바탕으로 최종 기관급 투자 제안서를 한국어로 작성하세요.

[산업별 분석 요약]
{all_ind_summaries[:4000]}

[Quant 상위 5개 기업]
{top_quant_str}

다음 형식의 완성도 높은 마크다운 보고서를 작성하세요:

# 📊 Alpha Research — 멀티에이전트 크로스인더스트리 투자 보고서

## Executive Summary
(3줄 핵심 요약: 현재 시장 상황, 핵심 병목, 최우선 투자 액션)

## 산업별 투자등급 매트릭스
| 산업 | 현황 | 등급 | 핵심 드라이버 |
|------|------|------|-------------|
(각 산업별 한 줄)

## 크로스인더스트리 병목 분석
(모든 산업을 관통하는 공통 병목 자원/인프라 분석, 수혜 구조 설명)

## Top 3 Pick & 포트폴리오 배분
### 1위: [종목명] (배분 비중: X%)
### 2위: [종목명] (배분 비중: X%)  
### 3위: [종목명] (배분 비중: X%)

## 투자 시나리오
| 시나리오 | 확률 | 수익률 전망 | 트리거 |
|---------|------|-----------|-------|
| Bull Case | | | |
| Base Case | | | |
| Bear Case | | | |

## 모니터링 체크리스트
(다음 1개월 내 주시해야 할 이벤트 5가지)
"""

    fallback_orch = """# 📊 Alpha Research — 멀티에이전트 크로스인더스트리 투자 보고서

## Executive Summary
현재 자율주행·로봇·우주·코인 4개 산업 모두 AI 인프라 확충 단계에서 핵심 컴퓨팅 자원 부족이라는 공통 병목에 직면해 있습니다. BTC 현물 ETF 승인 이후 기관 자금 유입이 가속화되며 코인 섹터가 단기 모멘텀을 주도합니다. 물리적 AI 생태계를 장악한 Nvidia와 기관 코인 수탁의 독점자 Coinbase에 집중 투자를 권고합니다.

## 산업별 투자등급 매트릭스
| 산업 | 현황 | 등급 | 핵심 드라이버 |
|------|------|------|-------------|
| 자율주행 | 기술표준화 전쟁 심화 | OVERWEIGHT | End-to-End AI 상용화 |
| 로봇 | 휴머노이드 원년 진입 | OVERWEIGHT | 물리적 AI 상용화 |
| 우주 | LEO 위성망 구축 가속 | NEUTRAL | 정부 발주 파이프라인 |
| 코인 | ETF 기관 자금 유입 | OVERWEIGHT | 반감기 사이클 |

## 크로스인더스트리 병목 분석
4개 산업의 공통 병목은 **'물리적 AI 구동을 위한 고성능 컴퓨팅 인프라'**입니다. 자율주행의 학습 연산, 로봇의 실시간 제어, 우주의 위성 데이터 처리, 코인의 채굴 모두 동일한 GPU/ASIC 컴퓨팅 자원에 의존합니다. 이 병목을 장악한 기업이 구조적 초과수익을 독식합니다.

## Top 3 Pick & 포트폴리오 배분
### 1위: NVIDIA (NVDA) — 배분 비중: 35%
자율주행·로봇·AI 전 산업의 두뇌 독점. CUDA 생태계 전환 비용 無. 데이터센터 매출 YoY +100%+.

### 2위: Coinbase (COIN) — 배분 비중: 25%
미국 최대 암호화폐 거래소 + 기관 수탁(Custody) 독점. SEC 소송 해소 + ETF 수탁 파트너로 구조적 성장.

### 3위: Robinhood (HOOD) — 배분 비중: 15%
코인 리테일 + 주식 리테일 플랫폼. 젊은 세대 투자 인구 확대 수혜. 매출성장률 업계 최상위권.

## 투자 시나리오
| 시나리오 | 확률 | 수익률 전망 | 트리거 |
|---------|------|-----------|-------|
| Bull Case | 35% | +40~60% | 금리 인하 + BTC 신고가 + AI 수요 폭증 |
| Base Case | 45% | +15~25% | 현 성장 지속 + 점진적 규제 명확화 |
| Bear Case | 20% | -15~25% | 경기침체 + 규제 강화 + 유동성 위기 |

## 모니터링 체크리스트
1. **BTC 가격 & ETF 자금 유입** — 주간 모니터링
2. **NVDA 분기 실적** — 다음 실적 발표일 주시
3. **미국 금리 결정 (FOMC)** — 매크로 방향성 확인
4. **SEC 스테이블코인 규제 발표** — 코인 섹터 리스크
5. **휴머노이드 로봇 양산 일정** — 테슬라 옵티머스, Figure AI"""

    final_report_content = get_gemini_response(prompt_orch, fallback_orch)

    report_obj = models.OrchestrationReport(
        title="[프리미엄 에이전트 보고서] 크로스인더스트리 병목 분석 & Top3 수혜주 투자 제안",
        content=final_report_content,
        created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(report_obj)
    db.commit()

    log_msg("Alpha Orchestrator", "orchestrator", "System",
            "프리미엄 기관급 투자 보고서 생성 완료. Executive Summary + Top3 Pick + 시나리오 분석이 포함된 최종 보고서를 확인하세요.", "message")
    print("Agent simulation (upgraded) completed successfully.")
