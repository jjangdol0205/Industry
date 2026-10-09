from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union

class FinancialDataBase(BaseModel):
    period_type: str
    date: str
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None      # 매출원가 (COGS)
    gross_profit: Optional[float] = None          # 매출총이익
    gross_margin: Optional[float] = None          # 매출총이익률 (%)
    operating_income: Optional[float] = None      # 영업이익
    op_margin: Optional[float] = None             # 영업이익률 (%)
    net_income: Optional[float] = None            # 순이익
    net_margin: Optional[float] = None            # 순이익률 (%)
    operating_cash_flow: Optional[float] = None   # 영업현금흐름
    capital_expenditure: Optional[float] = None   # 설비투자
    free_cash_flow: Optional[float] = None        # 잉여현금흐름
    total_assets: Optional[float] = None          # 총자산
    total_debt: Optional[float] = None            # 총부채
    shareholders_equity: Optional[float] = None   # 자기자본
    cash_and_equivalents: Optional[float] = None  # 현금성자산
    research_and_development: Optional[float] = None  # R&D 비용
    selling_general_admin: Optional[float] = None # SG&A 비용
    eps: Optional[float] = None                   # 주당순이익
    shares_outstanding: Optional[float] = None    # 발행주식수

class FinancialData(FinancialDataBase):
    id: int
    company_id: int

    class Config:
        from_attributes = True

class CompanyBase(BaseModel):
    name: str
    ticker: str
    role_description: str
    future_growth: Optional[str] = None
    value_chain_node_id: Optional[int] = None
    portfolio_tier: Optional[str] = "Standard"
    principle_reason: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    industry_id: int
    display_order: Optional[int] = 999
    financials: List[FinancialData] = []
    # 주도주 스코어링 (leading_stock_rankings.json 기반, 런타임 주입)
    leading_score: Optional[float] = None
    leading_grade: Optional[str] = None
    leading_breakdown: Optional[dict] = None
    # 성장성 기반 기업가치 업사이드 점수 (런타임 계산)
    upside_score: Optional[float] = None
    current_price: Optional[float] = None
    high_52w: Optional[float] = None
    mdd_pct: Optional[float] = None
    buy_signal: Optional[str] = None
    dca_stage: Optional[str] = None
    moat_score: Optional[float] = None

    class Config:
        from_attributes = True

class ValueChainNodeBase(BaseModel):
    node_name: str
    description: str

class ValueChainNodeCreate(ValueChainNodeBase):
    pass

class ValueChainNode(ValueChainNodeBase):
    id: int
    industry_id: int
    companies: List[Company] = []

    class Config:
        from_attributes = True

class IndustryReportBase(BaseModel):
    title: str
    summary: str
    file_path: str
    tag: str = "일반"

class IndustryReportCreate(IndustryReportBase):
    pass

class IndustryReport(IndustryReportBase):
    id: int
    value_chains: List[ValueChainNode] = []
    companies: List[Company] = []

    class Config:
        from_attributes = True


class SpecialWatchlistTimelineItem(BaseModel):
    id: Optional[int] = None
    news_id: str
    ticker: Optional[str] = None
    publish_date: str
    date: Optional[str] = None
    headline: str
    source: str
    summary: str
    key_takeaways: Optional[str] = None
    takeaways: Optional[str] = None
    sentiment: str
    sentiment_score: Optional[float] = None
    price_impact: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class SpecialWatchlistStudySchema(BaseModel):
    id: Optional[int] = None
    ticker: str
    name: str
    name_ko: str
    exchange: Optional[str] = None
    sector: Optional[str] = None
    portfolio_tier: Optional[str] = "Watchlist"
    current_price: Optional[float] = None
    high_52w: Optional[float] = None
    mdd_pct: Optional[float] = None
    buy_signal: Optional[str] = None
    dca_stage: Optional[str] = None
    business_model: str
    moat_analysis: str
    moat_bottleneck: Optional[str] = None
    tam_growth_drivers: str
    financial_margins: Optional[str] = None
    opm: Optional[float] = None
    roe: Optional[float] = None
    gross_margin: Optional[float] = None
    fcf_status: Optional[str] = None
    key_risks: str
    catalysts: Optional[str] = None
    valuation_thesis: Optional[str] = None
    institutional_verdict: Optional[str] = None
    target_price: Optional[float] = None
    technical_cockpit: Optional[dict] = None
    industry_dynamics: Optional[dict] = None
    study: Optional[dict] = None
    study_json: Optional[str] = None
    timeline: List[SpecialWatchlistTimelineItem] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class SpecialWatchlistResponse(BaseModel):
    status: str = "success"
    updated_at: str
    stocks: List[SpecialWatchlistStudySchema]


