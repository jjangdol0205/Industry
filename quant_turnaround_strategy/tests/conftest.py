"""
Pytest configuration, shared fixtures, and reference oracles for Quantitative Turnaround Strategy System.
Supports comprehensive 4-Tier test architecture across Features F1-F13.
"""
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pytest
import pandas as pd
import numpy as np

# Ensure root repository directory is on sys.path
REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from config.settings import DEFAULT_START_DATE, SEC_LAG_10Q_DAYS, SEC_LAG_10K_DAYS, CACHE_DIR
from src.data.cache_store import CacheStore
from src.data.universe import UniverseManager
from src.data.price_feed import PriceFeed
from src.models.schemas import (
    DailyBar,
    UniverseConstituent,
    PITFinancialStatement,
    CandidateEvaluation,
    WeeklySelectionResult,
    ExclusionReason,
)

# Optional M1 screening module fixtures
try:
    from src.screening.turnaround_scorer import PITFundamentalStore, TurnaroundScorer
except ImportError:
    PITFundamentalStore = None
    TurnaroundScorer = None


# ==============================================================================
# 1. Base Framework & Repository Fixtures
# ==============================================================================

@pytest.fixture
def cache_store():
    return CacheStore()


@pytest.fixture
def universe_manager():
    return UniverseManager()


@pytest.fixture
def price_feed(cache_store):
    return PriceFeed(cache_store=cache_store)


@pytest.fixture
def fundamental_store():
    if PITFundamentalStore is not None:
        return PITFundamentalStore.from_seed_file()
    return None


@pytest.fixture
def turnaround_scorer(fundamental_store):
    if TurnaroundScorer is not None and fundamental_store is not None:
        return TurnaroundScorer(fundamental_store=fundamental_store)
    return None


# ==============================================================================
# 2. Date & Parameter Fixtures
# ==============================================================================

@pytest.fixture(scope="session")
def inception_date_str() -> str:
    """The mandatory legal inception date for the strategy backtest."""
    return DEFAULT_START_DATE  # '2001-07-10'


