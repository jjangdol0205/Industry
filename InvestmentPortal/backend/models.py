from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from database import Base

class IndustryReport(Base):
    __tablename__ = "industry_reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    summary = Column(Text)
    file_path = Column(String)
    tag = Column(String, index=True, default="일반")
    
    value_chains = relationship("ValueChainNode", back_populates="industry")
    companies = relationship("Company", back_populates="industry")

class ValueChainNode(Base):
    __tablename__ = "value_chain_nodes"

    id = Column(Integer, primary_key=True, index=True)
    industry_id = Column(Integer, ForeignKey("industry_reports.id"))
    node_name = Column(String)
    description = Column(Text)
    
    industry = relationship("IndustryReport", back_populates="value_chains")
    companies = relationship("Company", back_populates="value_chain_node")

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    industry_id = Column(Integer, ForeignKey("industry_reports.id"))
    value_chain_node_id = Column(Integer, ForeignKey("value_chain_nodes.id"), nullable=True)
    
    name = Column(String, index=True)
    ticker = Column(String, index=True)
    role_description = Column(Text)
    future_growth = Column(Text)
    
    industry = relationship("IndustryReport", back_populates="companies")
    value_chain_node = relationship("ValueChainNode", back_populates="companies")
    financials = relationship("FinancialData", back_populates="company")
    profile = relationship("CompanyProfile", back_populates="company", uselist=False)


class CompanyProfile(Base):
    """TTM 기준 밸류에이션·프로파일 (FMP API)"""
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), unique=True)

    # --- 회사 기본 정보 ---
    sector = Column(String, nullable=True)          # 섹터 (Technology, Healthcare 등)
    industry_classification = Column(String, nullable=True)  # 세부 업종
    description = Column(Text, nullable=True)       # 10-K 기반 심층 비즈니스 설명 (영어 원문)
    description_ko = Column(Text, nullable=True)    # 한국어 번역
    ceo = Column(String, nullable=True)             # CEO 이름
    employees = Column(Integer, nullable=True)       # 임직원 수
    website = Column(String, nullable=True)

    # --- 시장 데이터 ---
    market_cap = Column(Float, nullable=True)       # 시가총액 (USD)
    current_price = Column(Float, nullable=True)    # 현재 주가
    beta = Column(Float, nullable=True)             # 베타 (시장 민감도)

    # --- 밸류에이션 (TTM) ---
    pe_ratio = Column(Float, nullable=True)         # PER (주가수익비율)
    pb_ratio = Column(Float, nullable=True)         # PBR (주가순자산비율)
    ps_ratio = Column(Float, nullable=True)         # PSR (주가매출비율)
    ev_ebitda = Column(Float, nullable=True)        # EV/EBITDA
    ev_sales = Column(Float, nullable=True)         # EV/Sales
    dcf_value = Column(Float, nullable=True)        # FMP DCF 내재가치

    # --- 수익성 (TTM) ---
    roe = Column(Float, nullable=True)              # ROE (자기자본이익률)
    roa = Column(Float, nullable=True)              # ROA (총자산이익률)
    roic = Column(Float, nullable=True)             # ROIC (투하자본이익률)
    gross_margin_ttm = Column(Float, nullable=True) # 매출총이익률
    op_margin_ttm = Column(Float, nullable=True)    # 영업이익률
    net_margin_ttm = Column(Float, nullable=True)   # 순이익률
    ebitda_margin_ttm = Column(Float, nullable=True)

    # --- 성장성 (YoY) ---
    revenue_growth = Column(Float, nullable=True)   # 매출 성장률
    eps_growth = Column(Float, nullable=True)       # EPS 성장률
    fcf_growth = Column(Float, nullable=True)       # FCF 성장률
    op_income_growth = Column(Float, nullable=True) # 영업이익 성장률

    # --- 재무건전성 (TTM) ---
    current_ratio = Column(Float, nullable=True)    # 유동비율
    debt_to_equity = Column(Float, nullable=True)   # 부채비율
    net_debt_to_ebitda = Column(Float, nullable=True) # 순부채/EBITDA
    interest_coverage = Column(Float, nullable=True)  # 이자보상배율

    # --- 주주환원 ---
    dividend_yield = Column(Float, nullable=True)   # 배당수익률
    payout_ratio = Column(Float, nullable=True)     # 배당성향

    # --- 효율성 ---
    asset_turnover = Column(Float, nullable=True)   # 자산회전율
    receivables_turnover = Column(Float, nullable=True) # 매출채권회전율
    inventory_turnover = Column(Float, nullable=True)   # 재고자산회전율

    # --- 업데이트 시각 ---
    last_updated = Column(String, nullable=True)

    company = relationship("Company", back_populates="profile")