class SpecialWatchlistRefreshRequest(BaseModel):
    force: Optional[bool] = False
    background: Optional[bool] = False


# ─────────────────────────────────────────────
# Thought Leaders & Gurus Hub (인사이트 센터) Schemas
# ─────────────────────────────────────────────
class GuruLetterBase(BaseModel):
    letter_id: str
    guru_name: str
    guru_name_en: str
    firm: str
    title: str
    publish_date: str
    url: Optional[str] = None
    summary: str
    original_quote: str
    original_quote_ko: str
    core_thesis: str
    thesis_pillar: str
    deep_concept_guide: Optional[str] = None
    related_tickers: Optional[Any] = []
    ticker_implications: Optional[Any] = {}
    sentiment: Optional[str] = "NEUTRAL"
    sentiment_score: Optional[float] = 0.0
    source_type: Optional[str] = "MEMO"
    item_type: Optional[str] = "GURU_LETTER"


class GuruLetter(GuruLetterBase):
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class TechLeaderInterviewBase(BaseModel):
    interview_id: str
    leader_name: str
    leader_name_en: str
    company: str
    role: str
    title: str
    publish_date: str
    media_source: str
    url: Optional[str] = None
    summary: str
    original_quote: str
    original_quote_ko: str
    core_thesis: str
    thesis_pillar: str
    tech_concept_guide: Optional[str] = None
    supply_chain_impact: Optional[str] = None
    related_tickers: Optional[Any] = []
    ticker_implications: Optional[Any] = {}
    sentiment: Optional[str] = "BULLISH"
    sentiment_score: Optional[float] = 0.0
    item_type: Optional[str] = "TECH_INTERVIEW"


class TechLeaderInterview(TechLeaderInterviewBase):
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class GuruSummary(BaseModel):
    guru_name: str
    name_ko: Optional[str] = None
    guru_name_en: str
    name_en: Optional[str] = None
    firm: str
    latest_title: Optional[str] = None
    latest_publish_date: Optional[str] = None
    thesis_pillar: Optional[str] = None
    sentiment: Optional[str] = None
    related_tickers: Optional[List[str]] = []
    letter_count: Optional[int] = 0


class TechLeaderSummary(BaseModel):
    leader_name: str
    name_ko: Optional[str] = None
    leader_name_en: str
    name_en: Optional[str] = None
    company: str
    role: str
    latest_title: Optional[str] = None
    latest_publish_date: Optional[str] = None
    media_source: Optional[str] = None
    thesis_pillar: Optional[str] = None
    sentiment: Optional[str] = None
    related_tickers: Optional[List[str]] = []
    interview_count: Optional[int] = 0


class FeedResponse(BaseModel):
    status: str = "success"
    total: int
    items: List[Any] = []
    updated_at: Optional[str] = None


class GuruListResponse(BaseModel):
    status: str = "success"
    total: int
    gurus: List[Any] = []
    letters: List[Any] = []
    updated_at: Optional[str] = None


class TechLeaderListResponse(BaseModel):
    status: str = "success"
    total: int
    leaders: List[Any] = []
    interviews: List[Any] = []
    updated_at: Optional[str] = None


class TickerInsightsResponse(BaseModel):
    status: str = "success"
    ticker: str
    total: int
    total_insights: Optional[int] = None
    guru_letters: List[Any] = []
    gurus: Optional[List[Any]] = []
    tech_interviews: List[Any] = []
    tech_leader_interviews: Optional[List[Any]] = []
    tech_leaders: Optional[List[Any]] = []
    consolidated: List[Any] = []


class RefreshResponse(BaseModel):
    status: str = "success"
    message: str
    data: Optional[Dict[str, Any]] = None


class InsightsRefreshRequest(BaseModel):
    force: Optional[bool] = False
    background: Optional[bool] = False


