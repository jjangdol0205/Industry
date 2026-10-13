# Project: Round 8 — Real Investment & SK Square Strategy

## Master Architecture
The project delivers an institutional-grade real-world investment framework comprising:
1. **Core ETF Allocation Engine**: Vectorized 1D grid search (101 points) optimizing QQQ vs. SOXX weights, sensitivity analysis, crisis drawdowns, Year-End vs. Year-Beginning after-tax study, and alternative high-yield ETF comparisons (SMH, XLK, QLD, TQQQ, SOXL).
2. **Hybrid 4-Asset Turnaround Engine**: Integrates QQQ, SOXX, and up to 2 individual 52-week-low turnaround stocks with daily -10% hard stop-loss, realistic slippage/gap-down handling, T+1 auto-replacement, +25% partial profit-taking (50%), SEC/FINRA fees, trade-by-trade FIFO capital gains, and annual Korean overseas stock tax modeling.
3. **SK Square Valuation & Executive Action Playbook**: Fundamental SOTP valuation (20.07% SK Hynix + unlisted assets + cash), NAV discount barometer, Corporate Value-Up assessment, and an actionable Day-1 execution playbook for the user's 76-share position.
4. **Streamlit Interactive Diagnosis Tab**: Dedicated view in `app.py` ("🎯 실전 투자 포트폴리오 & SK스퀘어 진단 (Real Investment & SK Square)") with full visualizations, interactive toggles, trade logs, and checklists.
5. **E2E Testing Suite**: Opaque-box requirement-driven 4-tier test suite validating 100% functional and mathematical integrity.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1.1 QQQ vs SOXX 1D Grid Search | 101 allocations (0% to 100% in 1%), 0.07% friction, Calmar/Sharpe/Return peak derivation in USD and KRW | M1 | ORIGINAL_REQUEST § R1 |
| 2 | F1.2 Sensitivity & Crisis Stress Tabulation | Weight sensitivity tables & annual drawdowns during 2002, 2008, 2020, 2022 | M1 | ORIGINAL_REQUEST § R1 |
| 3 | F1.3 Year-End vs Year-Beginning Tax Study | 2.5M KRW deduction, tax-loss harvesting vs tax deferral, net after-tax NAV, total taxes, after-tax CAGR/MDD/Calmar | M1 | ORIGINAL_REQUEST § 07:08:47Z |
| 4 | F1.4 Higher-Yield Alternative ETF Pairs | Comparative matrix of SMH vs SOXX, XLK/VGT vs QQQ, 2x QLD+USD, 3x TQQQ+SOXL to find top risk-adjusted returns | M1 | ORIGINAL_REQUEST § 07:09:37Z |
| 5 | F2.1 PIT Turnaround Screening Queue | Point-in-time 52w rolling low screening with 4-pillar proxy scoring (SEC 45d/90d lags) and dynamic ranked candidate queue | M2 | ORIGINAL_REQUEST § R2 |
| 6 | F2.2 4-Asset Backtesting Engine | Multi-asset portfolio simulating QQQ, SOXX, and up to 2 turnaround stocks (w_Stocks in [0%, 30%]) | M2 | ORIGINAL_REQUEST § R2 |
| 7 | F2.3 Strict Daily -10% Stop & Auto-Replacement | Daily close -10% hard stop with 10-15 bps slippage / gap-down fill, next-day auto-replacement with next qualified candidate | M2 | ORIGINAL_REQUEST § R2 & 07:11:02Z |
| 8 | F2.4 Partial Profit-Taking (+25% gain) | 50% partial exit at +25% gain, remaining 50% held until annual rebalance or stop trigger | M2 | ORIGINAL_REQUEST § R2 |
| 9 | F2.5 Real-World Execution Frictions | Brokerage commissions (5-8 bps), ETF slippage (2 bps), Stock slippage (10-15 bps), SEC Section 31 & FINRA TAF fees | M2 | ORIGINAL_REQUEST § 07:11:02Z |
| 10 | F2.6 FIFO Capital Gains & Tax Engine | Trade-by-trade FIFO lot tracking, annual 2.5M KRW deduction, 22% tax deduction at year-end, T+1 cash settlement | M2 | ORIGINAL_REQUEST § 07:11:02Z |
| 11 | F2.7 Friction Drag & Turnover Analysis | Annual turnover rate (%), total transaction costs, total taxes paid, gross vs net return comparison, alpha vs passive ETF | M2 | ORIGINAL_REQUEST § 07:11:02Z |
| 12 | F2.8 4-Asset Weight Space Optimization | Grid search over (w_QQQ, w_SOXX, w_Stocks) across 4 risk tiers maximizing Calmar ratio | M2 | ORIGINAL_REQUEST § R2 |
| 13 | F3.1 SK Square Fundamental Valuation | SOTP NAV calculation: 20.07% SK Hynix (142.7M shares) + Tmap, 11st, Wavve, Shieldus cash | M3 | ORIGINAL_REQUEST § R3 |
| 14 | F3.2 NAV Discount Barometer | Mathematical NAV discount calculation (current ~46.5%) and historical valuation comparison | M3 | ORIGINAL_REQUEST § R3 |
| 15 | F3.3 Corporate Value-Up Policy Analysis | Assessment of share cancellations, dividend yield, capital returns, discount compression catalysts | M3 | ORIGINAL_REQUEST § R3 |
| 16 | F3.4 Risk-Return Profile Comparison | Systematic upside & volatility of SK Square vs reallocating to QQQ/SOXX/SMH quant portfolio | M3 | ORIGINAL_REQUEST § R3 |
| 17 | F3.5 Actionable Today 76-Share Verdict | Unambiguous recommendation for 76 shares (Sell & Reallocate vs Hold to target vs Partial trim) with rationale | M3 | ORIGINAL_REQUEST § 07:12:52Z |
| 18 | F3.6 Actionable Today Day-1 Execution Playbook | Starting dollar/KRW and percentage weights, weekly checklist, annual checklist, stop-loss order type instructions | M3 | ORIGINAL_REQUEST § 07:12:52Z |
| 19 | F4.1 Dedicated Streamlit Tab Integration | "🎯 실전 투자 포트폴리오 & SK스퀘어 진단 (Real Investment & SK Square)" tab registered in app.py | M4 | ORIGINAL_REQUEST § R4 |
| 20 | F4.2 ETF Optimization & Tax UI Panels | Interactive weight curve, 101-grid heatmap, sensitivity table, Year-End vs Year-Beginning cards, alternative ETF matrix | M4 | ORIGINAL_REQUEST § R4 |
| 21 | F4.3 Active Turnaround Trade Log UI | Full trade history with timestamps, stop-loss records, slippage, auto-replacements, turnover rate, gross vs net return | M4 | ORIGINAL_REQUEST § R4 |
| 22 | F4.4 SK Square Barometer & Playbook UI | Interactive NAV discount gauge, 76-share evaluation, step-by-step operating checklist, USD/KRW currency toggles | M4 | ORIGINAL_REQUEST § R4 |
| 23 | F4.5 Automated Verification Test Suite | Regression & mathematical verification scripts covering all 4 requirements with 100% pass rate | M4 | ORIGINAL_REQUEST § R4 |
| 24 | F5.1 Clean Git Commit & Push | Commit all changes cleanly and push to GitHub repository jjangdol0205/Industry (main branch) | M5 | ORIGINAL_REQUEST § R4 |
| 25 | TE.1 Opaque-Box E2E Testing Track | Tier 1 (Feature Coverage), Tier 2 (Boundary), Tier 3 (Cross-Feature Pairwise), Tier 4 (Real-World Scenarios) | E2E | Project Pattern Mandate |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | ETF Optimization, Tax Timing & Alternative ETFs | F1.1, F1.2, F1.3, F1.4 | none | DONE |
| M2 | Hybrid 4-Asset Engine with Frictions & Taxes | F2.1, F2.2, F2.3, F2.4, F2.5, F2.6, F2.7, F2.8 | M1 interface | DONE |
| M3 | SK Square Valuation & Actionable Today Playbook | F3.1, F3.2, F3.3, F3.4, F3.5, F3.6 | none | DONE |
| M4 | Streamlit Tab Integration & Verification Suite | F4.1, F4.2, F4.3, F4.4, F4.5 | M1, M2, M3 | DONE |
| M5 | Git Commit & Push to GitHub Main Branch | F5.1 | M4, E2E Pass | IN_PROGRESS |
| E2E | Comprehensive Opaque-Box E2E Testing Suite | TE.1 (Tiers 1-4 Test Infrastructure & Test Cases) | Requirements | DONE |

