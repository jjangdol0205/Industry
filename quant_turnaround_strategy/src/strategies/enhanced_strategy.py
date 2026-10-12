"""
Enhanced Alternative Strategy module: Adaptive Regime-Switching Dual-Momentum (AR-DM).
Implements the 3 Core Engines:
1. Macro-Trend Regime Filter:
   - 200-day Simple Moving Average (SMA200) on QQQ.
   - 50-day Simple Moving Average (SMA50) trend slope.
   - Regime Bull: QQQ > SMA200 and SMA50 > SMA200 -> 100% equity exposure.
   - Regime Transition: QQQ > SMA200 but SMA50 <= SMA200 -> 60% equity, 40% cash defense.
   - Regime Bear: QQQ <= SMA200 -> 85-100% cash defense, freeze new turnaround stock purchases.
2. Dual-Momentum Relative Strength Tilt:
   - Evaluates quarterly momentum between QQQ and SOXX (63-day and 126-day relative price momentum).
   - In Bull regime, overweights the momentum leader (e.g. 55% SOXX / 30% QQQ when semiconductors lead,
     or 55% QQQ / 30% SOXX when technology leads).
3. Asymmetric Turnaround Profit Ratchet:
   - Stage 1 (Hard stop): Initial entry protected at -10% stop-loss.
   - Stage 2 (Break-even): Once unrealized gain hits +20%, stop is moved to Entry Price (0% downside risk).
   - Stage 3 (Trailing stop): Once gain exceeds +40%, locks in profits with an 8% trailing stop from peak.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
import logging
import pandas as pd
import numpy as np

from src.strategies.base_strategy import BaseStrategy, StrategyParameters

logger = logging.getLogger(__name__)


class ExitReason(str, Enum):
    """Exit reason enumeration for position liquidation."""
    NONE = "NONE"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    BREAKEVEN_STOP = "BREAKEVEN_STOP"
    TRAILING_STOP = "TRAILING_STOP"
    TIME_STOP = "TIME_STOP"
    RATCHET_STAGE_1 = "STOP_LOSS"
    RATCHET_STAGE_2 = "BREAKEVEN_STOP"
    RATCHET_STAGE_3 = "TRAILING_STOP"


@dataclass
class EnhancedStrategyParameters(StrategyParameters):
    """Configuration parameters for Adaptive Regime-Switching Dual-Momentum (AR-DM)."""
    # Core Engine 1: Macro Trend Filter
    sma_trend_window: int = 200
    sma_fast_window: int = 50
    bear_cash: float = 0.85
    transition_cash: float = 0.40

    # Core Engine 2: Relative Momentum Tilt
    momentum_window: int = 63
    momentum_window_long: int = 126
    bull_leader_weight: float = 0.55
    bull_laggard_weight: float = 0.30
    bull_turnaround_max: float = 0.15

    # Core Engine 3: Asymmetric Profit Ratchet
    breakeven_gain_pct: float = 0.20
    trailing_gain_pct: float = 0.40
    trailing_stop_pct: float = 0.08
    hard_stop_pct: float = -0.10


class EnhancedStrategy(BaseStrategy):
    """
    Adaptive Regime-Switching Dual-Momentum (AR-DM) Strategy.
    Subclasses BaseStrategy and integrates Macro Regime Switching,
    QQQ vs SOXX Relative Momentum Tilt, and Asymmetric Turnaround Ratchet.
    """

    def __init__(
        self,
        params: Optional[EnhancedStrategyParameters] = None,
        prices_df: Optional[pd.DataFrame] = None,
        **kwargs,
    ):
        if params is not None:
            self.params: EnhancedStrategyParameters = params
        else:
            self.params = EnhancedStrategyParameters(**kwargs)

        self._indicator_df: Optional[pd.DataFrame] = None
        self._rebalance_dates: List[pd.Timestamp] = []
        self._cursor: int = 0

        # Auto-initialize indicators if prices provided or available from cache
        if prices_df is not None and not prices_df.empty:
            self.prepare(prices_df)
        else:
            self._try_auto_load_indicators()

    def _try_auto_load_indicators(self) -> None:
        """Attempts to load cached benchmark prices to prepare indicators offline."""
        try:
            from src.data.cache_store import CacheStore
            from config.settings import CACHE_DIR
            cs = CacheStore(CACHE_DIR)
            if cs.exists("etf_prices.parquet"):
                df = cs.load_parquet("etf_prices.parquet")
                if df is not None and not df.empty:
                    self.prepare(df)
        except Exception as e:
            logger.debug(f"Auto-load cached indicators skipped: {e}")

    def prepare(self, prices_df: Optional[pd.DataFrame] = None) -> None:
        """
        Computes technical regime and momentum indicators across the full historical dataset.
        Zero lookahead: indicators for any day T are calculated strictly from price history <= T.
        """
        if prices_df is None or prices_df.empty:
            return

        # Extract QQQ and SOXX closing price series
        def extract_series(ticker: str) -> Optional[pd.Series]:
            if isinstance(prices_df.columns, pd.MultiIndex):
                if ("Close", ticker) in prices_df.columns:
                    return prices_df[("Close", ticker)].dropna()
                elif (ticker, "Close") in prices_df.columns:
                    return prices_df[(ticker, "Close")].dropna()
            elif ticker in prices_df.columns:
                return prices_df[ticker].dropna()
            return None

        qqq_close = extract_series("QQQ")
        soxx_close = extract_series("SOXX")

        if qqq_close is None or qqq_close.empty:
            return

        # Core Engine 1: Moving Averages
        w_trend = self.params.sma_trend_window
        w_fast = self.params.sma_fast_window
        sma200 = qqq_close.rolling(w_trend, min_periods=min(20, w_trend)).mean()
        sma50 = qqq_close.rolling(w_fast, min_periods=min(10, w_fast)).mean()

        # Core Engine 2: Relative Momentum
        w_mom = self.params.momentum_window
        w_mom_long = self.params.momentum_window_long
        qqq_mom = 0.5 * qqq_close.pct_change(w_mom).fillna(0.0) + 0.5 * qqq_close.pct_change(w_mom_long).fillna(0.0)

        if soxx_close is not None and not soxx_close.empty:
            soxx_mom = 0.5 * soxx_close.pct_change(w_mom).fillna(0.0) + 0.5 * soxx_close.pct_change(w_mom_long).fillna(0.0)
        else:
            soxx_mom = pd.Series(0.0, index=qqq_close.index)

        # Regimes classification
        regimes = []
        for dt, p in qqq_close.items():
            s200 = sma200.loc[dt] if dt in sma200.index else p
            s50 = sma50.loc[dt] if dt in sma50.index else p
            regimes.append(self.classify_regime(float(p), float(s200), float(s50)))

        regime_series = pd.Series(regimes, index=qqq_close.index, name="Regime")

        self._indicator_df = pd.DataFrame({
            "QQQ_Close": qqq_close,
            "SOXX_Close": soxx_close if soxx_close is not None else qqq_close,
            "SMA200": sma200,
            "SMA50": sma50,
            "QQQ_Mom": qqq_mom,
            "SOXX_Mom": soxx_mom,
            "Regime": regime_series,
        })

        # Precompute weekly rebalance calendar (Fridays or period end)
        self._rebalance_dates = [d for d in qqq_close.index if d.dayofweek == 4 or d == qqq_close.index[-1]]
        self._cursor = 0

    def reset(self) -> None:
        """Resets simulation step cursor to zero for reproducible backtest runs."""
        self._cursor = 0

    # -------------------------------------------------------------------------
    # Core Engine 1: Macro-Trend Regime Filter
    # -------------------------------------------------------------------------
    def classify_regime(self, price: float, sma200: float, sma50: float) -> str:
        """
        Classifies macroeconomic market regime:
        - BEAR: price < sma200 (Defensive capital preservation: cash 85-100%, buy freeze)
        - BULL: price >= sma200 AND sma50 > sma200 (Full risk-on equity exposure)
        - TRANSITION: price >= sma200 BUT sma50 <= sma200 (Cautious: 60% equity, 40% cash)
        """
        if price < sma200:
            return "BEAR"
        elif sma50 > sma200:
            return "BULL"
        else:
            return "TRANSITION"

    def determine_regime_allocation(self, regime: str) -> Dict[str, Union[float, bool]]:
        """
        Returns macro regime allocation constraints:
        - BEAR: max 15% equity, min 85% cash, turnaround purchases strictly forbidden.
        - TRANSITION: max 60% equity, min 40% cash, turnaround purchases allowed.
        - BULL: 100% equity, min 0% cash, turnaround purchases allowed.
        """
        if regime == "BEAR":
            return {
                "equity_max": 1.0 - self.params.bear_cash,
                "cash_min": self.params.bear_cash,
                "allow_turnaround_buy": False,
            }
        elif regime == "TRANSITION":
            return {
                "equity_max": 1.0 - self.params.transition_cash,
                "cash_min": self.params.transition_cash,
                "allow_turnaround_buy": True,
            }
        else:  # BULL
            return {
                "equity_max": 1.0,
                "cash_min": 0.0,
                "allow_turnaround_buy": True,
            }

    # -------------------------------------------------------------------------
    # Core Engine 2: Relative Momentum Tilt
    # -------------------------------------------------------------------------
    def compute_dual_momentum_tilt(self, qqq_mom: float, soxx_mom: float) -> Dict[str, float]:
        """
        Overweights the outperforming asset between QQQ and SOXX:
        - If SOXX momentum leads: 55% SOXX, 30% QQQ, 15% Turnaround sleeve.
        - If QQQ momentum leads: 55% QQQ, 30% SOXX, 15% Turnaround sleeve.
        """
        turnaround_max = self.params.bull_turnaround_max
        leader = self.params.bull_leader_weight
        laggard = self.params.bull_laggard_weight

        if soxx_mom > qqq_mom:
            return {"SOXX": leader, "QQQ": laggard, "Turnaround": turnaround_max}
        else:
            return {"QQQ": leader, "SOXX": laggard, "Turnaround": turnaround_max}

    # -------------------------------------------------------------------------
    # Core Engine 3: Asymmetric Turnaround Profit Ratchet
    # -------------------------------------------------------------------------
    def evaluate_profit_ratchet(
        self,
        entry_price: Any,
        current_price: Optional[float] = None,
        peak_price: Optional[float] = None,
        high_price: Optional[float] = None,
        low_price: Optional[float] = None,
        **kwargs,
    ) -> Tuple[float, str]:
        """
        Asymmetric 3-Stage Profit Ratchet:
        - Stage 1 (gain < 20%): Stop at entry * (1 + hard_stop_pct) [e.g. -10% hard stop].
        - Stage 2 (gain 20% to 40%): Stop moved to Entry Price [Break-even, 0% downside risk].
        - Stage 3 (gain >= 40%): Trailing stop from peak [e.g. 8% trailing stop].
        Returns (effective_stop_price, ratchet_stage).
        Supports being called with (entry_price, current_price, peak_price) or (pos, current_price, high_price, low_price).
        """
        if hasattr(entry_price, "entry_price"):
            pos = entry_price
            e_price = float(pos.entry_price)
            curr_p = float(current_price if current_price is not None else getattr(pos, "current_price", e_price))
            p_price = float(getattr(pos, "peak_price", e_price))
            if high_price is not None and high_price > p_price:
                p_price = float(high_price)
        else:
            e_price = float(entry_price) if entry_price is not None else 0.0
            curr_p = float(current_price) if current_price is not None else e_price
            p_price = float(peak_price) if peak_price is not None else max(e_price, curr_p)
            if high_price is not None and high_price > p_price:
                p_price = float(high_price)

        if e_price <= 0:
            return 0.0, "STAGE_1_HARD"

        peak_gain = (p_price - e_price) / e_price

        if peak_gain >= self.params.trailing_gain_pct:
            stop_price = p_price * (1.0 - self.params.trailing_stop_pct)
            return stop_price, "STAGE_3_TRAILING"
        elif peak_gain >= self.params.breakeven_gain_pct:
            stop_price = e_price * 1.00
            return stop_price, "STAGE_2_BREAKEVEN"
        else:
            stop_price = e_price * (1.0 + self.params.hard_stop_pct)
            return stop_price, "STAGE_1_HARD"

    def evaluate_daily_exit(
        self,
        pos: Any,
        current_price: Optional[float] = None,
        high_price: Optional[float] = None,
        low_price: Optional[float] = None,
        days_held: Optional[int] = None,
        **kwargs,
    ) -> ExitReason:
        """
        Intra-week daily exit evaluation for active turnaround positions using Core Engine 3 (Profit Ratchet).
        Checks:
        1. Maximum holding period (days_held >= params.max_holding_days) -> ExitReason.TIME_STOP.
        2. Asymmetric 3-Stage Profit Ratchet:
           - STAGE_1_HARD: Stop at entry * (1 + hard_stop_pct) [e.g. -10% hard stop].
           - STAGE_2_BREAKEVEN: Once peak gain >= +20%, stop at entry price [0% loss].
           - STAGE_3_TRAILING: Once peak gain >= +40%, 8% trailing stop from peak price.
           If check price (low_price or current_price) <= stop_price:
             returns ExitReason.STOP_LOSS (or ExitReason.BREAKEVEN_STOP / ExitReason.TRAILING_STOP).
        3. If no condition triggers, returns ExitReason.NONE.
        """
        if hasattr(pos, "entry_price"):
            entry_price = float(pos.entry_price)
            curr_p = float(current_price if current_price is not None else getattr(pos, "current_price", entry_price))
            peak_p = float(getattr(pos, "peak_price", entry_price))
            d_held = int(days_held if days_held is not None else getattr(pos, "days_held", 0))
        else:
            entry_price = float(pos) if pos is not None else 0.0
            curr_p = float(current_price if current_price is not None else entry_price)
            peak_p = float(high_price if high_price is not None else max(entry_price, curr_p))
            d_held = int(days_held) if days_held is not None else 0

        high_p = float(high_price if high_price is not None else curr_p)
        low_p = float(low_price if low_price is not None else curr_p)
        effective_peak = max(peak_p, high_p)

        # 1. Time stop check
        if d_held >= self.params.max_holding_days:
            return ExitReason.TIME_STOP

        # 2. Profit ratchet check
        stop_price, stage = self.evaluate_profit_ratchet(
            entry_price=entry_price,
            current_price=curr_p,
            peak_price=effective_peak,
            high_price=high_p,
            low_price=low_p,
        )

        check_p = low_p if (low_p is not None and low_p > 0) else curr_p
        if check_p <= stop_price:
            if stage == "STAGE_3_TRAILING":
                return ExitReason.TRAILING_STOP
            elif stage == "STAGE_2_BREAKEVEN":
                return ExitReason.BREAKEVEN_STOP
            else:
                return ExitReason.STOP_LOSS

        return ExitReason.NONE

    # -------------------------------------------------------------------------
    # Portfolio Weight Computation (BacktestEngine Integration)
    # -------------------------------------------------------------------------
    def compute_target_weights(
        self,
        active_turnaround_stocks: List[str],
        idle_policy: Optional[str] = None,
        current_date: Optional[Any] = None,
        regime: Optional[str] = None,
        qqq_mom: Optional[float] = None,
        soxx_mom: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, float]:
        """
        Computes normalized portfolio weights for current rebalancing decision.
        Adapts weights dynamically based on:
        - Macro regime (Bull, Transition, Bear)
        - QQQ vs SOXX relative momentum tilt
        - Number of active turnaround stocks (0 to 3)
        - Idle cash policy ('cash_buffer' vs 'etf_sweep')
        """
        policy = idle_policy or self.params.turnaround_idle_policy

        # Resolve current regime and momentum
        current_regime = regime
        cur_qm = qqq_mom
        cur_sm = soxx_mom

        if current_regime is None:
            if current_date is None:
                try:
                    import inspect
                    frame = inspect.currentframe().f_back
                    while frame:
                        if "trade_dt" in frame.f_locals:
                            current_date = frame.f_locals["trade_dt"]
                            break
                        elif "dt" in frame.f_locals:
                            current_date = frame.f_locals["dt"]
                            break
                        frame = frame.f_back
                except Exception:
                    pass

            if current_date is not None and self._indicator_df is not None and not self._indicator_df.empty:
                ts = pd.Timestamp(current_date)
                if ts.tzinfo is not None and self._indicator_df.index.tz is None:
                    ts = ts.tz_localize(None)
                elif ts.tzinfo is None and self._indicator_df.index.tz is not None:
                    ts = ts.tz_localize(self._indicator_df.index.tz)

                if ts in self._indicator_df.index:
                    row = self._indicator_df.loc[ts]
                else:
                    prior_dates = self._indicator_df.index[self._indicator_df.index <= ts]
                    if len(prior_dates) > 0:
                        row = self._indicator_df.loc[prior_dates[-1]]
                    else:
                        row = self._indicator_df.iloc[0]

                current_regime = row["Regime"]
                cur_qm = float(row["QQQ_Mom"])
                cur_sm = float(row["SOXX_Mom"])
            elif self._indicator_df is not None and len(self._rebalance_dates) > 0:
                idx = min(self._cursor, len(self._rebalance_dates) - 1)
                dt = self._rebalance_dates[idx]
                self._cursor += 1
                row = self._indicator_df.loc[dt]
                current_regime = row["Regime"]
                cur_qm = float(row["QQQ_Mom"])
                cur_sm = float(row["SOXX_Mom"])

        # Fallback to BULL if uninitialized
        if current_regime is None:
            current_regime = "BULL"
        if cur_qm is None:
            cur_qm = 0.0
        if cur_sm is None:
            cur_sm = 0.0

        weights: Dict[str, float] = {}

        # ---------------------------------------------------------------------
        # Case 1: BEAR Regime (Defensive Cash + Turnaround Freeze)
        # ---------------------------------------------------------------------
        if current_regime == "BEAR":
            cash_min = self.params.bear_cash
            equity_rem = max(0.0, 1.0 - cash_min)

            # Freeze: turnaround stocks are allocated 0.0 weight
            for ticker in active_turnaround_stocks:
                weights[ticker] = 0.0

            # Remainder allocated defensive core blend
            weights["QQQ"] = equity_rem * 0.60
            weights["SOXX"] = equity_rem * 0.40
            weights["Cash"] = cash_min

        # ---------------------------------------------------------------------
        # Case 2: TRANSITION Regime (Cautious Risk-On: 60% Equity / 40% Cash)
        # ---------------------------------------------------------------------
        elif current_regime == "TRANSITION":
            cash_min = self.params.transition_cash
            equity_cap = max(0.0, 1.0 - cash_min)  # 0.60

            # Momentum ratio within equity sleeve
            soxx_leads = (cur_sm > cur_qm)
            ratio_leader = self.params.bull_leader_weight / (self.params.bull_leader_weight + self.params.bull_laggard_weight)
            ratio_laggard = self.params.bull_laggard_weight / (self.params.bull_leader_weight + self.params.bull_laggard_weight)

            # Turnaround capacity in transition regime
            k = len(active_turnaround_stocks)
            max_turn_w = self.params.bull_turnaround_max * equity_cap  # ~0.09
            slot_w = max_turn_w / self.params.max_active_stocks

            for ticker in active_turnaround_stocks:
                weights[ticker] = slot_w

            allocated_turn = k * slot_w
            unallocated_turn = max_turn_w - allocated_turn
            remaining_equity = equity_cap - allocated_turn

            if policy == "etf_sweep":
                etf_pool = remaining_equity
                cash_w = cash_min
            else:
                # cash_buffer
                etf_pool = equity_cap - max_turn_w
                cash_w = cash_min + unallocated_turn

            if soxx_leads:
                weights["SOXX"] = etf_pool * ratio_leader
                weights["QQQ"] = etf_pool * ratio_laggard
            else:
                weights["QQQ"] = etf_pool * ratio_leader
                weights["SOXX"] = etf_pool * ratio_laggard

            weights["Cash"] = cash_w

        # ---------------------------------------------------------------------
        # Case 3: BULL Regime (Full Risk-On + Momentum Tilt)
        # ---------------------------------------------------------------------
        else:
            soxx_leads = (cur_sm > cur_qm)
            base_leader = self.params.bull_leader_weight
            base_laggard = self.params.bull_laggard_weight
            max_turn = self.params.bull_turnaround_max

            k = len(active_turnaround_stocks)
            slot_w = max_turn / self.params.max_active_stocks

            for ticker in active_turnaround_stocks:
                weights[ticker] = slot_w

            unallocated_slots = self.params.max_active_stocks - k
            unallocated_weight = unallocated_slots * slot_w

            if policy == "etf_sweep":
                etf_base_sum = base_leader + base_laggard
                sweep_lead = base_leader + unallocated_weight * (base_leader / etf_base_sum)
                sweep_lag = base_laggard + unallocated_weight * (base_laggard / etf_base_sum)
                cash_w = 0.0

                if soxx_leads:
                    weights["SOXX"] = sweep_lead
                    weights["QQQ"] = sweep_lag
                else:
                    weights["QQQ"] = sweep_lead
                    weights["SOXX"] = sweep_lag
            else:
                # cash_buffer
                cash_w = unallocated_weight
                if soxx_leads:
                    weights["SOXX"] = base_leader
                    weights["QQQ"] = base_laggard
                else:
                    weights["QQQ"] = base_leader
                    weights["SOXX"] = base_laggard

            weights["Cash"] = cash_w

        # Normalize weights to ensure sum invariant == 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6 and total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def should_buy_candidate(
        self,
        candidate_score: float,
        low_proximity: float,
        current_holdings_count: int,
        current_date: Optional[Any] = None,
        regime: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Evaluates whether a candidate qualifies for weekly entry.
        Strictly prohibits new purchases during BEAR market regimes.
        """
        # Determine regime
        cur_regime = regime
        if cur_regime is None:
            if current_date is None:
                try:
                    import inspect
                    frame = inspect.currentframe().f_back
                    while frame:
                        if "trade_dt" in frame.f_locals:
                            current_date = frame.f_locals["trade_dt"]
                            break
                        elif "dt" in frame.f_locals:
                            current_date = frame.f_locals["dt"]
                            break
                        frame = frame.f_back
                except Exception:
                    pass

            if current_date is not None and self._indicator_df is not None and not self._indicator_df.empty:
                ts = pd.Timestamp(current_date)
                if ts.tzinfo is not None and self._indicator_df.index.tz is None:
                    ts = ts.tz_localize(None)
                elif ts.tzinfo is None and self._indicator_df.index.tz is not None:
                    ts = ts.tz_localize(self._indicator_df.index.tz)

                if ts in self._indicator_df.index:
                    cur_regime = self._indicator_df.loc[ts, "Regime"]
                else:
                    prior_dates = self._indicator_df.index[self._indicator_df.index <= ts]
                    if len(prior_dates) > 0:
                        cur_regime = self._indicator_df.loc[prior_dates[-1], "Regime"]
                    else:
                        cur_regime = self._indicator_df.iloc[0]["Regime"]

        # Macro Trend Gate: freeze new stock purchases in Bear regime
        if cur_regime == "BEAR":
            return False

        # Capacity, fundamental score, and 52w-low proximity gates
        if current_holdings_count >= self.params.max_active_stocks:
            return False
        if candidate_score < self.params.min_turnaround_score:
            return False
        if low_proximity > self.params.low_52w_tolerance:
            return False

        return True


# Alias for backward-compatibility with test suite imports
AdaptiveRegimeDualMomentum = EnhancedStrategy
