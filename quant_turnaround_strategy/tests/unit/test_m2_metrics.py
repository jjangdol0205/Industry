"""
Unit test suite for M2 Annual MDD & Calmar / MAR Ratio Metrics (src/engine/metrics.py).
Verifies:
- Calendar Year Intra-Year MDD calculation across year boundaries.
- Rolling 1-year (252-day) MDD series.
- CAGR calculation.
- Calmar ratio (CAGR / max |Annual MDD|).
- MAR ratio (Mean Return / Mean |Annual MDD|).
- Dual-currency (USD and KRW) summary metrics generation.
"""
import pytest
import pandas as pd
import numpy as np
from src.engine.metrics import PerformanceMetrics


class TestMetricsCalculation:
    def test_calendar_year_mdd_multi_year(self):
        dates = [
            pd.Timestamp("2021-01-04"), pd.Timestamp("2021-06-01"), pd.Timestamp("2021-12-31"),
            pd.Timestamp("2022-01-03"), pd.Timestamp("2022-07-01"), pd.Timestamp("2022-12-30"),
        ]
        # 2021: 100 -> 120 -> 108. Peak 120, trough 108 -> MDD = (108-120)/120 = -0.10 (-10%)
        # 2022: 108 -> 81 -> 90. Peak 108, trough 81 -> MDD = (81-108)/108 = -0.25 (-25%)
        nav = pd.Series([100.0, 120.0, 108.0, 108.0, 81.0, 90.0], index=pd.DatetimeIndex(dates))

        df = PerformanceMetrics.calculate_calendar_year_mdd(nav)
        assert len(df) == 2
        assert list(df["Year"]) == [2021, 2022]

        r2021 = df.loc[df["Year"] == 2021].iloc[0]
        assert pytest.approx(r2021["Annual_MDD"], abs=1e-4) == -0.10
        assert pytest.approx(r2021["Annual_Return"], abs=1e-4) == 0.08  # (108-100)/100

        r2022 = df.loc[df["Year"] == 2022].iloc[0]
        assert pytest.approx(r2022["Annual_MDD"], abs=1e-4) == -0.25
        assert pytest.approx(r2022["Annual_Return"], abs=1e-4) == (90.0 - 108.0) / 108.0

    def test_calmar_ratio_formula(self):
        # CAGR = 18.0%, Max Annual MDD = -24.0%
        # Calmar = 0.18 / 0.24 = 0.75
        calmar = PerformanceMetrics.calculate_calmar_ratio(cagr=0.18, max_annual_mdd=-0.24)
        assert pytest.approx(calmar, abs=1e-6) == 0.75

        # Zero MDD safeguard
        assert PerformanceMetrics.calculate_calmar_ratio(cagr=0.10, max_annual_mdd=0.0) == 0.0

    def test_mar_ratio_formula(self):
        annual_df = pd.DataFrame([
            {"Year": 2021, "Annual_Return": 0.20, "Annual_MDD": -0.10},
            {"Year": 2022, "Annual_Return": 0.10, "Annual_MDD": -0.20},
        ])
        # Mean return = 0.15
        # Mean MDD = 0.15
        # MAR = 0.15 / 0.15 = 1.0
        mar = PerformanceMetrics.calculate_mar_ratio(annual_df)
        assert pytest.approx(mar, abs=1e-6) == 1.0

    def test_cagr_calculation(self):
        # 2 years: $100 -> $144 (20% per year)
        dates = [pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01"), pd.Timestamp("2022-01-01")]
        nav = pd.Series([100.0, 120.0, 144.0], index=pd.DatetimeIndex(dates))
        cagr = PerformanceMetrics.calculate_cagr(nav)
        assert pytest.approx(cagr, abs=1e-2) == 0.20

    def test_rolling_mdd_calculation(self):
        dates = pd.date_range("2021-01-01", periods=10, freq="D")
        vals = [100.0, 110.0, 120.0, 108.0, 96.0, 100.0, 110.0, 115.0, 100.0, 90.0]
        nav = pd.Series(vals, index=dates)

        rolling_mdd = PerformanceMetrics.calculate_rolling_mdd(nav, window=5)
        assert len(rolling_mdd) == 10
        # Day 4 (val=96, max in [100, 110, 120, 108, 96] is 120): (96 - 120) / 120 = -0.20
        assert pytest.approx(rolling_mdd.iloc[4], abs=1e-4) == -0.20

    def test_dual_currency_metrics(self):
        dates = pd.date_range("2021-01-01", periods=20, freq="D")
        nav_usd = pd.Series(np.linspace(100.0, 120.0, 20), index=dates)
        # KRW FX depreciates from 1100 to 1200
        fx = np.linspace(1100.0, 1200.0, 20)
        nav_krw = nav_usd * fx

        metrics = PerformanceMetrics.calculate_dual_currency_metrics(nav_usd, nav_krw)
        assert "cagr_usd" in metrics
        assert "cagr_krw" in metrics
        assert "calmar_ratio_usd" in metrics
        assert "calmar_ratio_krw" in metrics
        assert "annual_table_usd" in metrics
        assert "annual_table_krw" in metrics
        # Because KRW depreciated, KRW return is higher than USD return
        assert metrics["total_return_krw"] > metrics["total_return_usd"]
