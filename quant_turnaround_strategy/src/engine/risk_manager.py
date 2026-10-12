"""
Intra-week risk management and position exit module.
Provides daily continuous monitoring of turnaround positions:
- Hard stop-loss (e.g. -12% from entry price).
- Profit target (e.g. +35% from entry price).
- Trailing stop (e.g. -10% from peak price).
- Max holding duration time stop (e.g. 130 trading days / 26 weeks).
- Collision resolution with priority: STOP_LOSS > TAKE_PROFIT > TRAILING_STOP > TIME_STOP.
- Overnight gap-down fill modeling.
"""
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ExitSignal:
    ticker: str
    exit_type: str  # "STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP", "TIME_STOP"
    trigger_price: float
    effective_price: float
    pnl_pct: float
    days_held: int
    gap_down: bool = False


class RiskManager:
    """
    Intra-week risk management engine for monitoring and liquidating active positions.
    """

    def __init__(
        self,
        stop_loss_pct: float = -0.12,
        profit_target_pct: float = 0.35,
        trailing_stop_pct: float = 0.10,
        max_holding_days: int = 130,
    ):
        self.stop_loss_pct = stop_loss_pct
        self.profit_target_pct = profit_target_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.max_holding_days = max_holding_days

    def evaluate_daily_exit(
        self,
        entry_price: float,
        current_price: float,
        peak_price: float,
        days_held: int,
    ) -> Optional[str]:
        """
        Evaluates daily exit conditions with strict priority hierarchy:
        1. Hard Stop-Loss (Capital preservation)
        2. Take-Profit (Target reached)
        3. Trailing Stop (Peak giveback protection)
        4. Time Stop (Holding duration exhaustion)
        """
        pnl_from_entry = (current_price - entry_price) / entry_price if entry_price > 0 else 0.0

        # 1. Hard stop-loss
        if pnl_from_entry <= self.stop_loss_pct:
            return "STOP_LOSS"

        # 2. Profit target
        if pnl_from_entry >= self.profit_target_pct:
            return "TAKE_PROFIT"

        # 3. Trailing stop from peak
        if peak_price > entry_price:
            dd_from_peak = (current_price - peak_price) / peak_price
            if dd_from_peak <= -self.trailing_stop_pct:
                return "TRAILING_STOP"

        # 4. Time stop
        if days_held >= self.max_holding_days:
            return "TIME_STOP"

        return None

    def resolve_exit_priorities(
        self,
        entry_price: float,
        current_price: float,
        peak_price: float,
        days_held: int,
        stop_loss_pct: Optional[float] = None,
        profit_target_pct: Optional[float] = None,
        trailing_stop_pct: Optional[float] = None,
        max_holding_days: Optional[int] = None,
    ) -> Optional[str]:
        """
        Class method / instance resolver for parameter-override exit evaluation.
        Strictly enforces collision resolution hierarchy:
        Priority 1: STOP_LOSS
        Priority 2: TAKE_PROFIT
        Priority 3: TRAILING_STOP
        Priority 4: TIME_STOP
        """
        sl = stop_loss_pct if stop_loss_pct is not None else self.stop_loss_pct
        pt = profit_target_pct if profit_target_pct is not None else self.profit_target_pct
        ts = trailing_stop_pct if trailing_stop_pct is not None else self.trailing_stop_pct
        md = max_holding_days if max_holding_days is not None else self.max_holding_days

        pnl = (current_price - entry_price) / entry_price if entry_price > 0 else 0.0

        if pnl <= sl:
            return "STOP_LOSS"

        if pnl >= pt:
            return "TAKE_PROFIT"

        if peak_price > entry_price and ((current_price - peak_price) / peak_price <= -ts):
            return "TRAILING_STOP"

        if days_held >= md:
            return "TIME_STOP"

        return None

    def check_overnight_gap(
        self,
        entry_price: float,
        open_price: float,
        prior_close: float,
    ) -> Tuple[bool, Optional[str]]:
        """
        Checks whether market opened below stop-loss price.
        Returns (is_gap_triggered, exit_reason).
        """
        pnl_at_open = (open_price - entry_price) / entry_price if entry_price > 0 else 0.0
        if pnl_at_open <= self.stop_loss_pct:
            return True, "STOP_LOSS"
        return False, None
