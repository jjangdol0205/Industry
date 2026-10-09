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
    display_order = Column(Integer, default=999, nullable=True)  # 투자 순위 (자동 업데이트)
    portfolio_tier = Column(String, default="Standard", nullable=True)  # Core, Satellite, Watchlist, Standard
    principle_reason = Column(Text, nullable=True)  # 4단계 투자원칙 충족 이유

    industry = relationship("IndustryReport", back_populates="companies")
    value_chain_node = relationship("ValueChainNode", back_populates="companies")
    financials = relationship("FinancialData", back_populates="company")
    profile = relationship("CompanyProfile", back_populates="company", uselist=False)

    @property
    def current_price(self):
        return self.profile.current_price if self.profile else None

    @property
    def high_52w(self):
        return self.profile.high_52w if self.profile else None

    @property
    def mdd_pct(self):
        return self.profile.mdd_pct if self.profile else None

    @property
    def buy_signal(self):
        return self.profile.buy_signal if self.profile else None

    @property
    def dca_stage(self):
        return self.profile.dca_stage if self.profile else None

    @property
    def moat_score(self):
        return self.profile.moat_score if self.profile else None


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
    high_52w = Column(Float, nullable=True)         # 52주 최고가
    mdd_pct = Column(Float, nullable=True)          # 현재 MDD (고점 대비 %)
    buy_signal = Column(String, nullable=True)      # 4단계 제1원칙 매수신호
    dca_stage = Column(String, nullable=True)       # 4단계 DCA 단계 (CORE_DCA_1, CORE_DCA_2 등)
    moat_score = Column(Float, nullable=True)       # 100점 만점 해자 점수 (S_moat)
    rsi_14 = Column(Float, nullable=True)           # 14일 RSI 지표
    bollinger_pct_b = Column(Float, nullable=True)  # 볼린저 밴드 %B
    rebound_score = Column(Float, nullable=True)    # 100점 만점 과매도 기술적 반등 점수
    rebound_signal = Column(String, nullable=True)  # 기술적 반등 신호 (STRONG_REBOUND 등)
    support_price = Column(Float, nullable=True)    # 하방 지지가격
    principle_reason = Column(Text, nullable=True)  # 4단계 투자원칙 충족 근거
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
    ai_analysis_json = Column(Text, nullable=True)

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


class SpecialWatchlistStudy(Base):
    """6개 특별 관심종목 심층 스터디 5개 차원 모델 (Requirement R1)"""
    __tablename__ = "special_watchlist_studies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    name_ko = Column(String, nullable=False)
    exchange = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    portfolio_tier = Column(String, default="Watchlist", nullable=True)

    current_price = Column(Float, nullable=True)
    high_52w = Column(Float, nullable=True)
    mdd_pct = Column(Float, nullable=True)
    buy_signal = Column(String, nullable=True)
    dca_stage = Column(String, nullable=True)

    business_model = Column(Text, nullable=False)
    moat_analysis = Column(Text, nullable=False)
    moat_bottleneck = Column(Text, nullable=True)
    tam_growth_drivers = Column(Text, nullable=False)
    financial_margins = Column(Text, nullable=True)
    opm = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    gross_margin = Column(Float, nullable=True)
    fcf_status = Column(Text, nullable=True)

    key_risks = Column(Text, nullable=False)
    catalysts = Column(Text, nullable=True)
    valuation_thesis = Column(Text, nullable=True)
    institutional_verdict = Column(Text, nullable=True)
    target_price = Column(Float, nullable=True)
    study_json = Column(Text, nullable=True)

    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)

    timeline = relationship("SpecialWatchlistTimeline", back_populates="study", cascade="all, delete-orphan", order_by="desc(SpecialWatchlistTimeline.publish_date)")


