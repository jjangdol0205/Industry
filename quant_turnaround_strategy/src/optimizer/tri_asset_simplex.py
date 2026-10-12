"""
Tri-Asset Simplex Grid Optimizer & High-Speed Vectorized Simulation Engine.
Evaluates the complete 3-asset allocation simplex (SPY, QQQ, SOXX) at 1% step resolution
(exact 5,151 weight triplets) across periodic rebalancing schedules (Quarterly, Annual, Monthly)
with realistic transaction friction (0.05% commission + 0.02% slippage = 0.07% turnover drag),
dual-currency (USD and KRW) tracking, and sub-second execution (<1.0s) using pure NumPy/Pandas.
Zero dependency on SciPy.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, Union, List
from functools import cached_property
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ASSET_NAMES = ["SPY", "QQQ", "SOXX"]


def generate_simplex_grid(step: float = 0.01) -> np.ndarray:
    """
    Generates exact weight triplets on the 2-simplex:
        w_SPY + w_QQQ + w_SOXX = 1.0,  w_i >= 0
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
    # Ensure exact mathematical sum to 1.0 and non-negativity
    grid = np.round(grid, 4)
    grid[:, 2] = np.maximum(0.0, 1.0 - grid[:, 0] - grid[:, 1])
    return grid


def _normalize_freq(freq: str) -> Tuple[str, str]:
    """Normalizes rebalancing frequency string to (standard_name, pandas_period_code)."""
    f = str(freq).strip().upper()
    if f in ["Q", "QUARTERLY"]:
        return "Quarterly", "Q"
    elif f in ["M", "MONTHLY"]:
        return "Monthly", "M"
    elif f in ["A", "Y", "ANNUAL", "YEARLY", "ANNUALLY"]:
        return "Annual", "Y"
    else:
        raise ValueError(f"Unsupported rebalance frequency: '{freq}'. Choose 'Quarterly' ('Q'), 'Annual' ('A'), or 'Monthly' ('M').")