@pytest.fixture(scope="session")
def inception_date() -> date:
    return date(2001, 7, 10)


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Isolated temporary directory for caching during tests."""
    cache_path = tmp_path / "cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


@pytest.fixture
def test_cache_store(temp_cache_dir: Path) -> CacheStore:
    return CacheStore(temp_cache_dir)


@pytest.fixture
def test_price_feed(test_cache_store: CacheStore) -> PriceFeed:
    return PriceFeed(cache_store=test_cache_store)


# ==============================================================================
# 3. Synthetic Market Data Generators & Fixtures
# ==============================================================================

@pytest.fixture(scope="session")
def synthetic_benchmark_df() -> pd.DataFrame:
    """
    Creates a mathematically controlled synthetic MultiIndex DataFrame for QQQ and SOXX
    spanning July 10, 2001 to December 31, 2002 (370 trading days),
    with zero NaNs and realistic prices.
    """
    dates = pd.date_range("2001-07-10", "2002-12-31", freq="B")
    n = len(dates)

    np.random.seed(42)
    qqq_ret = np.random.normal(-0.0005, 0.015, n)
    soxx_ret = np.random.normal(-0.0010, 0.022, n)

    qqq_close = 35.0 * np.cumprod(1 + qqq_ret)
    soxx_close = 20.0 * np.cumprod(1 + soxx_ret)

    data = {
        ("Close", "QQQ"): qqq_close,
        ("High", "QQQ"): qqq_close * 1.015,
        ("Low", "QQQ"): qqq_close * 0.985,
        ("Open", "QQQ"): qqq_close * 1.002,
        ("Volume", "QQQ"): np.full(n, 10_000_000.0),
        ("Close", "SOXX"): soxx_close,
        ("High", "SOXX"): soxx_close * 1.020,
        ("Low", "SOXX"): soxx_close * 0.980,
        ("Open", "SOXX"): soxx_close * 1.005,
        ("Volume", "SOXX"): np.full(n, 2_000_000.0),
    }

    df = pd.DataFrame(data, index=dates)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


@pytest.fixture(scope="session")
def known_drawdown_fixtures() -> Dict[str, pd.Series]:
    """
    Synthetic NAV series with mathematically exact, hand-calculated drawdowns.
    Used as ground-truth test oracles.
    """
    # Series 1: Simple 50% drop (Peak 120 -> 60 -> -50.0%)
    d1 = pd.date_range("2001-01-01", periods=5, freq="D")
    s1 = pd.Series([100.0, 120.0, 60.0, 75.0, 90.0], index=d1)

    # Series 2: Monotonic increase (No drawdown)
    d2 = pd.date_range("2002-01-01", periods=4, freq="D")
    s2 = pd.Series([100.0, 110.0, 120.0, 130.0], index=d2)

    # Series 3: Monotonic decrease (Peak 100 -> 40 -> -60.0%)
    d3 = pd.date_range("2003-01-01", periods=4, freq="D")
    s3 = pd.Series([100.0, 80.0, 60.0, 40.0], index=d3)

    # Series 4: Multi-year series (2001-2004)
    dates_multi = [
        pd.Timestamp("2001-07-10"), pd.Timestamp("2001-09-01"), pd.Timestamp("2001-12-31"),
        pd.Timestamp("2002-01-02"), pd.Timestamp("2002-06-01"), pd.Timestamp("2002-12-31"),
        pd.Timestamp("2003-01-02"), pd.Timestamp("2003-07-01"), pd.Timestamp("2003-12-31"),
    ]
    vals_multi = [100.0, 70.0, 80.0, 80.0, 45.0, 50.0, 50.0, 80.0, 100.0]
    s4 = pd.Series(vals_multi, index=pd.DatetimeIndex(dates_multi))

    return {
        "fifty_pct_drop": s1,
        "monotonic_up": s2,
        "monotonic_down": s3,
        "multi_year": s4,
    }


# ==============================================================================
# 4. Reference Oracles (Authoritative Expected Outputs)
# ==============================================================================

class ReferenceOracles:
    """
    Mathematical reference oracle implementations derived strictly from
    PROJECT.md and ORIGINAL_REQUEST.md specifications.
    Every test compares against these authoritative calculations.
    """

    @staticmethod
    def rolling_252_day_low(prices: pd.Series, window: int = 252) -> pd.Series:
        return prices.rolling(window=window, min_periods=1).min()

    @staticmethod
    def low_proximity(close: float, low_52w: float) -> float:
        if low_52w <= 0:
            return 0.0
        return (close - low_52w) / low_52w

    @staticmethod
    def anti_falling_knife_filter(
        rsi_14: float,
        return_5d: float,
        min_rsi: float = 20.0,
        min_5d_return: float = -0.05
    ) -> bool:
        return (rsi_14 >= min_rsi) and (return_5d >= min_5d_return)

    @staticmethod
    def calendar_year_mdd(nav_series: pd.Series) -> pd.DataFrame:
        df = pd.DataFrame({"NAV": nav_series})
        df["Year"] = df.index.year

        results = []
        for year, group in df.groupby("Year"):
            values = group["NAV"].values
            peaks = np.maximum.accumulate(values)
            drawdowns = (values - peaks) / peaks
            annual_mdd = float(np.min(drawdowns))
            
            start_val = values[0]
            end_val = values[-1]
            annual_ret = float((end_val - start_val) / start_val) if start_val > 0 else 0.0
            
            if abs(annual_mdd) > 1e-4:
                ret_to_mdd = float(annual_ret / abs(annual_mdd))
            else:
                ret_to_mdd = float(annual_ret * 100.0)

            results.append({
                "Year": int(year),
                "Annual_Return": annual_ret,
                "Annual_MDD": annual_mdd,
                "Return_to_MDD": ret_to_mdd,
            })

        return pd.DataFrame(results)

    @staticmethod
    def calmar_ratio(cagr: float, max_annual_mdd: float) -> float:
        denom = abs(max_annual_mdd)
        if denom < 1e-6:
            return 0.0
        return float(cagr / denom)

    @staticmethod
    def verify_portfolio_weight_invariant(weights: Dict[str, float], tol: float = 1e-6) -> bool:
        total = sum(weights.values())
        return abs(total - 1.0) <= tol

    @staticmethod
    def evaluate_turnaround_4_pillars(
        rev_curr: float,
        rev_q4: float,
        rev_q1: float,
        rev_q5: float,
        opm_curr: float,
        opm_prev: float,
        current_ratio: float,
        debt_ebitda: float,
        ev_sales_discount: float
    ) -> Tuple[float, Dict[str, bool]]:
        g_curr = (rev_curr - rev_q4) / rev_q4 if rev_q4 > 0 else 0.0
        g_prev = (rev_q1 - rev_q5) / rev_q5 if rev_q5 > 0 else 0.0
        p1 = g_curr > g_prev

        p2 = opm_curr > opm_prev
        p3 = (current_ratio >= 1.0) and (debt_ebitda < 3.5)
        p4 = ev_sales_discount >= 0.30

        score = (
            (40.0 if p1 else 0.0) +
            (30.0 if p2 else 0.0) +
            (20.0 if p3 else 0.0) +
            (10.0 if p4 else 0.0)
        )

        return score, {"p1_rev_inflection": p1, "p2_opm_recovery": p2, "p3_solvency": p3, "p4_valuation": p4}

    @staticmethod
    def simulate_risk_manager_exits(
        entry_price: float,
        price_history: List[float],
        stop_loss_pct: float = -0.12,
        profit_target_pct: float = 0.35,
        trailing_stop_pct: float = 0.10,
        max_holding_days: int = 130
    ) -> Optional[Tuple[int, str, float]]:
        peak_price = entry_price
        for day_idx, p in enumerate(price_history):
            if p > peak_price:
                peak_price = p

            pnl_from_entry = (p - entry_price) / entry_price
            if pnl_from_entry <= stop_loss_pct:
                return (day_idx, "STOP_LOSS", p)

            if pnl_from_entry >= profit_target_pct:
                return (day_idx, "TAKE_PROFIT", p)

            if (p - peak_price) / peak_price <= -trailing_stop_pct:
                return (day_idx, "TRAILING_STOP", p)

            if day_idx >= max_holding_days:
                return (day_idx, "TIME_STOP", p)

        return None


@pytest.fixture(scope="session")
def reference_oracles() -> ReferenceOracles:
    return ReferenceOracles()


# ==============================================================================
# 5. Point-In-Time Sample Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_pit_financials() -> List[PITFinancialStatement]:
    return [
        PITFinancialStatement(
            ticker="AAPL",
            fiscal_period_end=date(2020, 3, 31),
            filing_date=date(2020, 5, 1),
            period_type="Q",
            revenue=58_313_000_000.0,
            operating_income=12_853_000_000.0,
            net_income=11_249_000_000.0,
            operating_cash_flow=13_311_000_000.0,
            total_debt=118_000_000_000.0,
            cash_and_equivalents=94_000_000_000.0,
            current_ratio=1.50,
            ebitda=15_000_000_000.0,
        ),
        PITFinancialStatement(
            ticker="NVDA",
            fiscal_period_end=date(2022, 1, 31),
            filing_date=date(2022, 3, 18),
            period_type="FY",
            revenue=26_914_000_000.0,
            operating_income=10_041_000_000.0,
            net_income=9_752_000_000.0,
            operating_cash_flow=9_108_000_000.0,
            total_debt=11_680_000_000.0,
            cash_and_equivalents=21_208_000_000.0,
            current_ratio=6.65,
            ebitda=11_200_000_000.0,
        ),
    ]


@pytest.fixture
def sample_universe_constituents() -> List[UniverseConstituent]:
    return [
        UniverseConstituent(
            ticker="ENE",
            start_date=date(1996, 1, 2),
            end_date=date(2001, 11, 30),
            name="Enron Corp",
            sector="Energy",
        ),
        UniverseConstituent(
            ticker="LEH",
            start_date=date(1996, 1, 2),
            end_date=date(2008, 9, 15),
            name="Lehman Brothers Holdings",
            sector="Financials",
        ),
        UniverseConstituent(
            ticker="AAPL",
            start_date=date(1996, 1, 2),
            end_date=date(2099, 12, 31),
            name="Apple Inc",
            sector="Technology",
        ),
        UniverseConstituent(
            ticker="TSLA",
            start_date=date(2020, 12, 21),
            end_date=date(2099, 12, 31),
            name="Tesla Inc",
            sector="Consumer Discretionary",
        ),
    ]
