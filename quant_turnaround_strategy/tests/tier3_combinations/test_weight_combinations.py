"""
Tier 3 Combinations: Portfolio Weight Invariants Across Permutations.
Verifies:
- Fundamental portfolio invariant: sum(w_i) + w_cash = 1.0 +- 1e-6 across all asset permutations.
- Tests permutations of QQQ (20-60%), SOXX (20-50%), Turnaround Stocks (0-3 at 5-10% each), and Cash.
- Invariant holds before, during, and after trading friction deductions.
- Invariant holds when asset prices move violently (e.g., individual stock rallies +100% or drops -50%).
"""
import itertools
from typing import Dict, List
import pytest
import numpy as np


class TestWeightCombinations:
    """Test suite for portfolio weight invariants."""

    def test_weight_invariant_across_standard_grid_permutations(self, reference_oracles):
        """
        Derivation:
        Iterate across discrete target grids:
        w_qqq in [0.30, 0.40, 0.50]
        w_soxx in [0.20, 0.30]
        w_turnaround_pool in [0.10, 0.20]
        w_cash = 1.0 - (w_qqq + w_soxx + w_turnaround_pool)
        Assert sum(w) == 1.0 +- 1e-6 for every single combination.
        """
        qqq_grid = [0.30, 0.40, 0.50]
        soxx_grid = [0.20, 0.30]
        turnaround_grid = [0.10, 0.20]

        for w_q, w_s, w_t in itertools.product(qqq_grid, soxx_grid, turnaround_grid):
            if w_q + w_s + w_t <= 1.0:
                w_cash = 1.0 - (w_q + w_s + w_t)
                weights = {"QQQ": w_q, "SOXX": w_s, "Turnaround": w_t, "Cash": w_cash}
                assert reference_oracles.verify_portfolio_weight_invariant(weights) is True

    def test_weight_invariant_with_three_individual_stocks(self, reference_oracles):
        """
        Derivation:
        Portfolio holds QQQ (45%), SOXX (25%), Cash (6%),
        and 3 individual turnaround stocks: AAPL (8%), NVDA (8%), INTC (8%).
        Sum = 45 + 25 + 6 + 8 + 8 + 8 = 100%.
        """
        weights = {
            "QQQ": 0.45,
            "SOXX": 0.25,
            "AAPL": 0.08,
            "NVDA": 0.08,
            "INTC": 0.08,
            "Cash": 0.06,
        }
        assert reference_oracles.verify_portfolio_weight_invariant(weights) is True

    def test_weight_invariant_after_drastic_asset_price_shocks(self, reference_oracles):
        """
        Derivation:
        Initial NAV = $100,000.
        Positions: QQQ $40k, SOXX $30k, StockA $10k, StockB $10k, Cash $10k.
        Shock:
        - StockA rallies +150% ($10k -> $25k)
        - StockB drops -40% ($10k -> $6k)
        - SOXX drops -10% ($30k -> $27k)
        - QQQ rallies +5% ($40k -> $42k)
        - Cash remains $10k.
        New NAV = 25k + 6k + 27k + 42k + 10k = $110k.
        Each weight w_i = Value_i / NAV.
        Sum of new weights must still strictly equal 1.0 +- 1e-6!
        """
        new_values = {
            "QQQ": 42_000.0,
            "SOXX": 27_000.0,
            "StockA": 25_000.0,
            "StockB": 6_000.0,
            "Cash": 10_000.0,
        }
        nav = sum(new_values.values())
        weights = {k: v / nav for k, v in new_values.items()}

        assert nav == 110_000.0
        assert reference_oracles.verify_portfolio_weight_invariant(weights) is True

    def test_weight_invariant_after_deducting_trading_fees(self, reference_oracles):
        """
        Derivation:
        When rebalancing incurs 5 bps commission and 10 bps slippage,
        trading costs are deducted from cash.
        Total NAV = New_Asset_Values + Reduced_Cash.
        Weights computed against this updated NAV must sum to exactly 1.0.
        """
        asset_values = {"QQQ": 50_000.0, "SOXX": 30_000.0, "Stock": 15_000.0}
        initial_cash = 5_000.0
        friction_cost = 45.0  # Fees deducted
        final_cash = initial_cash - friction_cost

        nav = sum(asset_values.values()) + final_cash
        weights = {k: v / nav for k, v in asset_values.items()}
        weights["Cash"] = final_cash / nav

        assert reference_oracles.verify_portfolio_weight_invariant(weights) is True

    def test_zero_equity_full_cash_regime_invariant(self, reference_oracles):
        """Expected: In 100% Cash defensive preservation regime, weights sum to 1.0."""
        weights = {"QQQ": 0.0, "SOXX": 0.0, "Cash": 1.0}
        assert reference_oracles.verify_portfolio_weight_invariant(weights) is True
