"""
Unit test suite for M2 Base Strategy Implementation (src/strategies/base_strategy.py).
Verifies:
- Parameter configuration and validation.
- Target portfolio weight calculation across turnaround slot counts.
- Idle policy enforcement ('cash_buffer' vs 'etf_sweep').
- Candidate qualification logic (52-week low proximity, turnaround score, capacity limit).
"""
import pytest
from src.strategies.base_strategy import BaseStrategy, StrategyParameters


class TestBaseStrategy:
    def test_default_parameters_and_invariants(self):
        strat = BaseStrategy()
        assert strat.params.w_qqq_base == 0.50
        assert strat.params.w_soxx_base == 0.30
        assert strat.params.w_turnaround_max == 0.20
        assert strat.max_active_stocks == 3
        assert strat.max_weekly_buy == 1

        # Weight sum invariant
        total = strat.params.w_qqq_base + strat.params.w_soxx_base + strat.params.w_turnaround_max
        assert pytest.approx(total, abs=1e-6) == 1.0

    def test_invalid_parameters_raise_error(self):
        with pytest.raises(ValueError):
            StrategyParameters(w_qqq_base=0.60, w_soxx_base=0.50)  # 1.10 > 1.0

    def test_target_weights_under_cash_buffer_policy(self):
        strat = BaseStrategy(StrategyParameters(
            w_qqq_base=0.50,
            w_soxx_base=0.30,
            w_turnaround_max=0.20,
            turnaround_idle_policy="cash_buffer",
        ))

        # Case 1: 0 turnaround stocks held -> 20% in Cash
        w0 = strat.compute_target_weights([])
        assert w0["QQQ"] == 0.50
        assert w0["SOXX"] == 0.30
        assert pytest.approx(w0["Cash"], abs=1e-6) == 0.20
        assert pytest.approx(sum(w0.values()), abs=1e-6) == 1.0

        # Case 2: 2 turnaround stocks held -> each gets ~6.67%, 6.67% in Cash
        w2 = strat.compute_target_weights(["A", "B"])
        assert w2["QQQ"] == 0.50
        assert w2["SOXX"] == 0.30
        assert pytest.approx(w2["A"], abs=1e-4) == 0.20 / 3
        assert pytest.approx(w2["B"], abs=1e-4) == 0.20 / 3
        assert pytest.approx(w2["Cash"], abs=1e-4) == 0.20 / 3
        assert pytest.approx(sum(w2.values()), abs=1e-6) == 1.0

        # Case 3: 3 turnaround stocks held -> 0% in Cash
        w3 = strat.compute_target_weights(["A", "B", "C"])
        assert w3["QQQ"] == 0.50
        assert w3["SOXX"] == 0.30
        assert pytest.approx(w3["Cash"], abs=1e-6) == 0.0
        assert pytest.approx(sum(w3.values()), abs=1e-6) == 1.0

    def test_target_weights_under_etf_sweep_policy(self):
        strat = BaseStrategy(StrategyParameters(
            w_qqq_base=0.50,
            w_soxx_base=0.30,
            w_turnaround_max=0.20,
            turnaround_idle_policy="etf_sweep",
        ))

        # When 0 stocks held, 20% swept to QQQ and SOXX (50:30 ratio)
        w0 = strat.compute_target_weights([])
        assert pytest.approx(w0["QQQ"], abs=1e-6) == 0.625
        assert pytest.approx(w0["SOXX"], abs=1e-6) == 0.375
        assert pytest.approx(w0["Cash"], abs=1e-6) == 0.0

    def test_candidate_qualification_logic(self):
        strat = BaseStrategy(StrategyParameters(
            low_52w_tolerance=0.05,
            min_turnaround_score=70.0,
            max_active_stocks=3,
        ))

        # Qualified: within 3% of 52w low, score 80, holding count 1 < 3
        assert strat.should_buy_candidate(candidate_score=80.0, low_proximity=0.03, current_holdings_count=1) is True

        # Rejected: score below threshold
        assert strat.should_buy_candidate(candidate_score=65.0, low_proximity=0.03, current_holdings_count=1) is False

        # Rejected: price too far from 52w low (8% > 5%)
        assert strat.should_buy_candidate(candidate_score=80.0, low_proximity=0.08, current_holdings_count=1) is False

        # Rejected: portfolio at full capacity (3 stocks held)
        assert strat.should_buy_candidate(candidate_score=95.0, low_proximity=0.01, current_holdings_count=3) is False
