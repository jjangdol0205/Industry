"""
Multi-asset portfolio management and capital accounting module.
Handles dynamic asset allocation across QQQ, SOXX, individual turnaround stocks (0-3 capacity), and cash.
Provides idle cash policies ('cash_buffer' vs 'etf_sweep') and dual-currency (USD/KRW) NAV tracking.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd


@dataclass
class Position:
    """Individual stock/ETF position tracking entry basis, peak price, and holding duration."""
    ticker: str
    shares: float
    entry_price: float
    entry_date: date
    entry_fx: float = 1200.0  # USD/KRW on entry date
    current_price: float = 0.0
    peak_price: float = 0.0
    days_held: int = 0
    is_stock: bool = True

    def __post_init__(self):
        if self.current_price <= 0:
            self.current_price = self.entry_price
        if self.peak_price <= 0:
            self.peak_price = self.entry_price

    def update_price(self, price: float) -> None:
        """Updates current price and ratchets peak price."""
        self.current_price = price
        if price > self.peak_price:
            self.peak_price = price
        self.days_held += 1

    @property
    def market_value_usd(self) -> float:
        return self.shares * self.current_price

    def market_value_krw(self, fx_rate: float) -> float:
        return self.shares * self.current_price * fx_rate

    @property
    def unrealized_pnl_usd(self) -> float:
        return self.shares * (self.current_price - self.entry_price)

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price

    def drawdown_from_peak(self) -> float:
        if self.peak_price <= 0:
            return 0.0
        return (self.current_price - self.peak_price) / self.peak_price


class Portfolio:
    """
    Portfolio capital accounting engine.
    Maintains cash, equity positions, transaction history, and dual-currency valuation.
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        max_stock_capacity: int = 3,
        turnaround_idle_policy: str = "cash_buffer",
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_stock_capacity = max_stock_capacity
        self.turnaround_idle_policy = turnaround_idle_policy  # 'cash_buffer' or 'etf_sweep'
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict[str, Any]] = []

    @property
    def holdings(self) -> Dict[str, float]:
        """Provides backward-compatible dict of ticker -> shares."""
        return {ticker: pos.shares for ticker, pos in self.positions.items() if abs(pos.shares) > 1e-6}

    @holdings.setter
    def holdings(self, val: Dict[str, float]):
        """Sets holdings directly for testing convenience."""
        self.positions.clear()
        for ticker, shares in val.items():
            if abs(shares) > 1e-6:
                self.positions[ticker] = Position(
                    ticker=ticker,
                    shares=shares,
                    entry_price=1.0,
                    entry_date=date(2001, 7, 10),
                    is_stock=(ticker not in ["QQQ", "SOXX"]),
                )

    def compute_nav(self, current_prices: Dict[str, float]) -> float:
        """
        Calculates total portfolio Net Asset Value (NAV) in USD:
        V(t) = Cash + sum(Shares_i * Price_i).
        """
        stock_value = 0.0
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, pos.current_price)
            stock_value += pos.shares * price
        return self.cash + stock_value

    def compute_nav_krw(self, current_prices: Dict[str, float], fx_rate: float) -> float:
        """Calculates total portfolio Net Asset Value (NAV) in KRW."""
        return self.compute_nav(current_prices) * fx_rate

    def get_turnaround_stocks(self) -> List[str]:
        """Returns list of currently held turnaround stock tickers (excluding QQQ, SOXX)."""
        return [ticker for ticker, pos in self.positions.items() if pos.is_stock and abs(pos.shares) > 1e-6]

    def can_buy_new_candidate(self, current_turnaround_stocks: Optional[List[str]] = None) -> bool:
        """
        Enforces maximum capacity constraint:
        Holds at most max_stock_capacity (default: 3) turnaround stocks.
        """
        if current_turnaround_stocks is None:
            active_count = len(self.get_turnaround_stocks())
        else:
            active_count = len(current_turnaround_stocks)
        return active_count < self.max_stock_capacity

    def compute_idle_etf_sweep_weights(
        self,
        base_qqq: float = 0.50,
        base_soxx: float = 0.30,
        max_turnaround_weight: float = 0.20,
        active_stock_count: int = 0,
    ) -> Dict[str, float]:
        """
        Under 'etf_sweep' policy, unallocated turnaround capacity (3 - k) * (max_turnaround_weight / 3)
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

    def compute_target_weights(
        self,
        base_qqq: float = 0.50,
        base_soxx: float = 0.30,
        max_turnaround_weight: float = 0.20,
        active_turnaround_tickers: Optional[List[str]] = None,
        idle_policy: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Computes normalized target weights for all portfolio assets based on active turnaround stock count.
        """
        policy = idle_policy or self.turnaround_idle_policy
        if active_turnaround_tickers is None:
            active_turnaround_tickers = self.get_turnaround_stocks()

        k = len(active_turnaround_tickers)
        per_stock_weight = max_turnaround_weight / self.max_stock_capacity

        targets = {}
        for ticker in active_turnaround_tickers:
            targets[ticker] = per_stock_weight

        if policy == "etf_sweep":
            sweep = self.compute_idle_etf_sweep_weights(
                base_qqq=base_qqq,
                base_soxx=base_soxx,
                max_turnaround_weight=max_turnaround_weight,
                active_stock_count=k,
            )
            targets["QQQ"] = sweep["QQQ"]
            targets["SOXX"] = sweep["SOXX"]
            targets["Cash"] = 0.0
        else:
            # cash_buffer policy
            targets["QQQ"] = base_qqq
            targets["SOXX"] = base_soxx
            unallocated_slots = self.max_stock_capacity - k
            targets["Cash"] = (1.0 - (base_qqq + base_soxx + k * per_stock_weight))
            # clamp cash to positive
            targets["Cash"] = max(0.0, targets["Cash"])

        return targets

    def accrue_interest(self, annual_rf_rate: float, days_per_year: int = 252) -> float:
        """
        Accrues daily risk-free interest on uninvested cash balance:
        C(t) = C(t-1) * (1 + r_f / 252).
        Returns accrued interest amount.
        """
        if self.cash <= 0 or annual_rf_rate <= 0:
            return 0.0
        daily_rate = annual_rf_rate / days_per_year
        interest = self.cash * daily_rate
        self.cash += interest
        return interest

    def open_position(
        self,
        ticker: str,
        shares: float,
        price: float,
        trade_date: date,
        fx_rate: float = 1200.0,
        is_stock: bool = True,
    ) -> Position:
        """Opens or increases a position."""
        if ticker in self.positions:
            pos = self.positions[ticker]
            new_shares = pos.shares + shares
            if new_shares > 0:
                weighted_price = (pos.shares * pos.entry_price + shares * price) / new_shares
                pos.shares = new_shares
                pos.entry_price = weighted_price
                pos.current_price = price
                pos.entry_fx = fx_rate
            return pos
        else:
            pos = Position(
                ticker=ticker,
                shares=shares,
                entry_price=price,
                entry_date=trade_date,
                entry_fx=fx_rate,
                current_price=price,
                peak_price=price,
                days_held=0,
                is_stock=is_stock,
            )
            self.positions[ticker] = pos
            return pos

    def close_position(self, ticker: str) -> Optional[Position]:
        """Closes and removes a position from active holdings."""
        return self.positions.pop(ticker, None)
