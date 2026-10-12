"""
Tab 3: Dynamic Asset Allocation & Exposure Heatmaps.
Renders 100% stacked area charts of portfolio weights over time,
monthly returns heatmaps, and macro regime transition analytics.
"""
from typing import Dict, Any
import streamlit as st
import pandas as pd
import numpy as np

from src.ui.charts import create_allocation_area_chart, create_monthly_return_heatmap
from src.ui.components import render_metric_card


def render_allocation_tab(
    sim_data: Dict[str, Any],
    currency: str = "USD",
    tax_mode: str = "Net After-Tax",
):
    """
    Renders Tab 3: Dynamic Asset Allocation & Heatmaps.
    """
    st.markdown("### 📊 Dynamic Asset Allocation & Exposure Heatmaps")

    res_enh = sim_data["res_enh"]
    alloc_df = res_enh.allocation_history

    # Select NAV series
    if currency == "KRW":
        s_nav = res_enh.after_tax_nav_krw if "Net" in tax_mode else res_enh.gross_nav_krw
    else:
        s_nav = res_enh.after_tax_nav_usd if "Net" in tax_mode else res_enh.gross_nav_usd

    # 1. Macro Regime Exposure Breakdown Cards
    if not alloc_df.empty:
        cash_series = alloc_df.get("Cash", pd.Series(0.0, index=alloc_df.index))
        equity_series = 1.0 - cash_series

        avg_equity = float(equity_series.mean()) * 100.0
        avg_cash = float(cash_series.mean()) * 100.0
        max_cash = float(cash_series.max()) * 100.0

        # Estimate time in regimes:
        # Bull: cash < 0.20
        # Transition: 0.20 <= cash < 0.60
        # Bear: cash >= 0.60
        time_bull = (cash_series < 0.20).sum() / len(cash_series) * 100.0
        time_trans = ((cash_series >= 0.20) & (cash_series < 0.60)).sum() / len(cash_series) * 100.0
        time_bear = (cash_series >= 0.60).sum() / len(cash_series) * 100.0

        st.markdown("#### 🛡️ Portfolio Exposure & Macro Regime Distribution")
        exp_cols = st.columns(4)
        with exp_cols[0]:
            render_metric_card(
                label="Average Equity Exposure",
                value_str=f"{avg_equity:.1f}%",
                sub_str=f"Avg Cash: {avg_cash:.1f}%",
                sub_type="pos",
            )
        with exp_cols[1]:
            render_metric_card(
                label="Time in Bull Regime",
                value_str=f"{time_bull:.1f}%",
                sub_str="100% Equity Allocation",
                sub_type="pos",
            )
        with exp_cols[2]:
            render_metric_card(
                label="Time in Transition",
                value_str=f"{time_trans:.1f}%",
                sub_str="60% Equity / 40% Cash",
                sub_type="neutral",
            )
        with exp_cols[3]:
            render_metric_card(
                label="Time in Bear Defense",
                value_str=f"{time_bear:.1f}%",
                sub_str=f"Max Cash Deployed: {max_cash:.1f}%",
                sub_type="neg",
            )

    st.markdown("---")

    # 2. 100% Stacked Area Chart (Time-series Exposure)
    st.markdown("#### 📈 Historical Asset Weight Evolution (2001-Present)")
    area_fig = create_allocation_area_chart(alloc_df)
    st.plotly_chart(area_fig, use_container_width=True)

    st.markdown("---")

    # 3. Monthly Return Heatmap
    st.markdown("#### 🗓️ Monthly Returns Heatmap (2001-Present)")
    heat_fig = create_monthly_return_heatmap(s_nav)
    st.plotly_chart(heat_fig, use_container_width=True)
