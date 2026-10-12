# Project: Tri-Asset ETF Portfolio Optimization & Streamlit Tab 6 (Round 7)

## Architecture
- **Host System**: `D:\Industry\quant_turnaround_strategy` in repository `https://github.com/jjangdol0205/Industry` (branch `main`).
- **Core Technology Stack**: Python 3.14.2, Streamlit 1.65.0, Plotly 7.1.0, NumPy 2.5.0, Pandas 3.0.3, PyArrow 25.0.1, Pytest 9.1.1. (Pure vectorized NumPy/Pandas, zero dependency on SciPy).
- **Subsystem Partitioning**:
  1. `src/data/tri_asset_loader.py`: Ingestion & caching of SPY, QQQ, SOXX (with 2001-07-10 ^SOX bridge) and USDKRW FX rates from 2001-07-10 to present.
  2. `src/optimizer/tri_asset_simplex.py`: Vectorized 5,151 weight triplet simplex evaluation ($w_{\text{SPY}} + w_{\text{QQQ}} + w_{\text{SOXX}} = 1.0, w_i \ge 0$), periodic rebalancing (Quarterly, Annual, Monthly), friction modeling (0.05% commission + 0.02% slippage = 0.07%), and dual-currency (USD/KRW) NAV generation.
  3. `src/optimizer/tri_asset_optimizer.py`: Calendar year intra-year MDD (2001–2026), CAGR, Sharpe Ratio, Calmar Ratio ($\text{CAGR} / \max_Y |\text{Annual MDD}_Y|$), 4-Tier constrained-MDD optimization, and crisis stress testing (2001-2003, 2008, 2020, 2022).
  4. `src/ui/tri_asset_tab.py`: Dedicated 6th tab implementation featuring Plotly ternary contour/risk-return frontier, 4-tier cards, calendar performance matrix, interactive slider, and USD/KRW toggle.
  5. `app.py`: Integrated 6-tab Streamlit dashboard.
  6. `tests/test_tri_asset_optimizer.py` & `verify_tri_asset.py`: Automated multi-tier verification test suite.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Tri-Asset Historical Data Ingestion | SPY, QQQ, SOXX total return series from 2001-07-10 to present + USDKRW daily FX rates cached in parquet | M1 | R1 |
| F2 | Simplex Grid Combinatorics | Exact 5,151 weight triplets ($w_{\text{SPY}} + w_{\text{QQQ}} + w_{\text{SOXX}} = 1.0, w_i \ge 0$) at 1% step | M1 | R1 |
| F3 | Multi-Frequency Periodic Rebalancing | Quarterly, Annual, Monthly rebalancing with portfolio weight reset | M1 | R1 |
| F4 | Real-World Transaction Friction | 0.05% brokerage commission + 0.02% slippage (7 bps total) applied on rebalance turnover | M1 | R1 |
| F5 | Dual-Currency Performance Engine | USD base tracking and daily/rebalance KRW conversion with FX impact tracking | M1 | R1 |
| F6 | Calendar Year Intra-Year MDD Matrix | Institutional calendar year MDD computation for each year 2001-2026 | M2 | R2 |
| F7 | Institutional Performance Metrics | CAGR, Sharpe Ratio (annualized), and Calmar Ratio ($\text{CAGR} / \max_Y |\text{Annual MDD}_Y|$) | M2 | R2 |
| F8 | 4-Tier Constrained-MDD Optimization | Tier 1 (<=20% MDD), Tier 2 (<=30% MDD), Tier 3 (<=40% MDD), Tier 4 (Unconstrained Max Calmar) | M2 | R2 |
| F9 | Crisis Resilience Stress Breakdown | Empirical drawdowns and returns during 2001-2003 (Dot-com), 2008 (GFC), 2020 (COVID), 2022 (Tech Bear) | M2 | R2 |
| F10 | Streamlit Tab 6 Registration | Add 6th tab "🏆 3대 ETF 최적 비중 분석 (Tri-Asset Optimizer)" to app.py | M3 | R3 |
| F11 | Ternary & Pareto Frontier Visualizations | Interactive Plotly ternary contour and risk-return Pareto frontier (CAGR vs Worst Annual MDD) | M3 | R3 |
| F12 | 4-Tier Summary Cards & Year Matrix Table | HTML/CSS KPI cards and calendar year returns/drawdown matrix table | M3 | R3 |
| F13 | Interactive Weight Slider | Custom user experimentation slider with instant reactive metric updates | M3 | R3 |
| F14 | Currency Toggle (USD ↔ KRW) | Dynamic currency switcher updating all metrics, tables, and charts | M3 | R3 |
| F15 | Automated Verification Test Suite | Multi-tier test suite validating data integrity, math precision, and 100% test pass | M4 | R3 |
| F16 | Streamlit Headless AppTest Verification | AppTest validating 6 tabs, Tab 6 widgets, and zero UI regressions | M4 | R3 |
| F17 | Clean Git Commit & GitHub Push | Git add, commit, and push to https://github.com/jjangdol0205/Industry (main branch) | M5 | R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Data Ingestion & Simplex Grid Engine | F1, F2, F3, F4, F5 | none | DONE |
| M2 | 4-Tier Optimization & Crisis Engine | F6, F7, F8, F9 | M1 | DONE |
| M3 | Streamlit Tab 6 Interactive UI | F10, F11, F12, F13, F14 | M2 | DONE |
| M4 | E2E Verification & Hardening | F15, F16 | M3 | DONE |
| M5 | Git Commit & GitHub Deployment | F17 | M4 | DONE |