class FinancialData(Base):
    """연간/분기 재무제표 (손익 + 재무상태표 + 현금흐름)"""
    __tablename__ = "financial_data"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    
    period_type = Column(String)    # "annual" or "quarterly"
    date = Column(String)           # YYYY-MM-DD (회계연도 종료일)
    fiscal_year = Column(String, nullable=True)  # e.g. "FY2024", "Q3 2024"

    # === 손익계산서 (Income Statement) ===
    revenue = Column(Float, nullable=True)              # 매출
    cost_of_revenue = Column(Float, nullable=True)      # 매출원가
    gross_profit = Column(Float, nullable=True)         # 매출총이익
    operating_income = Column(Float, nullable=True)     # 영업이익
    ebitda = Column(Float, nullable=True)               # EBITDA
    net_income = Column(Float, nullable=True)           # 순이익
    eps = Column(Float, nullable=True)                  # 주당순이익
    shares_outstanding = Column(Float, nullable=True)   # 발행주식수

    # 마진율 (계산값)
    gross_margin = Column(Float, nullable=True)         # 매출총이익률 (%)
    op_margin = Column(Float, nullable=True)            # 영업이익률 (%)
    net_margin = Column(Float, nullable=True)           # 순이익률 (%)
    ebitda_margin = Column(Float, nullable=True)        # EBITDA 마진 (%)

    # 성장률 (계산값)
    revenue_growth_yoy = Column(Float, nullable=True)   # 매출 YoY 성장률
    op_income_growth_yoy = Column(Float, nullable=True) # 영업이익 YoY 성장률
    eps_growth_yoy = Column(Float, nullable=True)       # EPS YoY 성장률

    # === 재무상태표 (Balance Sheet) ===
    total_assets = Column(Float, nullable=True)         # 총자산
    total_current_assets = Column(Float, nullable=True) # 유동자산
    cash_and_equivalents = Column(Float, nullable=True) # 현금 및 현금성자산
    total_debt = Column(Float, nullable=True)           # 총부채(차입금)
    total_liabilities = Column(Float, nullable=True)    # 총부채(전체)
    total_current_liabilities = Column(Float, nullable=True) # 유동부채
    shareholders_equity = Column(Float, nullable=True)  # 자기자본
    net_debt = Column(Float, nullable=True)             # 순부채

    # 재무건전성 비율
    current_ratio = Column(Float, nullable=True)        # 유동비율
    debt_to_equity_ratio = Column(Float, nullable=True) # 부채비율

    # === 현금흐름표 (Cash Flow) ===
    operating_cash_flow = Column(Float, nullable=True)  # 영업활동 현금흐름
    capital_expenditure = Column(Float, nullable=True)  # 설비투자 (CAPEX)
    free_cash_flow = Column(Float, nullable=True)       # 잉여현금흐름 (FCF)
    dividends_paid = Column(Float, nullable=True)       # 배당금 지급
    stock_buyback = Column(Float, nullable=True)        # 자사주매입

    # === 수익성/효율성 (계산값) ===
    roe = Column(Float, nullable=True)                  # ROE
    roa = Column(Float, nullable=True)                  # ROA
    fcf_margin = Column(Float, nullable=True)           # FCF 마진

    company = relationship("Company", back_populates="financials")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String)
    type = Column(String)
    target_id = Column(Integer, nullable=True)

class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String)
    sender_type = Column(String)
    recipient = Column(String)
    content = Column(Text)
    msg_type = Column(String)
    timestamp = Column(String)

class OrchestrationReport(Base):
    __tablename__ = "orchestration_reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    created_at = Column(String)
