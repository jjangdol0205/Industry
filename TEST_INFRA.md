# TrendPulse Investment Portal — E2E Test Infrastructure Specification

**Document Version**: 3.0.0  
**Author**: E2E Test Architect & Specialist (`.agents/teamwork/test_writer_insights`)  
**Date**: 2026-10-09  
**Target System**: TrendPulse Investment Portal (Thought Leaders & Gurus Hub, Macro Intelligence Module & Multi-Asset Evaluation Engine)  
**Authoritative Sources**: `D:\Industry\ORIGINAL_REQUEST.md`, `PROJECT.md`, and `SCOPE.md`

---

## 1. Test Architecture & Design Principles

The E2E Test Suite for the TrendPulse Investment Portal is an **opaque-box, requirement-driven verification harness**. It exercises the complete software lifecycle across all core modules:
- Universe Price & Indicator Sync Engine (Features F1–F7)
- Special Watchlist 8-Stock Deep Study & News Timeline (Feature F8)
- Macro Intelligence Module (Feature F9): Central bank research structuring, quantitative interest rate/liquidity dynamics, Ken Fisher 100-year backtest rules, NY Fed RIMP firm heterogeneity model, 4-quadrant macro regime engine.
- **Thought Leaders & Gurus Hub (Feature F10 / Features 1–15 in PROJECT.md)**: 7 Investment Gurus shareholder letters/memos, 7 AI & Tech Leaders interviews, 3 Core Thesis Axes, 16 institutional deep glossaries (8 Financial + 8 Technology), bi-directional ticker linkage engine for 9 core universe stocks, SHA-256 deduplication, SQLite persistence (`guru_letters`, `tech_leader_interviews`), 4-path atomic JSON distribution, and FastAPI endpoints.

```
+-------------------------------------------------------------------------------------------------------+
|                                        E2E Test Architecture                                          |
+-------------------------------------------------------------------------------------------------------+
                                                    │
            ┌───────────────────────────────────────┼──────────────────────────────────────┐
            ▼                                       ▼                                      ▼
  ┌───────────────────┐                   ┌───────────────────┐                  ┌───────────────────┐
  │ Tier 1: Features  │                   │ Tier 2: Boundary  │                  │ Tier 3: Cross-    │
  │ (F1-F10 Coverage) │                   │ & Corner Cases    │                  │ Feature Contracts │
  │  >=53 test cases  │                   │  >=47 test cases  │                  │  >=14 test cases  │
  └───────────────────┘                   └───────────────────┘                  └───────────────────┘
            │                                       │                                      │
            └───────────────────────────────────────┼──────────────────────────────────────┘
                                                    ▼
                                          ┌───────────────────┐
                                          │ Tier 4: Scenarios │
                                          │ (Real-World E2E)  │
                                          │  >=11 test cases  │
                                          └───────────────────┘
                                                    │
                                                    ▼
                                    [Test Runner: run_e2e_tests.py]
                                                    │
                 ┌──────────────────────────────────┴─────────────────────────────────┐
                 ▼                                                                    ▼
       Standalone Python Runner                                              Pytest Integration
       python run_e2e_tests.py                                              pytest tests/
       python run_e2e_tests.py --feature F10                                pytest tests/test_insights_module.py
```

### Core Testing Principles:
1. **Opaque-Box & Requirement-Driven**: Tests assert against documented interface contracts, mathematical formulas, domain logic, and user acceptance criteria from `ORIGINAL_REQUEST.md` and `PROJECT.md` without tight coupling to private helper functions.
2. **Progressive Testability**: Tests can be executed as a unified suite, scoped by testing tier (`--tier 1..4`), milestone (`--milestone M1..M5`), or specific feature (`--feature F1..F10`).
3. **Hermetic Isolation**: Tests run in self-contained sandboxes using temporary SQLite databases (`tempfile.mkdtemp()`) and isolated test directories, ensuring zero side-effects on production data (`investment_portal.db`).
4. **Authoritative Expected Output Derivation**: Every expected value is mathematically and semantically derived from documented specifications:
   - 7 Investment Gurus (Howard Marks, Warren Buffett, Terry Smith, Bill Ackman, David Einhorn, Seth Klarman, Cliff Asness).
   - 7 AI & Tech Leaders (Sam Altman, Elon Musk, Jensen Huang, Mark Zuckerberg, Lisa Su, Kwak Noh-jung, Dario Amodei).
   - 3 Core Theses: ① 모델·안전성, ② 반도체·에너지 인프라, ③ 플랫폼 비즈니스.
   - 16 Institutional Deep Glossaries with mathematical formulas and domain analysis.
   - Symmetrical Bi-Directional Ticker Linkage across 9 core stocks (`402340.KS`, `000660.KS`, `TSLA`, `UBER`, `CELH`, `ENPH`, `FLNC`, `MBLY`, `UPST`).
   - 16-character SHA-256 deduplication: `compute_letter_hash` and `compute_interview_hash`.
   - 4-path atomic JSON distribution invariance.
