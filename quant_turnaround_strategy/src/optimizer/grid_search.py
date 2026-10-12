"""
Parameter grid search optimization module.
Exhaustively searches multidimensional parameter spaces over allocation weights,
entry thresholds, and exit rules to maximize the Calmar Ratio (Return vs. Annual MDD).
"""
import itertools
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable
import logging

from src.optimizer.objective import ObjectiveFunction

logger = logging.getLogger(__name__)


@dataclass
class GridOptimizationResult:
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Dict[str, Any]]
    total_evaluated: int


class GridSearchOptimizer:
    """
    Multidimensional discrete parameter grid search optimizer.
    """

    def __init__(self, objective_metric: str = "calmar_max"):
        self.objective_metric = objective_metric

    def generate_parameter_combinations(self, grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Expands parameter dictionary into cartesian product combinations.
        """
        keys = list(grid.keys())
        values = list(grid.values())
        combos = []
        for instance in itertools.product(*values):
            combos.append(dict(zip(keys, instance)))
        return combos

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """
        Validates portfolio invariants and parameter sanity:
        - Sum of base weights <= 1.0
        - Stop-loss <= 0
        - Profit-taking > 0
        """
        w_qqq = params.get("w_qqq_base", 0.0)
        w_soxx = params.get("w_soxx_base", 0.0)
        w_turn = params.get("w_turnaround_max", 0.0)
        w_cash = params.get("w_cash_buffer", 0.0)
        total_weight = w_qqq + w_soxx + w_turn + w_cash
        if total_weight > 1.0 + 1e-6:
            return False

        sl = params.get("stop_loss_pct", -0.10)
        if sl > 0:
            return False

        pt = params.get("profit_taking_pct")
        if pt is not None and pt <= 0:
            return False

        return True

    def rank_results(self, evaluated_runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sorts evaluated runs by Calmar ratio descending.
        """
        return sorted(evaluated_runs, key=lambda x: x.get("calmar", x.get("score", 0.0)), reverse=True)

    def optimize(
        self,
        evaluator_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
        param_grid: Dict[str, List[Any]],
    ) -> GridOptimizationResult:
        """
        Executes parameter search across all valid combinations.
        """
        all_combos = self.generate_parameter_combinations(param_grid)
        valid_combos = [c for c in all_combos if self.validate_parameters(c)]

        evaluated = []
        for idx, params in enumerate(valid_combos):
            try:
                run_metrics = evaluator_fn(params)
                score = ObjectiveFunction.evaluate(run_metrics, metric=self.objective_metric)
                run_metrics["score"] = score
                run_metrics["calmar"] = run_metrics.get("calmar", score)
                run_metrics["params"] = params
                evaluated.append(run_metrics)
            except Exception as e:
                logger.warning(f"Error evaluating params {params}: {e}")

        ranked = self.rank_results(evaluated)
        best = ranked[0] if ranked else {}

        return GridOptimizationResult(
            best_params=best.get("params", {}),
            best_score=best.get("score", 0.0),
            all_results=ranked,
            total_evaluated=len(evaluated),
        )
