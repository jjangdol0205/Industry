"""
Tab 2: Calendar Year Breakdown (2001-2026) Table & Crisis Regime Analysis.
Displays full annual returns, calendar intra-year drawdowns, Return/MDD ratios,
and visual alerts for crisis regimes (2002, 2008, 2022).
"""
from typing import Dict, Any
import streamlit as st
import pandas as pd
import numpy as np

from src.ui.components import render_metric_card, fmt_pct, fmt_ratio
from src.ui.charts import create_annual_comparison_bar_chart
from src.engine.metrics import PerformanceMetrics


def render_calendar_tab(
    sim_data: Dict[str, Any],
    currency: str = "USD",
    tax_mode: str = "Net After-Tax",
):
    """
    Renders Tab 2: Calendar Year Breakdown Table and Crisis Analysis.
    """
    st.markdown("### 📅 Calendar Year Performance Breakdown (2001-2026)")

    res_enh = sim_data["res_enh"]
    res_base = sim_data["res_base"]
    s_qqq = sim_data["qqq_nav"]
    s_soxx = sim_data["soxx_nav"]

    # Select series
    if currency == "KRW":
        s_enh = res_enh.after_tax_nav_krw if "Net" in tax_mode else res_enh.gross_nav_krw
        s_base = res_base.after_tax_nav_krw if "Net" in tax_mode else res_base.gross_nav_krw
    else:
        s_enh = res_enh.after_tax_nav_usd if "Net" in tax_mode else res_enh.gross_nav_usd
        s_base = res_base.after_tax_nav_usd if "Net" in tax_mode else res_base.gross_nav_usd

    # Compute calendar tables for each
    df_enh = PerformanceMetrics.calculate_calendar_year_mdd(s_enh)
    df_base = PerformanceMetrics.calculate_calendar_year_mdd(s_base)
    df_qqq = PerformanceMetrics.calculate_calendar_year_mdd(s_qqq)
    df_soxx = PerformanceMetrics.calculate_calendar_year_mdd(s_soxx)

    # Merge into a comprehensive calendar table
    years = sorted(list(set(df_enh["Year"]).union(df_base["Year"]).union(df_qqq["Year"])))

    records = []
    for y in years:
        row_e = df_enh[df_enh["Year"] == y]
        row_b = df_base[df_base["Year"] == y]
        row_q = df_qqq[df_qqq["Year"] == y]
        row_s = df_soxx[df_soxx["Year"] == y]

        ret_e = float(row_e["Annual_Return"].values[0]) if not row_e.empty else 0.0
        mdd_e = float(row_e["Annual_MDD"].values[0]) if not row_e.empty else 0.0
        ratio_e = float(row_e["Return_to_MDD"].values[0]) if not row_e.empty else 0.0

        ret_b = float(row_b["Annual_Return"].values[0]) if not row_b.empty else 0.0
        mdd_b = float(row_b["Annual_MDD"].values[0]) if not row_b.empty else 0.0
        ratio_b = float(row_b["Return_to_MDD"].values[0]) if not row_b.empty else 0.0

        ret_q = float(row_q["Annual_Return"].values[0]) if not row_q.empty else 0.0
        mdd_q = float(row_q["Annual_MDD"].values[0]) if not row_q.empty else 0.0

        ret_s = float(row_s["Annual_Return"].values[0]) if not row_s.empty else 0.0
        mdd_s = float(row_s["Annual_MDD"].values[0]) if not row_s.empty else 0.0

        alpha_q = ret_e - ret_q

        records.append({
            "Year": y,
            "Enhanced_Return": ret_e,
            "Base_Return": ret_b,
            "QQQ_Return": ret_q,
            "SOXX_Return": ret_s,
            "Enhanced_Annual_MDD": mdd_e,
            "Base_Annual_MDD": mdd_b,
            "QQQ_Annual_MDD": mdd_q,
            "SOXX_Annual_MDD": mdd_s,
            "Enhanced_Return_to_MDD": ratio_e,
            "Base_Return_to_MDD": ratio_b,
            "Alpha_vs_QQQ": alpha_q,
        })

    master_df = pd.DataFrame(records)

    # 1. Crisis Years Highlights Banner
    st.markdown("#### 🚨 Historical Crisis Regime Protection Deep-Dive")
    crisis_cols = st.columns(3)

    crisis_info = [
        {"year": 2002, "label": "2002 Dot-com Crash", "desc": "Tech crash bottom; severe Nasdaq selloff"},
        {"year": 2008, "label": "2008 Lehman GFC", "desc": "Subprime global financial crisis"},
        {"year": 2022, "label": "2022 Tech Bear Market", "desc": "Rapid Fed rate hiking cycle & tech collapse"},
    ]

    for idx, c in enumerate(crisis_info):
        y_val = c["year"]
        c_row = master_df[master_df["Year"] == y_val]
        if not c_row.empty:
            e_mdd = float(c_row["Enhanced_Annual_MDD"].values[0])
            b_mdd = float(c_row["Base_Annual_MDD"].values[0])
            q_mdd = float(c_row["QQQ_Annual_MDD"].values[0])
            s_mdd = float(c_row["SOXX_Annual_MDD"].values[0])
            diff_mdd = abs(q_mdd) - abs(e_mdd)

            with crisis_cols[idx]:
                st.markdown(
                    f"""
                    <div class="metric-card" style="border-left: 4px solid #ff9100;">
                        <div class="metric-label">{c['label']}</div>
                        <div style="font-size: 0.95rem; color: #f5f5f5; margin-bottom: 6px;">{c['desc']}</div>
                        <div style="font-size: 0.85rem; color: #e0e0e0; line-height: 1.6;">
                            • <b>Enhanced MDD</b>: <span style="color: #00c853; font-weight:700;">{e_mdd*100:.1f}%</span><br>
                            • Base Strategy MDD: <span style="color: #ff5252;">{b_mdd*100:.1f}%</span><br>
                            • QQQ Benchmark MDD: <span style="color: #ff5252;">{q_mdd*100:.1f}%</span><br>
                            • SOXX Benchmark MDD: <span style="color: #ff5252;">{s_mdd*100:.1f}%</span>
                        </div>
                        <div class="metric-sub metric-sub-pos" style="margin-top: 8px;">
                            🛡️ Saved {diff_mdd*100:.1f}% Drawdown vs QQQ
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # 2. Comparative Annual Returns Grouped Bar Chart
    bar_fig = create_annual_comparison_bar_chart(master_df)
    st.plotly_chart(bar_fig, use_container_width=True)

    # 3. Formatted Data Table (2001-2026)
    st.markdown(f"#### 📋 Full Annual Performance Table (2001-2026, {currency}, {tax_mode})")

    # Display formatted DataFrame with styling
    display_df = master_df.copy()
    display_df["Year"] = display_df["Year"].astype(str)
    # Add crisis tag to Year
    display_df["Year"] = display_df["Year"].apply(lambda y: f"🚨 {y} (Crisis)" if y in ["2002", "2008", "2022"] else y)

    fmt_cols = {
        "Enhanced_Return": lambda v: fmt_pct(v),
        "Base_Return": lambda v: fmt_pct(v),
        "QQQ_Return": lambda v: fmt_pct(v),
        "SOXX_Return": lambda v: fmt_pct(v),
        "Enhanced_Annual_MDD": lambda v: fmt_pct(v),
        "Base_Annual_MDD": lambda v: fmt_pct(v),
        "QQQ_Annual_MDD": lambda v: fmt_pct(v),
        "SOXX_Annual_MDD": lambda v: fmt_pct(v),
        "Enhanced_Return_to_MDD": lambda v: fmt_ratio(v),
        "Base_Return_to_MDD": lambda v: fmt_ratio(v),
        "Alpha_vs_QQQ": lambda v: fmt_pct(v),
    }

    styled_df = display_df.copy()
    for col, formatter in fmt_cols.items():
        if col in styled_df.columns:
            styled_df[col] = styled_df[col].apply(formatter)

    styled_df.columns = [
        "Year",
        "Enhanced Return",
        "Base Return",
        "QQQ Return",
        "SOXX Return",
        "Enhanced MDD",
        "Base MDD",
        "QQQ MDD",
        "SOXX MDD",
        "Enhanced Ret/MDD",
        "Base Ret/MDD",
        "Alpha vs QQQ",
    ]

    st.dataframe(styled_df, use_container_width=True, hide_index=True)