5. **Adversarial & Resilience Verification**: Covers uninitialized/empty databases, duplicate insertion idempotency, invalid ticker handling, special characters and mathematical formulas in quotes, UTF-8 Korean preservation (zero `??`), and offline JSON fallback resilience.

---

## 2. Test Suite Taxonomy & Coverage Matrix

### 2.1 Tier Overview

| Tier | Focus | Scope | Test Case Count | Target Files |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **Feature Coverage** | Primary behavior & contracts for Features F1 to F10 | **53+ Cases** (F1–F8: 35+, F9: 10, F10: 8+) | `test_f1_sync_engine.py` to `test_f8_special_watchlist.py`, `test_macro_module.py`, `test_insights_module.py` |
| **Tier 2** | **Boundaries & Corners** | Boundary values, empty databases, duplicate idempotency, invalid tickers, special chars | **47+ Cases** (F1–F8: 37, F9: 5, F10: 5+) | `test_tier2_boundaries.py`, `test_macro_module.py`, `test_insights_module.py` |
| **Tier 3** | **Cross-Feature Interactions** | Bi-directional linkage, DB schema persistence, 4-target atomic JSON parity, ticker normalization | **14+ Cases** (F1–F8: 6, F9: 4, F10: 4+) | `test_tier3_combinations.py`, `test_macro_module.py`, `test_insights_module.py` |
| **Tier 4** | **Real-World Scenarios** | FastAPI endpoints, CLI pipeline execution, offline fallback resilience | **11+ Cases** (F1–F8: 5, F9: 3, F10: 3+) | `test_tier4_scenarios.py`, `test_macro_module.py`, `test_insights_module.py` |
| **Total**| **Complete E2E Suite** | **Comprehensive System Validation** | **125+ Cases** (92 Baseline + 22 Macro + 20 Insights) | `tests/` and `tests/e2e/` packages |

---

## 3. Feature Breakdown & Verification Details

### Feature 1–Feature 7: Universe Price & Indicator Engine (Baseline)
- **F1 (Sync Engine)**: Ticker normalization (`.KS`, `.KQ`, US), Yahoo Finance download, 52w high & MDD, MIN(id) SQLite deduplication.
- **F2 (Smart Cache)**: Weekend detection, weekday post-15:40 KST cache hits, sub-3s SLA, `--force` bypass.
- **F3 (Windows Automation)**: Silent VBScript (`run_sync_silent.vbs`), task installers, modernized `run.ps1`.
- **F4 (Moat Engine)**: 100-point moat score ($S_{\text{moat}}$), Core ($\ge 75$), Satellite ($\ge 60$), Watchlist ($\ge 50$).
- **F5 (MDD DCA & Rebound)**: Tier-specific DCA buy alerts ($-20\%, -30\%$), 100-point oversold rebound score ($S_{\text{rebound}}$).
- **F6 (Backend API)**: `/api/portfolio/universe` (0% NULLs), `/api/companies/{id}/profile`, `/api/portfolio/refresh_prices`.
- **F7 (Frontend React UI)**: Live remote DB over static cache merge, Korean buy signals, Vite production build.

### Feature 8: Special Watchlist Deep Study & News Timeline (`test_f8_special_watchlist.py`)
- **F8-01**: 8 tickers (UBER, FLNC, MBLY, UPST, TSLA, 402340.KS, ENPH, CELH) data completeness, UTF-8 Korean integrity, no `??`.
- **F8-02**: Time-series timeline deduplication & reverse-chronological ordering.
- **F8-03**: Backend FastAPI contracts (`GET /api/v1/special-watchlist`, `POST /api/v1/special-watchlist/refresh`).
- **F8-04**: React UI contracts in `App.jsx` (`special-watchlist` view, sidebar navigation, refresh buttons).
- **F8-05**: Multi-target atomic JSON distribution across 4 canonical paths.
- **F8-06**: CLI runner contract (`sync_special_watchlist.py`, `run_sync`).

