# Test Infrastructure: Real Investment & SK Square Quantitative Strategy (Round 8)

## 1. Test Philosophy & Principles
This test infrastructure serves as the institutional-grade opaque-box verification harness for Round 8 requirements:
- **Requirement-Driven & Opaque-Box**: Tests are derived strictly from `ORIGINAL_REQUEST.md` (timestamps 2026-10-13T07:08:00Z through 07:12:52Z) and `PROJECT.md`. Tests interact solely through documented public interfaces, validating behavior against independent mathematical and regulatory ground truth.
- **Strict Anti-Facade & Mathematical Rigor**: Tests verify real operational logic, financial math (CAGR, annual intra-year MDD, Calmar, Sharpe), South Korean capital gains taxation (2.5M KRW basic deduction, 22% rate, FIFO lot matching, calendar tax years), execution frictions (commissions, slippage, SEC Section 31, FINRA TAF), and fundamental SOTP Net Asset Value (NAV) mechanics.
- **Progressive Testability & Independence**: Each test case sets up its own state, executes deterministically, and never relies on state spillover or execution sequence.
- **Adversarial Robustness**: Tests systematically probe boundary degeneracies (0% weights, extreme gap-downs, empty candidate pools, negative cash traps, zero tax base, extreme equity market crashes).

---

## 2. Feature Inventory & Requirements Mapping

| # | Feature Code | Feature Name | Source Requirement | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Cross) | Tier 4 (Scenario) |
|---|--------------|--------------|-------------------|:-----------------:|:-----------------:|:--------------:|:-----------------:|
| 1 | **F1.1** | QQQ vs SOXX 1D Grid Search (101 weights, 0.07% friction, Calmar peak @ 100% QQQ, Sharpe peak @ 88-90% QQQ) | R1 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 2 | **F1.2** | Weight Sensitivity Table & Historical Crisis Drawdowns (2002, 2008, 2020, 2022) | R1 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 3 | **F1.3** | Year-End vs Year-Beginning After-Tax Study (2.5M KRW deduction, 22% tax, tax-loss harvesting vs 16m deferral) | 07:08:47Z | ≥5 | ≥5 | ✓ | ✓ |
| 4 | **F1.4** | Higher-Yield Alternative ETF Pairs (SMH vs SOXX +48 bps alpha, XLK/VGT, QLD+USD, TQQQ+SOXL) | 07:09:37Z | ≥5 | ≥5 | ✓ | ✓ |
| 5 | **F2.1** | PIT Turnaround Screening Queue (52w low proximity ≤5%, SEC 45d/90d reporting lags, no lookahead bias) | R2 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 6 | **F2.2** | 4-Asset Backtesting Engine (QQQ, SOXX, up to 2 stocks capacity, weights in [0%, 30%]) | R2 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 7 | **F2.3** | Daily Strict -10% Hard Stop-Loss & T+1 Auto-Replacement (10-15 bps slippage, gap-down fills, next candidate queue) | R2 & 07:11:02Z | ≥5 | ≥5 | ✓ | ✓ |
| 8 | **F2.4** | +25% Partial Profit-Taking (50% position exit, 50% retained until rebalance/stop) | R2 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 9 | **F2.5** | Real-World Execution Frictions (5 bps commission, 2 bps ETF / 12 bps stock slippage, SEC fee, FINRA TAF) | 07:11:02Z | ≥5 | ≥5 | ✓ | ✓ |
| 10 | **F2.6** | FIFO Capital Gains & Korean Tax Modeling (trade-by-trade FIFO lots, 2.5M deduction, 22% tax, T+1 settlement) | 07:11:02Z | ≥5 | ≥5 | ✓ | ✓ |
| 11 | **F2.7** | Friction Drag, Turnover & Net Alpha Analysis (annual turnover %, total costs, gross vs net return comparison) | 07:11:02Z | ≥5 | ≥5 | ✓ | ✓ |
| 12 | **F2.8** | 4-Asset Weight Space Optimization (search across 4 risk tiers maximizing Calmar) | R2 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 13 | **F3.1** | SK Square Fundamental SOTP Valuation (20.07% SK Hynix stake ₩205.93조 + ₩5.0조 unlisted/cash = ₩210.93조 NAV) | R3 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 14 | **F3.2** | NAV Discount Barometer (46.46% total discount, 45.16% vs Hynix alone, ₩1,600,693 NAV/sh vs ₩857,000 price) | R3 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 15 | **F3.3** | Corporate Value-Up Policy Analysis (treasury share cancellations, dividend yield, discount compression catalysts) | R3 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 16 | **F3.4** | Risk-Return Profile Comparison (SK Square holding vs QQQ/SOXX/SMH quant portfolio diversification) | R3 (07:08:00Z) | ≥5 | ≥5 | ✓ | ✓ |
| 17 | **F3.5** | Actionable Today 76-Share Verdict (unambiguous phased 50/50 reallocation: sell 38 shares now, hold 38 shares with trailing stop) | 07:12:52Z | ≥5 | ≥5 | ✓ | ✓ |
| 18 | **F3.6** | Actionable Today Day-1 Execution Playbook (Day-1 allocation amounts, weekly checklist, annual checklist, stop order rules) | 07:12:52Z | ≥5 | ≥5 | ✓ | ✓ |