---

## Interface Contracts

### 1. `src/optimizer/etf_rebalancer.py` (M1) ↔ `src/engine/hybrid_backtester.py` (M2)
- Input: `prices_df` (DataFrame with QQQ, SOXX, SMH, XLK, etc.), `fx_df` (USDKRW), `rebalance_dates` (Year-Beginning vs Year-End).
- Function: `compute_1d_grid_search(etf_a='QQQ', etf_b='SOXX', friction=0.0007) -> pd.DataFrame`
- Returns: DataFrame with columns `['weight_a', 'weight_b', 'cagr_usd', 'cagr_krw', 'annual_mdd_usd', 'calmar_usd', 'sharpe_usd']`.
- Function: `compare_tax_timing(etf_weights, capital_usd=100_000.0) -> Dict[str, Any]`
- Returns: `{'year_beginning': {'final_nav': float, 'taxes_paid': float, 'cagr': float, 'mdd': float, 'calmar': float}, 'year_end': {...}}`.
- Function: `evaluate_etf_alternatives() -> pd.DataFrame`
- Returns: Comparative table across (SMH, SOXX, XLK, VGT, QQQ, QLD+USD, TQQQ+SOXL).

### 2. `src/engine/hybrid_backtester.py` (M2) ↔ `app.py` (M4)
- Class: `HybridBacktester(w_qqq: float, w_soxx: float, w_stocks: float, stop_loss=-0.10, profit_take=0.25, slippage_stock_bps=12.0, commission_bps=5.0)`
- Method: `run_simulation() -> HybridBacktestResult`
- Output attributes:
  * `equity_curve: pd.DataFrame` (Dates, Portfolio NAV USD, Portfolio NAV KRW, Cash USD, Drawdown)
  * `trade_log: pd.DataFrame` (Ticker, Entry Date, Entry Price, Exit Date, Exit Price, Shares, Return %, Reason: STOP_LOSS / PARTIAL_TAKE / REBALANCE, Realized Gain KRW, Slippage Paid, Commission Paid, SEC/FINRA Fee Paid)
  * `turnover_summary: Dict[str, float]` (Annual Turnover %, Total Fees Paid USD/KRW, Total Taxes Paid KRW, Gross CAGR %, Net After-Tax CAGR %, Net Calmar)
  * `optimal_weights: Dict[str, float]` (Best triplet weights maximizing Calmar)