class SpecialWatchlistTimeline(Base):
    """6개 특별 관심종목 시계열 외신 리포트 및 타임라인 (Requirement R2)"""
    __tablename__ = "special_watchlist_timeline"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, ForeignKey("special_watchlist_studies.ticker"), index=True, nullable=False)
    news_id = Column(String, unique=True, index=True, nullable=False)
    publish_date = Column(String, nullable=False)  # YYYY-MM-DD
    headline = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    key_takeaways = Column(Text, nullable=True)
    sentiment = Column(String, nullable=False)  # POSITIVE, NEGATIVE, NEUTRAL
    sentiment_score = Column(Float, nullable=True)
    price_impact = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    created_at = Column(String, nullable=True)

    study = relationship("SpecialWatchlistStudy", back_populates="timeline")


class GuruLetter(Base):
    """7대 투자 거장 공식 서한 및 메모 모델 (Requirement R1, R3)"""
    __tablename__ = "guru_letters"

    id = Column(Integer, primary_key=True, index=True)
    letter_id = Column(String, unique=True, index=True, nullable=False)
    guru_name = Column(String, index=True, nullable=False)
    guru_name_en = Column(String, nullable=False)
    firm = Column(String, nullable=False)
    title = Column(String, nullable=False)
    publish_date = Column(String, index=True, nullable=False)  # YYYY-MM-DD
    url = Column(String, nullable=True)
    summary = Column(Text, nullable=False)
    original_quote = Column(Text, nullable=False)
    original_quote_ko = Column(Text, nullable=False)
    core_thesis = Column(Text, nullable=False)
    thesis_pillar = Column(String, index=True, nullable=False)
    deep_concept_guide = Column(Text, nullable=False)
    related_tickers = Column(Text, nullable=False)  # JSON encoded list
    ticker_implications = Column(Text, nullable=False)  # JSON encoded dict
    sentiment = Column(String, default="NEUTRAL", index=True)
    sentiment_score = Column(Float, default=0.0)
    source_type = Column(String, default="MEMO")
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


class TechLeaderInterview(Base):
    """7대 글로벌 AI & 테크 리더 인터뷰 모델 (Requirement R1, R3)"""
    __tablename__ = "tech_leader_interviews"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(String, unique=True, index=True, nullable=False)
    leader_name = Column(String, index=True, nullable=False)
    leader_name_en = Column(String, nullable=False)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    title = Column(String, nullable=False)
    publish_date = Column(String, index=True, nullable=False)  # YYYY-MM-DD
    media_source = Column(String, nullable=False)
    url = Column(String, nullable=True)
    summary = Column(Text, nullable=False)
    original_quote = Column(Text, nullable=False)
    original_quote_ko = Column(Text, nullable=False)
    core_thesis = Column(Text, nullable=False)
    thesis_pillar = Column(String, index=True, nullable=False)
    tech_concept_guide = Column(Text, nullable=False)
    supply_chain_impact = Column(Text, nullable=False)
    related_tickers = Column(Text, nullable=False)  # JSON encoded list
    ticker_implications = Column(Text, nullable=False)  # JSON encoded dict
    sentiment = Column(String, default="BULLISH", index=True)
    sentiment_score = Column(Float, default=0.0)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


# ─────────────────────────────────────────────
# Macro Intelligence Module Models (Milestone 2)
# ─────────────────────────────────────────────
class MacroReport(Base):
    """
    연준(FOMC) 및 연은(NY/St.Louis Fed) 리서치 보고서 영속화 모델
    SQLite 테이블: macro_reports
    """
    __tablename__ = "macro_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, unique=True, index=True, nullable=False)
    source = Column(String, index=True, nullable=False)              # FOMC, NY Fed, St. Louis Fed
    category = Column(String, index=True, nullable=False)            # FOMC Statement, Liberty Street Economics 등
    title = Column(String, nullable=False)
    publish_date = Column(String, index=True, nullable=False)        # YYYY-MM-DD
    url = Column(String, nullable=True)
    summary = Column(Text, nullable=False)
    key_takeaways = Column(Text, nullable=True)                      # JSON-encoded List[str]
    discount_rate_impact = Column(Text, nullable=False)              # ① 매크로 할인율 및 증시 밸류에이션
    factor_style_impact = Column(Text, nullable=False)               # ② 스타일/팩터 영향 (대형 퀄리티 vs 중소형)
    sector_industry_impact = Column(Text, nullable=False)            # ③ 주요 섹터 및 산업 영향
    fx_liquidity_flow_impact = Column(Text, nullable=False)          # ④ 외환 및 외국인 수급
    sentiment = Column(String, index=True, nullable=False)           # DOVISH, HAWKISH, NEUTRAL
    sentiment_score = Column(Float, default=0.0)
    pe_impact_pct_estimate = Column(Float, default=0.0)
    favored_factor = Column(String, nullable=True)
    unfavored_factor = Column(String, nullable=True)
    overweight_sectors = Column(Text, nullable=True)                 # JSON-encoded List[str]
    underweight_sectors = Column(Text, nullable=True)                # JSON-encoded List[str]
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


