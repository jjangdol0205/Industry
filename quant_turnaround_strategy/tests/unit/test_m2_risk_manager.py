"""
Unit test suite for M2 Intra-Week Risk Management (src/engine/risk_manager.py).
Verifies:
- Daily hard stop-loss trigger at -12%.
- Profit target trigger at +35%.
- Trailing stop trigger at -10% from peak.
- Max holding period time stop at 130 trading days.
- Priority collision resolution hierarchy: STOP_LOSS > TAKE_PROFIT > TRAILING_STOP > TIME_STOP.
- Overnight gap-down fill detection.
"""
import pytest
from src.engine.risk_manager import RiskManager


class TestRiskManagerUnit:
    def test_hard_stop_loss_boundary(self):
        rm = RiskManager(stop_loss_pct=-0.12)
        # Entry $100. Stop is at $88.0
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=88.5, peak_price=100.0, days_held=5) is None
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=88.0, peak_price=100.0, days_held=5) == "STOP_LOSS"
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=85.0, peak_price=100.0, days_held=5) == "STOP_LOSS"

    def test_profit_taking_boundary(self):
        rm = RiskManager(profit_target_pct=0.35)
        # Entry $100. Target is $135.0
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=134.9, peak_price=134.9, days_held=20) is None
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=135.0, peak_price=135.0, days_held=20) == "TAKE_PROFIT"
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=140.0, peak_price=140.0, days_held=20) == "TAKE_PROFIT"

    def test_trailing_stop_from_intra_holding_peak(self):
        rm = RiskManager(trailing_stop_pct=0.10)
        # Entry $100. Peaked at $120. Trailing stop is at $120 * 0.90 = $108.0
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=110.0, peak_price=120.0, days_held=30) is None
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=108.0, peak_price=120.0, days_held=30) == "TRAILING_STOP"
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=105.0, peak_price=120.0, days_held=30) == "TRAILING_STOP"

    def test_max_holding_period_time_stop(self):
        rm = RiskManager(max_holding_days=130)
        # Price is unchanged at $105. No stop loss, profit target, or trailing stop
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=105.0, peak_price=105.0, days_held=129) is None
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=105.0, peak_price=105.0, days_held=130) == "TIME_STOP"
        assert rm.evaluate_daily_exit(entry_price=100.0, current_price=105.0, peak_price=105.0, days_held=131) == "TIME_STOP"

    def test_collision_resolution_priorities(self):
        rm = RiskManager(stop_loss_pct=-0.12, profit_target_pct=0.35, trailing_stop_pct=0.10, max_holding_days=130)

        # 1. STOP_LOSS takes priority over TRAILING_STOP and TIME_STOP
        # Entry 100, Peak 110, Current 85 (-15% from entry, -22% from peak, days 135)
        exit1 = rm.resolve_exit_priorities(entry_price=100.0, current_price=85.0, peak_price=110.0, days_held=135)
        assert exit1 == "STOP_LOSS"

        # 2. TAKE_PROFIT takes priority over TIME_STOP
        # Entry 100, Peak 140, Current 140 (+40%, days 135)
        exit2 = rm.resolve_exit_priorities(entry_price=100.0, current_price=140.0, peak_price=140.0, days_held=135)
        assert exit2 == "TAKE_PROFIT"

        # 3. TRAILING_STOP takes priority over TIME_STOP
        # Entry 100, Peak 130, Current 115 (-11.5% from peak, days 135)
        exit3 = rm.resolve_exit_priorities(entry_price=100.0, current_price=115.0, peak_price=130.0, days_held=135)
        assert exit3 == "TRAILING_STOP"

    def test_overnight_gap_down_check(self):
        rm = RiskManager(stop_loss_pct=-0.12)
        # Entry $100. Prior close $92. Open $85 (-15% <= -12%)
        is_gap, reason = rm.check_overnight_gap(entry_price=100.0, open_price=85.0, prior_close=92.0)
        assert is_gap is True
        assert reason == "STOP_LOSS"

        # Open $90 (-10% > -12%) -> No gap exit
        is_gap2, reason2 = rm.check_overnight_gap(entry_price=100.0, open_price=90.0, prior_close=92.0)
        assert is_gap2 is False
        assert reason2 is None
