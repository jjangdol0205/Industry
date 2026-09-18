# TrendPulse Investment Portal — E2E Test Infrastructure Specification

**Document Version**: 1.0.0  
**Author**: E2E Test Architect (`.agents/e2e_test_writer`)  
**Date**: 2026-09-18  
**Target System**: TrendPulse Investment Portal (Automated Stock Sync & 4-Stage Investment Principles Engine)  
**Authoritative Source**: `D:\Industry\ORIGINAL_REQUEST.md` and `PROJECT.md`

---

## 1. Test Architecture & Design Principles

The E2E Test Suite for the TrendPulse Investment Portal is an **opaque-box, requirement-driven verification harness**. It exercises the complete software lifecycle across all seven core features (F1 through F7), testing against rigorous interface contracts, mathematical formulas, and user acceptance criteria without coupling to internal private implementation details.

```
+-------------------------------------------------------------------------------+
|                             E2E Test Architecture                             |
+-------------------------------------------------------------------------------+
                                        │
           ┌────────────────────────────┼───────────────────────────┐
           ▼                            ▼                           ▼
 ┌───────────────────┐        ┌───────────────────┐       ┌───────────────────┐
 │ Tier 1: Features  │        │ Tier 2: Boundary  │       │ Tier 3: Pairwise  │
 │ (F1-F7 Coverage)  │        │ & Corner Cases    │       │ Combinations      │
 │  >=35 test cases  │        │  >=35 test cases  │       │  >=6 test cases   │
 └───────────────────┘        └───────────────────┘       └───────────────────┘
           │                            │                           │
           └────────────────────────────┼───────────────────────────┘
                                        ▼
                              ┌───────────────────┐
                              │ Tier 4: Scenarios │
                              │ (Real-World E2E)  │
                              │  >=5 test cases   │
                              └───────────────────┘
                                        │
                                        ▼
                         [Test Runner: run_e2e_tests.py]
                                        │
             ┌──────────────────────────┴─────────────────────────┐
             ▼                                                    ▼
   Standalone Python Mode                                   Pytest Integration
   python run_e2e_tests.py                                  pytest tests/e2e/
```

### Core Testing Principles:
1. **Opaque-Box & Requirement-Driven**: Tests are designed strictly from the user requirements (`ORIGINAL_REQUEST.md`) and system interface contracts (`PROJECT.md`).
2. **Progressive Testability**: Tests can be executed as a unified suite or scoped to specific milestones (`--milestone M1`, `M2`, `M3`, `M4`) or features (`--feature F4`).
3. **Hermetic Isolation**: Tests run in isolated sandboxes using temporary SQLite databases and mock directories, ensuring zero side-effects on production data (`investment_portal.db`).
4. **Authoritative Expected Output Derivation**: Every expected value is mathematically derived from documented formulas (e.g. 100-pt Moat score, exact MDD DCA thresholds, RSI(14), Bollinger %B).

---

## 2. Test Suite Taxonomy & Coverage Matrix

### 2.1 Tier Overview

| Tier | Focus | Scope | Test Case Count | Target Files |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **Feature Coverage** | Primary behavior & contracts for Features F1 to F7 | **35 Cases** (5 per feature) | `test_f1_sync_engine.py` to `test_f7_frontend_integrity.py` |
| **Tier 2** | **Boundaries & Corners** | Extreme MDD (0%, -19.9%, -20.0%, -29.9%, -30.0%, -100%), missing data, timeouts | **37 Cases** (>=5 per feature) | `test_tier2_boundaries.py` |
| **Tier 3** | **Cross-Feature Interactions** | Pairwise module interactions: Sync+Tiering, Cache+MDD, DB+API+UI | **6 Cases** | `test_tier3_combinations.py` |
| **Tier 4** | **Real-World Scenarios** | Full boot pipeline, sub-3s SLA, silent execution, market crash transitions | **5 Cases** | `test_tier4_scenarios.py` |
| **Total**| **Complete E2E Suite** | **Comprehensive System Validation** | **83 Cases** | Entire `tests/e2e/` package |

---

## 3. Feature Breakdown & Verification Details

