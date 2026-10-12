"""
Plotly Chart Generators for Quantitative Strategy Dashboard.
Creates:
- Cumulative NAV curve with linked underwater drawdown subplot and crisis regime shading.
- Dynamic asset allocation 100% stacked area chart.
- Monthly performance return 2D heatmap.
- Calendar year comparative bar chart.
"""
from typing import Dict, Optional, List
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Standardized Institutional Palette
COLORS = {
    "Enhanced Strategy (AR-DM)": "#00C853",  # Vibrant Green
    "Enhanced Strategy": "#00C853",
    "Base Strategy": "#2979FF",             # Vibrant Blue
    "QQQ Benchmark": "#FF9100",             # Bright Amber
    "SOXX Benchmark": "#AA00FF",            # Vivid Purple
    "Custom Simulation": "#E91E63",         # Pink / Rose
    "Cash": "#9E9E9E",                      # Neutral Gray
}

CRISIS_PERIODS = [
    {"name": "Dot-com Bust", "start": "2001-07-10", "end": "2002-10-09", "color": "rgba(255, 82, 82, 0.08)"},
    {"name": "GFC (Lehman)", "start": "2007-10-09", "end": "2009-03-09", "color": "rgba(255, 82, 82, 0.08)"},
    {"name": "COVID Crash", "start": "2020-02-19", "end": "2020-03-23", "color": "rgba(255, 82, 82, 0.08)"},
    {"name": "Tech Bear 2022", "start": "2022-01-03", "end": "2022-10-13", "color": "rgba(255, 82, 82, 0.08)"},
]


def calculate_drawdown_series(nav_series: pd.Series) -> pd.Series:
    """Computes rolling percentage drawdown from prior cumulative peak."""
    if nav_series.empty:
        return nav_series
    peak = nav_series.cummax()
    return (nav_series - peak) / peak


def create_cumulative_and_underwater_chart(
    series_map: Dict[str, pd.Series],
    currency: str = "USD",
    log_scale: bool = True,
    title: str = "Cumulative Portfolio Performance & Underwater Drawdown (2001-Present)",
) -> go.Figure:
    """
    Constructs a dual-pane figure:
    Row 1: Cumulative NAV curves (Base, Enhanced, QQQ, SOXX, Custom).
    Row 2: Underwater Drawdown curves with shaded crisis periods.
    """
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.70, 0.30],
        subplot_titles=[
            f"Cumulative Net Asset Value ({currency})",
            "Underwater Drawdown from Peak (%)",
        ],
    )

    curr_sym = "₩" if currency == "KRW" else "$"

    for name, s in series_map.items():
        if s is None or s.empty:
            continue
        color = COLORS.get(name, "#00E5FF")
        width = 3.0 if "Enhanced" in name else (2.5 if "Custom" in name else (2.0 if "Base" in name else 1.5))
        dash = "solid" if "Enhanced" in name else ("dashdot" if "Custom" in name else ("dash" if "Base" in name else "dot"))

        # Row 1: Cumulative NAV
        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s.values,
                name=name,
                line=dict(color=color, width=width, dash=dash),
                hovertemplate=f"<b>{name}</b><br>Date: %{{x|%Y-%m-%d}}<br>NAV: {curr_sym}%{{y:,.0f}}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # Row 2: Drawdown
        dd = calculate_drawdown_series(s)
        fig.add_trace(
            go.Scatter(
                x=dd.index,
                y=dd.values * 100.0,
                name=f"{name} (DD)",
                line=dict(color=color, width=max(1.0, width - 0.5), dash=dash),
                showlegend=False,
                hovertemplate=f"<b>{name}</b><br>Date: %{{x|%Y-%m-%d}}<br>Drawdown: %{{y:.2f}}%<extra></extra>",
            ),
            row=2,
            col=1,
        )

    # Add crisis annotations & shaded vertical rects on Row 2
    for c in CRISIS_PERIODS:
        fig.add_vrect(
            x0=c["start"],
            x1=c["end"],
            fillcolor=c["color"],
            layer="below",
            line_width=1,
            line_color="rgba(255, 82, 82, 0.2)",
            annotation_text=c["name"],
            annotation_position="top left",
            annotation_font=dict(size=9, color="rgba(255, 255, 255, 0.45)"),
            row=2,
            col=1,
        )

    fig.update_yaxes(
        type="log" if log_scale else "linear",
        title_text=f"NAV ({currency})",
        row=1,
        col=1,
        gridcolor="rgba(255, 255, 255, 0.08)",
    )
    fig.update_yaxes(
        title_text="Drawdown (%)",
        row=2,
        col=1,
        range=[-80, 5],
        gridcolor="rgba(255, 255, 255, 0.08)",
    )
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.08)",
        showgrid=True,
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#f5f5f5")),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(18, 22, 34, 0.8)",
        margin=dict(l=60, r=30, t=50, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        hovermode="x unified",
        height=680,
    )

    return fig


