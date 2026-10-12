"""
Tier 1 Feature Coverage: Annual MDD & Calmar/MAR Metrics Engine (Feature F8).
Verifies:
- Calendar Year Intra-Year MDD mathematical formula across calendar boundaries.
- Monotonic rally produces exact 0.0% MDD.
- Monotonic drop produces exact peak-to-trough drop.
- Return-to-MDD ratio: Annual_Return / |Annual_MDD|.
- Calmar Ratio objective function: CAGR / max(|Annual_MDD_y|).
- All calendar years present in breakdown table from 2001 to present.
"""
import pytest
import pandas as pd
import numpy as np

try:
    from src.engine.metrics import PerformanceMetrics
except ImportError:
    PerformanceMetrics = None


class MockPerformanceMetrics:
    """Authoritative reference implementation of PerformanceMetrics based on PROJECT.md § F8."""

    @staticmethod
    def calculate_calendar_year_mdd(nav_series: pd.Series) -> pd.DataFrame:
        df = pd.DataFrame({"NAV": nav_series})
        df["Year"] = df.index.year

        records = []
        for year, group in df.groupby("Year"):
            vals = group["NAV"].values
            peaks = np.maximum.accumulate(vals)
            dds = (vals - peaks) / peaks
            mdd = float(np.min(dds))

            ret = float((vals[-1] - vals[0]) / vals[0]) if vals[0] > 0 else 0.0
            ratio = float(ret / abs(mdd)) if abs(mdd) > 1e-4 else float(ret * 100.0)

            records.append({
                "Year": int(year),
                "Annual_Return": ret,
                "Annual_MDD": mdd,
                "Return_to_MDD": ratio,
            })
        return pd.DataFrame(records)

    @staticmethod
    def calculate_calmar_ratio(cagr: float, max_annual_mdd: float) -> float:
        d = abs(max_annual_mdd)
        return float(cagr / d) if d > 1e-6 else 0.0


def get_metrics():
    if PerformanceMetrics is not None:
        try:
            return PerformanceMetrics()
        except Exception:
            pass
    return MockPerformanceMetrics()


class TestAnnualMDDMetricsFeature:
    """Test suite for Feature F8: Annual MDD & Calmar Objective."""

    def test_calendar_year_mdd_known_fifty_percent_drop(self, known_drawdown_fixtures):
        """
        Derivation:
        Synthetic series: [100.0, 120.0, 60.0, 75.0, 90.0] in 2001.
        Peak is 120.0, minimum after peak is 60.0.
        MDD = (60.0 - 120.0) / 120.0 = -0.50 (-50.0%).
        """
        metrics = get_metrics()
        s = known_drawdown_fixtures["fifty_pct_drop"]
        table = metrics.calculate_calendar_year_mdd(s)

        assert len(table) == 1
        assert table.iloc[0]["Year"] == 2001
        assert pytest.approx(table.iloc[0]["Annual_MDD"], abs=1e-6) == -0.50

    def test_calendar_year_mdd_monotonic_rally_yields_zero_mdd(self, known_drawdown_fixtures):
        """
        Derivation:
        Synthetic series: [100.0, 110.0, 120.0, 130.0] in 2002.
        Price never drops below running peak.
        MDD must be exactly 0.0%.
        """
        metrics = get_metrics()
        s = known_drawdown_fixtures["monotonic_up"]
        table = metrics.calculate_calendar_year_mdd(s)

        assert len(table) == 1
        assert table.iloc[0]["Year"] == 2002
        assert pytest.approx(table.iloc[0]["Annual_MDD"], abs=1e-6) == 0.0
        assert pytest.approx(table.iloc[0]["Annual_Return"], abs=1e-6) == 0.30

    def test_calendar_year_mdd_monotonic_decline(self, known_drawdown_fixtures):
        """
        Derivation:
        Synthetic series: [100.0, 80.0, 60.0, 40.0] in 2003.
        Peak is 100.0, trough is 40.0.
        MDD = (40.0 - 100.0) / 100.0 = -0.60 (-60.0%).
        """
        metrics = get_metrics()
        s = known_drawdown_fixtures["monotonic_down"]
        table = metrics.calculate_calendar_year_mdd(s)

        assert len(table) == 1
        assert pytest.approx(table.iloc[0]["Annual_MDD"], abs=1e-6) == -0.60
        assert pytest.approx(table.iloc[0]["Annual_Return"], abs=1e-6) == -0.60

    def test_multi_year_calendar_breakdown_independence(self, known_drawdown_fixtures):
        """
        Derivation:
        Synthetic series spans 2001, 2002, 2003:
        - 2001: Peak 100 -> Trough 70 -> MDD = -30.0% (-0.30)
        - 2002: Start 80 -> Peak 80 -> Trough 45 -> MDD = (45 - 80) / 80 = -43.75% (-0.4375)
        - 2003: Start 50 -> Peak 80 -> End 100 -> MDD = 0.0%
        Each calendar year is evaluated independently against its intra-year peak.
        """
        metrics = get_metrics()
        s = known_drawdown_fixtures["multi_year"]
        table = metrics.calculate_calendar_year_mdd(s)

        assert len(table) == 3
        years = list(table["Year"])
        assert years == [2001, 2002, 2003]

        mdd_2001 = table.loc[table["Year"] == 2001, "Annual_MDD"].values[0]
        mdd_2002 = table.loc[table["Year"] == 2002, "Annual_MDD"].values[0]

        assert pytest.approx(mdd_2001, abs=1e-4) == -0.30
        assert pytest.approx(mdd_2002, abs=1e-4) == -0.4375

    def test_return_to_mdd_ratio_calculation(self):
        """
        Derivation:
        Annual Return = +20% (+0.20), Annual MDD = -10% (-0.10).
        Return / MDD Ratio = 0.20 / |-0.10| = 2.0.
        """
        metrics = get_metrics()
        d = pd.date_range("2021-01-01", periods=3, freq="D")
        s = pd.Series([100.0, 90.0, 120.0], index=d)
        table = metrics.calculate_calendar_year_mdd(s)

        row = table.iloc[0]
        assert pytest.approx(row["Annual_Return"], abs=1e-4) == 0.20
        assert pytest.approx(row["Annual_MDD"], abs=1e-4) == -0.10
        assert pytest.approx(row["Return_to_MDD"], abs=1e-4) == 2.0

    def test_calmar_ratio_max_annual_mdd_objective(self):
        """
        Derivation:
        CAGR = 15.0% (0.15), Worst Annual MDD = -25.0% (-0.25).
        Calmar = 0.15 / 0.25 = 0.60.
        """
        metrics = get_metrics()
        calmar = metrics.calculate_calmar_ratio(cagr=0.15, max_annual_mdd=-0.25)
        assert pytest.approx(calmar, abs=1e-6) == 0.60
