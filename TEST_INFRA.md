# E2E Test Infra: Tri-Asset Portfolio Optimizer & Tab 6

## Test Philosophy
- **Requirement-Driven & Opaque-Box**: Tests are derived strictly from `ORIGINAL_REQUEST.md` (§ 2026-10-12T20:33:38Z) and user-facing requirements.
- **Verification Methodology**:
  - Category-Partition Testing (Equivalence Partitioning).
  - Boundary Value Analysis (BVA): simplex vertices, edges, extreme weights.
  - Pairwise & Combinatorial Testing: rebalancing frequencies (Quarterly, Annual, Monthly) x currencies (USD, KRW) x friction rates.
  - Real-World Stress Scenarios: Dot-com crash (2001-2003), GFC (2008), COVID (2020), Tech Bear (2022).
  - Headless UI Interaction: Streamlit `AppTest` verifying 6 tabs, Tab 6 widget rendering, and session state reactive reactivity.

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|-------------|:------:|:------:|:------:|:------:|
| F1 | Historical Ingestion (SPY, QQQ, SOXX, FX) | R1 | 5 | 5 | ✓ | ✓ |
| F2 | Simplex Grid (5,151 triplets, sum=1.0) | R1 | 5 | 5 | ✓ | ✓ |
| F3 | Multi-Frequency Rebalance (Q, A, M) | R1 | 5 | 5 | ✓ | ✓ |
| F4 | Transaction Friction (0.05% + 0.02%) | R1 | 5 | 5 | ✓ | ✓ |
| F5 | Dual-Currency Performance (USD / KRW) | R1 | 5 | 5 | ✓ | ✓ |
| F6 | Calendar Year Intra-Year MDD Matrix | R2 | 5 | 5 | ✓ | ✓ |
| F7 | Institutional Metrics (CAGR, Sharpe, Calmar) | R2 | 5 | 5 | ✓ | ✓ |
| F8 | 4-Tier Constrained Optimization (T1-T4) | R2 | 5 | 5 | ✓ | ✓ |
| F9 | Crisis Resilience Stress Breakdown | R2 | 5 | 5 | ✓ | ✓ |
| F10 | Streamlit Tab 6 Registration | R3 | 5 | 5 | ✓ | ✓ |
| F11 | Ternary & Pareto Frontier Charts | R3 | 5 | 5 | ✓ | ✓ |
| F12 | 4-Tier Summary Cards & Year Table | R3 | 5 | 5 | ✓ | ✓ |
| F13 | Interactive Weight Slider | R3 | 5 | 5 | ✓ | ✓ |
| F14 | Currency Toggle (USD <-> KRW) | R3 | 5 | 5 | ✓ | ✓ |
| F15 | Automated Verification Test Suite | R3 | 5 | 5 | ✓ | ✓ |
| F16 | Streamlit Headless AppTest Validation | R3 | 5 | 5 | ✓ | ✓ |
| F17 | Git Commit & GitHub Deployment | R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**:
  - Dedicated E2E test file: `D:\Industry\quant_turnaround_strategy\tests\test_tri_asset_optimizer.py`
  - Master Verification Script: `D:\Industry\quant_turnaround_strategy\verify_tri_asset.py`
  - Integration with existing `verify_system.py`
  - Pytest runner: `& "D:\Industry\.venv\Scripts\python.exe" -m pytest D:\Industry\quant_turnaround_strategy\tests -k "tri_asset" -v`
- **Headless UI Runner**:
  - `& "D:\Industry\.venv\Scripts\python.exe" -m pytest D:\Industry\quant_turnaround_strategy\tests\test_challenger_m4_ui_headless.py -v`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| 1 | Dot-Com Bust (2001-07-10 to 2003-12-31) | F1, F2, F6, F9 | SPY defensive buffer protects portfolio; tech heavy drawdowns captured |
| 2 | Global Financial Crisis (2008) | F1, F6, F8, F9 | Intra-year drawdowns exceed 47% in USD; KRW depreciation softens drawdowns |
| 3 | COVID Shock & Fast Recovery (2020) | F1, F3, F7, F9 | V-shaped recovery properly modeled with quarterly rebalancing |
| 4 | Inflation & Tech Bear Market (2022) | F1, F7, F8, F9 | SOXX/QQQ severe decline vs SPY moderate decline evaluated |
| 5 | Full 25-Year Compound Horizon (2001-2026) | All F1-F17 | 5,151 triplets evaluated; 4 distinct optimal tiers identified with zero lookahead bias |

## Coverage Thresholds
- Tier 1: >= 5 tests per feature
- Tier 2: >= 5 boundary/corner tests per feature
- Tier 3: Pairwise combination coverage
- Tier 4: >= 5 realistic real-world application scenarios
