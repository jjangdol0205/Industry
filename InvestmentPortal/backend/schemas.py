from pydantic import BaseModel
from typing import List, Optional

class FinancialDataBase(BaseModel):
    period_type: str
    date: str
    revenue: Optional[float]
    operating_income: Optional[float]
    net_income: Optional[float]
    gross_margin: Optional[float]

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
    financials: List[FinancialData] = []

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