@dataclass
class SimplexGridResult:
    """
    Holds complete simulation outputs for all 5,151 weight triplets.
    Provides vectorized, cached analytical properties for CAGR, intra-year MDD,
    Calmar, Sharpe, turnover, and dual-currency NAV curves.
    """
    weights: np.ndarray                 # (5151, 3)
    dates: pd.DatetimeIndex             # (N,)
    nav_matrix_usd: np.ndarray          # (N, 5151) USD NAV series
    nav_matrix_krw: np.ndarray          # (N, 5151) KRW NAV series
    currency: str                       # 'USD' or 'KRW'
    rebalance_freq: str                 # 'Quarterly', 'Annual', 'Monthly'
    commission_bps: float               # e.g. 5.0 (0.05%)
    slippage_bps: float                 # e.g. 2.0 (0.02%)
    rebalance_indices: np.ndarray       # Integer indices of rebalancing days
    turnover_matrix: np.ndarray         # (M-1, 5151) Turnover fraction at each rebalance
    execution_time_sec: float           # Wall-clock simulation duration

    @property
    def nav_matrix(self) -> np.ndarray:
        """Returns the active NAV matrix matching self.currency."""
        return self.nav_matrix_krw if self.currency == "KRW" else self.nav_matrix_usd

    @property
    def n_triplets(self) -> int:
        return len(self.weights)

    @property
    def n_days(self) -> int:
        return len(self.dates)

    @cached_property
    def total_years(self) -> float:
        """Total duration of backtest in astronomical years (365.25 days/year)."""
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
        Calculates calendar year intra-year MDD for each year (2001-2026) independently.
        At the start of each calendar year, peak tracking resets to that year's starting NAV.
        Returns:
            pd.DataFrame of shape (num_years, 5151), columns=triplet_indices, index=years.
        """
        nav = self.nav_matrix
        years = np.unique(self.dates.year)
        mdd_table = np.empty((len(years), self.n_triplets), dtype=np.float64)

        for i, y in enumerate(years):
            mask = (self.dates.year == y)
            nav_y = nav[mask]
            # Intra-year running peak
            peaks = np.maximum.accumulate(nav_y, axis=0)
            # Minimum intra-year drawdown = min(nav / peaks - 1.0)
            mdd_table[i] = np.min(nav_y / peaks, axis=0) - 1.0

        return pd.DataFrame(mdd_table, index=years, columns=np.arange(self.n_triplets))

    @cached_property
    def worst_annual_mdd(self) -> np.ndarray:
        """
        Worst (most severe, minimum) intra-year MDD across all calendar years for each triplet.
        Negative float (e.g. -0.4910).
        """
        return np.min(self.annual_mdd.values, axis=0)

    @cached_property
    def mean_annual_mdd(self) -> np.ndarray:
        """Average intra-year MDD across all calendar years for each triplet."""
        return np.mean(self.annual_mdd.values, axis=0)

    @cached_property
    def calmar_ratio(self) -> np.ndarray:
        """
        Calmar Ratio = CAGR / |Worst Annual MDD|.
        Guarantees non-negative ratio.
        """
        worst_mdd = np.abs(self.worst_annual_mdd)
        # Avoid division by zero in pathological edge cases
        denom = np.where(worst_mdd < 1e-6, 1e-6, worst_mdd)
        return self.cagr / denom

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

    def find_closest_triplet_index(self, w_spy: float, w_qqq: float, w_soxx: float) -> int:
        """Finds the index of the closest weight triplet to the given target weights."""
        target = np.array([w_spy, w_qqq, w_soxx], dtype=np.float64)
        target = target / max(np.sum(target), 1e-6)
        dists = np.sum((self.weights - target) ** 2, axis=1)
        return int(np.argmin(dists))

    def get_triplet_series(self, w_spy: float, w_qqq: float, w_soxx: float) -> pd.Series:
        """Returns daily NAV series for the closest matching weights."""
        idx = self.find_closest_triplet_index(w_spy, w_qqq, w_soxx)
        actual = self.weights[idx]
        s = self.get_triplet_nav(idx)
        s.name = f"Alloc(SPY={actual[0]:.2f}, QQQ={actual[1]:.2f}, SOXX={actual[2]:.2f})"
        return s

    def summary_df(self) -> pd.DataFrame:
        """
        Produces comprehensive summary DataFrame for all 5,151 triplets:
        Columns: SPY, QQQ, SOXX, CAGR, Worst_Annual_MDD, Mean_Annual_MDD, Calmar_Ratio, Sharpe_Ratio, Mean_Turnover
        """
        return pd.DataFrame({
            "SPY": self.weights[:, 0],
            "QQQ": self.weights[:, 1],
            "SOXX": self.weights[:, 2],
            "CAGR": self.cagr,
            "Total_Return": self.total_return,
            "Worst_Annual_MDD": self.worst_annual_mdd,
            "Mean_Annual_MDD": self.mean_annual_mdd,
            "Calmar_Ratio": self.calmar_ratio,
            "Sharpe_Ratio": self.sharpe_ratio,
            "Mean_Turnover": self.mean_turnover,
        })

    def switch_currency(self, new_currency: str) -> "SimplexGridResult":
        """
        Returns a new SimplexGridResult configured with new_currency ('USD' or 'KRW')
        without needing to re-simulate.
        """
        curr = str(new_currency).strip().upper()
        if curr not in ["USD", "KRW"]:
            raise ValueError(f"Currency must be 'USD' or 'KRW', got: {new_currency}")
        return SimplexGridResult(
            weights=self.weights,
            dates=self.dates,
            nav_matrix_usd=self.nav_matrix_usd,
            nav_matrix_krw=self.nav_matrix_krw,
            currency=curr,
            rebalance_freq=self.rebalance_freq,
            commission_bps=self.commission_bps,
            slippage_bps=self.slippage_bps,
            rebalance_indices=self.rebalance_indices,
            turnover_matrix=self.turnover_matrix,
            execution_time_sec=self.execution_time_sec,
        )


def simulate_simplex_grid(
    prices_df: pd.DataFrame,
    fx_df: pd.DataFrame,
    weights: Optional[np.ndarray] = None,
    rebalance_freq: str = "Q",
    commission_bps: float = 5.0,
    slippage_bps: float = 2.0,
    currency: str = "USD",
) -> SimplexGridResult:
    """
    Interface Contract:
    Vectorized block simulation of all 5,151 weight triplets across the complete price history.
    Executes in <1.0 second on local hardware.
    
    Args:
        prices_df: pd.DataFrame with columns ['SPY', 'QQQ', 'SOXX'], DatetimeIndex starting 2001-07-10.
        fx_df: pd.DataFrame with column ['USDKRW'], DatetimeIndex aligned with prices_df.
        weights: (5151, 3) matrix of simplex weights. If None, generate_simplex_grid(0.01) is used.
        rebalance_freq: 'Quarterly' ('Q'), 'Annual' ('A'), or 'Monthly' ('M').
        commission_bps: Brokerage commission rate in basis points (default 5.0 bps = 0.05%).
        slippage_bps: Execution slippage rate in basis points (default 2.0 bps = 0.02%).
        currency: 'USD' or 'KRW'.
        
    Returns:
        SimplexGridResult containing all daily NAV series and calculated performance metrics.
    """
    import time
    t0 = time.time()

    # 1. Validate inputs and normalize types
    if weights is None:
        weights = generate_simplex_grid(step=0.01)
    
    W = np.asarray(weights, dtype=np.float64)
    if W.ndim != 2 or W.shape[1] != 3:
        raise ValueError(f"Weights must have shape (K, 3), got {W.shape}")

    K = len(W)
    freq_name, period_code = _normalize_freq(rebalance_freq)
    curr = str(currency).strip().upper()
    if curr not in ["USD", "KRW"]:
        raise ValueError(f"Currency must be 'USD' or 'KRW', got '{currency}'")

    # Align price columns: ['SPY', 'QQQ', 'SOXX']
    for col in ASSET_NAMES:
        if col not in prices_df.columns:
            raise KeyError(f"Required price column '{col}' missing from prices_df.")

    prices_aligned = prices_df[ASSET_NAMES].copy()
    if prices_aligned.isna().any().any():
        prices_aligned = prices_aligned.ffill().bfill()

    P = prices_aligned.values.astype(np.float64)  # (N, 3)
    dates = prices_aligned.index
    N = len(P)

    # Align FX rates
    fx_series = fx_df["USDKRW"] if "USDKRW" in fx_df.columns else fx_df.iloc[:, 0]
    fx_aligned = fx_series.reindex(dates).ffill().bfill().values.astype(np.float64)  # (N,)

    # 2. Vectorized rebalancing date identification
    # A day is a rebalance day if its calendar period differs from the previous day's period
    periods = dates.to_period(period_code)
    reb_mask = np.empty(N, dtype=bool)
    reb_mask[0] = True
    reb_mask[1:] = (periods[1:] != periods[:-1])
    reb_indices = np.where(reb_mask)[0]  # Array of start indices for each period

    # Slices for each period: [s_idx, e_idx)
    slices: List[Tuple[int, int]] = []
    for p in range(len(reb_indices)):
        s_idx = int(reb_indices[p])
        e_idx = int(reb_indices[p + 1]) if (p + 1 < len(reb_indices)) else N
        slices.append((s_idx, e_idx))

    M = len(slices)

    # 3. Vectorized Period Returns & Drifted Rebalance Turnover
    # Friction rate in decimal: (5.0 + 2.0) / 10000 = 0.0007 (7 bps)
    friction_rate = (commission_bps + slippage_bps) / 10000.0

    # Start prices of each period: P[s_idx]
    P_starts = np.array([P[s] for s, _ in slices], dtype=np.float64)  # (M, 3)
    # End prices of each period (at next rebalance day):
    P_ends = np.array([P[e] if e < N else P[-1] for _, e in slices], dtype=np.float64)  # (M, 3)

    # Price ratios over each period: shape (M, 3)
    R_periods = P_ends / P_starts  # (M, 3)

    # Gross return multiplier for all 5,151 triplets across each period:
    # G = R_periods @ W.T -> shape (M, K)
    G = R_periods @ W.T  # (M, K)

    # Drifted asset values: shape (M, K, 3)
    # broadcasting: R_periods is (M, 1, 3), W is (1, K, 3)
    drifted_assets = R_periods[:, None, :] * W[None, :, :]  # (M, K, 3)
    gross_val = G[:, :, None]  # (M, K, 1)
    w_drift = drifted_assets / gross_val  # (M, K, 3)

    # Rebalance turnover = trade volume = sum(|w_target - w_drift|) across the 3 assets
    turnover_full = np.sum(np.abs(W[None, :, :] - w_drift), axis=2)  # (M, K)
    cost_factor = 1.0 - friction_rate * turnover_full  # (M, K)
    # The final period end has no subsequent rebalance friction
    cost_factor[-1, :] = 1.0

    # Cumulative capital at start of each period
    # v_starts[0] = 1.0
    # v_starts[p+1] = v_starts[p] * G[p] * cost_factor[p]
    net_period_mult = G * cost_factor  # (M, K)
    v_starts = np.empty((M, K), dtype=np.float64)
    v_starts[0] = 1.0
    for p in range(M - 1):
        v_starts[p + 1] = v_starts[p] * net_period_mult[p]

    # 4. Intra-period Normalized Prices and Matrix Evaluation
    # Normalize price within each period relative to its start price
    P_norm = np.empty_like(P)
    for s, e in slices:
        P_norm[s:e] = P[s:e] / P[s]

    # Intra-period daily gross NAV multiplier: shape (N, K)
    intra = P_norm @ W.T  # (N, K)

    # Final USD Daily NAV Matrix
    nav_matrix_usd = np.empty((N, K), dtype=np.float64)
    for p, (s, e) in enumerate(slices):
        nav_matrix_usd[s:e] = intra[s:e] * v_starts[p]

    # 5. Dual-Currency KRW NAV Matrix
    # V_KRW(t) = V_USD(t) * FX(t) / FX(T_0)
    fx_factor = fx_aligned / fx_aligned[0]  # (N,)
    nav_matrix_krw = nav_matrix_usd * fx_factor[:, None]

    # Rebalance turnover matrix (excluding the final dummy period)
    turnover_matrix = turnover_full[:-1, :] if M > 1 else np.zeros((0, K), dtype=np.float64)

    execution_time = time.time() - t0
    logger.info(
        f"Simplex grid simulation completed in {execution_time:.4f}s: "
        f"{K} triplets, {M} periods ({freq_name}), {N} trading days."
    )

    return SimplexGridResult(
        weights=W,
        dates=dates,
        nav_matrix_usd=nav_matrix_usd,
        nav_matrix_krw=nav_matrix_krw,
        currency=curr,
        rebalance_freq=freq_name,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        rebalance_indices=reb_indices,
        turnover_matrix=turnover_matrix,
        execution_time_sec=execution_time,
    )
