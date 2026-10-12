"""
Quantitative Turnaround Strategy System (2001-Present)
Interactive Streamlit Web Dashboard

Features:
- Dual-Currency accounting: USD ($) and KRW (₩) using daily USDKRW=X feed.
- Tax Mode toggle: Net After-Tax (22% Korean overseas capital gains tax with 2.5M KRW deduction) vs Gross Pre-Tax.
- 5 Responsive Tabs:
    1. Cumulative Performance & Underwater Drawdown Plotly curves (Base vs Enhanced vs QQQ vs SOXX).
    2. Calendar Year Breakdown (2001-2026) Table with crisis year alerts (2002, 2008, 2022).
    3. Dynamic Asset Allocation & Heatmaps (100% stacked area chart & monthly returns).
    4. Trade Log & Turnaround Selection Decisions (Filterable journal & PIT SEC rationale).
    5. Live Simulation Lab & Parameter Tuning (On-demand custom parameter walk-forward backtest).
- High Performance: Fast loading powered by @st.cache_data.
"""
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
import streamlit as st

from config.settings import CACHE_DIR, DEFAULT_START_DATE
from src.data.cache_store import CacheStore
from src.data.price_feed import PriceFeed
from src.engine.backtester import BacktestEngine, BacktestResult
from src.strategies.base_strategy import BaseStrategy
from src.strategies.enhanced_strategy import EnhancedStrategy
from src.engine.metrics import PerformanceMetrics
from src.ui.components import apply_custom_css
from src.ui.overview_tab import render_overview_tab
from src.ui.calendar_tab import render_calendar_tab
from src.ui.allocation_tab import render_allocation_tab
from src.ui.trade_log_tab import render_trade_log_tab
from src.ui.simulation_tab import render_simulation_tab


