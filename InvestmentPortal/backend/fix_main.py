import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Keep everything up to (but not including) the first ai-analysis decorator
cut_marker = '@app.get("/api/companies/{company_id}/ai-analysis")'
idx = content.find(cut_marker)
clean_top = content[:idx]

# New bottom section
new_bottom = '''@app.get("/api/companies/{company_id}/ai-analysis")
def get_company_ai_analysis(company_id: int, db: Session = Depends(get_db)):
    """Gemini AI 심층 기업 분석: 비즈니스 모델 / 수익 구조 / 비용 구조 / 해자 / 리스크 / 투자 포인트"""
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    profile = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == company_id).first()
    industry = db.query(models.IndustryReport).filter(models.IndustryReport.id == company.industry_id).first()
    vc_node = db.query(models.ValueChainNode).filter(models.ValueChainNode.id == company.value_chain_node_id).first()

    p = profile
    gpm = f"{(p.gross_margin_ttm*100):.1f}%" if p and p.gross_margin_ttm is not None else "N/A"
    opm = f"{(p.op_margin_ttm*100):.1f}%" if p and p.op_margin_ttm is not None else "N/A"
    npm = f"{(p.net_margin_ttm*100):.1f}%" if p and p.net_margin_ttm is not None else "N/A"
    roe = f"{(p.roe*100):.1f}%" if p and p.roe is not None else "N/A"
    rev_growth = f"{(p.revenue_growth*100):.1f}%" if p and p.revenue_growth is not None else "N/A"
    mktcap = f"${(p.market_cap/1e9):.1f}B" if p and p.market_cap else "N/A"

    industry_title = industry.title if industry else "해당 산업"
    vc_name = vc_node.node_name if vc_node else "N/A"

    context = (
        f"기업명: {company.name} ({company.ticker})\\n"
        f"산업: {industry_title}\\n"
        f"밸류체인 포지션: {vc_name}\\n"
        f"섹터: {p.sector if p else 'N/A'} / 업종: {p.industry_classification if p else 'N/A'}\\n"
        f"임직원: {p.employees if p else 'N/A'}명 | 시가총액: {mktcap}\\n\\n"
        f"[회사 설명]\\n{p.description[:1000] if p and p.description else 'N/A'}\\n\\n"
        f"[밸류체인 내 역할]\\n{company.role_description}\\n\\n"
        f"[미래 성장 포인트]\\n{company.future_growth}\\n\\n"
        f"[핵심 재무 지표 TTM]\\n"
        f"GPM: {gpm} / OPM: {opm} / NPM: {npm} / ROE: {roe} / 매출성장률: {rev_growth}"
    )

    json_template = """{{
  "what_they_sell": "핵심 제품/서비스를 구체적으로 설명. 주력 제품명, 고객층(정부/기업/개인), 시장 포지셔닝, 차별화 포인트를 4-5문장.",
  "revenue_model": "수익원을 구분(하드웨어/SW 라이선스/구독/정부 계약/데이터 판매 등). 각 수익원 비중과 마진, 반복수익 비율, 계약 구조, 고객 락인 구조를 4-5문장.",
  "cost_structure": "COGS, R&D, SG&A, CapEx 각각의 비중과 특성 서술. 고정비 vs 변동비, 핵심 원가 드라이버, 규모 성장 시 마진 개선 가능성을 4-5문장.",
  "how_they_profit": "이익을 남기는 구조 설명. 핵심 마진 드라이버, 영업 레버리지 작동 방식, FCF 전환율, ROIC/ROE 관점 자본효율성을 4-5문장.",
  "competitive_moat": "경제적 해자 유형(특허/IP, 네트워크 효과, 규모의 경제, 전환비용, 브랜드, 규제 라이선스)을 명시. 해자 강도와 경쟁사가 극복 어려운 이유를 구체적 수치/사례로 5문장 이상.",
  "key_segments": [
    {{"name": "사업부 명칭", "description": "매출 비중 추정, 성장률, 마진 특성 한 문장"}}
  ],
  "risk_factors": "3가지 핵심 리스크를 유형(경쟁/규제/기술/매크로/재무) 명시하며 구분. 각 리스크 실현 시 기업가치 영향과 대응 가능성 포함 5-6문장.",
  "investment_thesis": "왜 지금 매력적인가? 산업 트렌드(TAM 성장/정책 수혜/기술 전환)와 시장 지위 연결. 구체적 촉매(신제품/수주/규제/M&A)와 Risk/Reward 밸류에이션 논거 5-6문장.",
  "industry_connection": "INDUSTRY_TITLE_PLACEHOLDER 구조적 성장 트렌드(시장 규모/성장률/정책 동향) 제시 후, 이 기업의 밸류체인 포지션과 산업 성장 수혜 방식, 경쟁사 대비 우위를 5문장."
}}"""

    json_template = json_template.replace("INDUSTRY_TITLE_PLACEHOLDER", industry_title)

    prompt = (
        "You are a senior Wall Street equity analyst specializing in deep-dive business model analysis.\\n"
        "Analyze the company below and produce a DETAILED structured report entirely in KOREAN.\\n"
        "Each text field must be 4-6 sentences minimum with specifics. No vague generic statements.\\n\\n"
        + context
        + "\\n\\nOutput ONLY valid JSON (no markdown, no code block):\\n"
        + json_template
    )

    try:
        if not GEMINI_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set")
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if part.startswith("json"):
                    text = part[4:].strip()
                    break
                elif "{" in part:
                    text = part.strip()
                    break
        result = json.loads(text)
        result["ticker"] = company.ticker
        result["company_name"] = company.name
        result["generated_by"] = "gemini"
        return result
    except Exception as e:
        return {
            "ticker": company.ticker,
            "company_name": company.name,
            "generated_by": "fallback",
            "what_they_sell": (p.description[:800] + "...") if p and p.description else company.role_description,
            "revenue_model": company.role_description,
            "cost_structure": f"GPM {gpm} / OPM {opm} 기준. R&D 집중 투자 기업으로 영업비용 비중이 높습니다.",
            "how_they_profit": f"순이익률 {npm}, ROE {roe} 수준의 수익성을 유지하고 있습니다.",
            "competitive_moat": company.future_growth,
            "key_segments": [{"name": p.industry_classification if p else "핵심사업", "description": company.role_description}],
            "risk_factors": "시장 경쟁 심화, 매크로 경기 변동, 기술 전환 리스크가 존재합니다.",
            "investment_thesis": company.future_growth,
            "industry_connection": f"{industry_title} 성장의 핵심 수혜주로 포지셔닝되어 있습니다.",
            "error": str(e)
        }


# ─────────────────────────────────────────────
# PDF 파일 목록 스캔 API
# ─────────────────────────────────────────────

@app.get("/api/pdfs")
def list_pdfs():
    """산업자료 폴더를 스캔하여 카테고리별 PDF 목록 반환"""
    result = []
    if not os.path.exists(PDF_ROOT):
        return result
    for category in sorted(os.listdir(PDF_ROOT)):
        cat_path = os.path.join(PDF_ROOT, category)
        if not os.path.isdir(cat_path):
            continue
        files = []
        for fname in sorted(os.listdir(cat_path)):
            if fname.lower().endswith(".pdf"):
                from urllib.parse import quote
                rel = f"{category}/{fname}"
                url = f"/pdfs/{quote(rel)}"
                files.append({
                    "name": fname.replace(".pdf", ""),
                    "filename": fname,
                    "url": url,
                    "category": category,
                })
        if files:
            result.append({"category": category, "files": files})
    return result


# ─────────────────────────────────────────────

@app.get("/api/agents")
def get_agents(db: Session = Depends(get_db)):
    agent_harness.initialize_agents(db)
    return db.query(models.Agent).all()


def run_simulation_bg():
    db = database.SessionLocal()
    try:
        agent_harness.run_agent_simulation(db)
    finally:
        db.close()


@app.post("/api/agents/run")
def run_simulation(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_simulation_bg)
    return {"status": "running", "message": "Multi-agent analysis triggered."}


@app.get("/api/agents/messages")
def get_agent_messages(db: Session = Depends(get_db)):
    return db.query(models.AgentMessage).order_by(models.AgentMessage.id.asc()).all()


@app.get("/api/orchestration/report")
def get_latest_report(db: Session = Depends(get_db)):
    report = db.query(models.OrchestrationReport).order_by(models.OrchestrationReport.id.desc()).first()
    if not report:
        return {"title": "보고서 없음", "content": "* 분석 시뮬레이션을 가동하면 여기에 결과 리포트가 생성됩니다."}
    return report
'''

final = clean_top + new_bottom

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(final)

print(f"Done. New file has {final.count(chr(10))} lines.")
print(f"ai-analysis count: {final.count('@app.get(\"/api/companies/{company_id}/ai-analysis\")')}")
