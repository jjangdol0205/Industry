"""
Modular Backtesting Simulator module.
Simulates portfolio execution across QQQ, SOXX, individual turnaround stocks, and cash
from July 10, 2001 to the present.
Integrates:
- Real transaction friction (commissions & slippage).
- Intra-week daily risk management (stop-loss, profit-target, trailing-stop, time-stop).
- Korean overseas capital gains tax (22% on net realized gains exceeding 2.5M KRW).
- Dual-currency (USD and KRW) accounting.
- Weekly rebalancing cadence and idle cash policies.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple, Any
import inspect
import logging
import numpy as np
import pandas as pd

from src.engine.portfolio import Portfolio, Position
from src.engine.execution import ExecutionEngine, ExecutionResult
from src.engine.tax import KoreanTaxEngine, AnnualTaxRecord
from src.engine.risk_manager import RiskManager
from src.engine.metrics import PerformanceMetrics
from src.strategies.base_strategy import BaseStrategy, StrategyParameters

try:
    from src.strategies.enhanced_strategy import ExitReason
except ImportError:
    class ExitReason:  # type: ignore
        NONE = "NONE"
        STOP_LOSS = "STOP_LOSS"
        TAKE_PROFIT = "TAKE_PROFIT"
        BREAKEVEN_STOP = "BREAKEVEN_STOP"
        TRAILING_STOP = "TRAILING_STOP"
        TIME_STOP = "TIME_STOP"

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Comprehensive backtest simulation outputs."""
    daily_nav_usd: pd.Series
    daily_nav_krw: pd.Series
    gross_nav_usd: pd.Series
    after_tax_nav_usd: pd.Series
    gross_nav_krw: pd.Series
    after_tax_nav_krw: pd.Series
    trade_log: pd.DataFrame
    annual_tax_records: pd.DataFrame
    annual_metrics_usd: pd.DataFrame
    annual_metrics_krw: pd.DataFrame
    calmar_ratio_usd: float
    calmar_ratio_krw: float
    cagr_usd: float
    cagr_krw: float
    max_annual_mdd_usd: float
    max_annual_mdd_krw: float
    allocation_history: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())


