"""
Tri-Tech Simplex Grid Simulator & Vectorized Engine (SMH, XLK, VGT).
Evaluates the complete 3-asset allocation simplex:
    w_SMH + w_XLK + w_VGT = 1.0,  w_i >= 0
at 1% step resolution (exact 5,151 weight triplets) across periodic rebalancing schedules:
  1. Annual Rebalancing (연 1회, 1월 초)
  2. Quarterly Rebalancing (분기 1회, 3/6/9/12월 말)
  3. Buy-and-Hold (리밸런싱 없음)
Deducts 7 bps transaction friction (0.05% commission + 0.02% slippage = 0.07% turnover drag)
and optionally models Korean 22% overseas capital gains tax with 2.5M KRW deduction.
Executes all 5,151 triplets in <0.5s using pure vectorized NumPy/Pandas. Zero SciPy dependency.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, Union, List
from functools import cached_property
import logging
import time
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TECH_ASSET_NAMES = ["SMH", "XLK", "VGT"]
DEFAULT_FRICTION_BPS = 7.0  # 5 bps commission + 2 bps slippage
KOREAN_TAX_RATE = 0.22      # 22% capital gains tax
KOREAN_BASIC_DEDUCTION_KRW = 2_500_000.0


def generate_simplex_grid(step: float = 0.01) -> np.ndarray:
    """
    Generates exact weight triplets on the 2-simplex:
        w_SMH + w_XLK + w_VGT = 1.0,  w_i >= 0
    with step resolution (default 0.01 = 1%).

    For step=0.01, produces exactly C(100+3-1, 3-1) = C(102, 2) = 5,151 triplets.
    Returns:
        np.ndarray of shape (5151, 3), dtype float64, rounded to 4 decimal places.
    """
    n_steps = int(round(1.0 / step))
    triplets = []
    for i in range(n_steps + 1):
        for j in range(n_steps + 1 - i):
            k = n_steps - i - j
            triplets.append([i * step, j * step, k * step])
    grid = np.array(triplets, dtype=np.float64)
    grid = np.round(grid, 4)
    grid[:, 2] = np.maximum(0.0, 1.0 - grid[:, 0] - grid[:, 1])
    return grid


def _normalize_schedule(schedule: str) -> str:
    """Normalizes rebalancing schedule name."""
    s = str(schedule).strip().lower().replace("-", "_").replace(" ", "_")
    if s in ["annual", "yearly", "a", "y", "1"]:
        return "annual"
    elif s in ["quarterly", "q", "3", "quarter"]:
        return "quarterly"
    elif s in ["buy_and_hold", "buy_hold", "bah", "none", "hold"]:
        return "buy_and_hold"
    else:
        raise ValueError(f"Unsupported schedule '{schedule}'. Choose 'annual', 'quarterly', or 'buy_and_hold'.")


@dataclass
class TriTechSimplexResult:
    """
    Holds complete simulation outputs for all 5,151 weight triplets among SMH, XLK, VGT.
    Provides vectorized, cached analytical properties for CAGR, intra-year MDD,
    Calmar, Sharpe, turnover, and dual-currency NAV curves.
    """
    weights: np.ndarray                 # (5151, 3) [SMH, XLK, VGT]
    dates: pd.DatetimeIndex             # (N,)
    nav_matrix_usd: np.ndarray          # (N, 5151) USD NAV series
    nav_matrix_krw: np.ndarray          # (N, 5151) KRW NAV series
    currency: str                       # 'USD' or 'KRW'
    rebalance_schedule: str             # 'annual', 'quarterly', 'buy_and_hold'
    commission_bps: float               # e.g. 5.0
    slippage_bps: float                 # e.g. 2.0
    apply_tax: bool                     # Whether 22% tax was deducted
    rebalance_indices: np.ndarray       # Integer indices of rebalance events
    turnover_matrix: np.ndarray         # (M-1, 5151) Turnover fraction at each rebalance
    execution_time_sec: float           # Wall-clock simulation duration

    @property
    def nav_matrix(self) -> np.ndarray:
        """Active NAV matrix matching self.currency."""
        return self.nav_matrix_krw if self.currency == "KRW" else self.nav_matrix_usd

    @property
    def n_triplets(self) -> int:
        return len(self.weights)

    @property
    def n_days(self) -> int:
        return len(self.dates)

    @property
    def years(self) -> List[int]:
        """Unique calendar years present in the dataset."""
        return [int(y) for y in np.unique(self.dates.year)]

    @cached_property
    def total_years(self) -> float:
        """Total duration of backtest in astronomical years."""
        days = (self.dates[-1] - self.dates[0]).days
        return max(days / 365.25, 1e-6)

    @cached_property
    def cagr(self) -> np.ndarray:
        """
        Compound Annual Growth Rate for all 5,151 triplets in active currency.
        CAGR = (NAV_end / NAV_start) ^ (1 / Years) - 1.0
        """
        nav = self.nav_matrix
        start_vals = nav[0]
        end_vals = nav[-1]
        cagr_vals = (end_vals / start_vals) ** (1.0 / self.total_years) - 1.0
        return cagr_vals

    @cached_property
    def total_return(self) -> np.ndarray:
        """Total cumulative return across entire period in active currency."""
        nav = self.nav_matrix
        return (nav[-1] / nav[0]) - 1.0

    @cached_property
    def annual_mdd(self) -> pd.DataFrame:
        """
        Calculates calendar year intra-year MDD for each year (2012-2026) independently.
        At the start of each calendar year, peak tracking resets to that year's starting NAV.
        Returns:
            pd.DataFrame of shape (num_years, 5151), columns=triplet_indices, index=years.
        """
        nav = self.nav_matrix
        year_list = self.years
        mdd_table = np.empty((len(year_list), self.n_triplets), dtype=np.float64)

        for i, y in enumerate(year_list):
            mask = (self.dates.year == y)
            nav_y = nav[mask]
            peaks = np.maximum.accumulate(nav_y, axis=0)
            mdd_table[i] = np.min(nav_y / peaks, axis=0) - 1.0

        return pd.DataFrame(mdd_table, index=year_list, columns=np.arange(self.n_triplets))

    @property
    def annual_mdds(self) -> np.ndarray:
        """Array representation of annual intra-year MDD matrix."""
        return self.annual_mdd.values

    @cached_property
    def worst_annual_mdd(self) -> np.ndarray:
        """Worst (most severe, minimum) intra-year MDD across all calendar years for each triplet."""
        return np.min(self.annual_mdd.values, axis=0)

    @property
    def worst_mdd(self) -> np.ndarray:
        """Alias for worst_annual_mdd."""
        return self.worst_annual_mdd

    @cached_property
    def mean_annual_mdd(self) -> np.ndarray:
        """Average intra-year MDD across all calendar years for each triplet."""
        return np.mean(self.annual_mdd.values, axis=0)

    @cached_property
    def calmar_ratio(self) -> np.ndarray:
        """Calmar Ratio = CAGR / |Worst Annual MDD|."""
        worst_mdd_abs = np.abs(self.worst_annual_mdd)
        denom = np.where(worst_mdd_abs < 1e-6, 1e-6, worst_mdd_abs)
        return self.cagr / denom

    @property
    def calmar(self) -> np.ndarray:
        """Alias for calmar_ratio."""
        return self.calmar_ratio

    @cached_property
    def sharpe_ratio(self) -> np.ndarray:
        """
        Annualized Sharpe Ratio assuming risk-free rate rf = 2.0% annual (2.0% / 252 daily).
        Sharpe = sqrt(252) * mean(excess_daily) / std(daily)
        """
        nav = self.nav_matrix
        daily_ret = np.diff(nav, axis=0) / nav[:-1]
        rf_daily = 0.02 / 252.0
        excess_daily = daily_ret - rf_daily
        mean_excess = np.mean(excess_daily, axis=0)
        std_ret = np.std(daily_ret, axis=0)
        std_ret = np.where(std_ret < 1e-10, 1e-10, std_ret)
        return np.sqrt(252.0) * (mean_excess / std_ret)

    @property
    def sharpe(self) -> np.ndarray:
        """Alias for sharpe_ratio."""
        return self.sharpe_ratio

    @cached_property
    def mean_turnover(self) -> np.ndarray:
        """Average portfolio turnover per rebalance event across all triplets."""
        if len(self.turnover_matrix) == 0:
            return np.zeros(self.n_triplets, dtype=np.float64)
        return np.mean(self.turnover_matrix, axis=0)

    def get_triplet_nav(self, index: int) -> pd.Series:
        """Returns the daily NAV series for a specific weight triplet index."""
        if not (0 <= index < self.n_triplets):
            raise IndexError(f"Triplet index {index} out of range [0, {self.n_triplets}-1].")
        return pd.Series(self.nav_matrix[:, index], index=self.dates, name=f"Triplet_{index}")

    def find_closest_triplet_index(self, w_smh: float, w_xlk: float, w_vgt: float) -> int:
        """Finds the index of the closest weight triplet to the given target weights."""
        target = np.array([w_smh, w_xlk, w_vgt], dtype=np.float64)
        s = np.sum(target)
        if s > 0:
            target = target / s
        dists = np.sum((self.weights - target) ** 2, axis=1)
        return int(np.argmin(dists))

    def get_triplet_series(self, w_smh: float, w_xlk: float, w_vgt: float) -> pd.Series:
        """Returns daily NAV series for the closest matching weights."""
        idx = self.find_closest_triplet_index(w_smh, w_xlk, w_vgt)
        actual = self.weights[idx]
        s = self.get_triplet_nav(idx)
        s.name = f"Alloc(SMH={actual[0]:.2f}, XLK={actual[1]:.2f}, VGT={actual[2]:.2f})"
        return s

    def summary_df(self) -> pd.DataFrame:
        """
        Comprehensive summary DataFrame for all 5,151 triplets:
        Columns: SMH, XLK, VGT, CAGR, Worst_Annual_MDD, Mean_Annual_MDD, Calmar_Ratio, Sharpe_Ratio, Mean_Turnover
        """
        return pd.DataFrame({
            "SMH": self.weights[:, 0],
            "XLK": self.weights[:, 1],
            "VGT": self.weights[:, 2],
            "CAGR": self.cagr,
            "Total_Return": self.total_return,
            "Worst_Annual_MDD": self.worst_annual_mdd,
            "Mean_Annual_MDD": self.mean_annual_mdd,
            "Calmar_Ratio": self.calmar_ratio,
            "Sharpe_Ratio": self.sharpe_ratio,
            "Mean_Turnover": self.mean_turnover,
        })

    def switch_currency(self, new_currency: str) -> "TriTechSimplexResult":
        """Returns a new TriTechSimplexResult configured with new_currency ('USD' or 'KRW')."""
        curr = str(new_currency).strip().upper()
        if curr not in ["USD", "KRW"]:
            raise ValueError(f"Currency must be 'USD' or 'KRW', got: {new_currency}")
        return TriTechSimplexResult(
            weights=self.weights,
            dates=self.dates,
            nav_matrix_usd=self.nav_matrix_usd,
            nav_matrix_krw=self.nav_matrix_krw,
            currency=curr,
            rebalance_schedule=self.rebalance_schedule,
            commission_bps=self.commission_bps,
            slippage_bps=self.slippage_bps,
            apply_tax=self.apply_tax,
            rebalance_indices=self.rebalance_indices,
            turnover_matrix=self.turnover_matrix,
            execution_time_sec=self.execution_time_sec,
        )

    def __getitem__(self, item: str) -> Any:
        """Enables dictionary-style indexing (e.g. res['cagr'], res['worst_mdd'])."""
        if hasattr(self, item):
            val = getattr(self, item)
            return val
        raise KeyError(f"Key '{item}' not found in TriTechSimplexResult.")


def run_tri_tech_simplex(
    df_prices: pd.DataFrame,
    s_fx: Union[pd.Series, pd.DataFrame],
    schedule: str = "annual",
    friction_bps: float = DEFAULT_FRICTION_BPS,
    apply_tax: bool = False,
    currency: str = "USD",
    initial_capital_krw: float = 100_000_000.0,
    weights: Optional[np.ndarray] = None,
) -> TriTechSimplexResult:
    """
    Interface Contract:
    Vectorized pure-NumPy simulation of all 5,151 weight triplets across SMH, XLK, VGT.
    Executes in <0.5s.

    Args:
        df_prices: DataFrame with columns ['SMH', 'XLK', 'VGT'], DatetimeIndex >= 2011-12-20.
        s_fx: Series or DataFrame with USDKRW FX rates aligned to price dates.
        schedule: 'annual' (Jan rebalance), 'quarterly' (quarter ends), or 'buy_and_hold'.
        friction_bps: Total rebalance friction (commission + slippage) in bps (default 7.0 = 0.07%).
        apply_tax: Whether to deduct Korean 22% overseas capital gains tax with 2.5M KRW deduction.
        currency: 'USD' or 'KRW'.
        initial_capital_krw: Base capital in KRW for tax deduction calculation (default 100M KRW).
        weights: Optional custom (K, 3) weight matrix. Default is 5,151 triplets at 1% step.

    Returns:
        TriTechSimplexResult containing complete daily NAV matrix and metrics.
    """
    t0 = time.time()

    # 1. Weights grid
    if weights is None:
        weights = generate_simplex_grid(step=0.01)
    W = np.asarray(weights, dtype=np.float64)
    K = len(W)

    norm_sched = _normalize_schedule(schedule)
    curr = str(currency).strip().upper()
    if curr not in ["USD", "KRW"]:
        raise ValueError(f"Currency must be 'USD' or 'KRW', got '{currency}'")

    # Validate price columns
    for col in TECH_ASSET_NAMES:
        if col not in df_prices.columns:
            raise KeyError(f"Missing required price column '{col}' in df_prices.")

    prices_aligned = df_prices[TECH_ASSET_NAMES].copy()
    if prices_aligned.isna().any().any():
        prices_aligned = prices_aligned.ffill().bfill()

    P = prices_aligned.values.astype(np.float64)  # (N, 3)
    dates = prices_aligned.index
    N = len(P)

    # Align FX
    if isinstance(s_fx, pd.DataFrame):
        fx_s = s_fx["USDKRW"] if "USDKRW" in s_fx.columns else s_fx.iloc[:, 0]
    else:
        fx_s = s_fx
    fx_aligned = fx_s.reindex(dates).ffill().bfill().values.astype(np.float64)  # (N,)

    friction_rate = (friction_bps) / 10000.0

    # 2. Rebalancing Slices Identification
    if norm_sched == "buy_and_hold":
        # Buy and Hold: zero intermediate rebalancing
        P_norm = P / P[0]  # (N, 3)
        nav_matrix_usd = P_norm @ W.T  # (N, K)
        reb_indices = np.array([0], dtype=np.int64)
        turnover_matrix = np.zeros((0, K), dtype=np.float64)

    else:
        # Periodic Rebalancing
        period_code = "Y" if norm_sched == "annual" else "Q"
        periods = dates.to_period(period_code)
        reb_mask = np.empty(N, dtype=bool)
        reb_mask[0] = True
        reb_mask[1:] = (periods[1:] != periods[:-1])
        reb_indices = np.where(reb_mask)[0]

        slices: List[Tuple[int, int]] = []
        for p in range(len(reb_indices)):
            s_idx = int(reb_indices[p])
            e_idx = int(reb_indices[p + 1]) if (p + 1 < len(reb_indices)) else N
            slices.append((s_idx, e_idx))

        M = len(slices)

        # Start and End prices
        P_starts = np.array([P[s] for s, _ in slices], dtype=np.float64)  # (M, 3)
        P_ends = np.array([P[e if e < N else -1] for _, e in slices], dtype=np.float64)  # (M, 3)

        R_periods = P_ends / P_starts  # (M, 3)
        G = R_periods @ W.T  # (M, K) Gross period multiplier

        # Drifted weights at period end
        drifted_assets = R_periods[:, None, :] * W[None, :, :]  # (M, K, 3)
        w_drift = drifted_assets / G[:, :, None]  # (M, K, 3)

        # Turnover fraction
        turnover_full = np.sum(np.abs(W[None, :, :] - w_drift), axis=2)  # (M, K)
        cost_factor = 1.0 - friction_rate * turnover_full
        cost_factor[-1, :] = 1.0  # Terminal period has no exit friction

        net_period_mult = G * cost_factor  # (M, K)

        # Model Korean 22% capital gains tax if requested
        if apply_tax:
            # Track annual realized gains in KRW per triplet
            # Trimming an asset that appreciated relative to target realizes gain
            # Trimmed fraction of portfolio: max(0, w_drift - W)
            sold_fraction = np.maximum(0.0, w_drift - W[None, :, :])  # (M, K, 3)
            # Gain ratio on sold portion: approx max(0, 1 - 1 / R_periods)
            gain_ratio = np.maximum(0.0, 1.0 - 1.0 / R_periods)  # (M, 3)
            # Dollar gain per unit of portfolio at rebalance:
            dollar_gain_unit = np.sum(sold_fraction * gain_ratio[:, None, :], axis=2)  # (M, K)

            v_starts = np.empty((M, K), dtype=np.float64)
            v_starts[0] = 1.0
            initial_cap_usd = initial_capital_krw / fx_aligned[0]

            for p in range(M - 1):
                # Next portfolio capital before tax
                v_next = v_starts[p] * net_period_mult[p]
                # Is period end the end of a calendar year?
                end_day_idx = slices[p][1] - 1
                curr_year = dates[end_day_idx].year
                next_year = dates[min(end_day_idx + 1, N - 1)].year
                is_year_end = (curr_year != next_year) or (norm_sched == "annual")

                if is_year_end:
                    fx_end = fx_aligned[end_day_idx]
                    # Portfolio value in KRW before tax:
                    val_krw = v_next * initial_cap_usd * fx_end
                    # Realized gain in KRW:
                    realized_gain_krw = dollar_gain_unit[p] * val_krw
                    # Korean 2.5M KRW deduction:
                    taxable_gain_krw = np.maximum(0.0, realized_gain_krw - KOREAN_BASIC_DEDUCTION_KRW)
                    tax_krw = taxable_gain_krw * KOREAN_TAX_RATE
                    # Deduct tax fraction:
                    tax_fraction = np.where(val_krw > 0, tax_krw / val_krw, 0.0)
                    tax_multiplier = np.maximum(0.0, 1.0 - tax_fraction)
                    v_starts[p + 1] = v_next * tax_multiplier
                else:
                    v_starts[p + 1] = v_next
        else:
            v_starts = np.empty((M, K), dtype=np.float64)
            v_starts[0] = 1.0
            for p in range(M - 1):
                v_starts[p + 1] = v_starts[p] * net_period_mult[p]

        # Fast normalized daily price matrix
        P_norm = np.empty_like(P)
        for s, e in slices:
            P_norm[s:e] = P[s:e] / P[s]

        intra = P_norm @ W.T  # (N, K)
        v_expanded = np.empty((N, K), dtype=np.float64)
        for p, (s, e) in enumerate(slices):
            v_expanded[s:e] = v_starts[p]

        nav_matrix_usd = intra * v_expanded
        turnover_matrix = turnover_full[:-1, :] if M > 1 else np.zeros((0, K), dtype=np.float64)

    # 3. KRW NAV Matrix
    # V_KRW(t) = V_USD(t) * FX(t) / FX(0)
    fx_factor = fx_aligned / fx_aligned[0]  # (N,)
    nav_matrix_krw = nav_matrix_usd * fx_factor[:, None]

    execution_time = time.time() - t0
    logger.info(
        f"Simplex simulation completed in {execution_time:.4f}s: "
        f"{K} triplets, schedule='{norm_sched}', currency='{curr}', tax={apply_tax}."
    )

    return TriTechSimplexResult(
        weights=W,
        dates=dates,
        nav_matrix_usd=nav_matrix_usd,
        nav_matrix_krw=nav_matrix_krw,
        currency=curr,
        rebalance_schedule=norm_sched,
        commission_bps=5.0,
        slippage_bps=2.0,
        apply_tax=apply_tax,
        rebalance_indices=reb_indices,
        turnover_matrix=turnover_matrix,
        execution_time_sec=execution_time,
    )


# Alias
simulate_tri_tech_simplex = run_tri_tech_simplex
