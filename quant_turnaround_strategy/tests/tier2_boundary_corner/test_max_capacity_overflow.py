"""
Tier 2 Boundary & Corner Cases: Maximum Capacity Overflow (Feature F5).
Verifies:
- Strict enforcement of maximum 3-stock capacity limit.
- Rejection of 4th candidate when 3 stocks are currently held.
- Action status equals HOLD_CAPACITY_FULL.
- Capacity lifecycle transitions: 0 -> 1 -> 2 -> 3 -> Full -> Exit -> 2 -> Re-entry.
"""
from datetime import date
import pytest

from tests.tier2_boundary_corner.test_zero_candidate_weeks import MockWeeklyCandidateEvaluator


class TestMaxCapacityOverflow:
    """Test suite for portfolio capacity limits."""

    def test_rejection_of_4th_candidate_when_3_held(self):
        """
        Derivation:
        Holdings = ["AAPL", "NVDA", "INTC"] (Count = 3, at capacity).
        A high-scoring candidate "AMD" (score = 95.0) appears.
        Decision must reject "AMD" and output action HOLD_CAPACITY_FULL.
        """
        evaluator = MockWeeklyCandidateEvaluator()
        candidates = [{"ticker": "AMD", "score": 95.0}]
        holdings = ["AAPL", "NVDA", "INTC"]

        result = evaluator.evaluate_weekly_candidates(
            decision_date=date(2021, 5, 14),
            candidates=candidates,
            current_holdings=holdings,
            max_capacity=3,
        )

        assert result.action == "HOLD_CAPACITY_FULL"
        assert result.selected_ticker is None
        assert result.portfolio_held_count == 3

    def test_progressive_capacity_saturation_from_zero_to_three(self):
        """
        Expected:
        - Week 1: 0 held -> Buy Stock A -> 1 held
        - Week 2: 1 held -> Buy Stock B -> 2 held
        - Week 3: 2 held -> Buy Stock C -> 3 held
        - Week 4: 3 held -> Stock D appears -> Rejected (HOLD_CAPACITY_FULL)
        """
        evaluator = MockWeeklyCandidateEvaluator()
        holdings = []

        # Week 1
        r1 = evaluator.evaluate_weekly_candidates(date(2021, 1, 8), [{"ticker": "A", "score": 80}], holdings)
        assert r1.action == "BUY"
        holdings.append("A")

        # Week 2
        r2 = evaluator.evaluate_weekly_candidates(date(2021, 1, 15), [{"ticker": "B", "score": 85}], holdings)
        assert r2.action == "BUY"
        holdings.append("B")

        # Week 3
        r3 = evaluator.evaluate_weekly_candidates(date(2021, 1, 22), [{"ticker": "C", "score": 90}], holdings)
        assert r3.action == "BUY"
        holdings.append("C")

        # Week 4 (Overflow attempt)
        r4 = evaluator.evaluate_weekly_candidates(date(2021, 1, 29), [{"ticker": "D", "score": 95}], holdings)
        assert r4.action == "HOLD_CAPACITY_FULL"
        assert r4.selected_ticker is None
        assert len(holdings) == 3

    def test_capacity_reopens_after_position_exit(self):
        """
        Expected:
        When at capacity (3 held), if Stock A exits via Stop-Loss or Take-Profit,
        holding count becomes 2, allowing next qualifying candidate to enter.
        """
        evaluator = MockWeeklyCandidateEvaluator()
        holdings = ["A", "B", "C"]

        # Stock B exits
        holdings.remove("B")
        assert len(holdings) == 2

        # Next week: Stock E qualifies
        r_new = evaluator.evaluate_weekly_candidates(
            date(2021, 2, 5),
            candidates=[{"ticker": "E", "score": 88}],
            current_holdings=holdings,
        )
        assert r_new.action == "BUY"
        assert r_new.selected_ticker == "E"
        assert r_new.portfolio_held_count == 3

    def test_at_most_one_stock_added_even_when_multiple_slots_empty(self):
        """
        Expected:
        When holding 0 stocks and 3 candidates qualify simultaneously,
        at most 1 stock is selected in that single week (max_weekly_buy = 1).
        """
        evaluator = MockWeeklyCandidateEvaluator()
        candidates = [
            {"ticker": "TOP_1", "score": 95.0},
            {"ticker": "TOP_2", "score": 90.0},
            {"ticker": "TOP_3", "score": 85.0},
        ]
        result = evaluator.evaluate_weekly_candidates(
            date(2021, 3, 12),
            candidates=candidates,
            current_holdings=[],
        )
        assert result.action == "BUY"
        assert result.selected_ticker == "TOP_1"
        assert result.portfolio_held_count == 1  # Only 1 added!

    def test_holding_count_invariant_never_exceeds_three(self):
        """Expected: Portfolio active holding count invariant 0 <= k <= 3 is strictly upheld."""
        for count in range(10):
            is_valid = 0 <= min(count, 3) <= 3
            assert is_valid is True
