"""
Tab 5: Live Simulation Lab & Parameter Tuning.
Provides interactive controls to parameterize weights, stop-loss, profit-target,
holding period, and regime filters, with instant on-demand backtest execution
and KPI delta comparison cards.
"""
from typing import Dict, Any, Optional
import time
import streamlit as st
import pandas as pd
import numpy as np

from src.ui.components import render_metric_card, fmt_pct, fmt_ratio, fmt_currency
from src.engine.backtester import BacktestEngine, BacktestResult
from src.strategies.enhanced_strategy import EnhancedStrategy, EnhancedStrategyParameters
from src.strategies.base_strategy import BaseStrategy, StrategyParameters
from src.engine.metrics import PerformanceMetrics


def render_simulation_tab(
    sim_data: Dict[str, Any],
    currency: str = "USD",
    tax_mode: str = "Net After-Tax",
):
    """
    Renders Tab 5: Live Simulation Lab & Parameter Tuning.
    """
    st.markdown("### 🧪 Live Simulation Lab & Parameter Tuning")
    st.caption("Perform on-demand walk-forward simulations across the 2001-present dataset using customized parameters.")

    prices_df = sim_data["prices"]
    fx_series = sim_data["fx_series"]
    res_enh = sim_data["res_enh"]

    # Parameter Tuning Panels
    col_p1, col_p2, col_p3 = st.columns(3)

    with col_p1:
        st.markdown("##### 1. Asset Allocation Weights")
        w_qqq = st.slider("Target QQQ Weight (%)", min_value=10, max_value=70, value=40, step=5) / 100.0
        w_soxx = st.slider("Target SOXX Weight (%)", min_value=10, max_value=70, value=30, step=5) / 100.0
        w_turnaround = st.slider("Turnaround Stocks Allocation (%)", min_value=5, max_value=30, value=20, step=5) / 100.0
        max_stocks = st.number_input("Max Stock Capacity", min_value=1, max_value=5, value=3, step=1)

    with col_p2:
        st.markdown("##### 2. Risk Management & Exits")
        stop_loss = st.slider("Hard Stop-Loss (%)", min_value=-25, max_value=-5, value=-12, step=1) / 100.0
        take_profit = st.slider("Take-Profit Target (%)", min_value=15, max_value=80, value=35, step=5) / 100.0
        holding_weeks = st.slider("Max Holding Period (Weeks)", min_value=8, max_value=52, value=26, step=2)

    with col_p3:
        st.markdown("##### 3. Regime Filter & Momentum")
        enable_regime = st.checkbox("Enable Macro Trend Filter (SMA)", value=True)
        sma_window = st.slider("Regime SMA Window (Days)", min_value=50, max_value=250, value=200, step=10)
        mom_window = st.slider("Dual-Momentum Lookback (Days)", min_value=20, max_value=126, value=63, step=5)

    st.markdown("---")

    # Run Simulation Trigger
    run_btn = st.button("⚡ Run Custom Simulation", type="primary", use_container_width=True)

    if run_btn:
        t0 = time.time()
        with st.spinner("Executing event-driven simulation across 2001-Present historical data..."):
            try:
                if enable_regime:
                    custom_params = EnhancedStrategyParameters(
                        w_qqq_base=w_qqq,
                        w_soxx_base=w_soxx,
                        w_turnaround_max=w_turnaround,
                        max_active_stocks=int(max_stocks),
                        stop_loss_pct=stop_loss,
                        profit_target_pct=take_profit,
                        max_holding_weeks=int(holding_weeks),
                        max_holding_days=int(holding_weeks * 5),
                        sma_trend_window=int(sma_window),
                        momentum_window=int(mom_window),
                    )
                    strategy = EnhancedStrategy(params=custom_params, prices_df=prices_df)
                else:
                    custom_base_params = StrategyParameters(
                        w_qqq_base=w_qqq,
                        w_soxx_base=w_soxx,
                        w_turnaround_max=w_turnaround,
                        max_active_stocks=int(max_stocks),
                        stop_loss_pct=stop_loss,
                        profit_target_pct=take_profit,
                        max_holding_weeks=int(holding_weeks),
                        max_holding_days=int(holding_weeks * 5),
                    )
                    strategy = BaseStrategy(params=custom_base_params)

                engine = BacktestEngine(
                    initial_capital=100_000.0,
                    commission_bps=5.0,
                    slippage_etf_bps=2.0,
                    slippage_stock_bps=10.0,
                    max_stock_capacity=int(max_stocks),
                )
                tax_flag = ("Net" in tax_mode)
                res_custom: BacktestResult = engine.run(
                    strategy=strategy,
                    prices_df=prices_df,
                    fx_rates=fx_series,
                    tax_enabled=tax_flag,
                    start_date="2001-07-10",
                )
                duration = time.time() - t0

                st.session_state["res_custom"] = res_custom
                st.session_state["custom_duration"] = duration
                st.success(f"Simulation completed in {duration:.2f} seconds!")
            except Exception as e:
                st.error(f"Simulation error: {e}")

    # Display results if available in session state
    if "res_custom" in st.session_state:
        res_custom: BacktestResult = st.session_state["res_custom"]
        dur = st.session_state.get("custom_duration", 0.0)

        st.markdown(f"#### 📊 Custom Simulation Results vs Enhanced Baseline (Time: {dur:.2f}s)")

        # Determine series
        if currency == "KRW":
            s_c = res_custom.after_tax_nav_krw if "Net" in tax_mode else res_custom.gross_nav_krw
            s_e = res_enh.after_tax_nav_krw if "Net" in tax_mode else res_enh.gross_nav_krw
            cagr_c = res_custom.cagr_krw
            cagr_e = res_enh.cagr_krw
            mdd_c = res_custom.max_annual_mdd_krw
            mdd_e = res_enh.max_annual_mdd_krw
            calmar_c = res_custom.calmar_ratio_krw
            calmar_e = res_enh.calmar_ratio_krw
        else:
            s_c = res_custom.after_tax_nav_usd if "Net" in tax_mode else res_custom.gross_nav_usd
            s_e = res_enh.after_tax_nav_usd if "Net" in tax_mode else res_enh.gross_nav_usd
            cagr_c = res_custom.cagr_usd
            cagr_e = res_enh.cagr_usd
            mdd_c = res_custom.max_annual_mdd_usd
            mdd_e = res_enh.max_annual_mdd_usd
            calmar_c = res_custom.calmar_ratio_usd
            calmar_e = res_enh.calmar_ratio_usd

        # Deltas
        d_cagr = (cagr_c - cagr_e) * 100.0
        d_mdd = (abs(mdd_e) - abs(mdd_c)) * 100.0  # Positive means mdd is smaller (better)
        d_calmar = calmar_c - calmar_e

        fin_c = float(s_c.iloc[-1]) if not s_c.empty else 0.0

        res_cols = st.columns(4)
        with res_cols[0]:
            render_metric_card(
                label=f"Custom Final NAV ({currency})",
                value_str=fmt_currency(fin_c, currency=currency),
                sub_str=f"Base: {fmt_currency(float(s_e.iloc[-1]), currency=currency)}",
                sub_type="pos" if fin_c >= float(s_e.iloc[-1]) else "neg",
            )
        with res_cols[1]:
            render_metric_card(
                label="Custom CAGR",
                value_str=fmt_pct(cagr_c),
                sub_str=f"Δ {d_cagr:+.2f}% vs Enhanced",
                sub_type="pos" if d_cagr >= 0 else "neg",
            )
        with res_cols[2]:
            render_metric_card(
                label="Custom Max Annual MDD",
                value_str=fmt_pct(mdd_c),
                sub_str=f"{'Improved' if d_mdd >= 0 else 'Worsened'} by {abs(d_mdd):.1f}%",
                sub_type="pos" if d_mdd >= 0 else "neg",
            )
        with res_cols[3]:
            render_metric_card(
                label="Custom Calmar Ratio",
                value_str=fmt_ratio(calmar_c),
                sub_str=f"Δ {d_calmar:+.2f} vs Enhanced",
                sub_type="pos" if d_calmar >= 0 else "neg",
            )