### Feature 1: Unified Universe Price & Indicator Sync Engine (`test_f1_sync_engine.py`)
- **Module Under Test**: `sync_stocks.py`
- **Key Contracts**:
  - Ticker normalization: Handles Korean tickers (`A005930`, `005930` $\to$ `005930.KS`, `018290.KQ`) and US tickers (`NVDA`, `TSM`).
  - Atomic JSON distribution: Updates all 4 `universe_evaluated.json` and 3 `universal_deepdive_data.json` paths synchronously.
  - SQLite Deduplication: Links `company_profiles` to `MIN(id)` for duplicate tickers across industries, eliminating NULLs.
  - MDD Calculation: $\text{MDD} = \left(\frac{P_{\text{curr}} - P_{\text{52w\_high}}}{P_{\text{52w\_high}}}\right) \times 100\%$.
  - Graceful degradation: Retains existing cache on Yahoo Finance network timeout or 429 errors.

### Feature 2: Smart Caching & Sub-3s SLA Mechanism (`test_f2_smart_cache.py`)
- **Module Under Test**: `sync_stocks.py` / `sync_cache.json`
- **Key Contracts**:
  - Weekend detection: If synced after Friday 15:40 KST, cache is valid on Saturday/Sunday.
  - Weekday post-close detection: If synced today after 15:40 KST, re-execution hits cache.
  - Sub-3s SLA: Cache hit resolution completes in $< 3.0$ seconds (benchmark target: $< 0.1$s).
  - Cache bypass: `--force` flag forces fresh download even when cache is valid.

### Feature 3: Windows Silent Background Automation & Launcher (`test_f3_windows_automation.py`)
- **Modules Under Test**: `scripts/run_sync_silent.vbs`, `scripts/install_silent_task.bat`, `run.bat`, `run.ps1`
- **Key Contracts**:
  - Silent VBScript: Invokes `pythonw.exe` with window style `0` (`vbHide`) to eliminate console window popup.
  - Non-admin task installer: Uses `/sc onlogon /rl limited` or PowerShell `Register-ScheduledTask` for non-privileged logon execution.
  - Modernized `run.ps1`: Executes pre-sync pipeline and launches `InvestmentPortal.backend.main:app` (port 8000), eliminating redundant `pip install` loop.

### Feature 4: 4-Stage Moat & Margin Engine ($S_{\text{moat}}$) (`test_f4_moat_engine.py`)
- **Module Under Test**: `investment_engine.py`
- **Scoring Formula ($S_{\text{moat}} \in [0, 100]$)**:
  $$S_{\text{moat}} = S_{\text{dominance}} (25) + S_{\text{opm}} (25) + S_{\text{roe}} (20) + S_{\text{gpm}} (10) + S_{\text{growth}} (10) + S_{\text{fin\_health}} (10)$$
- **Tier Rules**:
  - **Core**: $S_{\text{moat}} \ge 75$ AND $\text{OPM} \ge 22\%$ AND $\text{ROE} \ge 15\%$ AND Dominance $\ge 18$.
  - **Satellite**: $S_{\text{moat}} \ge 60$ AND ($\text{Growth} \ge 15\%$ OR Dominance $\ge 18$) AND $\text{OPM} \ge 12\%$.
  - **Watchlist**: ($S_{\text{moat}} \ge 50$ OR High-potential niche) BUT not Core/Satellite.
  - **Standard**: All other universe stocks.

### Feature 5: Tier-Specific MDD DCA & Oversold Rebound Engine (`test_f5_mdd_rebound.py`)
- **Module Under Test**: `investment_engine.py`
- **DCA Thresholds & Standardized Korean Badges**:
  - **Core**: $\text{MDD} \le -30\% \to$ `BUY_READY (2차 분할매수 MDD {mdd:.1f}%)`, $-30\% < \text{MDD} \le -20\% \to$ `BUY_READY (1차 분할매수 MDD {mdd:.1f}%)`, $\text{MDD} > -20\% \to$ `WAIT (고점 부근 MDD {mdd:.1f}%)`.
  - **Satellite**: $\text{MDD} \le -35\% \to$ `BUY_READY (2차 분할매수...)`, $-35\% < \text{MDD} \le -25\% \to$ `BUY_READY (1차 분할매수...)`, $\text{MDD} > -25\% \to$ `WAIT`.
  - **Watchlist**: $\text{MDD} \le -35\% \to$ `BUY_READY (극단폭락 진입검토...)`, $\text{MDD} > -35\% \to$ `WAIT (폭락대기...)`.
  - **Standard**: $\text{MDD} \le -40\% \to$ `DEEP_DISCOUNT (일반 폭락...)`, $\text{MDD} > -40\% \to$ `WAIT (일반 관망...)`.
