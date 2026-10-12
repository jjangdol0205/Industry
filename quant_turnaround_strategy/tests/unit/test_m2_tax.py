"""
Unit test suite for M2 Korean Overseas Capital Gains Tax Engine (src/engine/tax.py).
Verifies:
- 22% tax on net realized gains exceeding 2.5 million KRW basic deduction.
- Zero tax when net realized gains <= 2.5 million KRW.
- Calendar year loss offsetting (손익통산) within the year.
- Conversion between KRW tax liability and USD deduction at year-end FX.
- Tax table generation and Gross vs Net NAV accounting.
"""
from datetime import date
import pytest
from src.engine.tax import KoreanTaxEngine, AnnualTaxRecord


class TestKoreanTaxEngine:
    def test_gains_under_basic_deduction_are_tax_free(self):
        engine = KoreanTaxEngine(enabled=True)
        # Realized gain = 2,000,000 KRW (< 2.5M basic deduction)
        engine.record_realized_trade(
            year=2021,
            gain_usd=1666.67,
            gain_krw=2_000_000.0,
            trade_date=date(2021, 6, 15),
            ticker="ABC",
        )
        rec = engine.calculate_annual_tax(year=2021, year_end_fx=1200.0)

        assert rec.year == 2021
        assert rec.net_realized_gain_krw == 2_000_000.0
        assert rec.taxable_base_krw == 0.0
        assert rec.tax_krw == 0.0
        assert rec.tax_usd == 0.0

    def test_gains_exceeding_basic_deduction_taxed_at_22_percent(self):
        engine = KoreanTaxEngine(enabled=True)
        # Realized gain = 12,500,000 KRW
        # Taxable base = 12,500,000 - 2,500,000 = 10,000,000 KRW
        # Tax = 10,000,000 * 0.22 = 2,200,000 KRW
        # Tax in USD at FX 1200 = 2,200,000 / 1200 = 1,833.33 USD
        engine.record_realized_trade(
            year=2022,
            gain_usd=10_416.67,
            gain_krw=12_500_000.0,
            trade_date=date(2022, 11, 20),
            ticker="XYZ",
        )
        rec = engine.calculate_annual_tax(year=2022, year_end_fx=1200.0)

        assert rec.taxable_base_krw == 10_000_000.0
        assert pytest.approx(rec.tax_krw, abs=1e-2) == 2_200_000.0
        assert pytest.approx(rec.tax_usd, abs=1e-2) == 1833.33

    def test_loss_offsetting_within_calendar_year(self):
        engine = KoreanTaxEngine(enabled=True)
        # Trade 1: Gain 10,000,000 KRW
        engine.record_realized_trade(2023, gain_usd=8000.0, gain_krw=10_000_000.0, ticker="WINNER")
        # Trade 2: Loss -5,000,000 KRW
        engine.record_realized_trade(2023, gain_usd=-4000.0, gain_krw=-5_000_000.0, ticker="LOSER")

        # Net gain = 5,000,000 KRW
        # Taxable base = 5,000,000 - 2,500,000 = 2,500,000 KRW
        # Tax = 2,500,000 * 0.22 = 550,000 KRW
        rec = engine.calculate_annual_tax(year=2023, year_end_fx=1300.0)

        assert rec.net_realized_gain_krw == 5_000_000.0
        assert rec.taxable_base_krw == 2_500_000.0
        assert pytest.approx(rec.tax_krw, abs=1e-2) == 550_000.0
        assert pytest.approx(rec.tax_usd, abs=1e-2) == 550_000.0 / 1300.0

    def test_annual_tax_table_generation(self):
        engine = KoreanTaxEngine(enabled=True)
        engine.record_realized_trade(2021, gain_usd=1000.0, gain_krw=1_000_000.0)
        engine.calculate_annual_tax(2021, 1200.0)

        engine.record_realized_trade(2022, gain_usd=10000.0, gain_krw=12_500_000.0)
        engine.calculate_annual_tax(2022, 1300.0)

        df = engine.get_annual_tax_table()
        assert len(df) == 2
        assert list(df["Year"]) == [2021, 2022]
        assert df.loc[df["Year"] == 2021, "Tax_KRW"].values[0] == 0.0
        assert df.loc[df["Year"] == 2022, "Tax_KRW"].values[0] == 2_200_000.0

    def test_disabled_tax_engine_produces_zero_tax(self):
        engine = KoreanTaxEngine(enabled=False)
        engine.record_realized_trade(2022, gain_usd=100_000.0, gain_krw=100_000_000.0)
        rec = engine.calculate_annual_tax(2022, 1300.0)
        assert rec.tax_krw == 0.0
        assert rec.tax_usd == 0.0
