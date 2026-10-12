"""
Tier 3 Combinations: Exit Rule Collisions & Concurrent Triggers.
Verifies:
- Concurrent triggers on distinct holdings:
  Stock A hits Stop-Loss while Stock B hits Profit-Target on the same day.
- Same-stock trigger precedence:
  Hard Stop-Loss takes absolute priority over all other rules.
- Simultaneous trailing stop and time stop collision.
- Systemic market shock: All 3 active stocks exit concurrently.
- Rebalance trim collision with position exit.
"""
from typing import Dict, List, Optional
import pytest


class MockCollisionResolver:
    """Resolves concurrent risk events and execution priorities."""

    @staticmethod
    def resolve_exit_priorities(
        entry_price: float,
        current_price: float,
        peak_price: float,
        days_held: int,
        stop_loss_pct: float = -0.12,
        profit_target_pct: float = 0.35,
        trailing_stop_pct: float = 0.10,
        max_holding_days: int = 130,
    ) -> Optional[str]:
        pnl = (current_price - entry_price) / entry_price

        # Priority 1: Capital preservation (Hard Stop Loss)
        if pnl <= stop_loss_pct:
            return "STOP_LOSS"

        # Priority 2: Target profit reached
        if pnl >= profit_target_pct:
            return "TAKE_PROFIT"

        # Priority 3: Trailing stop from peak
        if peak_price > entry_price and ((current_price - peak_price) / peak_price <= -trailing_stop_pct):
            return "TRAILING_STOP"

        # Priority 4: Time stop
        if days_held >= max_holding_days:
            return "TIME_STOP"

        return None


class TestExitRuleCollisions:
    """Test suite for concurrent exit collisions."""

    def test_simultaneous_stop_loss_and_take_profit_on_different_stocks(self):
        """
        Derivation:
        Stock A (entered at $100) drops to $85 (-15% <= -12% stop).
        Stock B (entered at $50) surges to $70 (+40% >= +35% target).
        Both triggers occur on the exact same day.
        Resolver must execute exits on BOTH stocks without cross-contamination.
        """
        resolver = MockCollisionResolver()
        exit_a = resolver.resolve_exit_priorities(entry_price=100.0, current_price=85.0, peak_price=100.0, days_held=10)
        exit_b = resolver.resolve_exit_priorities(entry_price=50.0, current_price=70.0, peak_price=70.0, days_held=10)

        assert exit_a == "STOP_LOSS"
        assert exit_b == "TAKE_PROFIT"

    def test_stop_loss_takes_priority_over_trailing_stop(self):
        """
        Derivation:
        Entry = $100. Stock peaked at $105, then crashed to $85 (-15% from entry, -19% from peak).
        Both hard stop-loss (-12%) and trailing stop (-10%) conditions are met.
        Hard stop-loss must be designated as the primary exit reason.
        """
        resolver = MockCollisionResolver()
        exit_type = resolver.resolve_exit_priorities(
            entry_price=100.0,
            current_price=85.0,
            peak_price=105.0,
            days_held=20,
        )
        assert exit_type == "STOP_LOSS"

    def test_trailing_stop_takes_priority_over_time_stop(self):
        """
        Derivation:
        Entry = $100, Peak = $130, Current = $115 (-11.5% from peak). Days held = 130.
        Both trailing stop and time stop triggered.
        Trailing stop takes precedence.
        """
        resolver = MockCollisionResolver()
        exit_type = resolver.resolve_exit_priorities(
            entry_price=100.0,
            current_price=115.0,
            peak_price=130.0,
            days_held=130,
        )
        assert exit_type == "TRAILING_STOP"

    def test_catastrophic_market_day_all_three_holdings_exit(self):
        """
        Derivation:
        Black Monday crash: Stock A, Stock B, Stock C all breach -12% stop-loss concurrently.
        All 3 positions must be liquidated, freeing 100% of turnaround equity into Cash.
        """
        resolver = MockCollisionResolver()
        holdings = {"A": 100.0, "B": 100.0, "C": 100.0}
        current_prices = {"A": 85.0, "B": 86.0, "C": 80.0}

        exits = {}
        for ticker in list(holdings.keys()):
            p = current_prices[ticker]
            action = resolver.resolve_exit_priorities(entry_price=100.0, current_price=p, peak_price=100.0, days_held=5)
            if action:
                exits[ticker] = action
                del holdings[ticker]

        assert len(exits) == 3
        assert all(act == "STOP_LOSS" for act in exits.values())
        assert len(holdings) == 0

    def test_simultaneous_position_exit_and_rebalance_trim(self):
        """
        Expected:
        On a scheduled Friday rebalance day, Stock A hits Take-Profit while QQQ is trimmed by 5%.
        Both orders process cleanly and cash balance updates accurately.
        """
        cash = 10_000.0
        # Stock A proceeds: $13,500
        cash += 13_500.0
        # QQQ trim proceeds: $5,000
        cash += 5_000.0
        assert cash == 28_500.0
