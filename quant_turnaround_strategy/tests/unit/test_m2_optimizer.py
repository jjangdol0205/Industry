"""
Unit test suite for M2 Systematic Parameter Optimization Engine (src/optimizer/).
Verifies:
- GridSearchOptimizer cartesian product expansion.
- Parameter validation and constraint checks.
- Calmar ranking of evaluated configurations.
- WalkForwardOptimizer rolling window generation (5y IS / 1y OOS, 2001 to 2026).
- Walk-Forward Efficiency (WFE) formula and threshold evaluation.
- ObjectiveFunction scoring.
"""
import pytest
from src.optimizer.grid_search import GridSearchOptimizer
from src.optimizer.walk_forward import WalkForwardOptimizer
from src.optimizer.objective import ObjectiveFunction


class TestOptimizerUnit:
    def test_grid_combinations_generation(self):
        optimizer = GridSearchOptimizer()
        grid = {
            "w_qqq_base": [0.45, 0.50],
            "w_soxx_base": [0.30, 0.35],
            "stop_loss_pct": [-0.10, -0.12, -0.15],
        }
        combos = optimizer.generate_parameter_combinations(grid)
        # 2 x 2 x 3 = 12
        assert len(combos) == 12
        assert all("w_qqq_base" in c for c in combos)
        assert all("w_soxx_base" in c for c in combos)
        assert all("stop_loss_pct" in c for c in combos)

    def test_parameter_validation_filters_invalid_weights(self):
        optimizer = GridSearchOptimizer()

        # Valid
        assert optimizer.validate_parameters({
            "w_qqq_base": 0.50, "w_soxx_base": 0.30, "w_turnaround_max": 0.20, "stop_loss_pct": -0.12
        }) is True

        # Invalid: weights sum = 1.10 > 1.0
        assert optimizer.validate_parameters({
            "w_qqq_base": 0.60, "w_soxx_base": 0.50, "stop_loss_pct": -0.12
        }) is False

        # Invalid: positive stop-loss
        assert optimizer.validate_parameters({
            "w_qqq_base": 0.50, "w_soxx_base": 0.30, "stop_loss_pct": 0.05
        }) is False

    def test_ranking_by_calmar_descending(self):
        optimizer = GridSearchOptimizer(objective_metric="calmar_max")
        runs = [
            {"name": "config1", "cagr": 0.12, "mdd": -0.24, "calmar": 0.50},
            {"name": "config2", "cagr": 0.18, "mdd": -0.20, "calmar": 0.90},
            {"name": "config3", "cagr": 0.15, "mdd": -0.25, "calmar": 0.60},
        ]
        ranked = optimizer.rank_results(runs)
        assert ranked[0]["name"] == "config2"
        assert ranked[1]["name"] == "config3"
        assert ranked[2]["name"] == "config1"

    def test_walk_forward_window_generation(self):
        wfa = WalkForwardOptimizer(is_years=5, oos_years=1, step_years=1)
        windows = wfa.generate_rolling_windows(start_year=2001, end_year=2026)

        # 2001-2005 -> 2006 (W1)
        # ...
        # 2021-2025 -> 2026 (W21)
        assert len(windows) == 21
        assert windows[0]["is_start_year"] == 2001
        assert windows[0]["is_end_year"] == 2005
        assert windows[0]["oos_year"] == 2006

        assert windows[2]["oos_year"] == 2008  # GFC crisis out-of-sample test
        assert windows[-1]["oos_year"] == 2026

    def test_walk_forward_efficiency_calculation(self):
        wfa = WalkForwardOptimizer()
        # CAGR_IS = 20%, CAGR_OOS = 16% -> ratio = 16/20 = 0.80
        # MDD_IS = -20%, MDD_OOS = -25% -> ratio = 20/25 = 0.80
        # WFE = 0.80 * 0.80 = 0.64
        wfe = wfa.compute_walk_forward_efficiency(
            cagr_is=0.20,
            cagr_oos=0.16,
            mdd_is=-0.20,
            mdd_oos=-0.25,
        )
        assert pytest.approx(wfe, abs=1e-4) == 0.64
        assert wfe >= 0.60

    def test_objective_compound_evaluation(self):
        # CAGR = 0.15, max_mdd = -0.20, avg_mdd = -0.10
        # J = 0.15 - 0.5*(0.20) - 0.5*(0.10) = 0.15 - 0.10 - 0.05 = 0.00
        score = ObjectiveFunction.compound_objective(
            cagr=0.15,
            max_annual_mdd=-0.20,
            avg_annual_mdd=-0.10,
            lambda_max=0.5,
            lambda_avg=0.5,
        )
        assert pytest.approx(score, abs=1e-6) == 0.00

    def test_walk_forward_type_hints_resolution(self):
        import typing
        hints = typing.get_type_hints(WalkForwardOptimizer.run_walk_forward)
        assert "grid_search_fn" in hints
        assert "evaluate_oos_fn" in hints
        assert "return" in hints