- **Oversold Rebound ($S_{\text{rebound}} \in [0, 100]$)**:
  - $\text{RSI}(14) < 25 \to 35$, $25-30 \to 28$, $30-38 \to 18$.
  - Bollinger Band $\%B \le 0.0 \to 25$, $0.0 < \%B \le 0.15 \to 15$.
  - MA Disparity ($20\text{d} \le 88\%$ or $60\text{d} \le 82\% \to 20$, $20\text{d} \le 92\%$ or $60\text{d} \le 88\% \to 12$).
  - Downside Support Buffer ($\le 3\% \to 20$, $3-7\% \to 12$).
  - Rebound Signal: $\ge 70 \to$ `STRONG_REBOUND`, $50-69 \to$ `MODERATE_REBOUND`, $30-49 \to$ `CONSOLIDATING`, $<30 \to$ `NEUTRAL`.

### Feature 6: Backend API Enhancements & Data Integrity (`test_f6_backend_api.py`)
- **Module Under Test**: `InvestmentPortal/backend/main.py`
- **Key Contracts**:
  - `GET /api/portfolio/universe`: 0% NULLs for active tickers.
  - `POST /api/portfolio/refresh_prices`: Properly routed and operational.
  - `GET /api/companies/{id}/profile`: Includes `current_price`, `high_52w`, `mdd_pct`, `buy_signal`, `rebound_score`.
  - `POST /api/companies/{id}/sync`: Preserves existing indicators without reset.

### Feature 7: Frontend React UI Live Integrity & Badges (`test_f7_frontend_integrity.py`)
- **Module Under Test**: `InvestmentPortal/frontend/src/App.jsx` & `dist/`
- **Key Contracts**:
  - Dynamic over static merge: `ru.current_price || st.current_price` (live remote DB overrides static JSON).
  - Korean Buy Signals: UI filter evaluates `1차 매수적기`, `2차 매수적기`, `극단폭락` as buy ready.
  - Rebound Badges: Renders `STRONG_REBOUND` / `MODERATE_REBOUND` badges.
  - Pre-built distribution bundle: `dist/index.html` verified and served.

---

## 4. Test Runner Invocation

The test suite can be run via the standalone runner `run_e2e_tests.py` or standard `pytest`.

### Standalone Runner Commands:

```powershell
# Run entire E2E test suite (All 4 Tiers, 83 test cases)
python run_e2e_tests.py

# Run by Tier
python run_e2e_tests.py --tier 1       # Tier 1: Feature Coverage (35 cases)
python run_e2e_tests.py --tier 2       # Tier 2: Boundaries & Corners (37 cases)
python run_e2e_tests.py --tier 3       # Tier 3: Cross-Feature Combinations (6 cases)
python run_e2e_tests.py --tier 4       # Tier 4: Real-World Scenarios (5 cases)

# Run by Feature
python run_e2e_tests.py --feature F1   # Sync Engine & Atomic JSON distribution
python run_e2e_tests.py --feature F2   # Smart Caching & Sub-3s SLA
python run_e2e_tests.py --feature F3   # Windows Silent Automation
python run_e2e_tests.py --feature F4   # 4-Stage Moat & Margin Engine
python run_e2e_tests.py --feature F5   # MDD DCA & Oversold Rebound Engine
python run_e2e_tests.py --feature F6   # Backend API & Data Integrity
python run_e2e_tests.py --feature F7   # Frontend React UI & Badges

# Run by Milestone
python run_e2e_tests.py --milestone M1 # Milestone 1 (F4, F5)
python run_e2e_tests.py --milestone M2 # Milestone 2 (F1, F6, F7)
python run_e2e_tests.py --milestone M3 # Milestone 3 (F2, F3)
python run_e2e_tests.py --milestone M4 # Milestone 4 (Full E2E Hardening)

# Verbose output
python run_e2e_tests.py -v
```

### Pytest Commands:

```powershell
# Run via pytest
pytest tests/e2e/ -v

# Run specific feature file
pytest tests/e2e/test_f4_moat_engine.py -v
```

---

## 5. Verification & Expected Exit Codes

- **Exit Code 0**: All executed test cases passed successfully.
- **Exit Code 1**: One or more test assertions failed or encountered an error.

During milestone-driven implementation (M1 $\to$ M2 $\to$ M3 $\to$ M4), implementing agents can run the milestone-specific command (e.g. `python run_e2e_tests.py --milestone M1`) to verify their deliverables in strict isolation before proceeding to downstream milestones.
