# TEST_READY: TrendPulse Investment Portal E2E Test Suite

**Declaration Date**: 2026-09-18T17:08:00+09:00  
**Test Architect**: E2E Test Architect (`.agents/e2e_test_writer`)  
**Status**: **READY FOR IMPLEMENTATION MILESTONES (M1, M2, M3, M4)**  
**Working Directory**: `D:\Industry\.agents\e2e_test_writer`  
**Test Suite Root**: `D:\Industry\tests\e2e\`  
**Executable Test Runner**: `D:\Industry\run_e2e_tests.py`  
**Documentation**: `D:\Industry\TEST_INFRA.md`

---

## 1. Executive Summary

The comprehensive, opaque-box, requirement-driven E2E test infrastructure has been fully constructed and validated. The test suite provides **83 distinct test cases** spanning all four testing tiers and covering 100% of the Acceptance Criteria outlined in `ORIGINAL_REQUEST.md` and `PROJECT.md`.

All implementing agents can now run targeted milestone tests (`--milestone M1`, `M2`, `M3`) during development and the full suite (`--milestone M4` or default) during final verification and hardening.

---

## 2. Test Artifacts Inventory

| Component | Absolute Path | Description | Test Cases |
| :--- | :--- | :--- | :---: |
| **Test Runner** | `D:\Industry\run_e2e_tests.py` | CLI test runner with tier/feature/milestone filtering | Runner |
| **Test Infrastructure** | `D:\Industry\TEST_INFRA.md` | Complete architectural specification & test matrix | Spec |
| **Shared Helpers** | `D:\Industry\tests\e2e\test_helpers.py` | Isolated SQLite builder, fixtures, paths, mock data | Utilities |
| **Feature 1 Test** | `D:\Industry\tests\e2e\test_f1_sync_engine.py` | Unified sync engine, atomic JSON distribution, dedup | 5 |
| **Feature 2 Test** | `D:\Industry\tests\e2e\test_f2_smart_cache.py` | Smart caching, weekend/close detection, < 3s SLA | 5 |
| **Feature 3 Test** | `D:\Industry\tests\e2e\test_f3_windows_automation.py` | Headless VBScript, Task Scheduler, run.bat/run.ps1 | 5 |
| **Feature 4 Test** | `D:\Industry\tests\e2e\test_f4_moat_engine.py` | 100-pt Moat/Margin engine ($S_{\text{moat}}$), 4 tiers | 5 |
| **Feature 5 Test** | `D:\Industry\tests\e2e\test_f5_mdd_rebound.py` | Tier-specific MDD DCA triggers, 100-pt Rebound ($S_{\text{rebound}}$) | 5 |
| **Feature 6 Test** | `D:\Industry\tests\e2e\test_f6_backend_api.py` | Zero-NULL universe API, /refresh_prices, profile metrics | 5 |
| **Feature 7 Test** | `D:\Industry\tests\e2e\test_f7_frontend_integrity.py` | Priority merge (ru over st), Korean badges, dist bundle | 5 |
| **Tier 2 Suite** | `D:\Industry\tests\e2e\test_tier2_boundaries.py` | Boundary & corner cases (extreme MDD, nulls, timeouts) | 37 |
| **Tier 3 Suite** | `D:\Industry\tests\e2e\test_tier3_combinations.py` | Cross-feature pairwise interactions | 6 |
| **Tier 4 Suite** | `D:\Industry\tests\e2e\test_tier4_scenarios.py` | Real-world application scenarios & workflows | 5 |
| **Total Test Cases** | | | **83** |

---

## 3. Milestone Handoff & Invocation Guidelines

Implementing agents MUST invoke tests according to their assigned milestone:

### Milestone 1: Core Quantitative Engine & Data Layer (F4, F5)
```powershell
python run_e2e_tests.py --milestone M1
```
*Validates*:
- `evaluate_stock_tier(metrics)` in `investment_engine.py`
- `compute_dca_signal(tier, mdd)` in `investment_engine.py`
- `compute_rebound_score(history_df)` in `investment_engine.py`

### Milestone 2: Full Stack Data Pipeline, Backend & Frontend (F1, F6, F7)
```powershell
python run_e2e_tests.py --milestone M2
```
*Validates*:
- `sync_stocks.py` price fetch, atomic write to 4 universe & 3 deepdive JSONs, and SQLite MIN(id) deduplication
- `InvestmentPortal/backend/main.py` routing for `@app.post("/api/portfolio/refresh_prices")` and zero-NULL universe payload
- `InvestmentPortal/frontend/src/App.jsx` dynamic over static merge priority (`ru.current_price || st.current_price`) and Korean badges

### Milestone 3: Windows Automation & Launcher Pipeline (F2, F3)
```powershell
python run_e2e_tests.py --milestone M3
```
*Validates*:
- `sync_cache.json` smart caching logic & sub-3s SLA
- `scripts/run_sync_silent.vbs` headless `pythonw.exe` invocation
- `scripts/install_silent_task.bat` / `.ps1` Task Scheduler registration
- Modernized `run.bat` & `run.ps1` pre-sync pipeline

### Milestone 4: Final E2E Verification & Hardening (All Tiers)
```powershell
python run_e2e_tests.py
# or
pytest tests/e2e/ -v
```
*Pass Criteria*: 100% of 83 test cases pass with exit code 0.
