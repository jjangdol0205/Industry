from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os, json
from dotenv import load_dotenv
load_dotenv()  # .env 파일에서 환경변수 자동 로드

import models, schemas, database, agent_harness
from openai import OpenAI

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Investment Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# PDF 정적 파일 서빙 (산업 자료 PDF)
# ─────────────────────────────────────────────
RELATIVE_PDF_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "산업자료"))
WINDOWS_PDF_ROOT = r"D:\Industry\산업자료"

if os.path.exists(RELATIVE_PDF_ROOT):
    PDF_ROOT = RELATIVE_PDF_ROOT
elif os.path.exists(WINDOWS_PDF_ROOT):
    PDF_ROOT = WINDOWS_PDF_ROOT
else:
    PDF_ROOT = None

if PDF_ROOT:
    app.mount("/pdfs", StaticFiles(directory=PDF_ROOT), name="pdfs")


# DeepSeek 설정 (OpenAI 호환 API)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
) if DEEPSEEK_API_KEY else None


# 로컬 미리 생성된 한국어 AI 분석 로드
PREGENERATED_ANALYSES_PATH = os.path.join(os.path.dirname(__file__), "pregenerated_ai_analyses.json")
pregenerated_analyses = {}
if os.path.exists(PREGENERATED_ANALYSES_PATH):
    try:
        with open(PREGENERATED_ANALYSES_PATH, "r", encoding="utf-8") as f:
            pregenerated_analyses = json.load(f)
        print(f"Loaded {len(pregenerated_analyses)} pregenerated company analyses.")
    except Exception as e:
        print("Failed to load pregenerated analyses:", e)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────
# Industry Reports
# ─────────────────────────────────────────────

@app.get("/api/reports", response_model=List[schemas.IndustryReport])
def get_reports(db: Session = Depends(get_db)):
    return db.query(models.IndustryReport).all()

@app.get("/api/reports/{report_id}", response_model=schemas.IndustryReport)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.IndustryReport).filter(models.IndustryReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.get("/api/reports/{report_id}/pdf_url")
def get_report_pdf_url(report_id: int, db: Session = Depends(get_db)):
    """산업 PDF URL 반환 — 프론트엔드 iframe 연동용"""
    report = db.query(models.IndustryReport).filter(models.IndustryReport.id == report_id).first()
    if not report or not report.file_path:
        return {"pdf_url": None, "file_name": None}
    fp = report.file_path.replace('\\', '/')
    # 산업자료/ 이후 상대 경로 추출
    marker = '산업자료/'
    idx = fp.find(marker)
    if idx >= 0:
        rel = fp[idx + len(marker):]
        return {"pdf_url": f"/pdfs/{rel}", "file_name": rel.split('/')[-1]}
    return {"pdf_url": None, "file_name": None}


# ─────────────────────────────────────────────
# Companies
# ─────────────────────────────────────────────

@app.get("/api/companies", response_model=List[schemas.Company])
def get_companies(db: Session = Depends(get_db)):
    return db.query(models.Company).all()

@app.get("/api/companies/{company_id}", response_model=schemas.Company)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@app.get("/api/companies/{company_id}/profile")
def get_company_profile(company_id: int, db: Session = Depends(get_db)):
    """
    회사의 기관급 밸류에이션·프로파일 데이터 반환
    P/E, P/B, EV/EBITDA, ROE, ROA, GPM, OPM, 배당수익률 등
    description은 DeepSeek으로 번역 후 DB 캐시
    """
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    profile = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == company_id).first()

    # ── 한국어 번역 (없으면 DeepSeek으로 생성 후 저장) ──────────
    description_ko = None
    if profile and profile.description:
        if profile.description_ko:
            description_ko = profile.description_ko
        elif deepseek_client:
            try:
                trans = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a professional Korean translator. Translate the following company description into natural Korean. Return ONLY the translated text, no explanation."},
                        {"role": "user", "content": profile.description}
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                )
                description_ko = trans.choices[0].message.content.strip()
                # DB에 저장 (캐시)
                profile.description_ko = description_ko
                db.commit()
            except Exception:
                description_ko = None

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "ticker": company.ticker,
            "role_description": company.role_description,
            "future_growth": company.future_growth,
        },
        "profile": {
            # 기본 정보
            "sector": profile.sector if profile else None,
            "industry": profile.industry_classification if profile else None,
            "description": profile.description if profile else None,
            "description_ko": description_ko,
            "ceo": profile.ceo if profile else None,
            "employees": profile.employees if profile else None,
            "website": profile.website if profile else None,
            # 시장 데이터
            "market_cap": profile.market_cap if profile else None,
            "current_price": profile.current_price if profile else None,
            "beta": profile.beta if profile else None,
            # 밸류에이션
            "pe_ratio": profile.pe_ratio if profile else None,
            "pb_ratio": profile.pb_ratio if profile else None,
            "ev_ebitda": profile.ev_ebitda if profile else None,
            "ev_sales": profile.ev_sales if profile else None,
            "dcf_value": profile.dcf_value if profile else None,
            # 수익성
            "roe": profile.roe if profile else None,
            "roa": profile.roa if profile else None,
            "roic": profile.roic if profile else None,
            "gross_margin_ttm": profile.gross_margin_ttm if profile else None,
            "op_margin_ttm": profile.op_margin_ttm if profile else None,
            "net_margin_ttm": profile.net_margin_ttm if profile else None,
            "ebitda_margin_ttm": profile.ebitda_margin_ttm if profile else None,
            # 성장성
            "revenue_growth": profile.revenue_growth if profile else None,
            "eps_growth": profile.eps_growth if profile else None,
            "fcf_growth": profile.fcf_growth if profile else None,
            # 재무건전성
            "current_ratio": profile.current_ratio if profile else None,
            "debt_to_equity": profile.debt_to_equity if profile else None,
            "net_debt_to_ebitda": profile.net_debt_to_ebitda if profile else None,
            # 주주환원
            "dividend_yield": profile.dividend_yield if profile else None,
            "payout_ratio": profile.payout_ratio if profile else None,
            "last_updated": profile.last_updated if profile else None,
        }
    }


