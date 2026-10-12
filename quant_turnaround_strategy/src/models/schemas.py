"""
Core domain models, dataclasses, and enumeration schemas for M1.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, List


class ExclusionReason(str, Enum):
    SOLVENCY_RISK = "solvency_risk"
    FALLING_KNIFE = "falling_knife_unstable"
    ILLIQUID = "insufficient_dollar_volume"
    SECTOR_CAPACITY = "sector_concentration_limit"
    LOW_TURNAROUND_SCORE = "score_below_threshold"
    TRADING_HISTORY_INSUFFICIENT = "trading_history_insufficient"
    ALREADY_HELD = "already_held"


@dataclass(frozen=True)
class DailyBar:
    ticker: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float


@dataclass(frozen=True)
class UniverseConstituent:
    ticker: str
    start_date: date
    end_date: date
    name: str = ""
    sector: str = "Technology"


@dataclass(frozen=True)
class PITFinancialStatement:
    ticker: str
    fiscal_period_end: date
    filing_date: date  # Date when report became publicly observable
    period_type: str  # "Q" (10-Q) or "FY" (10-K)
    revenue: float
    operating_income: float
    net_income: float
    operating_cash_flow: float
    total_debt: float
    cash_and_equivalents: float
    current_ratio: float
    ebitda: Optional[float] = None
    interest_expense: Optional[float] = None


@dataclass
class CandidateEvaluation:
    ticker: str
    evaluation_date: date
    close_price: float
    low_52w: float
    low_proximity: float
    rsi_14: float
    return_5d: float
    avg_dollar_volume: float
    turnaround_score: float
    solvency_score: float
    valuation_discount: float
    composite_rank_score: float
    passed_all_gates: bool
    exclusion_reasons: List[ExclusionReason] = field(default_factory=list)
    gics_sector: str = "Unknown"


@dataclass
class WeeklySelectionResult:
    decision_date: date
    selected_ticker: Optional[str]
    selected_candidate: Optional[CandidateEvaluation]
    portfolio_held_count: int  # 0, 1, 2, or 3
    action: str  # "BUY", "HOLD_CAPACITY_FULL", "NO_QUALIFIED_CANDIDATE"
    rationale: str
    all_evaluated_candidates: List[CandidateEvaluation] = field(default_factory=list)
