"""
Performance metrics and risk-adjusted return calculations module.
Specializes in:
- Calendar Year Intra-Year MDD (2001 to present).
- Rolling 1-Year MDD (252-day window).
- Annual Return and Return / Annual MDD ratio.
- Calmar Ratio objective function: CAGR / max_Y |Annual_MDD_Y|.
- Dual-currency performance reporting in USD and KRW.
"""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd


class PerformanceMetrics:
    """
    Quantitative performance metrics calculator.
    """

    @staticmethod
    def calculate_calendar_year_mdd(nav_series: pd.Series) -> pd.DataFrame:
        """
        Calculates intra-year Maximum Drawdown (MDD) for every calendar year independently:
        MDD_y = min_{t in y} (V(t) - max_{s <= t} V(s)) / max_{s <= t} V(s).
        Returns a DataFrame with columns:
        ['Year', 'Annual_Return', 'Annual_MDD', 'Return_to_MDD'].
        """
        if nav_series.empty:
            return pd.DataFrame(columns=["Year", "Annual_Return", "Annual_MDD", "Return_to_MDD"])

        df = pd.DataFrame({"NAV": nav_series})
        df["Year"] = df.index.year

        records = []
        for year, group in df.groupby("Year"):
            vals = group["NAV"].values.astype(float)
            if len(vals) == 0:
                continue

            peaks = np.maximum.accumulate(vals)
            dds = (vals - peaks) / peaks
            mdd = float(np.min(dds))

            start_val = vals[0]
            end_val = vals[-1]
            ret = float((end_val - start_val) / start_val) if start_val > 0 else 0.0

            if abs(mdd) > 1e-4:
                ratio = float(ret / abs(mdd))
            else:
                ratio = float(ret * 100.0)

            records.append({
                "Year": int(year),
                "Annual_Return": ret,
                "Annual_MDD": mdd,
                "Return_to_MDD": ratio,
            })

        return pd.DataFrame(records)

    @staticmethod
    def calculate_calmar_ratio(cagr: float, max_annual_mdd: float) -> float:
        """
        Calmar Ratio relative to maximum annual MDD:
        Calmar = CAGR / max_y |Annual_MDD_y|.
        """
        d = abs(max_annual_mdd)
        return float(cagr / d) if d > 1e-6 else 0.0

    @staticmethod
    def calculate_cagr(nav_series: pd.Series) -> float:
        """
        Compound Annual Growth Rate (CAGR) from start to end date.
        """
        if len(nav_series) < 2:
            return 0.0
        start_val = float(nav_series.iloc[0])
        end_val = float(nav_series.iloc[-1])
        if start_val <= 0 or end_val <= 0:
            return 0.0

        start_date = nav_series.index[0]
        end_date = nav_series.index[-1]
        days = (end_date - start_date).days
        years = days / 365.25
        if years <= 0:
            return 0.0
        return float((end_val / start_val) ** (1.0 / years) - 1.0)

    @staticmethod
    def calculate_rolling_mdd(nav_series: pd.Series, window: int = 252) -> pd.Series:
        """
        Calculates boundary-free rolling 252-day Maximum Drawdown.
        """
        rolling_peaks = nav_series.rolling(window=window, min_periods=1).max()
        rolling_dds = (nav_series - rolling_peaks) / rolling_peaks
        return rolling_dds

    @staticmethod
    def calculate_overall_mdd(nav_series: pd.Series) -> float:
        """
        Peak-to-trough Maximum Drawdown over the entire time horizon.
        """
        if nav_series.empty:
            return 0.0
        peaks = nav_series.cummax()
        dds = (nav_series - peaks) / peaks
        return float(dds.min())

    @staticmethod
    def calculate_sharpe_ratio(nav_series: pd.Series, rf_annual: float = 0.02) -> float:
        """
        Annualized Sharpe ratio.
        """
        daily_returns = nav_series.pct_change().dropna()
        if len(daily_returns) < 5:
            return 0.0
        rf_daily = rf_annual / 252.0
        excess_returns = daily_returns - rf_daily
        std = excess_returns.std()
        if std <= 1e-8:
            return 0.0
        return float(np.sqrt(252.0) * excess_returns.mean() / std)

    @staticmethod
    def calculate_mar_ratio(annual_df: pd.DataFrame) -> float:
        """
        MAR Ratio = Mean Annual Return / Mean Annual MDD.
        """
        if annual_df.empty or "Annual_Return" not in annual_df.columns:
            return 0.0
        mean_ret = annual_df["Annual_Return"].mean()
        mean_mdd = annual_df["Annual_MDD"].abs().mean()
        return float(mean_ret / mean_mdd) if mean_mdd > 1e-6 else 0.0

    @classmethod
    def calculate_summary_metrics(
        cls,
        nav_series: pd.Series,
        label: str = "USD",
    ) -> Dict[str, Any]:
        """
        Comprehensive summary metrics for a NAV series.
        """
        annual_table = cls.calculate_calendar_year_mdd(nav_series)
        cagr = cls.calculate_cagr(nav_series)
        max_ann_mdd = float(annual_table["Annual_MDD"].min()) if not annual_table.empty else 0.0
        calmar = cls.calculate_calmar_ratio(cagr, max_ann_mdd)
        mar = cls.calculate_mar_ratio(annual_table)
        sharpe = cls.calculate_sharpe_ratio(nav_series)
        overall_mdd = cls.calculate_overall_mdd(nav_series)
        tot_ret = float((nav_series.iloc[-1] - nav_series.iloc[0]) / nav_series.iloc[0]) if len(nav_series) > 1 else 0.0

        return {
            f"total_return_{label}": tot_ret,
            f"cagr_{label}": cagr,
            f"max_annual_mdd_{label}": max_ann_mdd,
            f"overall_mdd_{label}": overall_mdd,
            f"calmar_ratio_{label}": calmar,
            f"mar_ratio_{label}": mar,
            f"sharpe_ratio_{label}": sharpe,
            f"annual_table_{label}": annual_table,
        }

    @classmethod
    def calculate_dual_currency_metrics(
        cls,
        nav_usd: pd.Series,
        nav_krw: pd.Series,
    ) -> Dict[str, Any]:
        """
        Calculates side-by-side performance metrics in both USD and KRW.
        """
        metrics_usd = cls.calculate_summary_metrics(nav_usd, label="usd")
        metrics_krw = cls.calculate_summary_metrics(nav_krw, label="krw")

        combined = {}
        combined.update(metrics_usd)
        combined.update(metrics_krw)
        return combined
