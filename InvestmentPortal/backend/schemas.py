from pydantic import BaseModel
from typing import List, Optional

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
    future_growth: str
    value_chain_node_id: Optional[int] = None

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