## Interface Contracts

### `src/data/tri_asset_loader.py`
- `load_tri_asset_data(cache_dir: str = "data/cache") -> Tuple[pd.DataFrame, pd.DataFrame]`
  - Returns `(prices_df, fx_df)` where `prices_df` has columns `['SPY', 'QQQ', 'SOXX']` starting strictly from `2001-07-10` with 0 NaNs.
  - `fx_df` has column `['USDKRW']` aligned on trading days.

### `src/optimizer/tri_asset_simplex.py`
- `generate_simplex_grid(step: float = 0.01) -> np.ndarray`
  - Returns `(5151, 3)` matrix of weights summing to 1.0.
- `simulate_simplex_grid(prices_df: pd.DataFrame, fx_df: pd.DataFrame, weights: np.ndarray, rebalance_freq: str = 'Q', commission_bps: float = 5.0, slippage_bps: float = 2.0, currency: str = 'USD') -> SimplexGridResult`
  - Evaluates all 5,151 weights vectorized in $< 1.0$ second.

### `src/optimizer/tri_asset_optimizer.py`
- `optimize_risk_tiers(grid_result: SimplexGridResult) -> Dict[str, TierAllocationResult]`
  - Returns results for `Tier 1 (<=20% MDD)`, `Tier 2 (<=30% MDD)`, `Tier 3 (<=40% MDD)`, and `Tier 4 (Unconstrained Max Calmar)`.
- `calculate_crisis_stress(prices_df: pd.DataFrame, tier_weights: Dict[str, np.ndarray]) -> pd.DataFrame`
  - Returns drawdown and return table for 2001-2003, 2008, 2020, and 2022.

### `src/ui/tri_asset_tab.py`
- `render_tri_asset_tab(prices_df: pd.DataFrame, fx_df: pd.DataFrame, currency: str = 'USD') -> None`
  - Renders all Tab 6 visual components in Streamlit.

## Code Layout
- `D:\Industry\quant_turnaround_strategy\src\data\tri_asset_loader.py`
- `D:\Industry\quant_turnaround_strategy\src\optimizer\tri_asset_simplex.py`
- `D:\Industry\quant_turnaround_strategy\src\optimizer\tri_asset_optimizer.py`
- `D:\Industry\quant_turnaround_strategy\src\ui\tri_asset_tab.py`
- `D:\Industry\quant_turnaround_strategy\app.py`
- `D:\Industry\quant_turnaround_strategy\tests\test_tri_asset_optimizer.py`
- `D:\Industry\quant_turnaround_strategy\verify_tri_asset.py`
