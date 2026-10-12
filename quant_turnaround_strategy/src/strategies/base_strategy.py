"""
Base Strategy implementation: Quantitative Turnaround Strategy.
Combines core ETF anchors (QQQ and SOXX) with opportunistic 52-week-low turnaround stocks.
- Baseline asset allocation: QQQ (50%), SOXX (30%), Turnaround stocks (up to 20%), Cash buffer.
- Portfolio capacity: 0 to 3 individual turnaround stocks (each ~6.67%).
- Turnaround idle policy: 'cash_buffer' (dry powder) or 'etf_sweep' (temporary deployment into ETFs).
- Risk rules: hard stop-loss (-12%), profit target (+35%), trailing stop (-10%), time stop (26 weeks / 130 days).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import date


@dataclass
class StrategyParameters:
    """Configurable parameters for the Quantitative Turnaround Strategy."""
    w_qqq_base: float = 0.50
    w_soxx_base: float = 0.30
    w_turnaround_max: float = 0.20
    w_cash_buffer: float = 0.00
    max_active_stocks: int = 3
    max_weekly_buy: int = 1
    turnaround_idle_policy: str = "cash_buffer"  # "cash_buffer" or "etf_sweep"

    # Entry thresholds
    low_52w_tolerance: float = 0.05
    min_turnaround_score: float = 70.0

    # Exit thresholds
    stop_loss_pct: float = -0.12
    profit_target_pct: float = 0.35
    trailing_stop_pct: float = 0.10
    max_holding_weeks: int = 26
    max_holding_days: int = 130

    def __post_init__(self):
        total_base = self.w_qqq_base + self.w_soxx_base + self.w_turnaround_max + self.w_cash_buffer
        if total_base > 1.0 + 1e-6:
            raise ValueError(f"Total base weights exceed 1.0: {total_base}")


class BaseStrategy:
    """
    Base Turnaround Strategy with weekly candidate selection and intra-week risk management.
    """

    def __init__(self, params: Optional[StrategyParameters] = None, **kwargs):
        if params is not None:
            self.params = params
        else:
            self.params = StrategyParameters(**kwargs)

    @property
    def max_active_stocks(self) -> int:
        return self.params.max_active_stocks

    @property
    def max_weekly_buy(self) -> int:
        return self.params.max_weekly_buy

    def compute_target_weights(
        self,
        active_turnaround_stocks: List[str],
        idle_policy: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Computes normalized target portfolio weights given currently held turnaround stocks.
        """
        policy = idle_policy or self.params.turnaround_idle_policy
        k = len(active_turnaround_stocks)
        stock_slot_weight = self.params.w_turnaround_max / self.params.max_active_stocks

        weights = {}
        for ticker in active_turnaround_stocks:
            weights[ticker] = stock_slot_weight

        unallocated_slots = self.params.max_active_stocks - k
        unallocated_weight = unallocated_slots * stock_slot_weight

        if policy == "etf_sweep":
            etf_base_sum = self.params.w_qqq_base + self.params.w_soxx_base
            sweep_qqq = self.params.w_qqq_base + unallocated_weight * (self.params.w_qqq_base / etf_base_sum)
            sweep_soxx = self.params.w_soxx_base + unallocated_weight * (self.params.w_soxx_base / etf_base_sum)
            weights["QQQ"] = sweep_qqq
            weights["SOXX"] = sweep_soxx
            weights["Cash"] = self.params.w_cash_buffer
        else:
            # cash_buffer
            weights["QQQ"] = self.params.w_qqq_base
            weights["SOXX"] = self.params.w_soxx_base
            weights["Cash"] = self.params.w_cash_buffer + unallocated_weight

        # Normalize weights to ensure invariant sum == 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6 and total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def should_buy_candidate(
        self,
        candidate_score: float,
        low_proximity: float,
        current_holdings_count: int,
    ) -> bool:
        """
        Verifies whether a candidate qualifies for weekly purchase.
        """
        if current_holdings_count >= self.params.max_active_stocks:
            return False
        if candidate_score < self.params.min_turnaround_score:
            return False
        if low_proximity > self.params.low_52w_tolerance:
            return False
        return True
