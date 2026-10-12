# Project: Quantitative Turnaround Strategy System

Target Project Directory: `D:\Industry\quant_turnaround_strategy`
Authoritative Specification: `d:\Industry\.agents\teamwork\ORIGINAL_REQUEST.md` (§ 2026-10-12T12:49:12Z)

## Architecture

The Quantitative Turnaround Strategy System is a production-ready, modular quantitative research and algorithmic trading platform that simulates and optimizes an investment strategy combining QQQ, SOXX, and opportunistic 52-week-low turnaround stocks from July 10, 2001 to the present.

```
+---------------------------------------------------------------------------------------------------+
|                        QUANTITATIVE TURNAROUND STRATEGY SYSTEM ARCHITECTURE                       |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [ Data Pipeline ] ---> [ Strategy & Backtest Engine ] ---> [ Enhanced Strategy / Regime Filter ] |
|  - QQQ & SOXX from 2001    - Base: QQQ + SOXX + Turnaround   - Trend SMA + Vol-Target + Momentum  |
|  - 52w-Low screener        - Weekly Rebalancing (0-3 stocks) - Calmar / Annual MDD Optimization   |
|  - Zero Lookahead Bias     - Risk Manager (Stop/Take-Profit)                                      |
|            |                                |                                   |                 |
|            +--------------------------------+-----------------------------------+                 |
|                                             |                                                     |
|                                             v                                                     |
|                   +---------------------------------------------------+                           |
|                   |  STREAMLIT INTERACTIVE DASHBOARD (app.py)         |                           |
|                   |  -----------------------------------------------  |                           |
|                   |  - Tab 1: Cumulative Performance & Drawdown Curve |                           |
|                   |  - Tab 2: Calendar Year Breakdown (2001-2026)     |                           |
|                   |  - Tab 3: Dynamic Asset Allocation & Heatmaps     |                           |
|                   |  - Tab 4: Trade Log & Weekly Turnaround Decisions |                           |
|                   |  - Tab 5: Live Simulation Lab & Parameter Sidebar |                           |
|                   +---------------------------------------------------+                           |
|                                             |                                                     |
|            +--------------------------------+--------------------------------+                    |
|            v                                                                 v                    |
|  +-------------------------------------+                  +------------------------------------+  |
|  | AUTOMATED VERIFICATION SCRIPT       |                  | 4-TIER E2E TEST TRACK              |  |
|  | verify_system.py (5 Core Gates)     |                  | (pytest tests/)                    |  |
|  | 1. Data Bounds (2001-07-10 to now)  |                  | - Tier 1: Feature Coverage         |  |
|  | 2. Zero Lookahead Bias Audit        |                  | - Tier 2: Boundary & Corner Cases  |  |
|  | 3. Calendar Annual MDD & Calmar Math|                  | - Tier 3: Parameter Combinations   |  |
|  | 4. Strategy Comparison Metrics      |                  | - Tier 4: Historical Stress Regimes|  |
|  | 5. Streamlit Syntax & Dry-run Smoke |                  +------------------------------------+  |
|  +-------------------------------------+                                                          |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

## Feature Inventory

Every feature identified during the Phase 0 Survey is inventoried below with its assigned milestone:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Ingest QQQ & SOXX Daily Feeds | Daily adjusted price feeds from July 10, 2001 to present with split/dividend total return handling and July 10-12 launch bridge. | M1 | Survey 1 |
| F2 | Survivorship-Bias-Free Universe | Point-in-Time S&P 500 & NASDAQ 100 historical constituent intervals (1,262+ tickers) eliminating survivor bias. | M1 | Survey 1 |
| F3 | 52-Week Low Rolling Screener | Rolling 252-day low calculation, weekly schedule, and anti-falling-knife price stabilization filters. | M1 | Survey 1 |
| F4 | Point-in-Time Turnaround Screener | 4-pillar proxy scoring (Rev inflection, EBIT margin expansion, solvency runway, valuation) with strict 45d/90d SEC filing lag. | M1 | Survey 1 |
| F5 | Weekly Candidate Evaluation Logic | Portfolio capacity 0-3 individual stocks, select at most 1 stock per week, discretionary inclusion/exclusion gates. | M1 | Survey 1 |
| F6 | Modular Multi-Asset Backtest Simulator | Dynamic asset allocation (QQQ, SOXX, 0-3 stocks, Cash), weekly rebalance schedule, idle cash policies, transaction friction. | M2 | Survey 2 |
| F7 | Intra-Week Risk Management | Daily exit monitoring (hard stop-loss, profit-taking, trailing stop, max holding duration time stop). | M2 | Survey 2 |
| F8 | Annual MDD & Calmar/MAR Metrics Engine | Calendar year intra-year MDD (2001 to present), rolling 1-year MDD, and Calmar ratio `CAGR / max(Annual_MDD)` objective function. | M2 | Survey 2 |
| F9 | Systematic Optimization Engine | Multidimensional parameter grid search and 20-period Walk-Forward Analysis (5y IS / 1y OOS) with Walk-Forward Efficiency (WFE). | M2 | Survey 2 |
| F10 | Enhanced Alternative Strategy (AR-DM) | Adaptive Regime-Switching Dual-Momentum with 200-day trend gate, relative strength tilt, and asymmetric profit ratchet. | M3 | Survey 2 |
| F11 | Automated Verification Script | `verify_system.py` CLI implementing 5 strict programmatic validation gates (data bounds, lookahead audit, math, metrics, UI). | M3 | Survey 3 |
| F12 | Interactive Streamlit Dashboard | 5-tab web dashboard in `app.py`: Cumulative Curves, Calendar Breakdown Table, Stacked Allocation & Heatmaps, Trade Log, Live Lab. | M4 | Survey 3 |
| F13 | Git Scaffolding & Deployment Setup | Scaffolding in `D:\Industry\quant_turnaround_strategy`, 6 atomic commits, .gitignore, requirements.txt, bilingual README, launchers. | M4 | Survey 3 |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Data Pipeline & Lookahead-Free Turnaround Screener | Ingestion of QQQ/SOXX (2001-07-10 to present), PIT universe (1,262 tickers), rolling 252-day low, SEC 45/90d filing lag turnaround score, weekly candidate selection (0-3 capacity). | none | DONE |
| M2 | Modular Backtester & Parameter Optimization Engine | Modular multi-asset backtester, weekly rebalancer, daily exit triggers, calendar year MDD & Calmar metrics, multidimensional grid search & Walk-Forward Analysis. | M1 | DONE |
| M3 | Enhanced Alternative Strategy & Verification Script | Adaptive Regime-Switching Dual-Momentum (AR-DM) formulation, comparative empirical backtest, and `verify_system.py` automated verification script. | M2 | DONE |
| M4 | Interactive Streamlit Dashboard & Git Deployment | 5-Tab Streamlit application (`app.py`), Plotly financial charts, live simulation controls, Git initialization, atomic commit history, and deployment launchers. | M3 | IN_PROGRESS |
| E2E | E2E Testing Track (Tiers 1-4) | Comprehensive opaque-box test suite across Feature Coverage, Boundary Cases, Parameter Combinations, and Historical Stress Regimes. | none | DONE |
| FINAL | Final Verification & Hardening | 100% E2E test suite pass, Tier 5 adversarial coverage hardening, Forensic Auditor integrity check, final handoff to Sentinel. | M4, E2E | PLANNED |

## Interface Contracts

### Data Pipeline ↔ Backtest Engine
- Input: `start_date="2001-07-10"`, `end_date=None`
- Outputs:
  - `get_benchmark_prices() -> pd.DataFrame` (MultiIndex columns `[Close, High, Low, Open, Volume]` for `['QQQ', 'SOXX']`)
  - `screen_weekly_candidates(as_of_date: date, current_holdings: List[str], max_capacity: int = 3) -> WeeklySelectionResult`
  - `WeeklySelectionResult`: attributes `decision_date`, `selected_ticker`, `portfolio_held_count` (0-3), `action` (`BUY`, `HOLD_CAPACITY_FULL`, `NO_QUALIFIED_CANDIDATE`), `rationale`

### Backtest Engine ↔ Metrics & Optimizer
- Input: `strategy: BaseStrategy`, `prices_df: pd.DataFrame`, `signals_df: pd.DataFrame`
- Output: `BacktestResult`:
  - `daily_nav: pd.Series`
  - `trade_log: pd.DataFrame`
  - `allocations: pd.DataFrame`
  - `annual_metrics: pd.DataFrame` with columns `['Year', 'Annual_Return', 'Annual_MDD', 'Return_to_MDD']`
  - `calmar_ratio: float = cagr / abs(max_annual_mdd)`

### Strategy & Engine ↔ Streamlit UI
- `app.py` imports pre-computed or dynamically runs:
  - `run_simulation(config: StrategyConfig) -> BacktestResult`
  - Visual output interfaces: Plotly figures for cumulative curves, drawdowns, allocation area charts, annual bar comparisons.

## Code Layout (`D:\Industry\quant_turnaround_strategy`)

```
quant_turnaround_strategy/
├── .git/
├── .gitignore
├── requirements.txt
├── README.md
├── PROJECT.md
├── verify_system.py
├── run_app.bat
├── run_app.ps1
├── app.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── universe_metadata.json
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── price_feed.py
│   │   ├── universe.py
│   │   ├── screener_52w.py
│   │   └── pit_turnaround.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── backtester.py
│   │   ├── portfolio.py
│   │   ├── execution.py
│   │   └── metrics.py
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base_strategy.py
│   │   └── enhanced_strategy.py
│   ├── optimizer/
│   │   ├── __init__.py
│   │   ├── grid_search.py
│   │   └── walk_forward.py
│   └── ui/
│       ├── __init__.py
│       ├── components.py
│       ├── charts.py
│       └── tabs/
│           ├── tab_overview.py
│           ├── tab_calendar.py
│           ├── tab_allocation.py
│           ├── tab_trades.py
│           └── tab_simulation.py
├── data/
│   ├── cache/
│   └── seed/
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── tier1_feature_coverage/
    ├── tier2_boundary_corner/
    ├── tier3_combinations/
    └── tier4_real_world_scenarios/
```