class BacktestEngine:
    """
    Modular event-driven quantitative backtester.
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission_bps: float = 5.0,
        slippage_etf_bps: float = 2.0,
        slippage_stock_bps: float = 10.0,
        max_stock_capacity: int = 3,
        max_weekly_buy: int = 1,
        rebalance_deadzone: float = 0.01,
        rf_rate_annual: float = 0.02,
    ):
        self.initial_capital = initial_capital
        self.commission_fee = commission_bps / 10_000.0
        self.slippage_etf = slippage_etf_bps / 10_000.0
        self.slippage_stock = slippage_stock_bps / 10_000.0
        self.max_stock_capacity = max_stock_capacity
        self.max_weekly_buy = max_weekly_buy
        self.rebalance_deadzone = rebalance_deadzone
        self.rf_rate_annual = rf_rate_annual

        self.cash = initial_capital
        self.holdings: Dict[str, float] = {}  # ticker -> shares
        self.positions: Dict[str, Position] = {}
        self.portfolio = Portfolio(initial_capital, max_stock_capacity)
        self.execution = ExecutionEngine(
            commission_bps=commission_bps,
            slippage_etf_bps=slippage_etf_bps,
            slippage_stock_bps=slippage_stock_bps,
            rebalance_deadzone=rebalance_deadzone,
        )
        self.tax_engine = KoreanTaxEngine(enabled=True)
        self.risk_manager = RiskManager()

    def compute_nav(self, current_prices: Dict[str, float]) -> float:
        """
        Calculates current portfolio Net Asset Value (NAV):
        V(t) = Cash + sum(Shares_i * Price_i).
        """
        stock_val = sum(shares * current_prices.get(t, 0.0) for t, shares in self.holdings.items())
        return self.cash + stock_val

    def can_buy_new_candidate(self, current_turnaround_stocks: List[str]) -> bool:
        """Evaluates whether current turnaround stock holdings are below max capacity."""
        return len(current_turnaround_stocks) < self.max_stock_capacity

    def execute_trade(
        self,
        ticker: str,
        shares: float,
        price: float,
        is_stock: bool = True,
        trade_date: Optional[date] = None,
        current_fx: float = 1200.0,
    ) -> float:
        """
        Executes a trade, applying commission and slippage to cash.
        Positive shares = BUY, Negative shares = SELL.
        Returns total transaction friction.
        """
        trade_val = abs(shares * price)
        slippage_rate = self.slippage_stock if is_stock else self.slippage_etf
        friction = trade_val * (self.commission_fee + slippage_rate)

        entry_price = price
        entry_fx = current_fx
        if ticker in self.positions:
            entry_price = self.positions[ticker].entry_price
            entry_fx = self.positions[ticker].entry_fx

        if shares > 0:  # BUY
            effective_cost = (shares * price) + friction
            self.cash -= effective_cost
            self.holdings[ticker] = self.holdings.get(ticker, 0.0) + shares

            # Track in positions
            if ticker in self.positions:
                pos = self.positions[ticker]
                new_shares = pos.shares + shares
                pos.entry_price = (pos.shares * pos.entry_price + shares * price) / new_shares
                pos.shares = new_shares
                pos.current_price = price
            else:
                self.positions[ticker] = Position(
                    ticker=ticker,
                    shares=shares,
                    entry_price=price,
                    entry_date=trade_date or date(2001, 7, 10),
                    entry_fx=current_fx,
                    current_price=price,
                    peak_price=price,
                    is_stock=is_stock,
                )
        else:  # SELL
            gross_proceeds = abs(shares * price)
            net_proceeds = gross_proceeds - friction
            self.cash += net_proceeds
            self.holdings[ticker] = self.holdings.get(ticker, 0.0) + shares

            # Calculate realized gain for tax
            abs_shares = abs(shares)
            gain_usd = (price - entry_price) * abs_shares - friction
            gain_krw = (price * current_fx - entry_price * entry_fx) * abs_shares - (friction * current_fx)
            if trade_date is not None:
                self.tax_engine.record_realized_trade(
                    year=trade_date.year,
                    gain_usd=gain_usd,
                    gain_krw=gain_krw,
                    trade_date=trade_date,
                    ticker=ticker,
                )

            if abs(self.holdings[ticker]) < 1e-6:
                del self.holdings[ticker]
                self.positions.pop(ticker, None)
            else:
                if ticker in self.positions:
                    self.positions[ticker].shares = self.holdings[ticker]
                    self.positions[ticker].current_price = price

        return friction

    def compute_idle_etf_sweep_weights(
        self,
        base_qqq: float = 0.50,
        base_soxx: float = 0.30,
        max_turnaround_weight: float = 0.20,
        active_stock_count: int = 0,
    ) -> Dict[str, float]:
        """
        Under 'etf_sweep' policy, unallocated turnaround capacity (3 - k) * (0.20 / 3)
        is swept into QQQ and SOXX proportional to their base weights.
        """
        stock_slot_weight = max_turnaround_weight / self.max_stock_capacity
        unallocated_slots = self.max_stock_capacity - active_stock_count
        unallocated_weight = unallocated_slots * stock_slot_weight

        etf_base_sum = base_qqq + base_soxx
        sweep_qqq = base_qqq + unallocated_weight * (base_qqq / etf_base_sum)
        sweep_soxx = base_soxx + unallocated_weight * (base_soxx / etf_base_sum)

        return {
            "QQQ": sweep_qqq,
            "SOXX": sweep_soxx,
            "Turnaround_Slots_Used": active_stock_count * stock_slot_weight,
            "Cash": 0.0,
        }

    def run(
        self,
        strategy: Optional[BaseStrategy] = None,
        prices_df: Optional[pd.DataFrame] = None,
        candidate_selections: Optional[Dict[Any, Any]] = None,
        fx_rates: Optional[pd.Series] = None,
        rf_rates: Optional[pd.Series] = None,
        tax_enabled: bool = True,
        start_date: str = "2001-07-10",
        end_date: Optional[str] = None,
    ) -> BacktestResult:
        """
        Executes full time-series backtest simulation from start_date to end_date.
        """
        if strategy is None:
            strategy = BaseStrategy()
        if prices_df is None or prices_df.empty:
            raise ValueError("prices_df must be provided and non-empty.")

        # Filter price dates
        ts_start = pd.Timestamp(start_date)
        sim_df = prices_df[prices_df.index >= ts_start].copy()
        if end_date:
            sim_df = sim_df[sim_df.index <= pd.Timestamp(end_date)]

        if sim_df.empty:
            raise ValueError(f"No price data available between {start_date} and {end_date}.")

        # Prepare FX rates series
        if fx_rates is None or fx_rates.empty:
            fx_series = pd.Series(1200.0, index=sim_df.index)
        else:
            fx_series = fx_rates.reindex(sim_df.index).ffill().bfill()

        # Reset state
        self.cash = self.initial_capital
        self.holdings.clear()
        self.positions.clear()
        self.tax_engine = KoreanTaxEngine(enabled=tax_enabled)
        if hasattr(strategy, "reset") and callable(strategy.reset):
            strategy.reset()
        trade_records: List[Dict[str, Any]] = []

        daily_nav_usd = []
        daily_nav_krw = []
        daily_gross_usd = []
        daily_gross_krw = []
        daily_dates = []
        daily_allocations: List[Dict[str, float]] = []

        tax_paid_cumulative_usd = 0.0
        tax_paid_cumulative_krw = 0.0
        current_year = sim_df.index[0].year

        # Helper to get price
        def get_price(d_idx, ticker: str, col: str = "Close") -> float:
            if isinstance(sim_df.columns, pd.MultiIndex):
                if (col, ticker) in sim_df.columns:
                    val = sim_df.loc[d_idx, (col, ticker)]
                    return float(val) if pd.notnull(val) else 0.0
                elif ("Close", ticker) in sim_df.columns:
                    val = sim_df.loc[d_idx, ("Close", ticker)]
                    return float(val) if pd.notnull(val) else 0.0
            elif ticker in sim_df.columns:
                val = sim_df.loc[d_idx, ticker]
                return float(val) if pd.notnull(val) else 0.0
            return 0.0

        for idx, dt in enumerate(sim_df.index):
            trade_dt = dt.date() if hasattr(dt, "date") else dt
            fx = float(fx_series.loc[dt]) if dt in fx_series.index else 1200.0

            # 1. Year-end tax settlement on year rollover
            if trade_dt.year != current_year:
                if tax_enabled:
                    prior_year_fx = float(fx_series.loc[sim_df.index[idx-1]])
                    tax_rec = self.tax_engine.calculate_annual_tax(current_year, prior_year_fx)
                    if tax_rec.tax_usd > 0:
                        self.cash -= tax_rec.tax_usd
                        tax_paid_cumulative_usd += tax_rec.tax_usd
                        tax_paid_cumulative_krw += tax_rec.tax_krw
                current_year = trade_dt.year

            # 2. Accrue daily interest on cash
            rf_annual = self.rf_rate_annual
            if rf_rates is not None and dt in rf_rates.index:
                rf_annual = float(rf_rates.loc[dt])
            daily_interest = self.cash * (rf_annual / 252.0)
            self.cash += daily_interest

            # 3. Daily risk manager monitoring on active turnaround stocks
            active_turnaround = [t for t, pos in self.positions.items() if pos.is_stock]
            for ticker in list(active_turnaround):
                pos = self.positions.get(ticker)
                if not pos:
                    continue

                curr_p = get_price(dt, ticker, "Close")
                open_p = get_price(dt, ticker, "Open") or curr_p
                if curr_p <= 0:
                    continue

                # Check overnight gap-down
                is_gap, gap_reason = self.risk_manager.check_overnight_gap(
                    entry_price=pos.entry_price,
                    open_price=open_p,
                    prior_close=pos.current_price,
                )

                exit_reason = None
                fill_price = curr_p
                if is_gap:
                    exit_reason = gap_reason
                    fill_price = open_p
                else:
                    pos.update_price(curr_p)
                    high_p = get_price(dt, ticker, "High") or curr_p
                    low_p = get_price(dt, ticker, "Low") or curr_p

                    exit_eval_fn = getattr(strategy, "evaluate_daily_exit", None)
                    if callable(exit_eval_fn):
                        exit_reason = exit_eval_fn(pos, curr_p, high_p, low_p, pos.days_held)
                    else:
                        exit_reason = self.risk_manager.evaluate_daily_exit(
                            entry_price=pos.entry_price,
                            current_price=curr_p,
                            peak_price=pos.peak_price,
                            days_held=pos.days_held,
                        )
                    fill_price = curr_p

                if exit_reason in (ExitReason.NONE, "NONE", None):
                    exit_reason = None
                elif hasattr(exit_reason, "value"):
                    exit_reason = exit_reason.value

                if exit_reason:
                    # Execute position liquidation
                    shares_to_sell = -pos.shares
                    friction = self.execute_trade(
                        ticker=ticker,
                        shares=shares_to_sell,
                        price=fill_price,
                        is_stock=True,
                        trade_date=trade_dt,
                        current_fx=fx,
                    )
                    trade_records.append({
                        "date": trade_dt,
                        "ticker": ticker,
                        "action": "SELL",
                        "shares": abs(shares_to_sell),
                        "price": fill_price,
                        "friction": friction,
                        "reason": exit_reason,
                        "fx_rate": fx,
                    })

            # 4. Weekly Rebalance (Friday close, dt.dayofweek == 4, or weekly trigger)
            is_weekly_rebalance_day = (dt.dayofweek == 4) or (idx == len(sim_df) - 1)
            if is_weekly_rebalance_day:
                # Current active turnaround stocks
                current_active_stocks = [t for t, pos in self.positions.items() if pos.is_stock]

                # Select candidate if capacity allows
                if len(current_active_stocks) < self.max_stock_capacity and candidate_selections:
                    # Check candidate for this week
                    raw_cand = candidate_selections.get(trade_dt) or candidate_selections.get(dt)
                    selected = getattr(raw_cand, "selected_ticker", raw_cand)
                    if selected and selected not in current_active_stocks:
                        cand_price = get_price(dt, selected, "Close")
                        if cand_price > 0:
                            current_active_stocks.append(selected)

                # Compute target weights
                rebal_sig = inspect.signature(strategy.compute_target_weights).parameters
                if "current_date" in rebal_sig or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in rebal_sig.values()):
                    target_weights = strategy.compute_target_weights(
                        active_turnaround_stocks=current_active_stocks,
                        idle_policy=strategy.params.turnaround_idle_policy,
                        current_date=trade_dt,
                    )
                else:
                    target_weights = strategy.compute_target_weights(
                        active_turnaround_stocks=current_active_stocks,
                        idle_policy=strategy.params.turnaround_idle_policy,
                    )

                # Current prices for portfolio assets
                curr_prices = {
                    "QQQ": get_price(dt, "QQQ", "Close"),
                    "SOXX": get_price(dt, "SOXX", "Close"),
                }
                for t in current_active_stocks:
                    curr_prices[t] = get_price(dt, t, "Close")
                for t in self.holdings:
                    if t not in curr_prices:
                        curr_prices[t] = get_price(dt, t, "Close")

                total_nav = self.compute_nav(curr_prices)

                # Identify all assets to consider: target assets + existing holdings (excluding Cash)
                all_rebalance_assets = sorted(list(set(target_weights.keys()).union(self.holdings.keys()) - {"Cash"}))

                pending_sells = []
                pending_buys = []

                for asset in all_rebalance_assets:
                    asset_price = curr_prices.get(asset, 0.0)
                    if asset_price <= 0:
                        continue

                    target_w = target_weights.get(asset, 0.0)
                    current_val = self.holdings.get(asset, 0.0) * asset_price
                    current_w = current_val / total_nav if total_nav > 0 else 0.0
                    delta_w = target_w - current_w

                    if abs(delta_w) >= self.rebalance_deadzone:
                        target_val = total_nav * target_w
                        trade_dollar_delta = target_val - current_val
                        shares_delta = trade_dollar_delta / asset_price
                        is_stock = (asset not in ["QQQ", "SOXX"])

                        if abs(shares_delta) > 1e-4:
                            if shares_delta < 0:
                                pending_sells.append((asset, shares_delta, asset_price, is_stock))
                            else:
                                pending_buys.append((asset, shares_delta, asset_price, is_stock))

                # Pass 1: Execute all SELL orders first to liberate cash
                for asset, shares_delta, asset_price, is_stock in pending_sells:
                    friction = self.execute_trade(
                        ticker=asset,
                        shares=shares_delta,
                        price=asset_price,
                        is_stock=is_stock,
                        trade_date=trade_dt,
                        current_fx=fx,
                    )
                    trade_records.append({
                        "date": trade_dt,
                        "ticker": asset,
                        "action": "SELL",
                        "shares": abs(shares_delta),
                        "price": asset_price,
                        "friction": friction,
                        "reason": "REBALANCE",
                        "fx_rate": fx,
                    })

                # Pass 2: Execute all BUY orders using newly liberated cash
                for asset, shares_delta, asset_price, is_stock in pending_buys:
                    # Prevent buying more than cash allows
                    if (shares_delta * asset_price) > self.cash:
                        shares_delta = max(0.0, (self.cash * 0.99) / asset_price)

                    if abs(shares_delta) > 1e-4:
                        friction = self.execute_trade(
                            ticker=asset,
                            shares=shares_delta,
                            price=asset_price,
                            is_stock=is_stock,
                            trade_date=trade_dt,
                            current_fx=fx,
                        )
                        trade_records.append({
                            "date": trade_dt,
                            "ticker": asset,
                            "action": "BUY",
                            "shares": abs(shares_delta),
                            "price": asset_price,
                            "friction": friction,
                            "reason": "REBALANCE",
                            "fx_rate": fx,
                        })

            # Final simulation day tax settlement
            is_final_day = (idx == len(sim_df) - 1)
            if is_final_day and tax_enabled:
                if current_year not in self.tax_engine.tax_records:
                    tax_rec = self.tax_engine.calculate_annual_tax(current_year, fx)
                    if tax_rec.tax_usd > 0:
                        self.cash -= tax_rec.tax_usd
                        tax_paid_cumulative_usd += tax_rec.tax_usd
                        tax_paid_cumulative_krw += tax_rec.tax_krw

            # 5. Record Daily NAV (USD & KRW, Gross & Net)
            current_prices_today = {
                "QQQ": get_price(dt, "QQQ", "Close"),
                "SOXX": get_price(dt, "SOXX", "Close"),
            }
            for t in list(self.holdings.keys()):
                if t not in current_prices_today:
                    current_prices_today[t] = get_price(dt, t, "Close")

            net_nav_usd = self.compute_nav(current_prices_today)
            gross_nav_usd = net_nav_usd + tax_paid_cumulative_usd
            net_nav_krw = net_nav_usd * fx
            gross_nav_krw = gross_nav_usd * fx

            daily_dates.append(dt)
            daily_nav_usd.append(net_nav_usd)
            daily_nav_krw.append(net_nav_krw)
            daily_gross_usd.append(gross_nav_usd)
            daily_gross_krw.append(gross_nav_krw)

            # Record allocation snapshot
            alloc = {"Cash": self.cash / net_nav_usd if net_nav_usd > 0 else 1.0}
            for t, sh in self.holdings.items():
                p = current_prices_today.get(t, 0.0)
                alloc[t] = (sh * p) / net_nav_usd if net_nav_usd > 0 else 0.0
            daily_allocations.append(alloc)

        # Final year tax record if not yet recorded
        if tax_enabled and current_year not in self.tax_engine.tax_records:
            last_fx = float(fx_series.iloc[-1])
            self.tax_engine.calculate_annual_tax(current_year, last_fx)

        # Build series
        s_net_usd = pd.Series(daily_nav_usd, index=pd.DatetimeIndex(daily_dates), name="NAV_USD")
        s_net_krw = pd.Series(daily_nav_krw, index=pd.DatetimeIndex(daily_dates), name="NAV_KRW")
        s_gross_usd = pd.Series(daily_gross_usd, index=pd.DatetimeIndex(daily_dates), name="Gross_NAV_USD")
        s_gross_krw = pd.Series(daily_gross_krw, index=pd.DatetimeIndex(daily_dates), name="Gross_NAV_KRW")

        # Compute Metrics
        ann_table_usd = PerformanceMetrics.calculate_calendar_year_mdd(s_net_usd)
        ann_table_krw = PerformanceMetrics.calculate_calendar_year_mdd(s_net_krw)
        cagr_usd = PerformanceMetrics.calculate_cagr(s_net_usd)
        cagr_krw = PerformanceMetrics.calculate_cagr(s_net_krw)
        max_ann_mdd_usd = float(ann_table_usd["Annual_MDD"].min()) if not ann_table_usd.empty else 0.0
        max_ann_mdd_krw = float(ann_table_krw["Annual_MDD"].min()) if not ann_table_krw.empty else 0.0
        calmar_usd = PerformanceMetrics.calculate_calmar_ratio(cagr_usd, max_ann_mdd_usd)
        calmar_krw = PerformanceMetrics.calculate_calmar_ratio(cagr_krw, max_ann_mdd_krw)

        trade_log_df = pd.DataFrame(trade_records) if trade_records else pd.DataFrame(columns=[
            "date", "ticker", "action", "shares", "price", "friction", "reason", "fx_rate"
        ])
        tax_table = self.tax_engine.get_annual_tax_table()
        alloc_df = pd.DataFrame(daily_allocations, index=pd.DatetimeIndex(daily_dates)).fillna(0.0)

        return BacktestResult(
            daily_nav_usd=s_net_usd,
            daily_nav_krw=s_net_krw,
            gross_nav_usd=s_gross_usd,
            after_tax_nav_usd=s_net_usd,
            gross_nav_krw=s_gross_krw,
            after_tax_nav_krw=s_net_krw,
            trade_log=trade_log_df,
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
