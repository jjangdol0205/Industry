"""
Objective functions for parameter optimization and strategy evaluation.
Implements:
- Calmar Ratio: CAGR / max_Y |Annual_MDD_Y|
- MAR Ratio: Mean(Annual_Return) / Mean(|Annual_MDD|)
- Downside Penalized Compound Objective
"""
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


class ObjectiveFunction:
    """
    Standard quantitative objective functions for portfolio optimization.
    """

    @staticmethod
    def calmar_ratio(cagr: float, max_annual_mdd: float) -> float:
        """Calmar Ratio = CAGR / |max_annual_mdd|."""
        d = abs(max_annual_mdd)
        return float(cagr / d) if d > 1e-6 else 0.0

    @staticmethod
    def mar_ratio(annual_returns: pd.Series, annual_mdds: pd.Series) -> float:
        """MAR Ratio = Mean(Annual Return) / Mean(|Annual MDD|)."""
        mean_ret = annual_returns.mean()
        mean_mdd = annual_mdds.abs().mean()
        return float(mean_ret / mean_mdd) if mean_mdd > 1e-6 else 0.0

    @staticmethod
    def compound_objective(
        cagr: float,
        max_annual_mdd: float,
        avg_annual_mdd: float,
        lambda_max: float = 0.5,
        lambda_avg: float = 0.5,
    ) -> float:
        """
        Compound risk-adjusted score penalizing tail drawdown:
        J = CAGR - lambda_max * |max_mdd| - lambda_avg * |avg_mdd|.
        """
        return float(cagr - lambda_max * abs(max_annual_mdd) - lambda_avg * abs(avg_annual_mdd))

    @classmethod
    def evaluate(cls, run_stats: Dict[str, Any], metric: str = "calmar_max") -> float:
        """Evaluates a strategy backtest run against the target objective metric."""
        cagr = run_stats.get("cagr", 0.0)
        max_mdd = run_stats.get("max_annual_mdd", run_stats.get("mdd", -1.0))
        if metric in ["calmar", "calmar_max"]:
            return cls.calmar_ratio(cagr, max_mdd)
        elif metric == "cagr":
            return cagr
        elif metric == "sharpe":
            return run_stats.get("sharpe", 0.0)
        else:
            return cls.calmar_ratio(cagr, max_mdd)
