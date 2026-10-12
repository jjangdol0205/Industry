"""
Weekly Candidate Selector and Portfolio Capacity Manager.
Enforces capacity constraints (0-3 stocks), selects at most 1 optimal turnaround stock per week,
and executes discretionary risk-reward exclusion gates.
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Union
import logging
import numpy as np
import pandas as pd

from config.settings import DEFAULT_MAX_PORTFOLIO_CAPACITY
from src.models.schemas import (
    CandidateEvaluation,
    WeeklySelectionResult,
    ExclusionReason,
)
from src.data.universe import UniverseManager
from src.screening.rolling_low import RollingLowScreener
from src.screening.turnaround_scorer import TurnaroundScorer
from src.screening.exclusion_gates import ExclusionGates

logger = logging.getLogger(__name__)


class WeeklySelector:
    """
    Orchestrates weekly candidate evaluation and Top-1 selection with portfolio constraints.
    """

    def __init__(
        self,
        universe_manager: Optional[UniverseManager] = None,
        rolling_low_screener: Optional[RollingLowScreener] = None,
        turnaround_scorer: Optional[TurnaroundScorer] = None,
        exclusion_gates: Optional[ExclusionGates] = None,
        min_composite_score: float = 0.55,
        max_portfolio_capacity: int = DEFAULT_MAX_PORTFOLIO_CAPACITY,
    ):
        self.universe_manager = universe_manager or UniverseManager()
        self.rolling_low_screener = rolling_low_screener or RollingLowScreener()
        self.turnaround_scorer = turnaround_scorer or TurnaroundScorer()
        self.exclusion_gates = exclusion_gates or ExclusionGates()
        self.min_composite_score = min_composite_score
        self.max_portfolio_capacity = max_portfolio_capacity

    def screen_weekly_candidates(
        self,
        as_of_date: Union[date, datetime, str],
        current_holdings: List[str],
        candidate_price_dfs: Optional[Dict[str, pd.DataFrame]] = None,
        max_capacity: Optional[int] = None,
    ) -> WeeklySelectionResult:
        """
        Interface Contract:
        Evaluates turnaround candidates on weekly decision date.
        Selects at most 1 optimal stock if capacity permits (0 <= N_held <= 3).
        """
        capacity = max_capacity if max_capacity is not None else self.max_portfolio_capacity
        dt = pd.to_datetime(as_of_date).date() if not isinstance(as_of_date, date) else as_of_date
        held_count = len(current_holdings)

        # Constraint 1: Portfolio capacity check
        if held_count >= capacity:
            return WeeklySelectionResult(
                decision_date=dt,
                selected_ticker=None,
                selected_candidate=None,
                portfolio_held_count=held_count,
                action="HOLD_CAPACITY_FULL",
                rationale=f"Portfolio capacity full ({held_count}/{capacity} stocks held). Candidate screening skipped.",
                all_evaluated_candidates=[],
            )

        # Get point-in-time universe active constituents
        active_constituents = self.universe_manager.get_constituents_at(dt)
        holding_sectors = [self.universe_manager.get_sector(h) for h in current_holdings]

        # Candidate price history pools
        price_pools = candidate_price_dfs or {}

        evaluated_list: List[CandidateEvaluation] = []
        qualified_candidates: List[CandidateEvaluation] = []

        # Iterate strictly over point-in-time universe constituents that have price data
        tickers_to_evaluate = [t for t in active_constituents if t in price_pools]

        for ticker in tickers_to_evaluate:
            price_df = price_pools.get(ticker)
            if price_df is None or price_df.empty:
                continue

            sector = self.universe_manager.get_sector(ticker)

            # Step 1: 52-Week Low Screener + Stabilization
            qualifies_52w, low_metrics = self.rolling_low_screener.evaluate_candidate(price_df, dt)
            if not qualifies_52w:
                continue

            close_price = low_metrics["close_price"]
            low_52w = low_metrics["low_52w"]
            low_prox = low_metrics["low_proximity"]
            rsi = low_metrics["rsi_14"]
            ret_5d = low_metrics["return_5d"]
            ret_30d = low_metrics["return_30d"]
            avg_dv = low_metrics["avg_dollar_volume_20d"]

            # Step 2: Point-in-Time Turnaround Scorer (Zero Lookahead)
            turnaround_score, f_breakdown = self.turnaround_scorer.score_candidate(
                ticker=ticker,
                as_of_date=dt,
                stock_price=close_price,
                low_52w=low_52w,
            )

            solvency_score = f_breakdown.get("pillar3_solvency", 0.50)
            valuation_discount = f_breakdown.get("pillar4_valuation", 0.50)

            # Step 3: Technical curl factor (RSI bouncing from 20 up towards 50)
            technical_curl = float(np.clip((rsi - 20.0) / 40.0, 0.0, 1.0))

            # Step 4: Composite Ranking Score
            composite_score = (
                0.40 * turnaround_score
                + 0.30 * solvency_score
                + 0.20 * valuation_discount
                + 0.10 * technical_curl
            )
            composite_score = float(np.clip(composite_score, 0.0, 1.0))

            # Step 5: Exclusion Gates
            eval_metrics = {
                "avg_dollar_volume_20d": avg_dv,
                "return_5d": ret_5d,
                "return_30d": ret_30d,
                "rsi_14": rsi,
                "solvency_score": solvency_score,
                "turnaround_score": turnaround_score,
            }
            passed_gates, exclusion_reasons = self.exclusion_gates.evaluate_gates(
                ticker=ticker,
                sector=sector,
                current_holdings=current_holdings,
                current_holding_sectors=holding_sectors,
                metrics=eval_metrics,
            )

            candidate_eval = CandidateEvaluation(
                ticker=ticker,
                evaluation_date=dt,
                close_price=close_price,
                low_52w=low_52w,
                low_proximity=low_prox,
                rsi_14=rsi,
                return_5d=ret_5d,
                avg_dollar_volume=avg_dv,
                turnaround_score=turnaround_score,
                solvency_score=solvency_score,
                valuation_discount=valuation_discount,
                composite_rank_score=round(composite_score, 4),
                passed_all_gates=passed_gates,
                exclusion_reasons=exclusion_reasons,
                gics_sector=sector,
            )
            evaluated_list.append(candidate_eval)

            if passed_gates and composite_score >= self.min_composite_score:
                qualified_candidates.append(candidate_eval)

        # Step 6: Select at most 1 optimal stock
        if qualified_candidates:
            # Sort by composite rank score descending
            qualified_candidates.sort(key=lambda c: c.composite_rank_score, reverse=True)
            top_choice = qualified_candidates[0]

            return WeeklySelectionResult(
                decision_date=dt,
                selected_ticker=top_choice.ticker,
                selected_candidate=top_choice,
                portfolio_held_count=held_count,
                action="BUY",
                rationale=(
                    f"Selected {top_choice.ticker} (Composite Score: {top_choice.composite_rank_score:.3f}, "
                    f"Sector: {top_choice.gics_sector}) hitting 52-week low with strong turnaround proxy."
                ),
                all_evaluated_candidates=evaluated_list,
            )

        return WeeklySelectionResult(
            decision_date=dt,
            selected_ticker=None,
            selected_candidate=None,
            portfolio_held_count=held_count,
            action="NO_QUALIFIED_CANDIDATE",
            rationale="No candidate stocks satisfied 52-week low stabilization and turnaround exclusion gates this week.",
            all_evaluated_candidates=evaluated_list,
        )
