"""
Unit test suite for M2 Portfolio & Capital Accounting (src/engine/portfolio.py).
Verifies:
- Dynamic asset allocation across QQQ, SOXX, Turnaround stocks (0-3 capacity), and cash.
- Idle policies: 'cash_buffer' vs 'etf_sweep'.
- Dual-currency NAV computation in USD and KRW.
- Cash interest accrual using risk-free rate.
- Position lifecycle, peak tracking, and unrealized PnL.
"""
from datetime import date
import pytest
from src.engine.portfolio import Portfolio, Position


class TestPortfolioAccounting:
    def test_initial_state_and_nav(self):
        p = Portfolio(initial_capital=100_000.0, max_stock_capacity=3)
        assert p.cash == 100_000.0
        assert p.compute_nav({}) == 100_000.0
        assert p.compute_nav_krw({}, fx_rate=1300.0) == 130_000_000.0

    def test_position_tracking_and_peak_update(self):
        pos = Position(
            ticker="XYZ",
            shares=100.0,
            entry_price=50.0,
            entry_date=date(2021, 1, 15),
            entry_fx=1100.0,
        )
        assert pos.market_value_usd == 5000.0
        assert pos.market_value_krw(1200.0) == 6_000_000.0
        assert pos.unrealized_pnl_usd == 0.0
        assert pos.unrealized_pnl_pct == 0.0

        # Update price upward
        pos.update_price(60.0)
        assert pos.current_price == 60.0
        assert pos.peak_price == 60.0
        assert pos.days_held == 1
        assert pytest.approx(pos.unrealized_pnl_pct, abs=1e-6) == 0.20
        assert pos.drawdown_from_peak() == 0.0

        # Update price downward
        pos.update_price(54.0)
        assert pos.current_price == 54.0
        assert pos.peak_price == 60.0
        assert pos.days_held == 2
        assert pytest.approx(pos.drawdown_from_peak(), abs=1e-6) == -0.10

    def test_nav_conservation_with_multiple_positions(self):
        p = Portfolio(initial_capital=100_000.0)
        p.cash = 25_000.0
        p.open_position("QQQ", shares=500.0, price=100.0, trade_date=date(2021, 1, 4), is_stock=False)
        p.open_position("SOXX", shares=200.0, price=100.0, trade_date=date(2021, 1, 4), is_stock=False)
        p.open_position("ABC", shares=50.0, price=100.0, trade_date=date(2021, 1, 4), is_stock=True)

        prices = {"QQQ": 100.0, "SOXX": 100.0, "ABC": 100.0}
        # 25,000 + 50,000 + 20,000 + 5,000 = 100,000
        assert p.compute_nav(prices) == 100_000.0
        assert p.compute_nav_krw(prices, fx_rate=1200.0) == 120_000_000.0

    def test_capacity_constraint_and_candidate_gates(self):
        p = Portfolio(initial_capital=100_000.0, max_stock_capacity=3)
        assert p.can_buy_new_candidate([]) is True
        assert p.can_buy_new_candidate(["S1"]) is True
        assert p.can_buy_new_candidate(["S1", "S2"]) is True
        assert p.can_buy_new_candidate(["S1", "S2", "S3"]) is False

        p.open_position("S1", 10, 10, date(2021, 1, 1))
        p.open_position("S2", 10, 10, date(2021, 1, 1))
        p.open_position("S3", 10, 10, date(2021, 1, 1))
        assert p.can_buy_new_candidate() is False

        # Close one position
        p.close_position("S2")
        assert p.can_buy_new_candidate() is True

    def test_idle_policy_cash_buffer_weights(self):
        p = Portfolio(initial_capital=100_000.0, max_stock_capacity=3, turnaround_idle_policy="cash_buffer")
        # When 1 turnaround stock held
        weights = p.compute_target_weights(
            base_qqq=0.50,
            base_soxx=0.30,
            max_turnaround_weight=0.20,
            active_turnaround_tickers=["T1"],
            idle_policy="cash_buffer",
        )
        assert weights["QQQ"] == 0.50
        assert weights["SOXX"] == 0.30
        assert pytest.approx(weights["T1"], abs=1e-4) == 0.20 / 3  # ~0.0667
        # Remaining 2 slots (2 * 0.0667 = 0.1333) remain in cash buffer
        assert pytest.approx(weights["Cash"], abs=1e-4) == 0.20 * (2 / 3)
        assert pytest.approx(sum(weights.values()), abs=1e-6) == 1.0

    def test_idle_policy_etf_sweep_weights(self):
        p = Portfolio(initial_capital=100_000.0, max_stock_capacity=3, turnaround_idle_policy="etf_sweep")
        # When 0 turnaround stocks held: 20% swept to QQQ and SOXX (50:30 ratio)
        weights = p.compute_target_weights(
            base_qqq=0.50,
            base_soxx=0.30,
            max_turnaround_weight=0.20,
            active_turnaround_tickers=[],
            idle_policy="etf_sweep",
        )
        # QQQ gets 0.50 + 0.20 * (50/80) = 0.625
        # SOXX gets 0.30 + 0.20 * (30/80) = 0.375
        assert pytest.approx(weights["QQQ"], abs=1e-6) == 0.625
        assert pytest.approx(weights["SOXX"], abs=1e-6) == 0.375
        assert weights["Cash"] == 0.0
        assert pytest.approx(sum(weights.values()), abs=1e-6) == 1.0

    def test_daily_interest_accrual(self):
        p = Portfolio(initial_capital=100_000.0)
        p.cash = 100_000.0
        interest = p.accrue_interest(annual_rf_rate=0.0504, days_per_year=252)
        # Daily rate = 0.0504 / 252 = 0.0002 (2 bps)
        # Interest on $100,000 = $20.0
        assert pytest.approx(interest, abs=1e-4) == 20.0
        assert pytest.approx(p.cash, abs=1e-4) == 100_020.0