def create_allocation_area_chart(alloc_df: pd.DataFrame) -> go.Figure:
    """
    Creates a 100% stacked area chart of portfolio weights over time.
    Separates QQQ, SOXX, individual turnaround stocks, and Cash.
    """
    fig = go.Figure()

    if alloc_df.empty:
        return fig

    # Group turnaround stocks into a clean single aggregate or top holdings
    etf_and_cash = {"QQQ", "SOXX", "Cash"}
    stock_cols = [c for c in alloc_df.columns if c not in etf_and_cash]

    plot_df = pd.DataFrame(index=alloc_df.index)
    plot_df["Cash"] = alloc_df.get("Cash", 0.0)
    plot_df["QQQ"] = alloc_df.get("QQQ", 0.0)
    plot_df["SOXX"] = alloc_df.get("SOXX", 0.0)
    if stock_cols:
        plot_df["Turnaround Stocks"] = alloc_df[stock_cols].sum(axis=1)
    else:
        plot_df["Turnaround Stocks"] = 0.0

    palette = {
        "Cash": "rgba(158, 158, 158, 0.7)",
        "QQQ": "rgba(255, 145, 0, 0.7)",
        "SOXX": "rgba(170, 0, 255, 0.7)",
        "Turnaround Stocks": "rgba(0, 200, 83, 0.7)",
    }

    # Stack in order: Cash at bottom, then QQQ, SOXX, Turnaround Stocks on top
    for col in ["Cash", "QQQ", "SOXX", "Turnaround Stocks"]:
        if col in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df.index,
                    y=plot_df[col] * 100.0,
                    mode="lines",
                    name=col,
                    stackgroup="one",
                    fillcolor=palette.get(col, "rgba(41, 121, 255, 0.5)"),
                    line=dict(width=0.5, color="rgba(255, 255, 255, 0.3)"),
                    hovertemplate=f"<b>{col}</b>: %{{y:.1f}}%<extra></extra>",
                )
            )

    fig.update_layout(
        title="Dynamic Asset Allocation Over Time (100% Stacked)",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(18, 22, 34, 0.8)",
        margin=dict(l=60, r=30, t=50, b=40),
        yaxis=dict(
            title="Portfolio Weight (%)",
            range=[0, 100],
            gridcolor="rgba(255, 255, 255, 0.08)",
        ),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        height=450,
    )
    return fig


def create_monthly_return_heatmap(nav_series: pd.Series) -> go.Figure:
    """
    Renders a 2D Heatmap of Monthly Returns (Jan-Dec vs 2001-2026).
    """
    if nav_series.empty or len(nav_series) < 30:
        return go.Figure()

    # Resample to monthly end values
    monthly_nav = nav_series.resample("ME").last()
    monthly_ret = monthly_nav.pct_change() * 100.0

    # Build matrix: Years (Rows) x Months (Cols)
    df_m = pd.DataFrame({"Return": monthly_ret})
    df_m["Year"] = df_m.index.year
    df_m["Month"] = df_m.index.month

    pivot = df_m.pivot(index="Year", columns="Month", values="Return")
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Reindex columns 1..12
    for m in range(1, 13):
        if m not in pivot.columns:
            pivot[m] = np.nan
    pivot = pivot.sort_index(ascending=False)[list(range(1, 13))]
    pivot.columns = month_names

    z_vals = pivot.values
    y_vals = [str(y) for y in pivot.index]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=month_names,
            y=y_vals,
            colorscale="RdYlGn",
            zmid=0.0,
            text=np.where(np.isnan(z_vals), "", np.vectorize(lambda v: f"{v:+.1f}%" if not np.isnan(v) else "")(z_vals)),
            texttemplate="%{text}",
            textfont=dict(size=10),
            colorbar=dict(title="Return (%)"),
            hoverongaps=False,
            hovertemplate="Year: %{y}<br>Month: %{x}<br>Return: %{z:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="Monthly Returns Matrix (%)",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(18, 22, 34, 0.8)",
        margin=dict(l=60, r=30, t=50, b=40),
        xaxis=dict(title="Month", tickmode="array", tickvals=month_names),
        yaxis=dict(title="Year", autorange="reversed"),
        height=max(450, len(pivot) * 22),
    )
    return fig


def create_annual_comparison_bar_chart(annual_df: pd.DataFrame) -> go.Figure:
    """
    Creates a grouped bar chart comparing Annual Returns across strategies.
    """
    fig = go.Figure()

    if annual_df.empty or "Year" not in annual_df.columns:
        return fig

    years = annual_df["Year"].tolist()

    traces = [
        ("Enhanced Strategy (AR-DM)", "Enhanced_Return", "#00C853"),
        ("Base Strategy", "Base_Return", "#2979FF"),
        ("QQQ Benchmark", "QQQ_Return", "#FF9100"),
        ("SOXX Benchmark", "SOXX_Return", "#AA00FF"),
    ]

    for label, col, color in traces:
        if col in annual_df.columns:
            vals = (annual_df[col] * 100.0).tolist()
            fig.add_trace(
                go.Bar(
                    x=years,
                    y=vals,
                    name=label,
                    marker_color=color,
                    hovertemplate=f"<b>{label}</b><br>Year: %{{x}}<br>Return: %{{y:+.1f}}%<extra></extra>",
                )
            )

    fig.update_layout(
        title="Calendar Year Returns Comparison (2001-2026)",
        barmode="group",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(18, 22, 34, 0.8)",
        margin=dict(l=60, r=30, t=50, b=40),
        yaxis=dict(
            title="Annual Return (%)",
            gridcolor="rgba(255, 255, 255, 0.08)",
        ),
        xaxis=dict(
            title="Calendar Year",
            tickmode="array",
            tickvals=years,
            gridcolor="rgba(255, 255, 255, 0.08)",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        height=480,
    )
    return fig