# Page Configuration
st.set_page_config(
    page_title="Quant Turnaround Strategy System (2001-Present)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply CSS
apply_custom_css()


@st.cache_data(ttl=3600, show_spinner=False)
def load_market_data():
    """Loads benchmark prices and USD/KRW FX rates from persistent cache."""
    cs = CacheStore(CACHE_DIR)
    pf = PriceFeed(cache_store=cs)
    prices_df = pf.fetch_and_bridge_benchmarks(start_date=DEFAULT_START_DATE)

    fx_df = cs.load_parquet("fx_rates.parquet")
    if fx_df is not None and not fx_df.empty:
        fx_series = fx_df["USDKRW"] if "USDKRW" in fx_df.columns else fx_df.iloc[:, 0]
    else:
        # Fallback default FX
        fx_series = pd.Series(1300.0, index=prices_df.index)

    return prices_df, fx_series


@st.cache_data(ttl=3600, show_spinner=False)
def run_baseline_simulations():
    """Runs Base Strategy and Enhanced Strategy (AR-DM) and caches BacktestResults."""
    prices_df, fx_series = load_market_data()

    # 1. Base Strategy
    engine_base = BacktestEngine(initial_capital=100_000.0)
    strat_base = BaseStrategy()
    res_base = engine_base.run(
        strategy=strat_base,
        prices_df=prices_df,
        fx_rates=fx_series,
        tax_enabled=True,
        start_date=DEFAULT_START_DATE,
    )

    # 2. Enhanced Strategy (AR-DM)
    engine_enh = BacktestEngine(initial_capital=100_000.0)
    strat_enh = EnhancedStrategy(prices_df=prices_df)
    res_enh = engine_enh.run(
        strategy=strat_enh,
        prices_df=prices_df,
        fx_rates=fx_series,
        tax_enabled=True,
        start_date=DEFAULT_START_DATE,
    )

    # 3. Benchmarks (QQQ & SOXX)
    sim_idx = res_enh.daily_nav_usd.index
    qqq_close = prices_df[("Close", "QQQ")].reindex(sim_idx).ffill()
    soxx_close = prices_df[("Close", "SOXX")].reindex(sim_idx).ffill()
    fx_reindexed = fx_series.reindex(sim_idx).ffill()

    qqq_nav_usd = 100_000.0 * (qqq_close / qqq_close.iloc[0])
    soxx_nav_usd = 100_000.0 * (soxx_close / soxx_close.iloc[0])

    init_fx = float(fx_reindexed.iloc[0])
    qqq_nav_krw = (100_000.0 * init_fx) * (qqq_close / qqq_close.iloc[0]) * (fx_reindexed / init_fx)
    soxx_nav_krw = (100_000.0 * init_fx) * (soxx_close / soxx_close.iloc[0]) * (fx_reindexed / init_fx)

    return {
        "prices": prices_df,
        "fx_series": fx_series,
        "res_base": res_base,
        "res_enh": res_enh,
        "qqq_nav_usd": qqq_nav_usd,
        "soxx_nav_usd": soxx_nav_usd,
        "qqq_nav_krw": qqq_nav_krw,
        "soxx_nav_krw": soxx_nav_krw,
    }


def main():
    # Load cached simulation data
    with st.spinner("Loading quantitative strategy models & benchmark data..."):
        sim_data = run_baseline_simulations()

    # Sidebar Controls: Currency & Taxation
    st.sidebar.image("https://img.icons8.com/fluency/96/bullish.png", width=64)
    st.sidebar.title("Configuration & Toggles")
    st.sidebar.markdown("---")

    st.sidebar.markdown("### 💱 Dual-Currency Setting")
    currency_choice = st.sidebar.radio(
        "Display Currency",
        ["USD ($)", "KRW (₩)"],
        index=0,
        help="Dynamically switches all portfolio NAV curves, trade logs, and performance metrics.",
    )
    currency = "KRW" if "KRW" in currency_choice else "USD"

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏛️ Tax Accounting Mode")
    tax_choice = st.sidebar.radio(
        "Tax Mode",
        ["Net After-Tax & Costs", "Gross Pre-Tax"],
        index=0,
        help="Net After-Tax incorporates Korean overseas capital gains tax (22% with 2.5M KRW basic deduction).",
    )
    tax_mode = "Net After-Tax" if "Net" in tax_choice else "Gross Pre-Tax"

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Strategy Specifications")
    st.sidebar.info(
        """
        - **Timeline**: 2001-07-10 to Present
        - **Anchors**: QQQ (40%) + SOXX (30%)
        - **Turnaround Stocks**: 0 to 3 capacity
        - **Regime Defense**: 200-day Trend Filter
        - **Momentum Tilt**: Dual-Momentum
        - **Real Costs**: 5 bps comm + 2-10 bps slip
        """
    )

    # Main Application Header
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <div style="font-size: 2.2rem; font-weight: 800; color: #f5f5f5; letter-spacing: -0.02em;">
                📈 Quantitative Turnaround Strategy System
            </div>
            <div style="font-size: 1.05rem; color: #b0bec5; margin-top: 4px;">
                Institutional Algorithmic Trading & Asset Allocation Platform (July 10, 2001 – Present)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Package simulation data dictionary for the active currency
    active_sim_data = {
        "prices": sim_data["prices"],
        "fx_series": sim_data["fx_series"],
        "res_base": sim_data["res_base"],
        "res_enh": sim_data["res_enh"],
        "qqq_nav": sim_data["qqq_nav_krw"] if currency == "KRW" else sim_data["qqq_nav_usd"],
        "soxx_nav": sim_data["soxx_nav_krw"] if currency == "KRW" else sim_data["soxx_nav_usd"],
    }
    if "res_custom" in st.session_state:
        active_sim_data["res_custom"] = st.session_state["res_custom"]

    # 5 Responsive Core Tabs
    tab_overview, tab_calendar, tab_allocation, tab_trades, tab_simulation = st.tabs([
        "📈 Cumulative Performance & Overview",
        "📅 Calendar Year Breakdown (2001-2026)",
        "📊 Dynamic Asset Allocation & Heatmaps",
        "📜 Trade Log & Turnaround Decisions",
        "🧪 Live Simulation Lab & Tuning",
    ])

    with tab_overview:
        render_overview_tab(active_sim_data, currency=currency, tax_mode=tax_mode)

    with tab_calendar:
        render_calendar_tab(active_sim_data, currency=currency, tax_mode=tax_mode)

    with tab_allocation:
        render_allocation_tab(active_sim_data, currency=currency, tax_mode=tax_mode)

    with tab_trades:
        render_trade_log_tab(active_sim_data, currency=currency, tax_mode=tax_mode)

    with tab_simulation:
        render_simulation_tab(active_sim_data, currency=currency, tax_mode=tax_mode)


if __name__ == "__main__":
    main()
