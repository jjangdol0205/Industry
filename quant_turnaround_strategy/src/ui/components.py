"""
UI Components and Visual Helpers for Streamlit Dashboard.
Provides KPI cards, styled badges, formatters for dual-currency (USD/KRW),
and theme styling.
"""
from typing import Optional, Union, Dict, Any
import streamlit as st


CUSTOM_CSS = """
<style>
    /* Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 200, 83, 0.5);
    }
    .metric-label {
        font-size: 0.85rem;
        color: #9e9e9e;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #f5f5f5;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.8rem;
        margin-top: 6px;
        font-weight: 500;
    }
    .metric-sub-pos { color: #00c853; }
    .metric-sub-neg { color: #ff5252; }
    .metric-sub-neutral { color: #78909c; }

    /* Action Badges */
    .badge-buy {
        background-color: rgba(0, 200, 83, 0.15);
        color: #00c853;
        border: 1px solid #00c853;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-sell {
        background-color: rgba(255, 82, 82, 0.15);
        color: #ff5252;
        border: 1px solid #ff5252;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-rebalance {
        background-color: rgba(41, 121, 255, 0.15);
        color: #2979ff;
        border: 1px solid #2979ff;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-crisis {
        background-color: rgba(255, 145, 0, 0.2);
        color: #ff9100;
        border: 1px solid #ff9100;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.75rem;
    }

    /* Rationale Card */
    .rationale-box {
        background: rgba(30, 34, 45, 0.7);
        border-left: 4px solid #2979ff;
        border-radius: 4px;
        padding: 14px 18px;
        margin: 10px 0;
    }
</style>
"""


def apply_custom_css():
    """Injects custom CSS styles into Streamlit page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def fmt_currency(value: Union[float, int], currency: str = "USD") -> str:
    """Formats numeric money values according to currency (USD $ or KRW ₩)."""
    if value is None or (isinstance(value, float) and (value != value)):  # NaN check
        return "-"
    if currency == "KRW":
        if abs(value) >= 100_000_000:
            eok = value / 100_000_000
            return f"₩{eok:,.2f}억"
        return f"₩{int(round(value)):,}"
    else:
        return f"${value:,.2f}" if abs(value) < 1_000_000 else f"${value:,.0f}"


def fmt_pct(value: Union[float, int], show_plus: bool = True, decimals: int = 1) -> str:
    """Formats decimal return/ratio to percentage string (e.g. +14.2%)."""
    if value is None or (isinstance(value, float) and (value != value)):
        return "-"
    pct = value * 100.0
    if show_plus and pct > 0:
        return f"+{pct:.{decimals}f}%"
    return f"{pct:.{decimals}f}%"


def fmt_ratio(value: Union[float, int], decimals: int = 2) -> str:
    """Formats dimensionless ratio (e.g. 0.43)."""
    if value is None or (isinstance(value, float) and (value != value)):
        return "-"
    return f"{value:.{decimals}f}"


def render_metric_card(
    label: str,
    value_str: str,
    sub_str: Optional[str] = None,
    sub_type: str = "neutral",  # "pos", "neg", "neutral"
):
    """Renders a modern, responsive HTML metric card."""
    sub_class = f"metric-sub-{sub_type}"
    sub_html = f'<div class="metric-sub {sub_class}">{sub_str}</div>' if sub_str else ""
    html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value_str}</div>
        {sub_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
