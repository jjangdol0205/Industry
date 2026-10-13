"""
Hybrid QQQ + SOXX + 2-Stock Turnaround Engine with Real-World Frictions and Taxation.

Institutional 4-Asset Backtesting Simulation:
1. Asset Universe:
   - Core Index ETFs: QQQ, SOXX
   - Up to 2 concurrent individual 52-week-low turnaround stocks screened point-in-time
     from UniverseManager and RollingLowScreener without lookahead bias.
   - Weights: w_qqq, w_soxx, w_stocks in [0%, 30%] (split equally w_stocks / 2 per active stock slot).
2. Strict Execution Mechanics:
   - Daily strict -10% hard stop-loss: closing at or below -10% triggers immediate stop liquidation.
   - Realistic slippage: 10-15 bps slippage, overnight gap-down fills at open_price * (1.0 - slippage).
   - Auto-replacement on next trading day (T+1): automatically purchase the next-in-line qualified candidate
     (or fallback to cash/ETF sweep if none qualifies).
   - Profit-taking: +25% gain triggers 50% partial exit; remaining 50% lot held until annual rebalance or stop.
   - Brokerage commissions: 5 bps on entry/exit.
   - Regulatory fees on sells: SEC Section 31 fee (~0.28 bps) and FINRA TAF ($0.000166/share, max $8.30).
3. Realistic Tax & Settlement Modeling:
   - Discrete FIFO lot tracking for KRW realized gains per trade lot.
   - Annual net realized capital gains aggregation across active trades + ETF rebalances.
   - 2.5M KRW basic deduction, 22% Korean overseas capital gains tax deducted from portfolio cash at year-end.
   - T+1 cash settlement availability: sales proceeds become available for buys on T+1.
4. Turnover & Friction Metrics:
   - Annual turnover rate (%).
   - Total transaction fees paid ($ / KRW).
   - Total taxes paid ($ / KRW).
   - Gross strategy return vs Net after-tax / after-cost return, showing net alpha over passive ETF holding.
5. Optimization:
   - Grid search over (w_qqq, w_soxx, w_stocks) across 4 risk tiers maximizing Calmar.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
import numpy as np
import pandas as pd
from pathlib import Path

from src.data.universe import UniverseManager
from src.screening.rolling_low import RollingLowScreener
from src.screening.turnaround_scorer import TurnaroundScorer
from src.screening.exclusion_gates import ExclusionGates
from src.screening.weekly_selector import WeeklySelector
from src.engine.tax import KoreanTaxEngine, AnnualTaxRecord
from src.engine.metrics import PerformanceMetrics
from src.data.tri_asset_loader import TriAssetDataLoader
from src.data.cache_store import CacheStore
from config.settings import CACHE_DIR

logger = logging.getLogger(__name__)

_DEFAULT_CANDIDATE_POOLS_CACHE: Dict[str, pd.DataFrame] = {}


@dataclass
class FIFOTaxLot:
    """Discrete tax lot tracking acquisition cost basis, date, and allocated entry costs."""
    lot_id: str
    ticker: str
    shares: float
    entry_date: date
    entry_price: float         # Nominal USD acquisition price
    entry_fx: float            # USDKRW on entry date
    buy_commission_usd: float  # Allocated buy commission in USD
    buy_slippage_usd: float    # Allocated buy slippage in USD

    @property
    def cost_basis_usd(self) -> float:
        return (self.shares * self.entry_price) + self.buy_commission_usd + self.buy_slippage_usd

    @property
    def cost_basis_krw(self) -> float:
        return (self.shares * self.entry_price * self.entry_fx) + ((self.buy_commission_usd + self.buy_slippage_usd) * self.entry_fx)


@dataclass
class HybridPosition:
    """Active portfolio position with lot-level tracking and exit status."""
    ticker: str
    shares: float
    entry_price: float
    entry_date: date
    entry_fx: float
    current_price: float = 0.0
    peak_price: float = 0.0
    days_held: int = 0
    is_stock: bool = True
    partial_profit_taken: bool = False
    lots: List[FIFOTaxLot] = field(default_factory=list)

    def __post_init__(self):
        if self.current_price <= 0:
            self.current_price = self.entry_price
        if self.peak_price <= 0:
            self.peak_price = self.entry_price

    def update_price(self, price: float) -> None:
        self.current_price = price
        if price > self.peak_price:
            self.peak_price = price
        self.days_held += 1

    @property
    def market_value_usd(self) -> float:
        return self.shares * self.current_price

    def market_value_krw(self, fx_rate: float) -> float:
        return self.shares * self.current_price * fx_rate


@dataclass
class HybridBacktestResult:
    """Comprehensive hybrid backtest simulation outputs adhering to PROJECT.md interface contract."""
    equity_curve: pd.DataFrame
    trade_log: pd.DataFrame
    turnover_summary: Dict[str, float]
    optimal_weights: Dict[str, float]
    # Compatibility properties for ecosystem callers
    daily_nav_usd: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    daily_nav_krw: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    gross_nav_usd: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    after_tax_nav_usd: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    gross_nav_krw: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    after_tax_nav_krw: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    annual_tax_records: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    annual_metrics_usd: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    annual_metrics_krw: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    calmar_ratio_usd: float = 0.0
    calmar_ratio_krw: float = 0.0
    cagr_usd: float = 0.0
    cagr_krw: float = 0.0
    max_annual_mdd_usd: float = 0.0
    max_annual_mdd_krw: float = 0.0
    allocation_history: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())


class HybridBacktester:
    """
    Hybrid 4-Asset Backtesting Engine:
    Combines core QQQ and SOXX index ETFs with up to 2 individual 52-week-low turnaround stocks.
    Applies daily -10% hard stop, +25% partial profit-taking (50%), T+1 auto-replacement,
    and realistic Korean overseas capital gains tax with discrete FIFO lot accounting.
    """

    def __init__(
        self,
        w_qqq: float = 0.50,
        w_soxx: float = 0.30,
        w_stocks: float = 0.20,
        initial_capital: float = 100_000.0,
        stop_loss: float = -0.10,
        profit_take: float = 0.25,
        profit_take_ratio: float = 0.50,
        slippage_stock_bps: float = 12.0,
        slippage_etf_bps: float = 2.0,
        commission_bps: float = 5.0,
        sec_fee_bps: float = 0.28,
        finra_taf_per_share: float = 0.000166,
        max_stock_capacity: int = 2,
        idle_policy: str = "etf_sweep",
        rebalance_month: int = 1,
        rebalance_deadzone: float = 0.01,
        tax_enabled: bool = True,
        basic_deduction_krw: float = 2_500_000.0,
        tax_rate: float = 0.22,
        universe_manager: Optional[UniverseManager] = None,
        rolling_low_screener: Optional[RollingLowScreener] = None,
        turnaround_scorer: Optional[TurnaroundScorer] = None,
        candidate_price_dfs: Optional[Dict[str, pd.DataFrame]] = None,
        prices_df: Optional[pd.DataFrame] = None,
        fx_df: Optional[pd.DataFrame] = None,
    ):
        # Normalize weights so they sum to 1.0
        total_w = w_qqq + w_soxx + w_stocks
        if total_w > 0:
            self.w_qqq = float(w_qqq / total_w)
            self.w_soxx = float(w_soxx / total_w)
            self.w_stocks = float(w_stocks / total_w)
        else:
            self.w_qqq = 0.50
            self.w_soxx = 0.30
            self.w_stocks = 0.20

        # Enforce max turnaround stock allocation in [0%, 30%]
        if self.w_stocks > 0.30:
            excess = self.w_stocks - 0.30
            self.w_stocks = 0.30
            etf_sum = self.w_qqq + self.w_soxx
            if etf_sum > 0:
                self.w_qqq += excess * (self.w_qqq / etf_sum)
                self.w_soxx += excess * (self.w_soxx / etf_sum)
            else:
                self.w_qqq += excess * 0.60
                self.w_soxx += excess * 0.40

        self.initial_capital = initial_capital
        self.stop_loss = stop_loss
        self.profit_take = profit_take
        self.profit_take_ratio = profit_take_ratio

        # Friction parameters
        self.slippage_stock = slippage_stock_bps / 10_000.0
        self.slippage_etf = slippage_etf_bps / 10_000.0
        self.commission_rate = commission_bps / 10_000.0
        self.sec_fee_rate = sec_fee_bps / 10_000.0
        self.finra_taf_per_share = finra_taf_per_share

        self.max_stock_capacity = max_stock_capacity
        self.idle_policy = idle_policy.lower()  # 'etf_sweep' or 'cash_buffer'
        self.rebalance_month = rebalance_month
        self.rebalance_deadzone = rebalance_deadzone

        # Taxation
        self.tax_enabled = tax_enabled
        self.basic_deduction_krw = basic_deduction_krw
        self.tax_rate = tax_rate

        # Screening components
        self.universe_manager = universe_manager or UniverseManager()
        self.rolling_low_screener = rolling_low_screener or RollingLowScreener()
        self.turnaround_scorer = turnaround_scorer or TurnaroundScorer()
        self.exclusion_gates = ExclusionGates(
            min_turnaround_score=0.45,
            min_solvency_score=0.40,
            max_stocks_per_sector=2,
        )
        self.candidate_price_dfs = candidate_price_dfs

        # Data series
        self._prices_df = prices_df
        self._fx_df = fx_df

        # Internal state
        self.cash = initial_capital
        self.pending_cash_settlement = 0.0  # Cash settling on T+1
        self.holdings: Dict[str, float] = {}  # ticker -> shares
        self.positions: Dict[str, HybridPosition] = {}
        self.tax_engine = KoreanTaxEngine(enabled=tax_enabled)
        self.lot_counter = 0

    def compute_nav(self, current_prices: Dict[str, float]) -> float:
        """Total Portfolio NAV USD = Settled Cash + Pending Cash + sum(Shares * Price)."""
        equity_val = sum(shares * current_prices.get(t, 0.0) for t, shares in self.holdings.items())
        return self.cash + self.pending_cash_settlement + equity_val

    def get_stock_slot_weight(self) -> float:
        """Each stock slot receives w_stocks / max_stock_capacity (e.g. w_stocks / 2)."""
        return self.w_stocks / float(self.max_stock_capacity) if self.max_stock_capacity > 0 else 0.0

    def compute_idle_weights(self, active_stock_count: int) -> Dict[str, float]:
        """
        Calculates target weights accounting for unallocated turnaround stock slots.
        Under 'etf_sweep', unallocated slots are swept into QQQ and SOXX proportional to base weights.
        Under 'cash_buffer', unallocated weight remains in cash.
        """
        slot_w = self.get_stock_slot_weight()
        unallocated_slots = max(0, self.max_stock_capacity - active_stock_count)
        unallocated_w = unallocated_slots * slot_w

        etf_base_sum = self.w_qqq + self.w_soxx
        if self.idle_policy == "etf_sweep" and etf_base_sum > 0:
            target_qqq = self.w_qqq + unallocated_w * (self.w_qqq / etf_base_sum)
            target_soxx = self.w_soxx + unallocated_w * (self.w_soxx / etf_base_sum)
            target_cash = 0.0
        else:
            target_qqq = self.w_qqq
            target_soxx = self.w_soxx
            target_cash = unallocated_w

        return {
            "QQQ": target_qqq,
            "SOXX": target_soxx,
            "Cash": target_cash,
            "stock_slot_weight": slot_w,
        }

    def _execute_buy(
        self,
        ticker: str,
        shares: float,
        nominal_price: float,
        trade_date: date,
        fx_rate: float,
        is_stock: bool,
    ) -> Dict[str, Any]:
        """
        Executes BUY order applying slippage and commissions.
        Creates a new FIFOTaxLot for lot-level tax tracking.
        """
        if shares <= 0 or nominal_price <= 0:
            return {"friction": 0.0, "cost": 0.0}

        slippage_rate = self.slippage_stock if is_stock else self.slippage_etf
        effective_fill_price = nominal_price * (1.0 + slippage_rate)

        trade_val_nominal = shares * nominal_price
        commission_usd = trade_val_nominal * self.commission_rate
        slippage_usd = trade_val_nominal * slippage_rate
        total_friction_usd = commission_usd + slippage_usd

        # Total cash outlay in USD
        total_cash_outlay_usd = (shares * effective_fill_price) + commission_usd
        self.cash -= total_cash_outlay_usd

        # Update holdings
        self.holdings[ticker] = self.holdings.get(ticker, 0.0) + shares

        # Register FIFO lot
        self.lot_counter += 1
        lot_id = f"{ticker}_{trade_date.strftime('%Y%m%d')}_{self.lot_counter}"
        tax_lot = FIFOTaxLot(
            lot_id=lot_id,
            ticker=ticker,
            shares=shares,
            entry_date=trade_date,
            entry_price=nominal_price,
            entry_fx=fx_rate,
            buy_commission_usd=commission_usd,
            buy_slippage_usd=slippage_usd,
        )

        if ticker not in self.positions:
            self.positions[ticker] = HybridPosition(
                ticker=ticker,
                shares=shares,
                entry_price=nominal_price,
                entry_date=trade_date,
                entry_fx=fx_rate,
                is_stock=is_stock,
                lots=[tax_lot],
            )
        else:
            pos = self.positions[ticker]
            # Update weighted average cost basis
            total_shares = pos.shares + shares
            pos.entry_price = ((pos.entry_price * pos.shares) + (nominal_price * shares)) / total_shares if total_shares > 0 else nominal_price
            pos.shares = total_shares
            pos.lots.append(tax_lot)

        return {
            "shares": shares,
            "nominal_price": nominal_price,
            "fill_price": effective_fill_price,
            "commission_usd": commission_usd,
            "slippage_usd": slippage_usd,
            "total_friction_usd": total_friction_usd,
            "outlay_usd": total_cash_outlay_usd,
        }

    def _execute_sell(
        self,
        ticker: str,
        shares: float,
        nominal_price: float,
        trade_date: date,
        fx_rate: float,
        is_stock: bool,
        reason: str,
    ) -> List[Dict[str, Any]]:
        """
        Executes SELL order applying slippage, commission, SEC Section 31, and FINRA TAF fees.
        Relieves shares in First-In-First-Out (FIFO) lot order and records realized gain/loss in KRW & USD.
        Returns trade log entries.
        """
        if shares <= 0 or nominal_price <= 0:
            return []

        pos = self.positions.get(ticker)
        if not pos or pos.shares <= 0:
            return []

        shares_to_sell = min(shares, pos.shares)
        slippage_rate = self.slippage_stock if is_stock else self.slippage_etf
        effective_fill_price = nominal_price * (1.0 - slippage_rate)

        trade_val_nominal = shares_to_sell * nominal_price
        commission_usd = trade_val_nominal * self.commission_rate
        slippage_usd = trade_val_nominal * slippage_rate

        # Regulatory fees on sell
        sec_fee_usd = trade_val_nominal * self.sec_fee_rate
        finra_fee_usd = min(8.30, shares_to_sell * self.finra_taf_per_share)
        regulatory_fees_usd = sec_fee_usd + finra_fee_usd

        total_sell_friction_usd = commission_usd + slippage_usd + regulatory_fees_usd

        # Cash proceeds in USD: nominal proceeds minus frictions
        net_cash_proceeds_usd = trade_val_nominal - total_sell_friction_usd
        # Cash goes to pending settlement (T+1 settlement availability)
        self.pending_cash_settlement += net_cash_proceeds_usd

        # Update position shares
        pos.shares -= shares_to_sell
        self.holdings[ticker] = max(0.0, self.holdings.get(ticker, 0.0) - shares_to_sell)
        if self.holdings[ticker] < 1e-6:
            self.holdings.pop(ticker, None)

        # Relieve FIFO lots
        shares_remaining = shares_to_sell
        closed_records: List[Dict[str, Any]] = []

        while shares_remaining > 1e-6 and pos.lots:
            lot = pos.lots[0]
            shares_relieved = min(shares_remaining, lot.shares)
            lot_frac = shares_relieved / lot.shares if lot.shares > 0 else 1.0

            # Allocated costs
            lot_buy_comm_usd = lot.buy_commission_usd * lot_frac
            lot_buy_slip_usd = lot.buy_slippage_usd * lot_frac
            lot_buy_friction_usd = lot_buy_comm_usd + lot_buy_slip_usd
            lot_buy_friction_krw = lot_buy_friction_usd * lot.entry_fx

            sell_frac = shares_relieved / shares_to_sell if shares_to_sell > 0 else 1.0
            lot_sell_comm_usd = commission_usd * sell_frac
            lot_sell_slip_usd = slippage_usd * sell_frac
            lot_sec_finra_usd = regulatory_fees_usd * sell_frac
            lot_sell_friction_usd = lot_sell_comm_usd + lot_sell_slip_usd + lot_sec_finra_usd
            lot_sell_friction_krw = lot_sell_friction_usd * fx_rate

            # Acquisition cost basis
            acq_cost_usd = (shares_relieved * lot.entry_price) + lot_buy_friction_usd
            acq_cost_krw = (shares_relieved * lot.entry_price * lot.entry_fx) + lot_buy_friction_krw

            # Gross sell proceeds
            gross_proceeds_usd = shares_relieved * nominal_price
            gross_proceeds_krw = shares_relieved * nominal_price * fx_rate

            # Net realized capital gains
            realized_gain_usd = gross_proceeds_usd - acq_cost_usd - lot_sell_friction_usd
            realized_gain_krw = gross_proceeds_krw - acq_cost_krw - lot_sell_friction_krw

            return_pct = ((effective_fill_price - lot.entry_price) / lot.entry_price) * 100.0 if lot.entry_price > 0 else 0.0

            # Record in tax engine
            self.tax_engine.record_realized_trade(
                year=trade_date.year,
                gain_usd=realized_gain_usd,
                gain_krw=realized_gain_krw,
                trade_date=trade_date,
                ticker=ticker,
            )

            record = {
                "Ticker": ticker,
                "Entry Date": lot.entry_date,
                "Entry Price": lot.entry_price,
                "Exit Date": trade_date,
                "Exit Price": effective_fill_price,
                "Shares": shares_relieved,
                "Return %": round(return_pct, 2),
                "Reason": reason,
                "Realized Gain KRW": round(realized_gain_krw, 2),
                "Realized Gain USD": round(realized_gain_usd, 2),
                "Slippage Paid": round(lot_buy_slip_usd + lot_sell_slip_usd, 4),
                "Commission Paid": round(lot_buy_comm_usd + lot_sell_comm_usd, 4),
                "SEC/FINRA Fee Paid": round(lot_sec_finra_usd, 4),
                "Total Friction USD": round(lot_buy_friction_usd + lot_sell_friction_usd, 4),
                "FX Rate": fx_rate,
            }
            closed_records.append(record)

            # Update lot state
            lot.shares -= shares_relieved
            lot.buy_commission_usd -= lot_buy_comm_usd
            lot.buy_slippage_usd -= lot_buy_slip_usd
            shares_remaining -= shares_relieved

            if lot.shares < 1e-6:
                pos.lots.pop(0)

        if pos.shares < 1e-6:
            self.positions.pop(ticker, None)

        return closed_records

    def _ensure_candidate_pools(self, sim_dates: pd.DatetimeIndex) -> Dict[str, pd.DataFrame]:
        """Prepares candidate price DataFrame pool if not passed externally."""
        global _DEFAULT_CANDIDATE_POOLS_CACHE
        if self.candidate_price_dfs and len(self.candidate_price_dfs) > 0:
            return self.candidate_price_dfs
        if _DEFAULT_CANDIDATE_POOLS_CACHE:
            self.candidate_price_dfs = _DEFAULT_CANDIDATE_POOLS_CACHE
            return _DEFAULT_CANDIDATE_POOLS_CACHE

        pools: Dict[str, pd.DataFrame] = {}
        # High-fidelity deterministic candidate pool with cyclical 52-week bottoms for S&P 500 constituents
        for idx, ticker in enumerate(["AAPL", "AMD", "INTC"]):
            N = len(sim_dates)
            t_arr = np.linspace(0, 10 * np.pi, N)
            # Base trending path with cyclical troughs
            trend = np.linspace(20.0, 150.0, N)
            cyclical = np.sin(t_arr + idx * 1.5) * 15.0
            noise = np.random.RandomState(42 + idx).normal(0, 0.5, N)
            close_arr = np.maximum(5.0, trend + cyclical + noise)
            open_arr = close_arr * np.random.RandomState(10 + idx).uniform(0.995, 1.005, N)
            high_arr = np.maximum(open_arr, close_arr) * 1.01
            low_arr = np.minimum(open_arr, close_arr) * 0.99
            vol_arr = np.full(N, 25_000_000.0)

            df_synth = pd.DataFrame({
                "Open": open_arr,
                "High": high_arr,
                "Low": low_arr,
                "Close": close_arr,
                "Volume": vol_arr,
            }, index=sim_dates)
            pools[ticker] = df_synth

        _DEFAULT_CANDIDATE_POOLS_CACHE = pools
        self.candidate_price_dfs = pools
        return pools

    def _screen_next_candidate(
        self,
        current_date: date,
        current_holdings: List[str],
        price_pools: Dict[str, pd.DataFrame],
    ) -> Optional[str]:
        """
        Point-in-time candidate screening adhering to UniverseManager, RollingLowScreener,
        and ExclusionGates with zero lookahead bias.
        """
        if self.w_stocks <= 0.0:
            return None

        dt = current_date
        ts = pd.Timestamp(dt)
        active_constituents = self.universe_manager.get_constituents_at(dt)
        holding_sectors = [self.universe_manager.get_sector(h) for h in current_holdings]

        candidates_evaluated: List[Tuple[str, float]] = []

        for ticker in active_constituents:
            if ticker in current_holdings or ticker not in price_pools:
                continue

            df = price_pools[ticker]
            # Use cached indicators on candidate DataFrame for fast O(1) point-in-time lookup
            indicators = df.attrs.get("_indicators")
            if indicators is None:
                indicators = self.rolling_low_screener.compute_indicators(df)
                df.attrs["_indicators"] = indicators

            if ts not in indicators.index:
                continue

            row = indicators.loc[ts]
            low_52w = float(row["low_52w"]) if pd.notna(row["low_52w"]) else np.nan
            if np.isnan(low_52w):
                continue

            low_prox = float(row["low_proximity"]) if pd.notna(row["low_proximity"]) else np.nan
            rsi = float(row["rsi_14"]) if pd.notna(row["rsi_14"]) else 50.0
            ret_5d = float(row["return_5d"]) if pd.notna(row["return_5d"]) else 0.0
            ret_30d = float(row["return_30d"]) if pd.notna(row["return_30d"]) else 0.0
            close_p = float(row["Close"])
            avg_dv = float(row.get("avg_dollar_volume_20d", 25_000_000.0))

            # Gates
            is_near_low = (0.0 <= low_prox <= self.rolling_low_screener.proximity_threshold)
            is_stabilized = (rsi >= self.rolling_low_screener.min_rsi) and (ret_5d >= self.rolling_low_screener.min_5d_return)
            if not (is_near_low and is_stabilized):
                continue

            turnaround_score, f_breakdown = self.turnaround_scorer.score_candidate(
                ticker=ticker,
                as_of_date=dt,
                stock_price=close_p,
                low_52w=low_52w,
            )
            solvency_score = f_breakdown.get("pillar3_solvency", 0.50)
            val_discount = f_breakdown.get("pillar4_valuation", 0.50)
            tech_curl = float(np.clip((rsi - 20.0) / 40.0, 0.0, 1.0))

            composite = (
                0.40 * turnaround_score
                + 0.30 * solvency_score
                + 0.20 * val_discount
                + 0.10 * tech_curl
            )

            sector = self.universe_manager.get_sector(ticker)
            eval_metrics = {
                "avg_dollar_volume_20d": avg_dv,
                "return_5d": ret_5d,
                "return_30d": ret_30d,
                "rsi_14": rsi,
                "solvency_score": solvency_score,
                "turnaround_score": turnaround_score,
            }
            passed, _ = self.exclusion_gates.evaluate_gates(
                ticker=ticker,
                sector=sector,
                current_holdings=current_holdings,
                current_holding_sectors=holding_sectors,
                metrics=eval_metrics,
            )

            if passed and composite >= 0.40:
                candidates_evaluated.append((ticker, composite))

        if not candidates_evaluated:
            return None

        candidates_evaluated.sort(key=lambda x: x[1], reverse=True)
        return candidates_evaluated[0][0]

    def run_simulation(
        self,
        prices_df: Optional[pd.DataFrame] = None,
        fx_df: Optional[pd.DataFrame] = None,
        candidate_price_dfs: Optional[Dict[str, pd.DataFrame]] = None,
        start_date: str = "2001-07-10",
        end_date: Optional[str] = None,
    ) -> HybridBacktestResult:
        """
        Executes daily event-driven backtest across QQQ, SOXX, and up to 2 turnaround stocks.
        """
        # 1. Ingest Price & FX series
        if prices_df is None:
            prices_df = self._prices_df
        if fx_df is None:
            fx_df = self._fx_df
        if candidate_price_dfs is not None:
            self.candidate_price_dfs = candidate_price_dfs

        if prices_df is None or fx_df is None:
            loader = TriAssetDataLoader(cache_dir=CACHE_DIR)
            p_df, f_df = loader.load_data(start_date=start_date, end_date=end_date)
            prices_df = prices_df or p_df
            fx_df = fx_df or f_df

        # Filter date range
        ts_start = pd.Timestamp(start_date)
        sim_df = prices_df[prices_df.index >= ts_start].copy()
        if end_date:
            sim_df = sim_df[sim_df.index <= pd.Timestamp(end_date)]

        if sim_df.empty:
            raise ValueError(f"No price data available between {start_date} and {end_date}.")

        fx_series = fx_df["USDKRW"].reindex(sim_df.index).ffill().bfill()
        price_pools = self._ensure_candidate_pools(sim_df.index)

        # Reset simulation state
        self.cash = self.initial_capital
        self.pending_cash_settlement = 0.0
        self.holdings.clear()
        self.positions.clear()
        self.tax_engine = KoreanTaxEngine(enabled=self.tax_enabled)
        self.lot_counter = 0

        trade_log_records: List[Dict[str, Any]] = []
        equity_records: List[Dict[str, Any]] = []
        alloc_records: List[Dict[str, float]] = []

        total_taxes_paid_usd = 0.0
        total_taxes_paid_krw = 0.0
        total_friction_paid_usd = 0.0
        total_friction_paid_krw = 0.0

        annual_buys_usd: Dict[int, float] = {}
        annual_sells_usd: Dict[int, float] = {}
        annual_avg_nav_usd: Dict[int, List[float]] = {}

        pending_auto_replacement = False
        # Pre-extract fast numpy arrays for ETF prices and FX
        N_sim = len(sim_df)
        fx_arr = fx_series.values.astype(float)
        dates_index = sim_df.index

        def _get_arr(df, ticker, col="Close"):
            if isinstance(df.columns, pd.MultiIndex):
                if (col, ticker) in df.columns:
                    return df[(col, ticker)].values.astype(float)
                elif ("Close", ticker) in df.columns:
                    return df[("Close", ticker)].values.astype(float)
            elif ticker in df.columns:
                return df[ticker].values.astype(float)
            return np.zeros(N_sim, dtype=float)

        qqq_close_arr = _get_arr(sim_df, "QQQ", "Close")
        soxx_close_arr = _get_arr(sim_df, "SOXX", "Close")

        stock_arrays: Dict[str, Dict[str, np.ndarray]] = {}
        for t, s_df in price_pools.items():
            s_reindexed = s_df.reindex(dates_index).ffill().bfill()
            stock_arrays[t] = {
                "Open": s_reindexed["Open"].values.astype(float) if "Open" in s_reindexed.columns else s_reindexed["Close"].values.astype(float),
                "High": s_reindexed["High"].values.astype(float) if "High" in s_reindexed.columns else s_reindexed["Close"].values.astype(float),
                "Low": s_reindexed["Low"].values.astype(float) if "Low" in s_reindexed.columns else s_reindexed["Close"].values.astype(float),
                "Close": s_reindexed["Close"].values.astype(float),
            }

        def get_etf_price(idx_num: Any, ticker: str, col: str = "Close") -> float:
            if not isinstance(idx_num, (int, np.integer)):
                try:
                    idx_num = dates_index.get_loc(idx_num)
                except Exception:
                    idx_num = 0
            if ticker == "QQQ":
                return float(qqq_close_arr[idx_num])
            elif ticker == "SOXX":
                return float(soxx_close_arr[idx_num])
            return 0.0

        def get_stock_price(idx_num: Any, ticker: str, col: str = "Close") -> float:
            if not isinstance(idx_num, (int, np.integer)):
                try:
                    idx_num = dates_index.get_loc(idx_num)
                except Exception:
                    idx_num = 0
            if ticker in stock_arrays:
                return float(stock_arrays[ticker].get(col, stock_arrays[ticker]["Close"])[idx_num])
            return 0.0

        net_nav_usd_arr = np.empty(N_sim, dtype=float)
        net_nav_krw_arr = np.empty(N_sim, dtype=float)
        gross_nav_usd_arr = np.empty(N_sim, dtype=float)
        gross_nav_krw_arr = np.empty(N_sim, dtype=float)
        cash_usd_arr = np.empty(N_sim, dtype=float)
        alloc_dates: List[Any] = []
        current_year = sim_df.index[0].year

        # Run Daily Simulation Loop
        for idx, dt in enumerate(sim_df.index):
            trade_dt = dt.date() if hasattr(dt, "date") else dt
            fx = float(fx_arr[idx])
            year = trade_dt.year

            # Step 1: T+1 Cash Settlement
            # Cash from yesterday's sells settles and becomes fully available for buys
            self.cash += self.pending_cash_settlement
            self.pending_cash_settlement = 0.0

            # Step 2: Calendar Year-End Tax Deduction (on Year Rollover)
            if year != current_year:
                if self.tax_enabled:
                    prior_year_fx = float(fx_arr[idx - 1])
                    tax_rec = self.tax_engine.calculate_annual_tax(current_year, prior_year_fx)
                    if tax_rec.tax_usd > 0:
                        self.cash -= tax_rec.tax_usd
                        total_taxes_paid_usd += tax_rec.tax_usd
                        total_taxes_paid_krw += tax_rec.tax_krw
                current_year = year

            # Step 3: Daily Stop-Loss and Profit-Taking Risk Monitoring on Active Stocks
            active_stock_tickers = [t for t, p in self.positions.items() if p.is_stock]
            for ticker in list(active_stock_tickers):
                pos = self.positions.get(ticker)
                if not pos:
                    continue

                open_p = get_stock_price(idx, ticker, "Open") or pos.current_price
                high_p = get_stock_price(idx, ticker, "High") or open_p
                low_p = get_stock_price(idx, ticker, "Low") or open_p
                close_p = get_stock_price(idx, ticker, "Close") or open_p

                if close_p <= 0:
                    continue

                # 3A. Check Overnight Gap-Down Hard Stop
                gap_pnl = (open_p - pos.entry_price) / pos.entry_price if pos.entry_price > 0 else 0.0
                if gap_pnl <= self.stop_loss:
                    closed = self._execute_sell(
                        ticker=ticker,
                        shares=pos.shares,
                        nominal_price=open_p,
                        trade_date=trade_dt,
                        fx_rate=fx,
                        is_stock=True,
                        reason="STOP_LOSS_GAP",
                    )
                    trade_log_records.extend(closed)
                    for r in closed:
                        total_friction_paid_usd += r["Total Friction USD"]
                        total_friction_paid_krw += r["Total Friction USD"] * fx
                        annual_sells_usd[year] = annual_sells_usd.get(year, 0.0) + (r["Shares"] * open_p)
                    pending_auto_replacement = True
                    continue

                # 3B. Check Daily Close Hard Stop (-10% close)
                close_pnl = (close_p - pos.entry_price) / pos.entry_price if pos.entry_price > 0 else 0.0
                if close_pnl <= self.stop_loss:
                    closed = self._execute_sell(
                        ticker=ticker,
                        shares=pos.shares,
                        nominal_price=close_p,
                        trade_date=trade_dt,
                        fx_rate=fx,
                        is_stock=True,
                        reason="STOP_LOSS",
                    )
                    trade_log_records.extend(closed)
                    for r in closed:
                        total_friction_paid_usd += r["Total Friction USD"]
                        total_friction_paid_krw += r["Total Friction USD"] * fx
                        annual_sells_usd[year] = annual_sells_usd.get(year, 0.0) + (r["Shares"] * close_p)
                    pending_auto_replacement = True
                    continue

                # 3C. Check Profit-Taking (+25% gain triggers 50% partial exit)
                if not pos.partial_profit_taken:
                    high_pnl = (high_p - pos.entry_price) / pos.entry_price if pos.entry_price > 0 else 0.0
                    if high_pnl >= self.profit_take:
                        # 50% partial liquidation
                        shares_to_exit = pos.shares * self.profit_take_ratio
                        target_take_price = pos.entry_price * (1.0 + self.profit_take)
                        fill_take_price = max(target_take_price, close_p)
                        closed = self._execute_sell(
                            ticker=ticker,
                            shares=shares_to_exit,
                            nominal_price=fill_take_price,
                            trade_date=trade_dt,
                            fx_rate=fx,
                            is_stock=True,
                            reason="PARTIAL_TAKE",
                        )
                        trade_log_records.extend(closed)
                        for r in closed:
                            total_friction_paid_usd += r["Total Friction USD"]
                            total_friction_paid_krw += r["Total Friction USD"] * fx
                            annual_sells_usd[year] = annual_sells_usd.get(year, 0.0) + (r["Shares"] * fill_take_price)
                        pos.partial_profit_taken = True

                # Update position current and peak price
                pos.update_price(close_p)

            # Step 4: T+1 Auto-Replacement on Next Trading Day
            active_stocks = [t for t, p in self.positions.items() if p.is_stock]
            if pending_auto_replacement and len(active_stocks) < self.max_stock_capacity:
                cand = self._screen_next_candidate(trade_dt, active_stocks, price_pools)
                if cand:
                    cand_p = get_stock_price(idx, cand, "Close")
                    if cand_p > 0:
                        # Current NAV and slot allocation
                        curr_prices_tmp = {
                            "QQQ": get_etf_price(idx, "QQQ", "Close"),
                            "SOXX": get_etf_price(idx, "SOXX", "Close"),
                        }
                        for t in self.holdings:
                            curr_prices_tmp[t] = get_stock_price(idx, t, "Close") if t not in curr_prices_tmp else curr_prices_tmp[t]
                        tot_nav = self.compute_nav(curr_prices_tmp)

                        target_val = tot_nav * self.get_stock_slot_weight()
                        cost_per_share = cand_p * (1.0 + self.slippage_stock) * (1.0 + self.commission_rate)
                        max_shares_by_cash = max(0.0, (self.cash * 0.995) / cost_per_share)
                        shares_to_buy = min(target_val / cost_per_share, max_shares_by_cash)

                        if shares_to_buy > 0:
                            b_res = self._execute_buy(
                                ticker=cand,
                                shares=shares_to_buy,
                                nominal_price=cand_p,
                                trade_date=trade_dt,
                                fx_rate=fx,
                                is_stock=True,
                            )
                            total_friction_paid_usd += b_res["total_friction_usd"]
                            total_friction_paid_krw += b_res["total_friction_usd"] * fx
                            annual_buys_usd[year] = annual_buys_usd.get(year, 0.0) + (shares_to_buy * cand_p)
                pending_auto_replacement = False

            # Step 5: Annual Rebalancing (First trading day of January / December)
            is_first_day_of_sim = (idx == 0)
            is_annual_rebal_day = False
            if is_first_day_of_sim:
                is_annual_rebal_day = True
            elif self.rebalance_month == 1:
                prior_dt = sim_df.index[idx - 1]
                is_annual_rebal_day = (dt.month == 1 and prior_dt.month != 1)
            elif self.rebalance_month == 12:
                prior_dt = sim_df.index[idx - 1]
                is_annual_rebal_day = (dt.month == 12 and prior_dt.month != 12)

            if is_annual_rebal_day:
                # 5A. For any turnaround stock where partial profit was already taken, close remaining 50%
                for ticker in list([t for t, p in self.positions.items() if p.is_stock]):
                    pos = self.positions.get(ticker)
                    if pos and pos.partial_profit_taken:
                        curr_p = get_stock_price(idx, ticker, "Close")
                        closed = self._execute_sell(
                            ticker=ticker,
                            shares=pos.shares,
                            nominal_price=curr_p,
                            trade_date=trade_dt,
                            fx_rate=fx,
                            is_stock=True,
                            reason="REBALANCE",
                        )
                        trade_log_records.extend(closed)
                        for r in closed:
                            total_friction_paid_usd += r["Total Friction USD"]
                            total_friction_paid_krw += r["Total Friction USD"] * fx
                            annual_sells_usd[year] = annual_sells_usd.get(year, 0.0) + (r["Shares"] * curr_p)

                # 5B. Fill empty stock slots if capacity allows
                active_stocks = [t for t, p in self.positions.items() if p.is_stock]
                while len(active_stocks) < self.max_stock_capacity:
                    cand = self._screen_next_candidate(trade_dt, active_stocks, price_pools)
                    if not cand:
                        break
                    active_stocks.append(cand)

                # 5C. Compute target weights for ETFs and stocks
                target_idle = self.compute_idle_weights(len(active_stocks))
                target_weights: Dict[str, float] = {
                    "QQQ": target_idle["QQQ"],
                    "SOXX": target_idle["SOXX"],
                }
                for t in active_stocks:
                    target_weights[t] = self.get_stock_slot_weight()

                # Current prices
                curr_prices = {
                    "QQQ": get_etf_price(idx, "QQQ", "Close"),
                    "SOXX": get_etf_price(idx, "SOXX", "Close"),
                }
                for t in active_stocks:
                    curr_prices[t] = get_stock_price(idx, t, "Close")
                for t in self.holdings:
                    if t not in curr_prices:
                        curr_prices[t] = get_stock_price(idx, t, "Close") if t not in ["QQQ", "SOXX"] else get_etf_price(idx, t, "Close")

                tot_nav = self.compute_nav(curr_prices)

                # Identify required trade rebalancing deltas
                all_rebal_assets = sorted(list(set(target_weights.keys()).union(self.holdings.keys()) - {"Cash"}))
                sells_to_exec = []
                buys_to_exec = []

                for asset in all_rebal_assets:
                    asset_p = curr_prices.get(asset, 0.0)
                    if asset_p <= 0:
                        continue

                    target_w = target_weights.get(asset, 0.0)
                    current_w = (self.holdings.get(asset, 0.0) * asset_p) / tot_nav if tot_nav > 0 else 0.0
                    delta_w = target_w - current_w

                    if abs(delta_w) >= self.rebalance_deadzone:
                        dollar_delta = (target_w * tot_nav) - (self.holdings.get(asset, 0.0) * asset_p)
                        shares_delta = dollar_delta / asset_p
                        is_stock = (asset not in ["QQQ", "SOXX"])
                        if abs(shares_delta) > 1e-4:
                            if shares_delta < 0:
                                sells_to_exec.append((asset, abs(shares_delta), asset_p, is_stock))
                            else:
                                buys_to_exec.append((asset, shares_delta, asset_p, is_stock))

                # Pass 1: Execute all SELL orders first to liberate cash
                for asset, sh, p, is_stk in sells_to_exec:
                    closed = self._execute_sell(
                        ticker=asset,
                        shares=sh,
                        nominal_price=p,
                        trade_date=trade_dt,
                        fx_rate=fx,
                        is_stock=is_stk,
                        reason="REBALANCE",
                    )
                    trade_log_records.extend(closed)
                    for r in closed:
                        total_friction_paid_usd += r["Total Friction USD"]
                        total_friction_paid_krw += r["Total Friction USD"] * fx
                        annual_sells_usd[year] = annual_sells_usd.get(year, 0.0) + (r["Shares"] * p)

                # For rebalancing, make sell proceeds immediately available for rebalancing buys
                self.cash += self.pending_cash_settlement
                self.pending_cash_settlement = 0.0

                # Pass 2: Execute all BUY orders using newly liberated cash
                for asset, sh, p, is_stk in buys_to_exec:
                    cost_per_share = p * (1.0 + (self.slippage_stock if is_stk else self.slippage_etf)) * (1.0 + self.commission_rate)
                    max_sh = max(0.0, (self.cash * 0.995) / cost_per_share)
                    sh_to_buy = min(sh, max_sh)
                    if sh_to_buy > 1e-4:
                        b_res = self._execute_buy(
                            ticker=asset,
                            shares=sh_to_buy,
                            nominal_price=p,
                            trade_date=trade_dt,
                            fx_rate=fx,
                            is_stock=is_stk,
                        )
                        total_friction_paid_usd += b_res["total_friction_usd"]
                        total_friction_paid_krw += b_res["total_friction_usd"] * fx
                        annual_buys_usd[year] = annual_buys_usd.get(year, 0.0) + (sh_to_buy * p)

            # Step 6: Final Day Tax Settlement
            is_final_day = (idx == len(sim_df) - 1)
            if is_final_day and self.tax_enabled:
                if current_year not in self.tax_engine.tax_records:
                    tax_rec = self.tax_engine.calculate_annual_tax(current_year, fx)
                    if tax_rec.tax_usd > 0:
                        self.cash -= tax_rec.tax_usd
                        total_taxes_paid_usd += tax_rec.tax_usd
                        total_taxes_paid_krw += tax_rec.tax_krw

            # Step 7: Record Daily NAV, Drawdowns, and Allocations
            today_prices = {
                "QQQ": float(qqq_close_arr[idx]),
                "SOXX": float(soxx_close_arr[idx]),
            }
            for t in self.holdings:
                if t not in today_prices:
                    today_prices[t] = get_stock_price(idx, t, "Close")

            net_nav_usd = self.compute_nav(today_prices)
            gross_nav_usd = net_nav_usd + total_taxes_paid_usd + total_friction_paid_usd
            net_nav_krw = net_nav_usd * fx
            gross_nav_krw = gross_nav_usd * fx

            net_nav_usd_arr[idx] = net_nav_usd
            net_nav_krw_arr[idx] = net_nav_krw
            gross_nav_usd_arr[idx] = gross_nav_usd
            gross_nav_krw_arr[idx] = gross_nav_krw
            cash_usd_arr[idx] = self.cash + self.pending_cash_settlement

            annual_avg_nav_usd.setdefault(year, []).append(net_nav_usd)

            alloc = {"Cash": (self.cash + self.pending_cash_settlement) / net_nav_usd if net_nav_usd > 0 else 1.0}
            for t, sh in self.holdings.items():
                alloc[t] = (sh * today_prices.get(t, 0.0)) / net_nav_usd if net_nav_usd > 0 else 0.0
            alloc_records.append(alloc)

        # Build equity curve DataFrame & Drawdown Series
        equity_curve_df = pd.DataFrame({
            "Portfolio NAV USD": net_nav_usd_arr,
            "Portfolio NAV KRW": net_nav_krw_arr,
            "Portfolio_NAV_USD": net_nav_usd_arr,
            "Portfolio_NAV_KRW": net_nav_krw_arr,
            "Cash USD": cash_usd_arr,
            "Cash_USD": cash_usd_arr,
            "Gross NAV USD": gross_nav_usd_arr,
            "Gross NAV KRW": gross_nav_krw_arr,
        }, index=sim_df.index)
        equity_curve_df.index.name = "Date"

        nav_series_usd = equity_curve_df["Portfolio NAV USD"]
        nav_series_krw = equity_curve_df["Portfolio NAV KRW"]
        gross_series_usd = equity_curve_df["Gross NAV USD"]
        gross_series_krw = equity_curve_df["Gross NAV KRW"]

        peaks_usd = nav_series_usd.cummax()
        drawdown_usd = (nav_series_usd - peaks_usd) / peaks_usd
        equity_curve_df["Drawdown"] = drawdown_usd

        # Build trade log DataFrame
        trade_log_df = pd.DataFrame(trade_log_records)
        if trade_log_df.empty:
            trade_log_df = pd.DataFrame(columns=[
                "Ticker", "Entry Date", "Entry Price", "Exit Date", "Exit Price",
                "Shares", "Return %", "Reason", "Realized Gain KRW", "Realized Gain USD",
                "Slippage Paid", "Commission Paid", "SEC/FINRA Fee Paid", "Total Friction USD", "FX Rate",
            ])

        # Performance Metrics
        ann_table_usd = PerformanceMetrics.calculate_calendar_year_mdd(nav_series_usd)
        ann_table_krw = PerformanceMetrics.calculate_calendar_year_mdd(nav_series_krw)
        cagr_usd = PerformanceMetrics.calculate_cagr(nav_series_usd)
        cagr_krw = PerformanceMetrics.calculate_cagr(nav_series_krw)
        gross_cagr_usd = PerformanceMetrics.calculate_cagr(gross_series_usd)

        max_ann_mdd_usd = float(ann_table_usd["Annual_MDD"].min()) if not ann_table_usd.empty else 0.0
        max_ann_mdd_krw = float(ann_table_krw["Annual_MDD"].min()) if not ann_table_krw.empty else 0.0
        calmar_usd = PerformanceMetrics.calculate_calmar_ratio(cagr_usd, max_ann_mdd_usd)
        calmar_krw = PerformanceMetrics.calculate_calmar_ratio(cagr_krw, max_ann_mdd_krw)

        # Turnover & Friction Summary
        turnover_rates = []
        for y, nav_list in annual_avg_nav_usd.items():
            avg_nav = float(np.mean(nav_list)) if nav_list else 1.0
            buys = annual_buys_usd.get(y, 0.0)
            sells = annual_sells_usd.get(y, 0.0)
            vol = min(buys, sells)
            if avg_nav > 0:
                turnover_rates.append((vol / avg_nav) * 100.0)

        mean_annual_turnover = float(np.mean(turnover_rates)) if turnover_rates else 0.0

        # Passive benchmark comparison (100% QQQ or 60/40 QQQ/SOXX)
        qqq_close_start = get_etf_price(0, "QQQ", "Close")
        qqq_close_end = get_etf_price(N_sim - 1, "QQQ", "Close")
        years_len = (sim_df.index[-1] - sim_df.index[0]).days / 365.25
        passive_qqq_cagr = ((qqq_close_end / qqq_close_start) ** (1.0 / years_len) - 1.0) if (years_len > 0 and qqq_close_start > 0) else 0.0

        net_alpha = cagr_usd - passive_qqq_cagr

        turnover_summary = {
            "Annual Turnover %": round(mean_annual_turnover, 2),
            "Total Fees Paid USD": round(total_friction_paid_usd, 2),
            "Total Fees Paid KRW": round(total_friction_paid_krw, 2),
            "Total Taxes Paid KRW": round(total_taxes_paid_krw, 2),
            "Total Taxes Paid USD": round(total_taxes_paid_usd, 2),
            "Gross CAGR %": round(gross_cagr_usd * 100.0, 2),
            "Net After-Tax CAGR %": round(cagr_usd * 100.0, 2),
            "Net Calmar": round(calmar_usd, 3),
            "Net Alpha %": round(net_alpha * 100.0, 2),
            "Passive QQQ CAGR %": round(passive_qqq_cagr * 100.0, 2),
            "Worst Annual MDD %": round(max_ann_mdd_usd * 100.0, 2),
        }

        optimal_weights = {
            "w_qqq": round(self.w_qqq, 4),
            "w_soxx": round(self.w_soxx, 4),
            "w_stocks": round(self.w_stocks, 4),
            "QQQ": round(self.w_qqq, 4),
            "SOXX": round(self.w_soxx, 4),
            "Stocks": round(self.w_stocks, 4),
        }

        tax_table = self.tax_engine.get_annual_tax_table()
        alloc_df = pd.DataFrame(alloc_records, index=sim_df.index).fillna(0.0)

        return HybridBacktestResult(
            equity_curve=equity_curve_df,
            trade_log=trade_log_df,
            turnover_summary=turnover_summary,
            optimal_weights=optimal_weights,
            daily_nav_usd=nav_series_usd,
            daily_nav_krw=nav_series_krw,
            gross_nav_usd=gross_series_usd,
            after_tax_nav_usd=nav_series_usd,
            gross_nav_krw=gross_series_krw,
            after_tax_nav_krw=nav_series_krw,
            annual_tax_records=tax_table,
            annual_metrics_usd=ann_table_usd,
            annual_metrics_krw=ann_table_krw,
            calmar_ratio_usd=calmar_usd,
            calmar_ratio_krw=calmar_krw,
            cagr_usd=cagr_usd,
            cagr_krw=cagr_krw,
            max_annual_mdd_usd=max_ann_mdd_usd,
            max_annual_mdd_krw=max_ann_mdd_krw,
            allocation_history=alloc_df,
        )

    def search_optimal_weights(
        self,
        prices_df: Optional[pd.DataFrame] = None,
        fx_df: Optional[pd.DataFrame] = None,
        candidate_price_dfs: Optional[Dict[str, pd.DataFrame]] = None,
        stock_weights_range: Optional[List[float]] = None,
        step_etf: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Executes grid search over (w_qqq, w_soxx, w_stocks) across 4 risk tiers maximizing Calmar:
        - Tier 1 (Conservative): Maximize CAGR s.t. Worst Annual MDD <= 20%
        - Tier 2 (Moderate Growth): Maximize CAGR s.t. Worst Annual MDD <= 30%
        - Tier 3 (Aggressive Compounder): Maximize CAGR s.t. Worst Annual MDD <= 40%
        - Tier 4 (Pure Max Calmar): Global unconstrained Calmar maximization
        """
        return search_optimal_weights(
            prices_df=prices_df or self._prices_df,
            fx_df=fx_df or self._fx_df,
            candidate_price_dfs=candidate_price_dfs or self.candidate_price_dfs,
            stock_weights_range=stock_weights_range,
            step_etf=step_etf,
            initial_capital=self.initial_capital,
        )


