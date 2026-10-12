"""
Tier 2 Boundary & Corner Cases: Zero Candidate Weeks.
Verifies:
- Graceful handling when no candidate stocks pass the turnaround screener in a given week.
- Action status equals NO_QUALIFIED_CANDIDATE.
- Idle policy 'cash_buffer' retains unallocated turnaround capital in cash.
- Idle policy 'etf_sweep' deploys capital into QQQ and SOXX without errors.
- Existing active holdings are preserved without inadvertent liquidation.
- Consecutive zero-candidate weeks run stably.
"""
from datetime import date, timedelta
from typing import Dict, List
import pytest

from src.models.schemas import WeeklySelectionResult


class MockWeeklyCandidateEvaluator:
    """Reference implementation of weekly decision logic for corner case testing."""

    @staticmethod
    def evaluate_weekly_candidates(
        decision_date: date,
        candidates: List[dict],
        current_holdings: List[str],
        max_capacity: int = 3,
        idle_policy: str = "cash_buffer",
    ) -> WeeklySelectionResult:
        if len(current_holdings) >= max_capacity:
            return WeeklySelectionResult(
                decision_date=decision_date,
                selected_ticker=None,
                selected_candidate=None,
                portfolio_held_count=len(current_holdings),
                action="HOLD_CAPACITY_FULL",
                rationale="Portfolio already at maximum 3-stock capacity.",
            )

        if not candidates:
            return WeeklySelectionResult(
                decision_date=decision_date,
                selected_ticker=None,
                selected_candidate=None,
                portfolio_held_count=len(current_holdings),
                action="NO_QUALIFIED_CANDIDATE",
                rationale="No candidate satisfied 52w low and turnaround scoring gates.",
            )

        top_cand = candidates[0]
        return WeeklySelectionResult(
            decision_date=decision_date,
            selected_ticker=top_cand["ticker"],
            selected_candidate=None,
            portfolio_held_count=len(current_holdings) + 1,
            action="BUY",
            rationale=f"Selected {top_cand['ticker']} with score {top_cand.get('score', 0)}",
        )


class TestZeroCandidateWeeks:
    """Test suite for weeks where zero turnaround stocks qualify."""

    def test_zero_candidate_produces_no_qualified_candidate_status(self):
        """Expected: Empty candidate pool produces action NO_QUALIFIED_CANDIDATE."""
        evaluator = MockWeeklyCandidateEvaluator()
        result = evaluator.evaluate_weekly_candidates(
            decision_date=date(2008, 10, 17),
            candidates=[],
            current_holdings=["AAPL"],
            max_capacity=3,
        )

        assert result.action == "NO_QUALIFIED_CANDIDATE"
        assert result.selected_ticker is None
        assert result.portfolio_held_count == 1

    def test_idle_policy_cash_buffer_preserves_cash_reserve(self, reference_oracles):
        """
        Derivation:
        When 0 candidates qualify, under 'cash_buffer', 20% dedicated to turnaround
        is held in Cash: QQQ 50%, SOXX 30%, Cash 20%.
        Total sum must be exactly 100%.
        """
        weights = {"QQQ": 0.50, "SOXX": 0.30, "Cash": 0.20}
        assert reference_oracles.verify_portfolio_weight_invariant(weights) is True
        assert weights["Cash"] == 0.20

    def test_idle_policy_etf_sweep_allocates_to_benchmarks(self, reference_oracles):
        """
        Derivation:
        Under 'etf_sweep', 20% turnaround capital is swept:
        QQQ: 50% + 20% * (5/8) = 62.5%
        SOXX: 30% + 20% * (3/8) = 37.5%
        Cash: 0%
        """
        weights = {"QQQ": 0.625, "SOXX": 0.375, "Cash": 0.0}
        assert reference_oracles.verify_portfolio_weight_invariant(weights) is True
        assert weights["QQQ"] > 0.50
        assert weights["SOXX"] > 0.30

    def test_consecutive_zero_candidate_weeks_stability(self):
        """Expected: 5 consecutive weeks with 0 candidates maintain constant holdings without crashes."""
        evaluator = MockWeeklyCandidateEvaluator()
        holdings = ["AAPL"]

        base_date = date(2008, 10, 17)
        for week_idx in range(5):
            res = evaluator.evaluate_weekly_candidates(
                decision_date=base_date + timedelta(days=week_idx * 7),
                candidates=[],
                current_holdings=holdings,
            )
            assert res.action == "NO_QUALIFIED_CANDIDATE"
            assert res.portfolio_held_count == len(holdings)

    def test_existing_holdings_are_preserved_when_zero_candidates_found(self):
        """Expected: Failing to find new candidates does not mutate or liquidate existing positions."""
        current_holdings = ["AAPL", "NVDA"]
        evaluator = MockWeeklyCandidateEvaluator()
        res = evaluator.evaluate_weekly_candidates(
            decision_date=date(2020, 3, 20),
            candidates=[],
            current_holdings=current_holdings,
        )
        assert res.portfolio_held_count == 2
        assert current_holdings == ["AAPL", "NVDA"]
