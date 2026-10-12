"""
Walk-Forward Analysis (WFA) cross-validation optimization module.
Mitigates backtest data-snooping and curve-fitting bias by dividing historical data
into rolling In-Sample (5-year training) and Out-of-Sample (1-year testing) windows.
Calculates Walk-Forward Efficiency (WFE) across 20+ historical periods.
"""
from dataclasses import dataclass, field
from typing import Tuple, Dict, List, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardPeriodResult:
    period_idx: int
    is_start_year: int
    is_end_year: int
    oos_year: int
    best_is_params: Dict[str, Any]
    cagr_is: float
    mdd_is: float
    calmar_is: float
    cagr_oos: float
    mdd_oos: float
    calmar_oos: float
    wfe: float


@dataclass
class WalkForwardResult:
    periods: List[WalkForwardPeriodResult]
    mean_wfe: float
    is_robust: bool  # True if mean_wfe >= 0.60
    total_periods: int


class WalkForwardOptimizer:
    """
    Rolling Walk-Forward Analysis engine for parameter validation.
    """

    def __init__(self, is_years: int = 5, oos_years: int = 1, step_years: int = 1):
        self.is_years = is_years
        self.oos_years = oos_years
        self.step_years = step_years

    def generate_rolling_windows(
        self,
        start_year: int = 2001,
        end_year: int = 2026,
    ) -> List[Dict[str, Any]]:
        """
        Generates rolling (IS, OOS) window boundaries across calendar years.
        For start=2001, end=2026, 5y IS, 1y OOS: generates 21 windows.
        """
        windows = []
        curr_train_start = start_year
        while curr_train_start + self.is_years + self.oos_years <= end_year + 1:
            train_end = curr_train_start + self.is_years - 1
            test_year = train_end + 1
            windows.append({
                "is_start_year": curr_train_start,
                "is_end_year": train_end,
                "oos_year": test_year,
            })
            curr_train_start += self.step_years
        return windows

    def compute_walk_forward_efficiency(
        self,
        cagr_is: float,
        cagr_oos: float,
        mdd_is: float,
        mdd_oos: float,
    ) -> float:
        """
        Walk-Forward Efficiency (WFE):
        WFE = (CAGR_OOS / CAGR_IS) * (|MDD_IS| / |MDD_OOS|)
        A ratio >= 0.60 indicates a statistically robust, generalizable strategy.
        """
        cagr_ratio = cagr_oos / cagr_is if cagr_is > 0 else 0.0
        mdd_ratio = abs(mdd_is) / abs(mdd_oos) if abs(mdd_oos) > 0 else 1.0
        return float(cagr_ratio * mdd_ratio)

    def run_walk_forward(
        self,
        grid_search_fn: Callable[[int, int], Tuple[Dict[str, Any], float, float]],
        evaluate_oos_fn: Callable[[int, Dict[str, Any]], Tuple[float, float]],
        start_year: int = 2001,
        end_year: int = 2026,
    ) -> WalkForwardResult:
        """
        Executes complete rolling walk-forward analysis.
        """
        windows = self.generate_rolling_windows(start_year, end_year)
        period_results: List[WalkForwardPeriodResult] = []

        for idx, win in enumerate(windows):
            is_start = win["is_start_year"]
            is_end = win["is_end_year"]
            oos_yr = win["oos_year"]

            # Train on IS
            best_params, cagr_is, mdd_is = grid_search_fn(is_start, is_end)
            calmar_is = cagr_is / abs(mdd_is) if abs(mdd_is) > 1e-6 else 0.0

            # Test on OOS
            cagr_oos, mdd_oos = evaluate_oos_fn(oos_yr, best_params)
            calmar_oos = cagr_oos / abs(mdd_oos) if abs(mdd_oos) > 1e-6 else 0.0

            wfe = self.compute_walk_forward_efficiency(cagr_is, cagr_oos, mdd_is, mdd_oos)

            period_results.append(WalkForwardPeriodResult(
                period_idx=idx + 1,
                is_start_year=is_start,
                is_end_year=is_end,
                oos_year=oos_yr,
                best_is_params=best_params,
                cagr_is=cagr_is,
                mdd_is=mdd_is,
                calmar_is=calmar_is,
                cagr_oos=cagr_oos,
                mdd_oos=mdd_oos,
                calmar_oos=calmar_oos,
                wfe=wfe,
            ))

        mean_wfe = sum(p.wfe for p in period_results) / len(period_results) if period_results else 0.0
        is_robust = mean_wfe >= 0.60

        return WalkForwardResult(
            periods=period_results,
            mean_wfe=mean_wfe,
            is_robust=is_robust,
            total_periods=len(period_results),
        )
