"""
Point-in-Time Turnaround Screener with Strict SEC Filing Lags (Zero Lookahead Bias).
Implements the 4-Pillar Proxy Framework:
1. Revenue Inflection (2nd derivative > 0)
2. Operating Margin / EBIT Recovery
3. Solvency Runway (Current Ratio >= 1.0, Net Debt / EBITDA < 3.5)
4. Valuation Discount / Margin of Safety
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple, Union
import numpy as np
import pandas as pd

from config.settings import SEC_LAG_10Q_DAYS, SEC_LAG_10K_DAYS
from src.models.schemas import PITFinancialStatement


class PITFundamentalStore:
    """
    In-memory or persistent store of historical point-in-time financial statements.
    Enforces strict observation availability dates based on SEC EDGAR filing timestamps
    or regulatory 45/90 day publication lags.
    """

    def __init__(self, statements: Optional[List[PITFinancialStatement]] = None):
        self._statements: List[PITFinancialStatement] = statements or []
        self._by_ticker: Dict[str, List[PITFinancialStatement]] = {}
        self._index_statements()

    def _index_statements(self) -> None:
        self._by_ticker = {}
        for st in self._statements:
            ticker = st.ticker.upper()
            if ticker not in self._by_ticker:
                self._by_ticker[ticker] = []
            self._by_ticker[ticker].append(st)
        # Sort each ticker's statements by filing_date ascending
        for t in self._by_ticker:
            self._by_ticker[t].sort(key=lambda x: (x.filing_date, x.fiscal_period_end))

    @classmethod
    def from_seed_file(cls, seed_path: Optional[Union[str, Path]] = None) -> "PITFundamentalStore":
        """Loads fundamental statements from seed JSON or Parquet file."""
        import json
        from pathlib import Path
        from config.settings import SEED_DIR
        
        path = Path(seed_path) if seed_path else Path(SEED_DIR) / "pit_fundamentals.json"
        if not path.exists():
            return cls([])

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            statements = []
            for item in data:
                st = PITFinancialStatement(
                    ticker=item["ticker"],
                    fiscal_period_end=pd.to_datetime(item["fiscal_period_end"]).date(),
                    filing_date=pd.to_datetime(item["filing_date"]).date(),
                    period_type=item.get("period_type", "Q"),
                    revenue=float(item["revenue"]),
                    operating_income=float(item["operating_income"]),
                    net_income=float(item["net_income"]),
                    operating_cash_flow=float(item["operating_cash_flow"]),
                    total_debt=float(item["total_debt"]),
                    cash_and_equivalents=float(item["cash_and_equivalents"]),
                    current_ratio=float(item["current_ratio"]),
                    ebitda=float(item["ebitda"]) if item.get("ebitda") is not None else None,
                    interest_expense=float(item["interest_expense"]) if item.get("interest_expense") is not None else None,
                )
                statements.append(st)
            return cls(statements)
        except Exception as e:
            return cls([])

    def add_statement(self, st: PITFinancialStatement) -> None:
        self._statements.append(st)
        self._index_statements()

    def add_statements(self, statements: List[PITFinancialStatement]) -> None:
        self._statements.extend(statements)
        self._index_statements()

    def get_statements_observable_at(
        self,
        ticker: str,
        as_of_date: Union[date, datetime, str],
    ) -> List[PITFinancialStatement]:
        """
        Returns all financial statements for ticker that were publicly filed/observable
        ON OR BEFORE as_of_date. Zero lookahead guarantee: statements filed after as_of_date
        are strictly excluded.
        """
        if isinstance(as_of_date, str):
            dt = pd.to_datetime(as_of_date).date()
        elif isinstance(as_of_date, datetime):
            dt = as_of_date.date()
        else:
            dt = as_of_date

        ticker_upper = ticker.upper()
        all_st = self._by_ticker.get(ticker_upper, [])
        return [s for s in all_st if s.filing_date <= dt]


class TurnaroundScorer:
    """
    Evaluates corporate turnaround probability across 4 quantitative pillars
    using only point-in-time financial data available at historical decision points.
    """

    def __init__(
        self,
        fundamental_store: Optional[PITFundamentalStore] = None,
        lag_10q_days: int = SEC_LAG_10Q_DAYS,
        lag_10k_days: int = SEC_LAG_10K_DAYS,
    ):
        if fundamental_store is not None:
            self.store = fundamental_store
        else:
            loaded = PITFundamentalStore.from_seed_file()
            self.store = loaded if len(loaded._statements) > 0 else PITFundamentalStore()
        self.lag_10q = timedelta(days=lag_10q_days)
        self.lag_10k = timedelta(days=lag_10k_days)

    def calculate_reporting_lag(self, fiscal_period_end: date, period_type: str) -> date:
        """
        Calculates conservative point-in-time observable date based on SEC reporting deadlines.
        10-Q (quarterly): 45 calendar days.
        10-K (annual): 90 calendar days.
        """
        if period_type.upper() in ["FY", "10-K", "ANNUAL", "K"]:
            return fiscal_period_end + self.lag_10k
        return fiscal_period_end + self.lag_10q

    def score_candidate(
        self,
        ticker: str,
        as_of_date: Union[date, datetime, str],
        market_cap: Optional[float] = None,
        stock_price: Optional[float] = None,
        low_52w: Optional[float] = None,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculates the turnaround score for ticker at as_of_date.
        Returns composite score (0.0 to 1.0) and component breakdown.
        """
        observable = self.store.get_statements_observable_at(ticker, as_of_date)
        
        # If no PIT statements exist, provide conservative baseline or synthetic proxy
        if not observable:
            # When fundamentals are not loaded, return default neutral-conservative score
            return 0.50, {
                "pillar1_rev_inflection": 0.50,
                "pillar2_opm_recovery": 0.50,
                "pillar3_solvency": 0.50,
                "pillar4_valuation": 0.50,
                "composite_score": 0.50,
                "statement_count": 0,
            }

        latest = observable[-1]
        prior = observable[-2] if len(observable) >= 2 else None

        # Pillar 1: Revenue Inflection (2nd derivative > 0)
        p1_score = self._calc_revenue_inflection(observable)

        # Pillar 2: Operating Margin / EBIT Recovery
        p2_score = self._calc_opm_recovery(latest, prior)

        # Pillar 3: Solvency Runway
        p3_score = self._calc_solvency_runway(latest)

        # Pillar 4: Valuation Discount / Margin of Safety
        p4_score = self._calc_valuation_discount(latest, stock_price, low_52w)

        # Weighted composite score
        # 35% Rev Inflection + 30% EBIT Recovery + 20% Solvency + 15% Valuation
        composite = (
            0.35 * p1_score
            + 0.30 * p2_score
            + 0.20 * p3_score
            + 0.15 * p4_score
        )
        composite = float(np.clip(composite, 0.0, 1.0))

        breakdown = {
            "pillar1_rev_inflection": round(p1_score, 4),
            "pillar2_opm_recovery": round(p2_score, 4),
            "pillar3_solvency": round(p3_score, 4),
            "pillar4_valuation": round(p4_score, 4),
            "composite_score": round(composite, 4),
            "statement_count": len(observable),
        }

        return composite, breakdown

    def _calc_revenue_inflection(self, statements: List[PITFinancialStatement]) -> float:
        """
        Evaluates revenue acceleration (2nd derivative):
        Growth_Q0 vs Growth_Q-1.
        """
        if len(statements) < 2:
            return 0.50

        rev_0 = statements[-1].revenue
        rev_1 = statements[-2].revenue

        if rev_1 <= 0:
            return 0.50

        growth_curr = (rev_0 - rev_1) / rev_1

        if len(statements) >= 3 and statements[-3].revenue > 0:
            growth_prev = (rev_1 - statements[-3].revenue) / statements[-3].revenue
            accel = growth_curr - growth_prev
            # Positive acceleration (2nd derivative > 0) gives high score
            score = 0.50 + (accel * 2.5)
        else:
            score = 0.50 + (growth_curr * 1.5)

        return float(np.clip(score, 0.05, 0.95))

    def _calc_opm_recovery(
        self,
        latest: PITFinancialStatement,
        prior: Optional[PITFinancialStatement],
    ) -> float:
        """
        Evaluates operating margin recovery (EBIT margin expansion).
        """
        if latest.revenue <= 0:
            return 0.30

        opm_latest = latest.operating_income / latest.revenue

        if prior is None or prior.revenue <= 0:
            # Single statement: score based on absolute margin
            return float(np.clip(0.50 + opm_latest * 1.5, 0.1, 0.9))

        opm_prior = prior.operating_income / prior.revenue
        delta_opm = opm_latest - opm_prior

        # Operating margin expansion yields higher score
        base_score = 0.50
        if delta_opm > 0:
            score = base_score + (delta_opm * 4.0)
        else:
            score = base_score + (delta_opm * 2.0)

        # Extra bonus if swinging from negative to positive EBIT
        if prior.operating_income < 0 and latest.operating_income > 0:
            score += 0.20

        return float(np.clip(score, 0.05, 0.95))

    def _calc_solvency_runway(self, st: PITFinancialStatement) -> float:
        """
        Evaluates balance sheet survival runway:
        - Current ratio >= 1.0
        - Operating cash flow > 0
        - Net Debt / EBITDA < 3.5
        """
        score = 0.50

        # Current ratio check
        if st.current_ratio >= 1.5:
            score += 0.15
        elif st.current_ratio >= 1.0:
            score += 0.05
        else:
            score -= 0.25

        # Operating Cash Flow check
        if st.operating_cash_flow > 0:
            score += 0.15
        else:
            score -= 0.15

        # Net Debt / EBITDA check
        net_debt = st.total_debt - st.cash_and_equivalents
        if net_debt <= 0:
            # Net cash position is exceptionally safe
            score += 0.20
        elif st.ebitda is not None and st.ebitda > 0:
            leverage = net_debt / st.ebitda
            if leverage < 2.0:
                score += 0.15
            elif leverage < 3.5:
                score += 0.05
            elif leverage > 5.0:
                score -= 0.25

        return float(np.clip(score, 0.05, 0.95))

    def _calc_valuation_discount(
        self,
        st: PITFinancialStatement,
        stock_price: Optional[float],
        low_52w: Optional[float],
    ) -> float:
        """
        Evaluates valuation discount / margin of safety.
        """
        # When price is near 52w low, valuation is already discounted
        score = 0.60
        if stock_price is not None and low_52w is not None and low_52w > 0:
            proximity = (stock_price - low_52w) / low_52w
            if proximity <= 0.02:
                score += 0.20
            elif proximity <= 0.05:
                score += 0.10

        return float(np.clip(score, 0.10, 0.95))
