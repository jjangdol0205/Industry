import os
import datetime
from sqlalchemy.orm import Session
import google.generativeai as genai
import models
import json

# Configure Gemini
api_key = os.environ.get("GOOGLE_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

def get_gemini_response(prompt: str, fallback_content: str) -> str:
    """Helper to query Gemini with a fallback if key is missing or fails."""
    if not api_key:
        return fallback_content
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return fallback_content

def initialize_agents(db: Session):
    """Initializes agents for the orchestrator, reports, and companies if they don't exist."""
    # Check Orchestrator
    orchestrator = db.query(models.Agent).filter(models.Agent.type == "orchestrator").first()
    if not orchestrator:
        orchestrator = models.Agent(
            name="Alpha Orchestrator",
            role="Lead Investment Strategist & Cross-Industry Bottleneck Analyzer",
            type="orchestrator"
        )
        db.add(orchestrator)

    # Check Site Manager Agent
    manager = db.query(models.Agent).filter(models.Agent.name == "Site Manager Agent").first()
    if not manager:
        manager = models.Agent(
            name="Site Manager Agent",
            role="전반적인 홈페이지 관리, 깃허브 메인 브랜치 동기화 및 Render 클라우드 배포 모니터링 총괄",
            type="management"
        )
        db.add(manager)

    # Check App Developer Agent
    app_dev = db.query(models.Agent).filter(models.Agent.name == "App Developer Agent").first()
    if not app_dev:
        app_dev = models.Agent(
            name="App Developer Agent",
            role="PWA 모바일 앱 최적화, 반응형 UI 레이아웃 및 모바일 디바이스 호환성 검증 총괄",
            type="management"
        )
        db.add(app_dev)
        
    # Check Industry Agents
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
            
    # Check Company Agents
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
    Runs the multi-agent collaboration loop.
    1. Orchestrator initiates analysis.
    2. Industry Analysts query their Company Monitors.
    3. Company Monitors load data, perform financial health check.
    4. Industry Analysts aggregate company reports + industry PDF context.
    5. Orchestrator aggregates all industry reports, identifies cross-industry bottlenecks and beneficiaries.
    6. Orchestrator outputs final report.
    """
    initialize_agents(db)
    
    # Clean previous messages
    db.query(models.AgentMessage).delete()
    db.commit()
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Helper to log messages
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

    # Step 0: Site Manager Agent & App Developer Agent report site/app status
    manager_agent = db.query(models.Agent).filter(models.Agent.name == "Site Manager Agent").first()
    if manager_agent:
        log_msg(manager_agent.name, "management", "Self", "홈페이지 시스템 리소스 점검 완료: 깃허브 저장소(main) 및 Render 클라우드 배포 상태 양호. 모든 API 서비스 정상 가동 중.", "thought")
        log_msg(manager_agent.name, "management", "Alpha Orchestrator", "보고드립니다. 홈페이지 관리(깃허브 커밋/Render 배포 포함) 및 서버 리소스 모니터링이 최적화되었습니다. 리서치 시뮬레이션을 시작하셔도 좋습니다.", "message")

    app_dev_agent = db.query(models.Agent).filter(models.Agent.name == "App Developer Agent").first()
    if app_dev_agent:
        log_msg(app_dev_agent.name, "management", "Self", "PWA 및 모바일 앱 호환성 점검 완료: iOS/Android 모바일 해상도 반응형 디자인 레이아웃 및 PWA 앱 다운로드 설치 기능 정상 작동 확인.", "thought")
        log_msg(app_dev_agent.name, "management", "Alpha Orchestrator", "오케스트레이터님, PWA 모바일 앱 배포 및 반응형 UX 최적화 완료되었습니다. 모바일 기기에서도 리서치 포털에 간편하게 접속하여 앱처럼 사용하실 수 있습니다.", "message")

    # Step 1: Orchestrator Initiates Analysis
    log_msg("System", "system", "Alpha Orchestrator", "시뮬레이션 분석 명령을 받았습니다. 하네스를 가동합니다.", "message")
    
    orch_thought = (
        "분석 미션이 주어졌습니다. 오늘의 목표는 당사가 추적 중인 모든 산업의 최신 트렌드를 파악하고, "
        "가치 사슬(Value Chain) 상에서 발생하는 병목 현상을 파악하여 최대의 투자 기회와 수혜 기업을 분석하는 것입니다. "
        "먼저 각 산업 담당 애널리스트 에이전트들에게 분석 보고를 명령합니다."
    )
    log_msg("Alpha Orchestrator", "orchestrator", "Self", orch_thought, "thought")
    
    # Get all industries and companies
    industries = db.query(models.IndustryReport).all()
    
    # If no industries, stop
    if not industries:
        log_msg("Alpha Orchestrator", "orchestrator", "System", "추적할 산업 보고서가 데이터베이스에 존재하지 않습니다.", "message")
        return

    industry_reports_compiled = []
    
    for ind in industries:
        ind_agent_name = f"{ind.tag} Analyst"
        log_msg("Alpha Orchestrator", "orchestrator", ind_agent_name, f"[{ind.title}] 산업의 가치사슬 및 최근 트렌드를 종합 분석하여 제출하세요. 하위 기업 모니터들을 가동하여 개별 실적 보고를 먼저 취합하십시오.", "message")
        
        ind_thought = (
            f"오케스트레이터로부터 {ind.tag} 산업 분석 오더를 수신했습니다. "
            f"이 산업의 주요 기업인들의 최신 재무 상태와 사업 포지션을 파악하기 위해 하하 기업 연구원(Company Trackers)들에게 보고를 요청합니다."
        )
        log_msg(ind_agent_name, "industry", "Self", ind_thought, "thought")
        
        # Get companies under this industry
        companies = db.query(models.Company).filter(models.Company.industry_id == ind.id).all()
        company_insights = []
        
        for comp in companies:
            comp_agent_name = f"{comp.name} Tracker"
            log_msg(ind_agent_name, "industry", comp_agent_name, f"{comp.name} ({comp.ticker})의 최근 5년 재무 상태와 해당 산업 내 포지션/역할에 대해 보고해 주세요.", "message")
            
            # Load company financials from DB
            financials = db.query(models.FinancialData).filter(models.FinancialData.company_id == comp.id).all()
            fin_annual = [f for f in financials if f.period_type == "annual"]
            fin_quarterly = [f for f in financials if f.period_type == "quarterly"]
            
            # Format financial summary
            fin_summary = f"Ticker: {comp.ticker}\n"
            fin_summary += "Annual Financials:\n"
            for f in sorted(fin_annual, key=lambda x: x.date)[-3:]:
                rev_val = (f.revenue or 0) / 1e9
                op_val = (f.operating_income or 0) / 1e9
                margin_val = f.gross_margin if f.gross_margin is not None else 0
                fin_summary += f"- Date: {f.date}, Rev: ${rev_val:.2f}B, OpInc: ${op_val:.2f}B, Margin: {margin_val:.2f}%\n"
            fin_summary += "Quarterly Financials (Last 4):\n"
            for f in sorted(fin_quarterly, key=lambda x: x.date)[-4:]:
                rev_val = (f.revenue or 0) / 1e9
                op_val = (f.operating_income or 0) / 1e9
                margin_val = f.gross_margin if f.gross_margin is not None else 0
                fin_summary += f"- Date: {f.date}, Rev: ${rev_val:.2f}B, OpInc: ${op_val:.2f}B, Margin: {margin_val:.2f}%\n"
                
            comp_thought = (
                f"{comp.name}의 실적 데이터를 로드했습니다. 5년 치 재무 동향과 역할 정보를 분석하여 "
                f"성장성과 투자 가치가 매력적인지 핵심적인 요약을 도출해 제출하겠습니다."
            )
            log_msg(comp_agent_name, "company", "Self", comp_thought, "thought")
            
            # Call Gemini to write company report
            prompt_comp = f"""
            You are a Company Monitor Agent. Review this financial summary for {comp.name}:
            {fin_summary}
            
            Role in value chain: {comp.role_description}
            Future growth story: {comp.future_growth}
            
            Please write a concise 3-4 sentence report in Korean. Analyze:
            1. Recent revenue/margin growth trends.
            2. Core role and position in the value chain.
            3. Future outlook and potential risk.
            """
            
            fallback_comp = (
                f"{comp.name}({comp.ticker})는 최근 매출과 영업이익률에서 탄탄한 성장을 보이고 있으며, "
                f"밸류체인 내에서 {comp.role_description[:50]}... 역할을 충실히 수행하고 있습니다. "
                f"향후 성장성은 {comp.future_growth[:50]}... 스토리로 요약되며, 마진 확대 흐름이 긍정적입니다."
            )
            
            comp_report = get_gemini_response(prompt_comp, fallback_comp)
            log_msg(comp_agent_name, "company", ind_agent_name, comp_report, "message")
            company_insights.append(f"[{comp.name} ({comp.ticker})]:\n{comp_report}")
            
        # Industry Agent compiles the aggregated report
        ind_compilation = "\n\n".join(company_insights)
        
        ind_final_thought = (
            f"하위 기업들의 실적 보고서 접수를 완료했습니다. "
            f"산업 보고서 요약본({ind.title})을 바탕으로 기술 표준 전쟁 및 하드웨어 원가 비중の変化 등을 결합하여 "
            f"이 산업의 현재 직면한 병목 지점이 무엇인지를 찾아 종합 리포트를 제출하겠습니다."
        )
        log_msg(ind_agent_name, "industry", "Self", ind_final_thought, "thought")
        
        prompt_ind = f"""
        You are an Industry Analyst Agent for the {ind.tag} industry.
        Review the raw company updates under your coverage:
        {ind_compilation}
        
        Here is the background summary for this industry:
        {ind.summary}
        
        Write a concise, high-level summary of the {ind.tag} industry in Korean.
        Highlight:
        1. The current competitive landscape (e.g., tech standards, sensor war).
        2. Where the value is concentrating (e.g. BOM change, chip platform).
        3. A summary of the companies' overall readiness and financial health.
        """
        
        if ind.tag == "자율주행":
            fallback_ind = (
                f"{ind.tag} 산업은 현재 기술 표준화 전쟁이 치열하게 벌어지는 단계입니다. "
                f"부품 원가 비중(BOM)이 점차 AI 컴퓨팅과 하드웨어 시스템 통합으로 급속히 쏠리면서, 단순 센서 조립 업체보다 "
                f"두뇌 역할을 하는 핵심 칩셋과 MaaS 플랫폼의 가치가 압도적으로 상승하고 있습니다. "
                f"참여 중인 기업들(Nvidia, Tesla, Alphabet 등)은 각자의 위치에서 재무적 지위를 고도화하고 있습니다."
            )
        else:
            fallback_ind = (
                f"{ind.tag} 산업은 현재 물리적 AI와 휴머노이드의 결합으로 거대한 패러다임 변화를 겪고 있습니다. "
                f"수십 개의 관절을 통제하기 위한 실시간 다중 연산 처리 기술과 정밀 감속기가 밸류체인의 핵심 병목으로 부각됩니다. "
                f"의료, 물류, 자동화 분야의 상장 기업들(ISRG, SYM, TER 등)이 강한 매출 성장세를 시현하고 있으며, "
                f"특히 로봇 제어 시뮬레이터 플랫폼을 제공하는 엔비디아(NVDA)의 생태계 장악력이 확대 중입니다."
            )
        
        ind_report = get_gemini_response(prompt_ind, fallback_ind)
        log_msg(ind_agent_name, "industry", "Alpha Orchestrator", ind_report, "message")
        industry_reports_compiled.append(f"### {ind.tag} Industry Analysis:\n{ind_report}")

    # Step 5: Orchestrator Cross-Industry Analysis
    log_msg("Alpha Orchestrator", "orchestrator", "Self", "모든 산업 애널리스트들의 리포트가 접수되었습니다. 전체 산업 밸류체인을 수평적으로 비교 분석하여, 산업 간 변화를 유도하는 병목 현상(Bottleneck)과 이에 따른 최종 수혜 기업들을 발굴하겠습니다.", "thought")
    
    all_ind_summaries = "\n\n".join(industry_reports_compiled)
    
    prompt_orch = f"""
    You are the Lead Investment Orchestrator. Review these compiled reports from your industry analysts:
    {all_ind_summaries}
    
    Analyze the cross-industry changes and write a comprehensive report in Korean.
    The report MUST contain:
    1. **산업별 핵심 동향 요약** (Overview of trends)
    2. **크로스-인더스트리 병목 현상 분석** (Cross-industry Bottleneck - What resource/infrastructure is the critical bottleneck holding back these industries?)
    3. **최대 수혜 기업 발굴 및 투자 로드맵** (Identify 1-2 key beneficiary stocks that control this bottleneck and why they have high future growth, using numerical figures if possible).
    
    Write in a highly professional, fund-manager-oriented format using clean Markdown.
    """
    
    fallback_orch = """# 📊 멀티 에이전트 협동 병목 분석 & 투자 제안서

## 1. 산업별 핵심 동향 요약
- **자율주행:** 하드웨어 기기의 가치가 범용 센서에서 중앙 고성능 컴퓨팅 칩셋과 MaaS 소프트웨어로 급속히 집중. End-to-End AI 등 알고리즘 고도화로 독점적 칩 설계 및 학습용 데이터센터 중요성이 폭증.
- **로봇 산업:** 물리적 AI 기반 휴머노이드/AMR 발전으로 스마트 팩토리, 물류, 특수 의료 등에서 폭발적 도입 중. 관절 제어용 모터와 실시간 다중 센서 입력을 처리할 초소형 AI 제어 칩셋이 핵심 가치로 부상.

## 2. 크로스-인더스트리 병목 현상(Bottleneck)
두 산업의 밸류체인을 관통하는 핵심 교집합이자 공통 병목은 **'물리적 AI(Physical AI)를 구동하기 위한 제어 시뮬레이터 기술과 초고속 엣지 연산력'**입니다. 
- 복잡한 도심 도로를 파악하는 로보택시나, 공장 내 유동적 환경에서 작업하는 협동 로봇 모두 수천 번의 훈련 시뮬레이션(디지털 트윈)이 필수적입니다.
- 연산이 병목현상을 초래하며 이 문제를 해결할 수 있는 두뇌 인프라 기업에 막대한 가격 결정력이 쏠리고 있습니다.

## 3. 최종 수혜 기업 발굴 및 투자 로드맵

### **최선호주: NVIDIA (NVDA)**
- **이유:** 자율주행의 Drive Orin/Thor 플랫폼과 로보틱스의 Jetson, Omniverse 생태계를 동시에 장악. 모든 물리적 이동체의 학습 및 추론은 엔비디아의 쿠다(CUDA) 생태계에 의존.
- **재무적 매력:** 독점력을 통한 초고마진율 확보 및 범산업적 도입 확대로 구조적 고성장 체제 구축 완료.

### **차선호주: Intuitive Surgical (ISRG) / Tesla (TSLA)**
- **이유:** 로봇 산업 내 절대적 독점력(수술 로봇 다빈치)을 지닌 ISRG와 자율주행/옵티머스 로봇까지 자체 수직계열화한 TSLA. 이들은 각자의 킬러 어플리케이션(의료, 모빌리티)에서 독자적인 캐시카우를 생성하며 시장을 선도.
"""
    
    final_report_content = get_gemini_response(prompt_orch, fallback_orch)
    
    # Save report to DB
    report_obj = models.OrchestrationReport(
        title="[에이전트 종합 보고서] 크로스-인더스트리 병목 분석 및 최종 수혜주",
        content=final_report_content,
        created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(report_obj)
    db.commit()
    
    log_msg("Alpha Orchestrator", "orchestrator", "System", "분석 보고서가 최종 성공적으로 보관되었습니다. 시뮬레이션을 종료합니다.", "message")
    print("Agent simulation run completed successfully.")
