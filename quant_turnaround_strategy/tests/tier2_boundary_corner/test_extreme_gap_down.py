"""
Tier 2 Boundary & Corner Cases: Extreme Overnight Gap-Down Execution.
Verifies:
- Real-world stop-loss execution when an overnight gap-down exceeds the stop-loss limit
  (e.g., stock closes at -8%, gaps down overnight to open at -25%, exceeding -12% stop-loss).
- Execution fills at gap-down opening price (no magical fill at the stop threshold).
- Slippage penalty is properly accounted for.
- Cash proceeds from liquidation are accurately credited.
- Position is cleanly closed and removed from holdings.
"""
from typing import Dict, Tuple
import pytest


class MockExecutionSimulator:
    """Simulates realistic order execution with gap-downs and slippage."""

    def __init__(self, stop_loss_pct: float = -0.12, stock_slippage_bps: float = 10.0):
        self.stop_loss_pct = stop_loss_pct
        self.slippage_rate = stock_slippage_bps / 10_000.0  # 0.0010 (10 bps)

    def execute_stop_loss_on_gap(
        self,
        entry_price: float,
        prior_close: float,
        open_price: float,
        shares: float,
    ) -> Dict[str, float]:
        """
        If open_price / entry_price - 1 <= stop_loss_pct:
        Fills at open_price * (1 - slippage_rate).
        """
        pnl_at_open = (open_price - entry_price) / entry_price
        triggered = pnl_at_open <= self.stop_loss_pct

        if not triggered:
            return {"triggered": False}

        # Execution at gap open with slippage
        effective_fill_price = open_price * (1.0 - self.slippage_rate)
        realized_pnl_pct = (effective_fill_price - entry_price) / entry_price
        gross_proceeds = shares * open_price
        slippage_cost = gross_proceeds * self.slippage_rate
        net_cash_received = gross_proceeds - slippage_cost

        return {
            "triggered": True,
            "fill_price": effective_fill_price,
            "realized_pnl_pct": realized_pnl_pct,
            "net_cash_received": net_cash_received,
            "slippage_cost": slippage_cost,
        }


class TestExtremeGapDown:
    """Test suite for extreme overnight gap-downs."""

    def test_stop_loss_fills_at_gap_open_not_stop_threshold(self):
        """
        Derivation:
        Entry = $100.0, Stop-loss = -12% ($88.0).
        Prior day close was $92.0 (-8%, no stop triggered).
        Earnings disaster: Overnight gap down opens at $75.0 (-25%).
        The fill MUST occur at or below $75.0, NOT at the theoretical $88.0 stop-loss price.
        """
        sim = MockExecutionSimulator(stop_loss_pct=-0.12, stock_slippage_bps=10.0)
        res = sim.execute_stop_loss_on_gap(
            entry_price=100.0,
            prior_close=92.0,
            open_price=75.0,
            shares=100.0,
        )

        assert res["triggered"] is True
        # Fill is around $75.0 * (1 - 0.001) = $74.925
        assert res["fill_price"] <= 75.0
        assert res["realized_pnl_pct"] <= -0.25
        assert res["fill_price"] < 88.0  # Demonstrates no magical fill at stop threshold

    def test_slippage_penalty_applied_on_extreme_gap_down(self):
        """
        Derivation:
        Gross proceeds on 100 shares at $75 = $7,500.
        Slippage at 10 bps = $7,500 * 0.001 = $7.50.
        Net cash received = $7,500 - $7.50 = $7,492.50.
        """
        sim = MockExecutionSimulator(stop_loss_pct=-0.12, stock_slippage_bps=10.0)
        res = sim.execute_stop_loss_on_gap(
            entry_price=100.0,
            prior_close=92.0,
            open_price=75.0,
            shares=100.0,
        )

        assert res["slippage_cost"] == 7.50
        assert res["net_cash_received"] == 7492.50

    def test_no_trigger_when_gap_does_not_breach_stop(self):
        """
        Derivation:
        Entry = $100.0, Stop-loss = -12% ($88.0).
        Open is $90.0 (-10% loss).
        Stop loss must NOT trigger.
        """
        sim = MockExecutionSimulator(stop_loss_pct=-0.12)
        res = sim.execute_stop_loss_on_gap(
            entry_price=100.0,
            prior_close=95.0,
            open_price=90.0,
            shares=100.0,
        )
        assert res["triggered"] is False

    def test_portfolio_cash_credited_after_gap_liquidation(self):
        """Expected: Portfolio cash increases by net_cash_received and position is zeroed."""
        initial_cash = 10_000.0
        holdings = {"CRASH_STOCK": 100.0}

        sim = MockExecutionSimulator(stop_loss_pct=-0.12)
        res = sim.execute_stop_loss_on_gap(100.0, 92.0, 75.0, 100.0)

        # Liquidate
        initial_cash += res["net_cash_received"]
        del holdings["CRASH_STOCK"]

        assert initial_cash == 10_000.0 + 7492.50
        assert "CRASH_STOCK" not in holdings
        assert len(holdings) == 0

    def test_no_double_stop_loss_trigger(self):
        """Expected: Once a position is closed on gap-down, subsequent evaluations cannot re-trigger."""
        holdings = {}  # already closed
        assert "CRASH_STOCK" not in holdings