# ─────────────────────────────────────────────
# Macro Intelligence Schemas (Milestone 2)
# ─────────────────────────────────────────────
class MacroReportPerspectives(BaseModel):
    discount_rate_impact: str
    factor_style_impact: str
    sector_industry_impact: str
    fx_liquidity_flow_impact: str


class MacroReportItem(BaseModel):
    id: Optional[int] = None
    report_id: str
    source: str
    category: str
    title: str
    publish_date: str
    url: Optional[str] = None
    summary: str
    key_takeaways: List[str] = []
    perspectives: Optional[MacroReportPerspectives] = None
    discount_rate_impact: str
    factor_style_impact: str
    sector_industry_impact: str
    fx_liquidity_flow_impact: str
    sentiment: str
    sentiment_score: float = 0.0
    pe_impact_pct_estimate: float = 0.0
    favored_factor: Optional[str] = None
    unfavored_factor: Optional[str] = None
    overweight_sectors: List[str] = []
    underweight_sectors: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class FactorAllocations(BaseModel):
    core_pct: float
    satellite_pct: float
    cash_pct: float
    favored: str
    unfavored: str
    quality_alpha_spread_pct: float


class SectorMatrixItem(BaseModel):
    sector: str
    sensitivity: str
    rating: str
    score: int
    rationale: str


class MacroRegimeData(BaseModel):
    regime_id: str
    as_of_date: str
    current_regime: str
    regime_code: str
    regime_description: str
    per_multiple_outlook: str
    pe_expansion_compression_pct: float
    ken_fisher_signal: str
    rimp_model_analysis: str
    factor_allocations: Optional[Union[FactorAllocations, Dict[str, Any]]] = None
    sector_matrix: List[Union[SectorMatrixItem, Dict[str, Any]]] = []
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class IndicatorHistoryItem(BaseModel):
    indicator_date: str
    us_10y_yield: float
    us_2y_yield: float
    yield_spread_10y_2y: float
    yield_curve_state: str
    net_liquidity_billion: float


class MacroIndicatorsData(BaseModel):
    indicator_date: str
    us_10y_yield: float
    us_2y_yield: float
    yield_spread_10y_2y: float
    yield_curve_state: str
    curve_shift_type: str
    fed_funds_rate: float
    real_neutral_rate_r_star: float
    core_pce_inflation: float
    policy_restrictiveness_gap: float
    policy_stance: str
    policy_stance_ko: str
    tga_balance_billion: float
    on_rrp_balance_billion: float
    on_rrp_depletion_alert: bool
    on_rrp_buffer_status: str
    fed_total_assets_trillion: float
    net_liquidity_billion: float
    net_liquidity_change_30d: float = 0.0
    net_liquidity_change_90d: float = 0.0
    dxy_index: Optional[float] = None
    usdkrw_exchange_rate: Optional[float] = None
    vix_index: Optional[float] = None
    recorded_at: Optional[str] = None
    history: List[IndicatorHistoryItem] = []

    class Config:
        from_attributes = True


class MacroSummaryResponse(BaseModel):
    status: str = "success"
    updated_at: Optional[str] = None
    as_of_date: Optional[str] = None
    regime: Optional[MacroRegimeData] = None
    ken_fisher_signal: Optional[str] = None
    per_multiple_outlook: Optional[str] = None
    pe_expansion_compression_pct: Optional[float] = None
    policy_stance: Optional[str] = None
    policy_stance_ko: Optional[str] = None
    liquidity_metrics: Optional[Dict[str, Any]] = None
    indicators_summary: Optional[Dict[str, Any]] = None


class MacroTimelineResponse(BaseModel):
    status: str = "success"
    total: int
    items: List[MacroReportItem] = []
    updated_at: Optional[str] = None


class MacroIndicatorsResponse(BaseModel):
    status: str = "success"
    latest: Optional[Dict[str, Any]] = None
    indicators: Optional[MacroIndicatorsData] = None
    history: List[IndicatorHistoryItem] = []
    updated_at: Optional[str] = None


class MacroRefreshResponse(BaseModel):
    status: str = "success"
    message: str
    summary: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    updated_at: Optional[str] = None


class MacroRefreshRequest(BaseModel):
    force: Optional[bool] = False
    background: Optional[bool] = False