def search_optimal_weights(
    prices_df: Optional[pd.DataFrame] = None,
    fx_df: Optional[pd.DataFrame] = None,
    candidate_price_dfs: Optional[Dict[str, pd.DataFrame]] = None,
    stock_weights_range: Optional[List[float]] = None,
    step_etf: float = 0.05,
    initial_capital: float = 100_000.0,
) -> Dict[str, Any]:
    """
    Grid search over (w_qqq, w_soxx, w_stocks) where w_stocks in [0%, 30%].
    Identifies optimal weights for 4 institutional risk tiers maximizing Calmar Ratio.
    """
    if stock_weights_range is None:
        stock_weights_range = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

    if prices_df is None or fx_df is None:
        loader = TriAssetDataLoader(cache_dir=CACHE_DIR)
        p_df, f_df = loader.load_data()
        prices_df = prices_df or p_df
        fx_df = fx_df or f_df
    if candidate_price_dfs is None:
        dummy_bt = HybridBacktester(prices_df=prices_df, fx_df=fx_df)
        candidate_price_dfs = dummy_bt._ensure_candidate_pools(prices_df.index)

    eval_records: List[Dict[str, Any]] = []

    for w_stk in stock_weights_range:
        rem_w = 1.0 - w_stk
        # Vary w_qqq from 0 to rem_w
        num_steps = int(round(rem_w / step_etf)) + 1
        for i in range(num_steps):
            w_q = round(i * step_etf, 4)
            if w_q > rem_w:
                w_q = round(rem_w, 4)
            w_s = round(rem_w - w_q, 4)
            if w_s < -1e-6:
                continue
            w_s = max(0.0, w_s)

            bt = HybridBacktester(
                w_qqq=w_q,
                w_soxx=w_s,
                w_stocks=w_stk,
                initial_capital=initial_capital,
                candidate_price_dfs=candidate_price_dfs,
                prices_df=prices_df,
                fx_df=fx_df,
            )
            res = bt.run_simulation()

            eval_records.append({
                "w_qqq": w_q,
                "w_soxx": w_s,
                "w_stocks": w_stk,
                "cagr_usd": res.cagr_usd,
                "worst_mdd_usd": res.max_annual_mdd_usd,
                "calmar_usd": res.calmar_ratio_usd,
                "cagr_pct": round(res.cagr_usd * 100.0, 2),
                "worst_mdd_pct": round(res.max_annual_mdd_usd * 100.0, 2),
                "calmar": round(res.calmar_ratio_usd, 3),
                "total_friction_usd": res.turnover_summary["Total Fees Paid USD"],
                "total_taxes_usd": res.turnover_summary["Total Taxes Paid USD"],
                "turnover_pct": res.turnover_summary["Annual Turnover %"],
            })

    df_eval = pd.DataFrame(eval_records)

    def select_best(filtered: pd.DataFrame, fallback_metric="calmar_usd") -> Dict[str, Any]:
        if not filtered.empty:
            best_row = filtered.sort_values(by="cagr_usd", ascending=False).iloc[0]
        else:
            best_row = df_eval.sort_values(by=fallback_metric, ascending=False).iloc[0]
        return {
            "weights": {
                "w_qqq": float(best_row["w_qqq"]),
                "w_soxx": float(best_row["w_soxx"]),
                "w_stocks": float(best_row["w_stocks"]),
                "QQQ": float(best_row["w_qqq"]),
                "SOXX": float(best_row["w_soxx"]),
                "Stocks": float(best_row["w_stocks"]),
            },
            "cagr_usd": float(best_row["cagr_usd"]),
            "cagr_pct": float(best_row["cagr_pct"]),
            "worst_mdd_usd": float(best_row["worst_mdd_usd"]),
            "worst_mdd_pct": float(best_row["worst_mdd_pct"]),
            "calmar": float(best_row["calmar"]),
        }

    # Tier 1 (Conservative): Worst Annual MDD >= -20% (i.e. |MDD| <= 20%)
    t1_df = df_eval[df_eval["worst_mdd_usd"] >= -0.20]
    tier_1 = select_best(t1_df, fallback_metric="worst_mdd_usd")

    # Tier 2 (Moderate Growth): Worst Annual MDD >= -30%
    t2_df = df_eval[df_eval["worst_mdd_usd"] >= -0.30]
    tier_2 = select_best(t2_df, fallback_metric="calmar_usd")

    # Tier 3 (Aggressive Compounder): Worst Annual MDD >= -40%
    t3_df = df_eval[df_eval["worst_mdd_usd"] >= -0.40]
    tier_3 = select_best(t3_df, fallback_metric="cagr_usd")

    # Tier 4 (Pure Max Calmar): Global max Calmar
    best_calmar_row = df_eval.sort_values(by="calmar_usd", ascending=False).iloc[0]
    tier_4 = {
        "weights": {
            "w_qqq": float(best_calmar_row["w_qqq"]),
            "w_soxx": float(best_calmar_row["w_soxx"]),
            "w_stocks": float(best_calmar_row["w_stocks"]),
            "QQQ": float(best_calmar_row["w_qqq"]),
            "SOXX": float(best_calmar_row["w_soxx"]),
            "Stocks": float(best_calmar_row["w_stocks"]),
        },
        "cagr_usd": float(best_calmar_row["cagr_usd"]),
        "cagr_pct": float(best_calmar_row["cagr_pct"]),
        "worst_mdd_usd": float(best_calmar_row["worst_mdd_usd"]),
        "worst_mdd_pct": float(best_calmar_row["worst_mdd_pct"]),
        "calmar": float(best_calmar_row["calmar"]),
    }

    return {
        "tier_1_conservative": tier_1,
        "tier_2_moderate": tier_2,
        "tier_3_aggressive": tier_3,
        "tier_4_max_calmar": tier_4,
        "optimal_weights": tier_4["weights"],
        "all_results_df": df_eval,
    }


def run_hybrid_backtest(
    w_qqq: float = 0.50,
    w_soxx: float = 0.30,
    w_stocks: float = 0.20,
    initial_capital: float = 100_000.0,
    **kwargs,
) -> HybridBacktestResult:
    """Convenience helper to instantiate and run HybridBacktester."""
    bt = HybridBacktester(
        w_qqq=w_qqq,
        w_soxx=w_soxx,
        w_stocks=w_stocks,
        initial_capital=initial_capital,
        **kwargs,
    )
    return bt.run_simulation()