---

## 3. 4-Tier Test Architecture

```
quant_turnaround_strategy/tests/test_e2e_real_investment.py
├── Tier 1: Feature Coverage (≥5 unit/functional tests per major feature)
│   ├── TestTier1_ETFRebalancerGridSearch
│   ├── TestTier1_TaxTimingStudy
│   ├── TestTier1_AlternativeETFs
│   ├── TestTier1_Hybrid4AssetEngine
│   ├── TestTier1_StrictStopAndAutoReplacement
│   ├── TestTier1_PartialProfitTaking
│   ├── TestTier1_ExecutionFrictionAndFIFOTax
│   ├── TestTier1_TurnoverAndNetAlpha
│   ├── TestTier1_SKSquareValuation
│   └── TestTier1_ActionableTodayPlaybook
├── Tier 2: Boundary & Corner Cases (≥5 boundary tests per feature domain)
│   ├── TestTier2_BoundaryWeightsAndAllocations
│   ├── TestTier2_ExtremeGapsAndExecutionStress
│   ├── TestTier2_TaxDeductionBoundaries
│   └── TestTier2_SKSquareValuationBoundaries
├── Tier 3: Cross-Feature Combinations (Pairwise & Multi-Feature Interactions)
│   ├── TestTier3_ActiveTradingPlusTaxRebalancing
│   ├── TestTier3_MultipleStopOutsAndAutoReplacements
│   ├── TestTier3_PartialProfitFollowedByStopLoss
│   └── TestTier3_DualCurrencyFXInteraction
└── Tier 4: Real-World Application Scenarios (End-to-End Realistic Workloads)
    ├── TestTier4_FullHistory2001To2026RealInvestment
    ├── TestTier4_DotComBustCrisisSurvival
    ├── TestTier4_GFC2008CrisisSurvival
    ├── TestTier4_TechBear2022CrisisSurvival
    └── TestTier4_UserAccountMigrationSimulation
```

---

## 4. Coverage Thresholds & Quality Criteria
- **Tier 1 (Feature Coverage)**: ≥5 explicit test methods for every core functional component.
- **Tier 2 (Boundary & Corner Cases)**: ≥5 edge/stress test methods covering degenerate values, empty sets, zero weights, extreme drawdowns, and high capital ceilings.
- **Tier 3 (Cross-Feature Combinations)**: Complete verification of multi-subsystem contracts (FIFO lot matching across multiple trades, profit trim then stop loss, FX conversion on rebalance).
- **Tier 4 (Real-World Scenarios)**: 5 end-to-end multi-year market simulations including historical crisis survival and user account portfolio migration.
- **Total Test Suite**: Comprehensive, zero flaky tests, 100% pass rate.

---

## 5. Test Execution Instructions

### Running with Pytest
```powershell
& "D:\Industry\.venv\Scripts\python.exe" -m pytest "D:\Industry\quant_turnaround_strategy\tests\test_e2e_real_investment.py" -v
```

### Running Specific Tiers
```powershell
# Tier 1 Feature Coverage
& "D:\Industry\.venv\Scripts\python.exe" -m pytest "D:\Industry\quant_turnaround_strategy\tests\test_e2e_real_investment.py" -k "TestTier1" -v

# Tier 2 Boundary & Corner Cases
& "D:\Industry\.venv\Scripts\python.exe" -m pytest "D:\Industry\quant_turnaround_strategy\tests\test_e2e_real_investment.py" -k "TestTier2" -v

# Tier 3 Cross-Feature Interactions
& "D:\Industry\.venv\Scripts\python.exe" -m pytest "D:\Industry\quant_turnaround_strategy\tests\test_e2e_real_investment.py" -k "TestTier3" -v

# Tier 4 Real-World Application Scenarios
& "D:\Industry\.venv\Scripts\python.exe" -m pytest "D:\Industry\quant_turnaround_strategy\tests\test_e2e_real_investment.py" -k "TestTier4" -v
```