### Feature 9: Macro Intelligence Module (`tests/test_macro_module.py`)
- **F9-01**: Yield Curve Spread ($S = Y_{10Y} - Y_{2Y}$) and 4 curve states (`NORMAL`, `STEEP`, `FLAT`, `INVERTED`).
- **F9-02**: Net Liquidity Index ($\text{Assets} - \text{TGA} - \text{ON RRP}$) with unit scaling and buffer depletion alerts ($< \$150\text{B}$).
- **F9-03**: Real Neutral Rate ($r^*$) Policy Restrictiveness Gap and 4 policy stances.
- **F9-04**: Ken Fisher 100-Year Backtest Rules (KF-1 through KF-4) and NY Fed RIMP firm heterogeneity model.
- **F9-05**: 4-Quadrant Macro Regime and 4 mandatory Korean equity perspectives with zero `??` corruption.
- **F9-06**: 16-character SHA-256 deduplication and 4-target atomic JSON distribution.

### Feature 10: Thought Leaders & Gurus Hub Module (`tests/test_insights_module.py`)
- **Module Under Test**: `sync_insights.py`, `InvestmentPortal/backend/sync_insights.py`, `InvestmentPortal/backend/main.py`, `InvestmentPortal/backend/investment_portal.db`
- **Key Verification Contracts**:
  1. **7 Investment Gurus Dataset Completeness**:
     - Howard Marks (Oaktree Capital): *The Calculus of Disruption* & *Sea Change*, Market Cycles, Second-Level Thinking.
     - Warren Buffett (Berkshire Hathaway): *Annual Shareholder Letter*, Economic Moat, Owner Earnings, Capital Allocation.
     - Terry Smith (Fundsmith): *Capital Discipline in the AI Era*, High ROCE, Gross Margin Superiority.
     - Bill Ackman (Pershing Square): *High-Moat Platforms*, Concentrated Quality, Pricing Power.
     - David Einhorn (Greenlight Capital): *Real Cash Return vs Index Illusions*, Value 2.0, FCF Yield.
     - Seth Klarman (Baupost Group): *Navigating Uncharted Terrain with a Margin of Safety*, Downside Protection.
     - Cliff Asness (AQR Capital): *The Epic Value vs Growth Divergence*, Value Factor Spread Extremes, QMJ.
  2. **7 AI & Tech Leaders Dataset Completeness**:
     - Sam Altman (OpenAI): Test-Time Compute Scaling, Gigawatt Datacenters, o1/o3 reasoning models.
     - Elon Musk (Tesla / xAI): FSD End-to-End Neural Networks, Cybercab, Colossus cluster, Megapack BESS.
     - Jensen Huang (NVIDIA): Blackwell NVL72 AI Factory, CoWoS Advanced Packaging, Liquid Cooling, SK Hynix partnership.
     - Mark Zuckerberg (Meta): Llama Open-Source Foundation Models, Orion AR Glasses, Multimodal Edge AI.
     - Lisa Su (AMD): MI325X 288GB HBM3E, Chiplet Architecture, Open ROCm Ecosystem.
     - Kwak Noh-jung (SK하이닉스): 2030 High-Performance Memory Supply Shortage, Advanced MR-MUF, Custom HBM4.
     - Dario Amodei (Anthropic): Constitutional AI & RSP, Multi-Billion Training Scaling, Computer Use API.
  3. **3 Core Thesis Axes Structuring**:
     - ① 모델·안전성 (Models & Safety)
     - ② 반도체·에너지 인프라 (Semiconductor & Energy Infrastructure)
     - ③ 플랫폼 비즈니스 (Platform Business)
  4. **16 Institutional Deep Glossaries**:
     - 8 Financial/Accounting: ROCE ($\frac{\text{EBIT}}{\text{Total Assets} - \text{Current Liabilities}}$), Owner Earnings ($\text{Net Income} + \text{D&A} - \text{CapEx}$), Second-Level Thinking, Margin of Safety, FCF Yield ($\frac{\text{FCF}}{\text{Market Cap}}$), Pricing Power, Value Factor Spread, Sea Change.
     - 8 Technology: Advanced MR-MUF, CoWoS & Advanced Packaging, Test-Time Compute Scaling, Memory Wall, End-to-End Neural Networks, Constitutional AI & RSP, Liquid Cooling, Megapack & BESS.
  5. **Bi-Directional Ticker Linkage Engine**:
     - Covers 9 core universe stocks: `402340.KS`, `000660.KS`, `TSLA`, `UBER`, `CELH`, `ENPH`, `FLNC`, `MBLY`, `UPST`.
     - Ticker normalization: Resolves queries with or without `.KS` suffix (e.g. `402340` vs `402340.KS`, `000660` vs `000660.KS`).
     - Ticker implications: Structured actionable sentiment (`BULLISH`, `NEUTRAL`, `BEARISH`) and Korean rationale.
  6. **Deterministic 16-Character SHA-256 Deduplication**:
     - `compute_letter_hash(guru_name, publish_date, title)` -> exactly 16 hex characters.
     - `compute_interview_hash(leader_name, publish_date, title)` -> exactly 16 hex characters.
  7. **SQLite Database Schema & Persistence**:
     - `guru_letters` table: 20 columns, primary key, unique `letter_id`.
     - `tech_leader_interviews` table: 21 columns, primary key, unique `interview_id`.
     - `PRAGMA busy_timeout = 30000;` on all connections.
  8. **Multi-Target Atomic JSON Distribution Parity**:
     `insights_data.json` synchronized atomically via `.tmp` and `os.replace` across:
     1. `d:\Industry\insights_data.json` (Root)
     2. `d:\Industry\InvestmentPortal\backend\insights_data.json` (Backend)
     3. `d:\Industry\InvestmentPortal\frontend\public\insights_data.json` (Frontend Public)
     4. `d:\Industry\InvestmentPortal\frontend\dist\insights_data.json` (Frontend Dist)
  9. **FastAPI Endpoints & Fallback Resilience**:
     - `GET /api/v1/insights/feed` (& `/api/insights/feed`)
     - `GET /api/v1/insights/gurus` (& `/api/insights/gurus`)
     - `GET /api/v1/insights/tech-leaders` (& `/api/insights/tech-leaders`)
     - `GET /api/v1/insights/ticker/{ticker}` (& `/api/insights/ticker/{ticker}`)
     - `POST /api/v1/insights/refresh` (& `/api/insights/refresh`, `GET /api/v1/insights/refresh`)
     - Resilient offline fallback to static JSON when SQLite is locked or unavailable.

