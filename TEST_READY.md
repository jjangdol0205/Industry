# TEST_READY: Special Watchlist E2E Test Suite Specification

**Project**: Special Watchlist Deep Study & Time-Series News Tracking System  
**Feature**: Feature 8 (F8) — Special Watchlist & Timeline Tracking  
**Author**: Test Writer (`test_writer_1`)  
**Date**: 2026-09-27  
**Status**: READY FOR MILESTONE VERIFICATION (Track A Complete)

---

## 1. Overview & Test Architecture

The E2E test suite for Feature 8 (`tests/e2e/test_f8_special_watchlist.py`) provides opaque-box, requirement-driven automated verification for the Special Watchlist system. It exercises the full lifecycle from multi-target institutional JSON storage, SQLite persistence, CLI engine execution, and FastAPI contracts through to React UI navigation and interactive trigger buttons.

### Test Runner & Framework
- **Framework**: Standard Python `unittest` with `starlette.testclient.TestClient`
- **Execution Environment**: `.venv\Scripts\python.exe` (Windows Python 3.11 virtual environment)
- **Primary Harness**: `run_e2e_tests.py`
- **Test File Location**: `tests/e2e/test_f8_special_watchlist.py`
- **Test Count**: 6 comprehensive E2E test cases expanding the full test suite from 83 to 89 tests.

---

## 2. Feature 8 Test Case Inventory & Coverage Matrix

| Test ID | Test Method Name | Target Feature / Contract | Authoritative Requirement | Expected Outcome / Verification Criteria |
|---------|------------------|---------------------------|---------------------------|------------------------------------------|
| **[F8-01]** | `test_f8_01_six_stocks_data_completeness_and_encoding` | 6 Special Watchlist Stocks Data Completeness & Encoding Integrity | `ORIGINAL_REQUEST §R1`<br>`PROJECT.md §F8-1, §F8-2` | All 6 tickers (`UBER`, `FLNC`, `MBLY`, `UPST`, `TSLA`, `402340.KS`) present. 5-dimension study fields (`business_model`, `moat_analysis`, `tam_growth_drivers`, `financial_margins`, `key_risks`) are non-empty strings (>10 chars). Zero question-mark encoding corruption (`??`). Valid quantitative metrics (`current_price` > 0, `mdd_pct` numeric, `buy_signal` non-empty). |
| **[F8-02]** | `test_f8_02_time_series_timeline_deduplication_and_ordering` | Time-Series Timeline Deduplication & Reverse-Chronological Ordering | `ORIGINAL_REQUEST §R2`<br>`PROJECT.md §F8-3` | Each stock contains $\ge 2$ timeline news records. SHA-256 / headline deduplication guarantees zero duplicates. Timeline dates strictly ordered reverse-chronologically (latest date first). Mandatory news attributes (`publish_date`, `headline`, `source`, `summary`) present without `??`. |
| **[F8-03]** | `test_f8_03_backend_api_endpoints_contract` | FastAPI HTTP Contracts & Route Registration | `ORIGINAL_REQUEST §R3`<br>`PROJECT.md §F8-5` | Both `/api/v1/special-watchlist` (GET) and `/api/v1/special-watchlist/refresh` (POST) are registered. GET returns HTTP 200 with $\ge 6$ stocks and zero NULL critical fields. POST returns HTTP 200/201/202 with JSON confirmation. |
| **[F8-04]** | `test_f8_04_frontend_react_ui_and_trigger_contracts` | React Frontend Navigation & Trigger Button Contracts | `ORIGINAL_REQUEST §R3, §R4`<br>`PROJECT.md §F8-6, §F8-9` | `InvestmentPortal/frontend/src/App.jsx` contains `'special-watchlist'` view mode, `'특별 관심종목'` sidebar navigation item, `'시계열 외신 최신화'` button label, and `'(특별 관심종목 돌려줘)'` requirement keyword. |
| **[F8-05]** | `test_f8_05_atomic_multi_target_json_distribution` | Multi-Target Atomic JSON File Persistence | `ORIGINAL_REQUEST §R1, §R3`<br>`PROJECT.md §F8-1, §F8-9` | `special_watchlist_data.json` exists across all 4 canonical paths: Root, Backend, Frontend Public, and Frontend Dist. All 4 files are non-empty (>500 bytes) and contain $\ge 6$ valid stock records. |
| **[F8-06]** | `test_f8_06_cli_runner_execution_contract` | Standalone CLI Runner & Callable API Contract | `ORIGINAL_REQUEST §R3`<br>`PROJECT.md §F8-4` | `sync_special_watchlist.py` exists in project root, is syntactically valid Python, and exports a callable `run_sync` entry point function. |

