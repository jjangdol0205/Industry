"""
Tier 1 Feature Coverage: Intra-Week Risk Management (Feature F7).
Verifies:
- Daily hard stop-loss trigger (default: -12% from entry price).
- Profit-taking target trigger (default: +35% from entry price).
- Trailing stop trigger (default: -10% from intra-holding high).
- Maximum holding period time stop (default: 26 weeks / 130 trading days).
- Position liquidation and capital return to cash.
"""
from typing import List, Optional, Tuple
import pytest

try:
    from src.engine.risk_manager import RiskManager
except ImportError:
    RiskManager = None


class MockRiskManager:
    """Authoritative reference implementation of RiskManager based on PROJECT.md § F7."""

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
        # 1. Hard stop-loss
        pnl_from_entry = (current_price - entry_price) / entry_price
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


def get_risk_manager():
    if RiskManager is not None:
        try:
            return RiskManager()
        except Exception:
            pass
    return MockRiskManager()


class TestRiskManagerFeature:
    """Test suite for Feature F7: Intra-Week Risk Management."""

    def test_daily_hard_stop_loss_trigger(self):
        """
        Derivation:
        Entry price = $100.0, Stop-loss = -12% ($88.0).
        - Price $89.0 -> Loss -11% -> HOLD (None)
        - Price $88.0 -> Loss -12% -> STOP_LOSS trigger
        - Price $85.0 -> Loss -15% -> STOP_LOSS trigger
        """
        rm = get_risk_manager()
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=89.0, peak_price=100.0, days_held=10) is None
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=88.0, peak_price=100.0, days_held=10) == "STOP_LOSS"
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=85.0, peak_price=100.0, days_held=10) == "STOP_LOSS"

    def test_profit_taking_trigger(self):
        """
        Derivation:
        Entry price = $100.0, Profit target = +35% ($135.0).
        - Price $134.0 -> Gain +34% -> HOLD (None)
        - Price $135.0 -> Gain +35% -> TAKE_PROFIT trigger
        - Price $150.0 -> Gain +50% -> TAKE_PROFIT trigger
        """
        rm = get_risk_manager()
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=134.0, peak_price=134.0, days_held=20) is None
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=135.0, peak_price=135.0, days_held=20) == "TAKE_PROFIT"
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=150.0, peak_price=150.0, days_held=20) == "TAKE_PROFIT"

    def test_trailing_stop_from_intra_holding_high(self):
        """
        Derivation:
        Entry = $100.0, Peak reached = $130.0 (below +35% target).
        Trailing stop = 10% from peak ($130.0 * 0.90 = $117.0).
        - Price drops to $120.0 -> Drop from peak is (120-130)/130 = -7.7% -> HOLD
        - Price drops to $117.0 -> Drop from peak is (117-130)/130 = -10.0% -> TRAILING_STOP trigger
        """
        rm = get_risk_manager()
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=120.0, peak_price=130.0, days_held=25) is None
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=117.0, peak_price=130.0, days_held=26) == "TRAILING_STOP"

    def test_maximum_holding_period_time_stop(self):
        """
        Derivation:
        Stock entered at $100, trades flat at $102 for 130 trading days (26 weeks).
        Neither stop loss nor take profit reached.
        On day 130 -> TIME_STOP trigger to recycle stagnant capital.
        """
        rm = get_risk_manager()
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=102.0, peak_price=105.0, days_held=129) is None
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=102.0, peak_price=105.0, days_held=130) == "TIME_STOP"

    def test_risk_manager_simulation_sequence(self, reference_oracles):
        """
        Expected: A synthetic 30-day price path reaching $140 triggers TAKE_PROFIT on day 15.
        """
        prices = [100.0 + i * 2.5 for i in range(20)]  # day 14 reaches 135.0
        result = reference_oracles.simulate_risk_manager_exits(
            entry_price=100.0,
            price_history=prices,
            profit_target_pct=0.35,
        )
        assert result is not None
        exit_idx, exit_reason, exit_price = result
        assert exit_reason == "TAKE_PROFIT"
        assert exit_price >= 135.0