class MacroIndicator(Base):
    """
    거시 금리 및 유동성 일별 지표 시계열 모델
    SQLite 테이블: macro_indicators
    """
    __tablename__ = "macro_indicators"

    id = Column(Integer, primary_key=True, index=True)
    indicator_date = Column(String, unique=True, index=True, nullable=False)  # YYYY-MM-DD
    us_10y_yield = Column(Float, nullable=False)
    us_2y_yield = Column(Float, nullable=False)
    yield_spread_10y_2y = Column(Float, nullable=False)                       # 10Y - 2Y (%)
    yield_curve_state = Column(String, nullable=False)                        # INVERTED, FLAT, NORMAL, STEEP
    curve_shift_type = Column(String, nullable=False)                         # BULL_STEEPENER, BEAR_STEEPENER 등
    fed_funds_rate = Column(Float, nullable=False)
    real_neutral_rate_r_star = Column(Float, nullable=False)                  # r* 추정치 (기본 1.10%)
    core_pce_inflation = Column(Float, nullable=False)
    policy_restrictiveness_gap = Column(Float, nullable=False)                # (FFR - Core PCE) - r*
    tga_balance_billion = Column(Float, nullable=False)                       # 재무부 일반계정 ($B)
    on_rrp_balance_billion = Column(Float, nullable=False)                    # 역레포 잔고 ($B)
    fed_total_assets_trillion = Column(Float, nullable=False)                 # 연준 총자산 ($T)
    net_liquidity_billion = Column(Float, nullable=False)                     # Assets - TGA - RRP ($B)
    net_liquidity_change_30d = Column(Float, default=0.0)
    net_liquidity_change_90d = Column(Float, default=0.0)
    dxy_index = Column(Float, nullable=True)                                  # 달러 인덱스
    usdkrw_exchange_rate = Column(Float, nullable=True)                       # 원/달러 환율
    vix_index = Column(Float, nullable=True)                                  # 변동성 지수
    recorded_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


class MacroRegime(Base):
    """
    거시 경제 국면 판정 및 켄 피셔 시그널 영속화 모델
    SQLite 테이블: macro_regime
    """
    __tablename__ = "macro_regime"

    id = Column(Integer, primary_key=True, index=True)
    regime_id = Column(String, unique=True, index=True, nullable=False)       # 'CURRENT' 또는 일자별 식별자
    as_of_date = Column(String, index=True, nullable=False)                   # 기준 일자 (YYYY-MM-DD)
    current_regime = Column(String, nullable=False)                           # 국면 국문 명칭
    regime_code = Column(String, nullable=False)                              # TRANSITION_UNINVERSION 등
    regime_description = Column(Text, nullable=False)
    per_multiple_outlook = Column(String, nullable=False)                     # COMPRESSION, EXPANSION, NEUTRAL
    pe_expansion_compression_pct = Column(Float, default=0.0)
    ken_fisher_signal = Column(String, nullable=False)                        # HIGH_RECESSION_DEFENSE_ALERT 등
    rimp_model_analysis = Column(Text, nullable=False)                        # NY Fed 기업 이질성 분석
    factor_allocations_json = Column(Text, nullable=False)                    # 포트폴리오 비중 (JSON)
    sector_matrix_json = Column(Text, nullable=False)                         # 섹터 민감도 매트릭스 (JSON)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