---

## 4. Test Runner Invocation

The test suite can be executed via the standalone runner `run_e2e_tests.py`, standard Python `unittest`, or `pytest`.

### Standalone Runner Commands (`run_e2e_tests.py`):

```powershell
# Run entire E2E test suite (All 4 Tiers, 114+ test cases)
python run_e2e_tests.py

# Run Feature 10 (Thought Leaders & Gurus Hub Module)
python run_e2e_tests.py --feature F10

# Run Feature 9 (Macro Intelligence Module)
python run_e2e_tests.py --feature F9

# Run Feature 8 (Special Watchlist)
python run_e2e_tests.py --feature F8

# Run by Testing Tier
python run_e2e_tests.py --tier 1       # Tier 1: Feature Coverage
python run_e2e_tests.py --tier 2       # Tier 2: Boundaries & Corners
python run_e2e_tests.py --tier 3       # Tier 3: Cross-Feature Combinations
python run_e2e_tests.py --tier 4       # Tier 4: Real-World Scenarios

# Verbose output
python run_e2e_tests.py -v
```

### Direct Unittest & Pytest Commands:

```powershell
# Run Insights Hub tests via standard unittest
python -m unittest tests/test_insights_module.py

# Run Macro Module tests via standard unittest
python -m unittest tests/test_macro_module.py

# Run Insights Hub tests via pytest
pytest tests/test_insights_module.py -v

# Run entire test suite via pytest
pytest tests/ -v
```

---

## 5. Verification & Expected Exit Codes

- **Exit Code 0**: All executed test cases passed successfully.
- **Exit Code 1**: One or more test assertions failed, or an implementation defect was discovered.

All tests are completely hermetic, run within temporary sandboxes, clean up all temporary artifacts, and do not mutate production databases during testing runs.
