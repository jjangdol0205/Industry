"""
UI Package for Quantitative Turnaround Strategy Streamlit Dashboard.
"""
from src.ui.components import apply_custom_css, render_metric_card, fmt_currency, fmt_pct, fmt_ratio
from src.ui.charts import (
    create_cumulative_and_underwater_chart,
    create_allocation_area_chart,
    create_monthly_return_heatmap,
    create_annual_comparison_bar_chart,
)
from src.ui.overview_tab import render_overview_tab
from src.ui.calendar_tab import render_calendar_tab
from src.ui.allocation_tab import render_allocation_tab
from src.ui.trade_log_tab import render_trade_log_tab
from src.ui.simulation_tab import render_simulation_tab

__all__ = [
    "apply_custom_css",
    "render_metric_card",
    "fmt_currency",
    "fmt_pct",
    "fmt_ratio",
    "create_cumulative_and_underwater_chart",
    "create_allocation_area_chart",
    "create_monthly_return_heatmap",
    "create_annual_comparison_bar_chart",
    "render_overview_tab",
    "render_calendar_tab",
    "render_allocation_tab",
    "render_trade_log_tab",
    "render_simulation_tab",
]
