"""
Exclusion Gates for discretionary risk-reward filtering.
Enforces liquidity, solvency, momentum drop limits, sector concentration, and history.
"""
from typing import List, Dict, Optional, Tuple, Set
import logging

from config.settings import DEFAULT_MIN_DOLLAR_VOLUME
from src.models.schemas import ExclusionReason

logger = logging.getLogger(__name__)


class ExclusionGates:
    """
    Applies strict risk-reward filter gates to candidate stocks.
    """

    def __init__(
        self,
        min_dollar_volume: float = DEFAULT_MIN_DOLLAR_VOLUME,
        max_30d_drop: float = -0.50,  # Max -50% 30-day drop
        min_5d_return: float = -0.05,  # Min -5% 5-day return
        min_rsi: float = 20.0,
        min_solvency_score: float = 0.40,
        min_turnaround_score: float = 0.50,
        max_stocks_per_sector: int = 1,
    ):
        self.min_dollar_volume = min_dollar_volume
        self.max_30d_drop = max_30d_drop
        self.min_5d_return = min_5d_return
        self.min_rsi = min_rsi
        self.min_solvency_score = min_solvency_score
        self.min_turnaround_score = min_turnaround_score
        self.max_stocks_per_sector = max_stocks_per_sector

    def check_liquidity(self, avg_dollar_volume: float) -> bool:
        """
        Returns True if 20-day average dollar volume satisfies the minimum threshold.
        """
        return avg_dollar_volume >= self.min_dollar_volume

    def evaluate_gates(
        self,
        ticker: str,
        sector: str,
        current_holdings: List[str],
        current_holding_sectors: List[str],
        metrics: Dict[str, float],
    ) -> Tuple[bool, List[ExclusionReason]]:
        """
        Evaluates candidate against all risk-reward exclusion gates.
        Returns (passed_all, list_of_exclusion_reasons).
        """
        reasons: List[ExclusionReason] = []

        # Gate 0: Already Held
        if ticker.upper() in [h.upper() for h in current_holdings]:
            reasons.append(ExclusionReason.ALREADY_HELD)

        # Gate 1: Liquidity ($20M 20-day Average Dollar Volume)
        avg_dv = metrics.get("avg_dollar_volume_20d", 0.0)
        # Exclude stocks below threshold (including $0 volume / halted / dead stocks)
        if avg_dv < self.min_dollar_volume:
            reasons.append(ExclusionReason.ILLIQUID)

        # Gate 2: Momentum / Falling Knife
        ret_5d = metrics.get("return_5d", 0.0)
        ret_30d = metrics.get("return_30d", 0.0)
        rsi = metrics.get("rsi_14", 50.0)

        if ret_30d < self.max_30d_drop or ret_5d < self.min_5d_return or rsi < self.min_rsi:
            reasons.append(ExclusionReason.FALLING_KNIFE)

        # Gate 3: Solvency Risk
        solvency_score = metrics.get("solvency_score", 0.50)
        if solvency_score < self.min_solvency_score:
            reasons.append(ExclusionReason.SOLVENCY_RISK)

        # Gate 4: Turnaround Score Quality
        turnaround_score = metrics.get("turnaround_score", 0.50)
        if turnaround_score < self.min_turnaround_score:
            reasons.append(ExclusionReason.LOW_TURNAROUND_SCORE)

        # Gate 5: Sector Concentration Limit (Max 1 per GICS sector in portfolio)
        if sector and sector != "Unknown" and current_holding_sectors:
            sector_count = current_holding_sectors.count(sector)
            if sector_count >= self.max_stocks_per_sector:
                reasons.append(ExclusionReason.SECTOR_CAPACITY)

        passed = len(reasons) == 0
        return passed, reasons
