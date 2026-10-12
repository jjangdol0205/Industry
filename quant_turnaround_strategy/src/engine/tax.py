"""
Korean Overseas Stock Capital Gains Tax Engine (해외주식 양도소득세).
Models institutional taxation under Korean tax law:
- 22% tax rate (20% transfer income tax + 2% local income tax).
- 2,500,000 KRW annual basic deduction per calendar year.
- Deducted annually at calendar year-end on net realized gains in KRW:
    Taxable Base = max(0, Net Realized Gain_KRW - 2,500,000 KRW)
    Tax_KRW = Taxable Base * 0.22
    Tax_USD = Tax_KRW / Year_End_FX
- Provides dual Gross (pre-tax) vs Net (after-tax & after-cost) accounting.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional
import pandas as pd


@dataclass
class AnnualTaxRecord:
    """Record of annual realized gains and tax liability for one calendar year."""
    year: int
    net_realized_gain_usd: float
    net_realized_gain_krw: float
    basic_deduction_krw: float
    taxable_base_krw: float
    tax_krw: float
    tax_usd: float
    year_end_fx: float
    paid: bool = False


class KoreanTaxEngine:
    """
    Simulates annual capital gains tax assessment and deduction for Korean investors.
    """

    BASIC_DEDUCTION_KRW: float = 2_500_000.0  # 2.5 million KRW basic deduction
    TAX_RATE: float = 0.22                   # 22% (20% national + 2% local)

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.annual_gains_usd: Dict[int, float] = {}
        self.annual_gains_krw: Dict[int, float] = {}
        self.tax_records: Dict[int, AnnualTaxRecord] = {}
        self.trade_logs: List[Dict] = []

    def record_realized_trade(
        self,
        year: int,
        gain_usd: float,
        gain_krw: float,
        trade_date: Optional[date] = None,
        ticker: str = "",
    ) -> None:
        """Records a realized trade outcome within its calendar tax year."""
        self.annual_gains_usd[year] = self.annual_gains_usd.get(year, 0.0) + gain_usd
        self.annual_gains_krw[year] = self.annual_gains_krw.get(year, 0.0) + gain_krw
        self.trade_logs.append({
            "year": year,
            "trade_date": trade_date,
            "ticker": ticker,
            "gain_usd": gain_usd,
            "gain_krw": gain_krw,
        })

    def calculate_annual_tax(self, year: int, year_end_fx: float) -> AnnualTaxRecord:
        """
        Calculates tax liability at calendar year-end for the given year.
        If tax is disabled, tax liability is 0.0.
        """
        net_gain_usd = self.annual_gains_usd.get(year, 0.0)
        net_gain_krw = self.annual_gains_krw.get(year, 0.0)

        if not self.enabled or net_gain_krw <= self.BASIC_DEDUCTION_KRW:
            taxable_base = 0.0
            tax_krw = 0.0
            tax_usd = 0.0
        else:
            taxable_base = net_gain_krw - self.BASIC_DEDUCTION_KRW
            tax_krw = taxable_base * self.TAX_RATE
            tax_usd = tax_krw / year_end_fx if year_end_fx > 0 else 0.0

        record = AnnualTaxRecord(
            year=year,
            net_realized_gain_usd=net_gain_usd,
            net_realized_gain_krw=net_gain_krw,
            basic_deduction_krw=self.BASIC_DEDUCTION_KRW,
            taxable_base_krw=taxable_base,
            tax_krw=tax_krw,
            tax_usd=tax_usd,
            year_end_fx=year_end_fx,
            paid=True,
        )
        self.tax_records[year] = record
        return record

    def get_annual_tax_table(self) -> pd.DataFrame:
        """Returns annual tax assessment records as a clean pandas DataFrame."""
        if not self.tax_records:
            return pd.DataFrame(columns=[
                "Year", "Net_Realized_Gain_USD", "Net_Realized_Gain_KRW",
                "Basic_Deduction_KRW", "Taxable_Base_KRW", "Tax_KRW", "Tax_USD", "Year_End_FX",
            ])
        rows = []
        for year in sorted(self.tax_records.keys()):
            r = self.tax_records[year]
            rows.append({
                "Year": r.year,
                "Net_Realized_Gain_USD": r.net_realized_gain_usd,
                "Net_Realized_Gain_KRW": r.net_realized_gain_krw,
                "Basic_Deduction_KRW": r.basic_deduction_krw,
                "Taxable_Base_KRW": r.taxable_base_krw,
                "Tax_KRW": r.tax_krw,
                "Tax_USD": r.tax_usd,
                "Year_End_FX": r.year_end_fx,
            })
        return pd.DataFrame(rows)

    def get_total_tax_paid_krw(self) -> float:
        return sum(r.tax_krw for r in self.tax_records.values())

    def get_total_tax_paid_usd(self) -> float:
        return sum(r.tax_usd for r in self.tax_records.values())

    def reset(self) -> None:
        self.annual_gains_usd.clear()
        self.annual_gains_krw.clear()
        self.tax_records.clear()
        self.trade_logs.clear()
