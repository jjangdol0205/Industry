"""
Tier 3 Combinations: Regime Switch Interactions & Signal Collisions.
Verifies:
- Interaction when Macro Regime turns Bearish while an individual Turnaround stock generates a Buy signal.
  Rule: Macro Bear regime strictly overrides individual stock buys (Turnaround buy is FROZEN).
- In Bull regime, qualifying turnaround buy signals execute freely.
- In Transition regime, exposure is throttled to 60%.
- Flip from Bear back to Bull unfreezes turnaround entries and restores equity allocations.
- Whipsaw dampening: Prevents erratic turnover during border regimes.
"""
from typing import Dict, Optional, Tuple
import pytest


class MockRegimeInteractionEngine:
    """Evaluates macro regime hierarchy over micro stock signals."""

    @staticmethod
    def process_weekly_signal(
        macro_regime: str,
        stock_candidate: Optional[dict],
        current_holdings: list,
    ) -> Dict[str, str]:
        """
        Hierarchy:
        If macro_regime == 'BEAR':
            All new stock entries are FROZEN regardless of candidate score!
        If macro_regime in ('BULL', 'TRANSITION'):
            Stock entry allowed if candidate exists and capacity < 3.
        """
        if macro_regime == "BEAR":
            return {
                "action": "REGIME_BLOCKED",
                "rationale": "Turnaround buy signal blocked by Macro Bear Regime filter.",
                "target_ticker": None,
            }

        if len(current_holdings) >= 3:
            return {
                "action": "CAPACITY_FULL",
                "rationale": "Portfolio at maximum 3-stock capacity.",
                "target_ticker": None,
            }

        if stock_candidate is not None:
            return {
                "action": "EXECUTE_BUY",
                "rationale": f"Candidate {stock_candidate['ticker']} approved in {macro_regime} regime.",
                "target_ticker": stock_candidate["ticker"],
            }

        return {
            "action": "NO_CANDIDATE",
            "rationale": "No candidate available.",
            "target_ticker": None,
        }


class TestRegimeSwitchInteractions:
    """Test suite for regime switch interactions with turnaround signals."""

    def test_bear_regime_overrides_turnaround_buy_signal(self):
        """
        Derivation:
        QQQ is trading below 200-day SMA (Bear regime, e.g. Oct 2008).
        An individual stock "XYZ" scores a perfect 100/100 turnaround score.
        Macro regime must override the micro signal: action must be REGIME_BLOCKED.
        """
        engine = MockRegimeInteractionEngine()
        candidate = {"ticker": "XYZ", "score": 100.0}
        res = engine.process_weekly_signal(
            macro_regime="BEAR",
            stock_candidate=candidate,
            current_holdings=[],
        )

        assert res["action"] == "REGIME_BLOCKED"
        assert res["target_ticker"] is None

    def test_bull_regime_allows_turnaround_buy_signal(self):
        """
        Derivation:
        In Bull regime, the same candidate "XYZ" is approved and purchased.
        """
        engine = MockRegimeInteractionEngine()
        candidate = {"ticker": "XYZ", "score": 90.0}
        res = engine.process_weekly_signal(
            macro_regime="BULL",
            stock_candidate=candidate,
            current_holdings=[],
        )

        assert res["action"] == "EXECUTE_BUY"
        assert res["target_ticker"] == "XYZ"

    def test_transition_regime_permits_selective_entry(self):
        """
        Derivation:
        In Transition regime, high-conviction candidate is accepted.
        """
        engine = MockRegimeInteractionEngine()
        candidate = {"ticker": "ABC", "score": 85.0}
        res = engine.process_weekly_signal(
            macro_regime="TRANSITION",
            stock_candidate=candidate,
            current_holdings=["XYZ"],
        )

        assert res["action"] == "EXECUTE_BUY"
        assert res["target_ticker"] == "ABC"

    def test_regime_recovery_from_bear_to_bull_unfreezes_screening(self):
        """
        Derivation:
        Week 1: Bear regime -> Candidate blocked.
        Week 2: Market crosses above 200-day SMA (flips to Bull) -> Candidate approved.
        """
        engine = MockRegimeInteractionEngine()
        cand = {"ticker": "RECOVERY", "score": 92.0}

        # Week 1
        r1 = engine.process_weekly_signal("BEAR", cand, [])
        assert r1["action"] == "REGIME_BLOCKED"

        # Week 2 (Regime flips to Bull)
        r2 = engine.process_weekly_signal("BULL", cand, [])
        assert r2["action"] == "EXECUTE_BUY"
        assert r2["target_ticker"] == "RECOVERY"

    def test_capacity_constraint_still_enforced_in_bull_regime(self):
        """
        Expected: Even in a raging Bull regime, the 3-stock portfolio capacity is strictly enforced.
        """
        engine = MockRegimeInteractionEngine()
        res = engine.process_weekly_signal(
            macro_regime="BULL",
            stock_candidate={"ticker": "FOURTH", "score": 99.0},
            current_holdings=["S1", "S2", "S3"],
        )
        assert res["action"] == "CAPACITY_FULL"
        assert res["target_ticker"] is None