@app.get("/api/companies/{company_id}/financials")
def get_company_financials(
    company_id: int,
    period_type: Optional[str] = None,  # "annual" or "quarterly"
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    연간/분기 재무제표 반환 (손익 + 재무상태표 + 현금흐름 통합)
    """
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    query = db.query(models.FinancialData).filter(models.FinancialData.company_id == company_id)
    if period_type:
        query = query.filter(models.FinancialData.period_type == period_type)
    
    financials = query.order_by(models.FinancialData.date.desc()).limit(limit).all()
    financials = list(reversed(financials))  # 차트용 asc 재정렬 (최신 데이터 포함 보장)
    
    result = []
    for f in financials:
        result.append({
            "date": f.date,
            "period_type": f.period_type,
            "fiscal_year": f.fiscal_year,
            # 손익
            "revenue": f.revenue,
            "gross_profit": f.gross_profit,
            "operating_income": f.operating_income,
            "ebitda": f.ebitda,
            "net_income": f.net_income,
            "eps": f.eps,
            # 마진율
            "gross_margin": f.gross_margin,
            "op_margin": f.op_margin,
            "net_margin": f.net_margin,
            "ebitda_margin": f.ebitda_margin,
            # 성장률
            "revenue_growth_yoy": f.revenue_growth_yoy,
            "op_income_growth_yoy": f.op_income_growth_yoy,
            "eps_growth_yoy": f.eps_growth_yoy,
            # 재무상태표
            "total_assets": f.total_assets,
            "total_current_assets": f.total_current_assets,
            "cash_and_equivalents": f.cash_and_equivalents,
            "total_debt": f.total_debt,
            "shareholders_equity": f.shareholders_equity,
            "net_debt": f.net_debt,
            # 재무건전성
            "current_ratio": f.current_ratio,
            "debt_to_equity_ratio": f.debt_to_equity_ratio,
            # 현금흐름
            "operating_cash_flow": f.operating_cash_flow,
            "capital_expenditure": f.capital_expenditure,
            "free_cash_flow": f.free_cash_flow,
            # 수익성
            "roe": f.roe,
            "roa": f.roa,
            "fcf_margin": f.fcf_margin,
        })
    
    return {"ticker": company.ticker, "name": company.name, "financials": result}


@app.post("/api/companies/{company_id}/sync")
def sync_company_full(company_id: int, db: Session = Depends(get_db)):
    """
    기관급 데이터 최신화 (프로파일 + 풀 재무제표 재수집)
    """
    from comprehensive_fetcher import fetch_full_company_data
    
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    full_data = fetch_full_company_data(company.ticker)
    
    # Update profile
    db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == company_id).delete()
    if full_data["profile"]:
        allowed_keys = {c.name for c in models.CompanyProfile.__table__.columns} - {'id', 'company_id'}
        clean_profile = {k: v for k, v in full_data["profile"].items() if k in allowed_keys}
        db.add(models.CompanyProfile(company_id=company_id, **clean_profile))
    
    # Update financials
    db.query(models.FinancialData).filter(models.FinancialData.company_id == company_id).delete()
    for f in full_data["financials"]:
        allowed_fin = {c.name for c in models.FinancialData.__table__.columns} - {'id', 'company_id'}
        clean_f = {k: v for k, v in f.items() if k in allowed_fin}
        db.add(models.FinancialData(company_id=company_id, **clean_f))
    
    db.commit()
    return {"message": f"Synced {company.ticker} with institutional-grade data", "source": full_data["source"]}


@app.get("/api/companies/{company_id}/price")
def get_company_price(company_id: int, db: Session = Depends(get_db)):
    """
    실시간 주가 조회 (yfinance) — 빠른 가격 갱신 전용
    DB의 CompanyProfile을 업데이트하고 현재 가격 반환
    """
    import yfinance as yf
    
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        ticker = yf.Ticker(company.ticker)
        info = ticker.info
        
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        market_cap = info.get("marketCap")
        pe_ratio = info.get("trailingPE")
        
        # DB 업데이트
        profile = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == company_id).first()
        if profile and price:
            profile.current_price = price
            if market_cap:
                profile.market_cap = market_cap
            if pe_ratio:
                profile.pe_ratio = pe_ratio
            from datetime import datetime
            profile.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
            db.commit()
        
        return {
            "ticker": company.ticker,
            "name": company.name,
            "current_price": price,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "updated": True,
        }
    except Exception as e:
        return {"ticker": company.ticker, "error": str(e), "updated": False}


@app.get("/api/companies/{company_id}/ai-analysis")
def get_company_ai_analysis(company_id: int, db: Session = Depends(get_db)):
    """Gemini AI 심층 기업 분석: 비즈니스 모델 / 수익 구조 / 비용 구조 / 해자 / 리스크 / 투자 포인트"""
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # 1. 로컬에 미리 생성된 데이터가 있으면 즉시 반환
    cid_str = str(company_id)
    if cid_str in pregenerated_analyses:
        res = dict(pregenerated_analyses[cid_str])
        res["ticker"] = company.ticker
        res["company_name"] = company.name
        res["generated_by"] = "antigravity"
        return res

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
        f"기업명: {company.name} ({company.ticker})\n"
        f"산업: {industry_title}\n"
        f"밸류체인 포지션: {vc_name}\n"
        f"섹터: {p.sector if p else 'N/A'} / 업종: {p.industry_classification if p else 'N/A'}\n"
        f"임직원: {p.employees if p else 'N/A'}명 | 시가총액: {mktcap}\n\n"
        f"[회사 설명]\n{p.description[:1000] if p and p.description else 'N/A'}\n\n"
        f"[밸류체인 내 역할]\n{company.role_description}\n\n"
        f"[미래 성장 포인트]\n{company.future_growth}\n\n"
        f"[핵심 재무 지표 TTM]\n"
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
        "You are a senior Wall Street equity analyst specializing in deep-dive business model analysis.\n"
        "Analyze the company below and produce a DETAILED structured report entirely in KOREAN.\n"
        "Each text field must be 4-6 sentences minimum with specifics. No vague generic statements.\n\n"
        + context
        + "\n\nOutput ONLY valid JSON (no markdown, no code block):\n"
        + json_template
    )

    try:
        if not deepseek_client:
            raise ValueError("DEEPSEEK_API_KEY not set")
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a senior Wall Street equity analyst. Always respond in valid JSON format only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        text = response.choices[0].message.content.strip()
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
        result["generated_by"] = "deepseek"
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