### 3. `src/valuation/sk_square.py` (M3) ↔ `app.py` (M4)
- Class: `SKSquareValuationEngine()`
- Methods:
  * `get_valuation_summary() -> Dict[str, Any]`:
    Returns `{'market_price': 857000, 'shares_outstanding': 131774099, 'market_cap': 112.93e12, 'hynix_price': 1443000, 'hynix_stake_value': 205.93e12, 'unlisted_value': 5.0e12, 'total_nav': 210.93e12, 'nav_per_share': 1600693, 'nav_discount_pct': 46.46, 'user_76_shares_value_krw': 65132000, 'user_76_shares_value_usd': 46523}`
  * `get_holding_recommendation() -> Dict[str, Any]`:
    Returns target prices, discount compression scenarios, clear verdict (Hold to target discount vs Reallocate to 80% QQQ / 20% SMH quant engine).
  * `get_actionable_playbook() -> Dict[str, Any]`:
    Returns Day-1 brokerage allocation amounts, weekly checklists, annual tax rebalance checklist, order type rules.

---

## Code Layout
- `quant_turnaround_strategy/src/optimizer/etf_rebalancer.py` — 1D grid search, sensitivity, tax timing & ETF alternatives (M1 exclusive).
- `quant_turnaround_strategy/src/engine/hybrid_backtester.py` — 4-asset backtester, strict -10% stop, auto-replacement, FIFO tax (M2 exclusive).
- `quant_turnaround_strategy/src/valuation/sk_square.py` — SK Square valuation, NAV discount & Actionable Today Playbook (M3 exclusive).
- `quant_turnaround_strategy/src/ui/real_investment_tab.py` — Dedicated UI tab 7 for real investment and SK Square analysis.
- `quant_turnaround_strategy/app.py` — Streamlit dedicated tab "🎯 실전 투자 포트폴리오 & SK스퀘어 진단 (Real Investment & SK Square)" (M4 exclusive).
- `quant_turnaround_strategy/verify_real_investment.py` — Automated verification script (M4 exclusive).
- `quant_turnaround_strategy/tests/test_e2e_real_investment.py` — Opaque-box E2E test suite (E2E Track exclusive).
