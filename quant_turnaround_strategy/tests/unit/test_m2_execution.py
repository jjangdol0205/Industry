"""
Unit test suite for M2 Real-World Execution Frictions (src/engine/execution.py).
Verifies:
- Brokerage commission deductions (e.g. 5 bps).
- Slippage model for ETFs (2 bps) vs individual turnaround stocks (10 bps).
- Rebalance dead-zone threshold (1.0% = 0.01) to prevent micro-turnover.
- Overnight gap-down execution fill at open price with slippage penalty.
- Buy vs Sell net cash proceeds accounting.
"""
import pytest
from src.engine.execution import ExecutionEngine


class TestExecutionFriction:
    def test_commission_and_slippage_on_stock_buy(self):
        engine = ExecutionEngine(commission_bps=5.0, slippage_stock_bps=10.0)
        res = engine.execute_trade(ticker="XYZ", shares=100.0, price=50.0, is_stock=True)

        assert res.action == "BUY"
        assert res.trade_value == 5000.0
        # Commission = 5 bps = 5000 * 0.0005 = $2.50
        # Slippage = 10 bps = 5000 * 0.0010 = $5.00
        assert pytest.approx(res.commission, abs=1e-6) == 2.50
        assert pytest.approx(res.slippage, abs=1e-6) == 5.00
        assert pytest.approx(res.total_friction, abs=1e-6) == 7.50
        # Effective fill price = 50 * (1 + 0.001) = 50.05
        assert pytest.approx(res.effective_fill_price, abs=1e-6) == 50.05
        # Cash impact = -(5000 + 7.50) = -5007.50
        assert pytest.approx(res.net_cash_impact, abs=1e-6) == -5007.50

    def test_commission_and_slippage_on_etf_sell(self):
        engine = ExecutionEngine(commission_bps=5.0, slippage_etf_bps=2.0)
        res = engine.execute_trade(ticker="QQQ", shares=-200.0, price=100.0, is_stock=False)

        assert res.action == "SELL"
        assert res.trade_value == 20_000.0
        # Commission = 5 bps = $10.00
        # ETF Slippage = 2 bps = $4.00
        # Total friction = $14.00
        assert pytest.approx(res.commission, abs=1e-6) == 10.00
        assert pytest.approx(res.slippage, abs=1e-6) == 4.00
        assert pytest.approx(res.total_friction, abs=1e-6) == 14.00
        # Effective fill price = 100 * (1 - 0.0002) = 99.98
        assert pytest.approx(res.effective_fill_price, abs=1e-6) == 99.98
        # Net proceeds = 20,000 - 14.00 = 19,986.00
        assert pytest.approx(res.net_cash_impact, abs=1e-6) == 19_986.00

    def test_rebalance_deadzone_filtering(self):
        engine = ExecutionEngine(rebalance_deadzone=0.01)  # 1.0%

        # Target 50%, Current 49.5% (Delta = 0.5% < 1.0%) -> Skip
        assert engine.should_rebalance(current_weight=0.495, target_weight=0.50) is False

        # Target 50%, Current 50.8% (Delta = 0.8% < 1.0%) -> Skip
        assert engine.should_rebalance(current_weight=0.508, target_weight=0.50) is False

        # Target 50%, Current 48.9% (Delta = 1.1% >= 1.0%) -> Execute
        assert engine.should_rebalance(current_weight=0.489, target_weight=0.50) is True

        # Target 50%, Current 51.5% (Delta = 1.5% >= 1.0%) -> Execute
        assert engine.should_rebalance(current_weight=0.515, target_weight=0.50) is True

    def test_overnight_gap_down_fills_at_open_price(self):
        engine = ExecutionEngine(slippage_stock_bps=10.0)
        # Entry at $100. Prior close $90 (-10%). Open crashes to $80 (-20% <= -12% stop)
        res = engine.execute_stop_loss_on_gap(
            entry_price=100.0,
            prior_close=90.0,
            open_price=80.0,
            shares=100.0,
            stop_loss_pct=-0.12,
        )

        assert res["triggered"] is True
        # Fills at open price with slippage: 80 * (1 - 0.001) = 79.92, NOT at $88.0 stop threshold!
        assert pytest.approx(res["fill_price"], abs=1e-4) == 79.92
        assert res["fill_price"] < 88.0
        assert res["slippage_cost"] == 8.00  # 10 bps on $8,000
        assert res["net_cash_received"] == 7992.00