---

## 3. Test Runner Commands

All test runs must use the Python virtual environment (`.venv\Scripts\python.exe`) from the project root (`d:\Industry`).

### Run Only Feature 8 (Special Watchlist) Tests
```powershell
.venv\Scripts\python.exe run_e2e_tests.py --feature F8
```
*or case-insensitive:*
```powershell
.venv\Scripts\python.exe run_e2e_tests.py --feature f8
```

### Run Tier 1 Feature Tests (Including F1 through F8)
```powershell
.venv\Scripts\python.exe run_e2e_tests.py --tier 1
```

### Run Milestone 5 Verification (F8)
```powershell
.venv\Scripts\python.exe run_e2e_tests.py --milestone M5
```

### Run Full Regression Suite (All Tiers 1-4, 89 Tests)
```powershell
.venv\Scripts\python.exe run_e2e_tests.py
```

### Run Standalone via Python unittest
```powershell
.venv\Scripts\python.exe -m unittest tests.e2e.test_f8_special_watchlist
```

---

## 4. Authoritative Expected Output Derivation

Expected outputs are derived strictly from:
1. `ORIGINAL_REQUEST.md` (dated 2026-09-27T07:19:03Z):
   - 6 Tickers: UBER, FLNC, MBLY, UPST, TSLA, 402340.KS
   - 5 Institutional Study Dimensions: BM, Moat, TAM, Margins (OPM/ROE), Risks
   - Time-series timeline news tracking with incremental deduplication & reverse-chronological order
   - CLI script `sync_special_watchlist.py` & FastAPI route `/api/v1/special-watchlist/refresh`
   - Trigger button label: `"🔄 시계열 외신 최신화 (특별 관심종목 돌려줘)"`
2. `PROJECT.md` & `TEST_INFRA.md`:
   - Canonical 4-target JSON paths:
     1. `d:\Industry\special_watchlist_data.json`
     2. `d:\Industry\InvestmentPortal\backend\special_watchlist_data.json`
     3. `d:\Industry\InvestmentPortal\frontend\public\special_watchlist_data.json`
     4. `d:\Industry\InvestmentPortal\frontend\dist\special_watchlist_data.json`
   - FastAPI endpoint schema: `GET /api/v1/special-watchlist` returning JSON `{ "status": "success", "stocks": [...] }`

---

## 5. Milestone Dependency & Implementation Tracking

| Test Case | Depends On | Current Status | Expected Implementation Phase |
|-----------|------------|----------------|-------------------------------|
| `[F8-01]` | `special_watchlist_data.json` generation | Waiting for M1 | Milestone 1 (Backend Data & CLI Engine) |
| `[F8-02]` | Time-series news ingestion in JSON / DB | Waiting for M1 | Milestone 1 (Backend Data & CLI Engine) |
| `[F8-03]` | FastAPI routes in `InvestmentPortal/backend/main.py` | Waiting for M1 | Milestone 1 (Backend FastAPI Routes) |
| `[F8-04]` | UI components in `InvestmentPortal/frontend/src/App.jsx` | Waiting for M2 | Milestone 2 (Frontend React Portal) |
| `[F8-05]` | Multi-target file distribution helper | Waiting for M1 | Milestone 1 (Backend Sync Pipeline) |
| `[F8-06]` | `sync_special_watchlist.py` script | Waiting for M1 | Milestone 1 (Backend CLI Script) |

All 6 test cases are fully implemented, statically validated, and mapped into `run_e2e_tests.py`. When M1 and M2 implementations are executed, running `.venv\Scripts\python.exe run_e2e_tests.py --feature F8` will provide definitive pass/fail verification for each requirement.
