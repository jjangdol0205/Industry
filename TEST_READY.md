# TEST_READY: Thought Leaders & Gurus Hub E2E Test Suite Specification

**Project**: Thought Leaders & Gurus Hub (인사이트 센터)  
**Feature**: Feature 10 (F10) — Thought Leaders & Gurus Hub Pipeline, Bi-Directional Linkage & Portal API  
**Author**: E2E Test Writer (`test_writer_insights`, Testing Track)  
**Date**: 2026-10-09  
**Status**: READY FOR IMPLEMENTATION TRACK VERIFICATION (Testing Track Deliverables Complete)

---

## 1. Overview & Test Architecture

The E2E test suite for Feature 10 (`tests/test_insights_module.py`) provides an opaque-box, semantically authoritative, requirement-driven verification harness for the Thought Leaders & Gurus Hub across **all 4 testing tiers**. It rigorously tests:
1. **Content Completeness & Domain Data Modeling**:
   - 7 Investment Gurus (Howard Marks, Warren Buffett, Terry Smith, Bill Ackman, David Einhorn, Seth Klarman, Cliff Asness) official letters and investment memos with English quotes and Korean translations.
   - 7 AI & Tech Leaders (Sam Altman, Elon Musk, Jensen Huang, Mark Zuckerberg, Lisa Su, Kwak Noh-jung, Dario Amodei) core interviews, official YouTube video links, and supply chain impact analysis.
   - 3 Core Thesis Axes: ① 모델·안전성 (Models & Safety), ② 반도체·에너지 인프라 (Semiconductor & Energy Infrastructure), ③ 플랫폼 비즈니스 (Platform Business).
   - 16 Institutional Deep Glossaries (8 Financial/Accounting + 8 Technology) with formal mathematical formulas and domain analysis.
   - Zero double question mark (`??`) encoding corruptions across all fields.
2. **Deterministic Deduplication & Idempotent Persistence**:
   - 16-character SHA-256 deduplication hashing for letters (`compute_letter_hash`) and interviews (`compute_interview_hash`).
   - SQLite tables `guru_letters` (20 columns) and `tech_leader_interviews` (21 columns) with WAL, busy timeout (`PRAGMA busy_timeout = 30000;`), and unique hash constraints.
   - Idempotent seeding and incremental synchronization.
3. **Bi-Directional Ticker Linkage Engine**:
   - Symmetrical linkage between the 14 thought leaders and the 9 core universe stocks (`402340.KS`, `000660.KS`, `TSLA`, `UBER`, `CELH`, `ENPH`, `FLNC`, `MBLY`, `UPST`).
   - Ticker normalization supporting both full `.KS` tickers and numeric codes (`402340` vs `402340.KS`, `000660` vs `000660.KS`).
   - 4-path atomic JSON distribution parity (`insights_data.json`) across Root, Backend, Frontend Public, and Frontend Dist paths with matching SHA-256 hashes.
4. **FastAPI Endpoints & Offline Fallback Resilience**:
   - FastAPI routes `/api/v1/insights/feed`, `/api/v1/insights/gurus`, `/api/v1/insights/tech-leaders`, `/api/v1/insights/ticker/{ticker}`, and `/api/v1/insights/refresh` with dual routing (`/api/...`).
   - Resilient offline fallback to static JSON files when the database is unreachable or locked.

### Test Harness Specifications
- **Test File Locations**:
  - Primary Suite: `d:\Industry\tests\test_insights_module.py`
  - Forwarding Discovery Shim: `d:\Industry\tests\e2e\test_insights_module.py`
- **Master Test Runner**: `run_e2e_tests.py` (Registered under `--feature F10` / `f10`)
- **Total Test Cases**: **21 comprehensive E2E tests** (8 Tier 1, 5 Tier 2, 4 Tier 3, 4 Tier 4).
- **Test Integrity**: Zero facade tests. Every test executes against real specifications, formulas, and interface contracts.

---

## 2. Feature 10 Test Case Inventory & Coverage Matrix

| Test ID | Test Method Name | Testing Tier | Target Contract & Feature | Authoritative Specification / Verification Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **[T1-01]** | `test_t1_01_seven_investment_gurus_dataset_completeness` | Tier 1 | 7 Gurus Data Completeness | Validates presence of Howard Marks, Warren Buffett, Terry Smith, Bill Ackman, David Einhorn, Seth Klarman, and Cliff Asness with firm, title, publish date, URL, and summary. |
| **[T1-02]** | `test_t1_02_seven_tech_leaders_dataset_completeness` | Tier 1 | 7 Tech Leaders Data Completeness | Validates presence of Sam Altman, Elon Musk, Jensen Huang, Mark Zuckerberg, Lisa Su, Kwak Noh-jung, and Dario Amodei with company, role, title, publish date, media source, and URL. |
| **[T1-03]** | `test_t1_03_three_core_theses_axes_categorization` | Tier 1 | 3 Core Thesis Axes Structuring | Categorizes into ① 모델·안전성, ② 반도체·에너지 인프라, ③ 플랫폼 비즈니스. Every axis has $\ge 2$ associated items. |
| **[T1-04]** | `test_t1_04_quotes_and_korean_translations_integrity` | Tier 1 | Quotes & Korean Translations | Original English quotes (length $\ge 25$) and Korean translations/summaries (length $\ge 25$) are present without placeholder text. |
| **[T1-05]** | `test_t1_05_zero_question_mark_encoding_corruption` | Tier 1 | Zero Encoding Corruption | Forensic scan across all records: asserts zero double question marks (`??`) across all text fields. |
| **[T1-06]** | `test_t1_06_youtube_and_official_source_urls_validity` | Tier 1 | YouTube & Source Links Validity | Tech leader interviews include valid YouTube URLs (`https://www.youtube.com/watch?v=...`), and Guru letters have valid HTTP(S) source URLs. |
| **[T1-07]** | `test_t1_07_deterministic_16_char_sha256_deduplication` | Tier 1 | 16-Char SHA-256 Deduplication | `compute_letter_hash` and `compute_interview_hash` yield exactly 16 hex characters; invariant to whitespace and letter casing. |
| **[T1-08]** | `test_t1_08_sixteen_deep_institutional_glossaries` | Tier 1 | 16 Deep Institutional Glossaries | Verifies coverage of 8 Financial/Accounting glossaries (ROCE, Owner Earnings, etc.) and 8 Technology glossaries (Advanced MR-MUF, CoWoS, etc.). |
| **[T2-01]** | `test_t2_01_empty_database_graceful_handling` | Tier 2 | Empty Database Handling | Queries on an uninitialized/empty DB return valid `{status: "success", ...}` with empty arrays without throwing errors. |
| **[T2-02]** | `test_t2_02_duplicate_insertion_idempotency` | Tier 2 | Duplicate Insertion Idempotency | Re-running seeding multiple times does NOT duplicate rows; maintains strictly 7 Gurus and 7 Tech Leaders. |
| **[T2-03]** | `test_t2_03_invalid_and_unsupported_ticker_handling` | Tier 2 | Invalid Ticker Handling | Querying nonexistent or malformed tickers returns `{status: "success", total: 0, ...}` rather than raising a 500 error. |
| **[T2-04]** | `test_t2_04_special_characters_quotes_and_formulas_preservation` | Tier 2 | Special Characters & Formulas | Mathematical symbols, LaTeX expressions, quotes, and Korean punctuation marks are safely persisted in SQLite and JSON. |
| **[T2-05]** | `test_t2_05_unicode_korean_fidelity_and_roundtrip` | Tier 2 | Unicode Korean Roundtrip | Korean Hangul characters (`곽노정`, `투하자본수익률`, `SK하이닉스`) round-trip cleanly without CP949 mojibake. |
| **[T3-01]** | `test_t3_01_bi_directional_ticker_linkage_coverage_for_nine_stocks` | Tier 3 | Bi-Directional Linkage for 9 Tickers | Verifies linkage for `402340.KS`, `000660.KS`, `TSLA`, `UBER`, `CELH`, `ENPH`, `FLNC`, `MBLY`, `UPST` with actionable rationale. |
| **[T3-02]** | `test_t3_02_ticker_normalization_korean_stocks` | Tier 3 | Ticker Normalization (.KS suffix) | Queries with and without `.KS` (e.g. `000660` vs `000660.KS`, `402340` vs `402340.KS`) return identical results. |
| **[T3-03]** | `test_t3_03_sqlite_db_persistence_and_table_schemas` | Tier 3 | SQLite Schema Persistence | Verifies `guru_letters` (20 columns) and `tech_leader_interviews` (21 columns) table structures and constraints. |
| **[T3-04]** | `test_t3_04_four_target_atomic_json_distribution_parity` | Tier 3 | 4-Target Atomic JSON Parity | Atomic distribution via `.tmp` and `os.replace` produces identical files and matching SHA-256 hashes across 4 canonical paths. |
| **[T4-01]** | `test_t4_01_fastapi_endpoints_feed_gurus_leaders_contracts` | Tier 4 | FastAPI Feed, Gurus & Leaders API | Verifies `GET /api/v1/insights/feed`, `/gurus`, and `/tech-leaders` return 200 OK with valid schema; dual routes `/api/...`. |
| **[T4-02]** | `test_t4_02_fastapi_ticker_detail_endpoint_contract` | Tier 4 | FastAPI Ticker Detail API | Verifies `GET /api/v1/insights/ticker/{ticker}` returns 200 OK with structured `guru_letters` and `tech_interviews`. |
| **[T4-03]** | `test_t4_03_cli_sync_pipeline_execution_contract` | Tier 4 | CLI Pipeline Contract | Verifies `sync_insights.run_sync(force=True)` executes end-to-end and returns `{status: "success", ...}`. |
| **[T4-04]** | `test_t4_04_offline_and_db_unreachable_fallback_resilience` | Tier 4 | Offline Fallback Resilience | Verifies that when the SQLite database is unreachable, queries fall back seamlessly to static `insights_data.json`. |

---

## 3. Test Runner Invocation Commands

All commands are executed using the project Python virtual environment (`.venv\Scripts\python.exe`) from repository root (`d:\Industry`).

### Run Only Feature 10 (Thought Leaders & Gurus Hub) Tests
```powershell
& "d:\Industry\.venv\Scripts\python.exe" run_e2e_tests.py --feature F10
```
*or case-insensitive:*
```powershell
& "d:\Industry\.venv\Scripts\python.exe" run_e2e_tests.py --feature f10
```

### Run Directly via Standard Python `unittest`
```powershell
& "d:\Industry\.venv\Scripts\python.exe" -m unittest tests/test_insights_module.py
```

### Run via Pytest
```powershell
& "d:\Industry\.venv\Scripts\python.exe" -m pytest tests/test_insights_module.py -v
```

### Run Full Regression Suite (Features F1–F8 + Baseline)
```powershell
& "d:\Industry\.venv\Scripts\python.exe" run_e2e_tests.py
```

---

## 4. Authoritative Expected Output Derivation & Reference Matrix

Expected outputs are semantically and structurally derived from documented specifications in `PROJECT.md` and `ORIGINAL_REQUEST.md`:

### Ticker-to-Insights Linkage Reference Matrix:
1. **SK스퀘어 (402340.KS)**:
   - Linked Gurus: 하워드 막스 (사이클 바닥 안전마진), 워런 버핏 (자사주 매입·소각), 빌 애크먼 (지배구조 밸류업), 데이비드 아인혼 (NAV 대비 60%+ 할인율), 세스 클라만 (지분가치 대비 저평가 안전마진), 클리프 아스네스 (딥 밸류 스프레드 축소).
   - Linked Tech Leaders: 젠슨 황 (엔비디아 공급망 지분 수혜), 리사 수 (반도체 밸류체인 재평가), 곽노정 (SK하이닉스 지분법 이익).
2. **SK하이닉스 (000660.KS)**:
   - Linked Gurus: 하워드 막스 (메모리 다운턴 업턴 변곡점), 워런 버핏 (HBM 패키징 수율 독점 해자), 테리 스미스 (OPM 70%+ 및 높은 ROCE), 세스 클라만 (하방 리스크 제한), 클리프 아스네스 (QMJ 팩터 최상위).
   - Linked Tech Leaders: 샘 알트만 (추론 연산 폭증과 HBM 필수성), 일론 머스크 (Colossus 100k+ 가속기 메모리), 젠슨 황 (Blackwell/Rubin HBM3E 최고 파트너), 마크 저커버그 (Llama 인프라 메모리 납품), 리사 수 (MI325X 288GB HBM3E 다변화), 곽노정 (2030 메모리 쇼티지 지속 공식 천명), 다리오 아모데이 (Claude 클러스터향 대용량 메모리).
3. **테슬라 (TSLA)**:
   - Linked Gurus: 클리프 아스네스 (모멘텀 팩터 및 밸류에이션 변동성).
   - Linked Tech Leaders: 일론 머스크 (사이버캡 로보택시 및 메가팩 매출 성장), 젠슨 황 (FSD 자율주행 학습 클러스터), 곽노정 (차세대 자율주행 HW 메모리 협력).
4. **우버 (UBER)**:
   - Linked Gurus: 워런 버핏 (양면 네트워크 효과 및 주주이익 전환), 테리 스미스 (Asset-Light 비즈니스의 ROCE 극대화), 빌 애크먼 (Take Rate 28%+ 가격 결정력), 클리프 아스네스 (FCF 마진 개선 퀄리티 팩터).
   - Linked Tech Leaders: 일론 머스크 (로보택시 플랫폼 통합/경쟁), 마크 저커버그 (Llama 오픈소스 기반 운영비 절감), 다리오 아모데이 (컴퓨터 화면 조작 AI 기반 배차 자동화).
5. **셀시우스 (CELH)**:
   - Linked Gurus: 워런 버핏 (펩시코 DSD 유통망 해자), 테리 스미스 (48%+ 고마진 무차입 경영 ROCE).
   - Linked Tech Leaders: 마크 저커버그 (소셜 AI 타겟 마케팅을 통한 Z세대 고객 획득).
6. **엔페이즈 에너지 (ENPH)**:
   - Linked Gurus: 데이비드 아인혼 (재고 조정 이후 FCF 마진율 검증).
   - Linked Tech Leaders: 샘 알트만 (AI 데이터센터 마이크로그리드 연동 수요).
7. **플루언스 에너지 (FLNC)**:
   - Linked Gurus: 데이비드 아인혼 (수주잔고의 실질 FCF 전환율), 세스 클라만 (에너지 인프라 보수적 안전마진).
   - Linked Tech Leaders: 샘 알트만 (기가와트 데이터센터 부하 완충 BESS), 일론 머스크 (글로벌 BESS 동반 팽창), 젠슨 황 (초고밀도 랙 피크 전력 완충), 곽노정 (용인 반도체 클러스터 전력망 안정화).
8. **모빌아이 (MBLY)**:
   - Linked Gurus: 세스 클라만 (인텔 지분 매각 오버행 대비 보수적 가치 평가).
   - Linked Tech Leaders: 리사 수 (차량용 임베디드 AI 칩셋 경쟁/협력).
9. **업스타트 (UPST)**:
   - Linked Gurus: 하워드 막스 (고금리 사이클 하 신용 리스크 관리), 데이비드 아인혼 (대출 채권 신용 부실 모니터링).
   - Linked Tech Leaders: 다리오 아모데이 (설명 가능한 헌법적 AI 언더라이팅).

---

## 5. Milestone Dependency & Implementation Tracking

| Test Case | Depends On Module / Deliverable | Status Prior to M1 | Target Implementation Milestone |
| :--- | :--- | :--- | :--- |
| `[T1-01]` to `[T1-08]` | 14 Profiles, 3 Theses, 16 Glossaries in `sync_insights.py` | Implementation Pending | Milestone 1 (Insights Core Pipeline & DB) |
| `[T2-01]` to `[T2-05]` | Boundary conditions & unicode handling in `sync_insights.py` | Implementation Pending | Milestone 1 (Insights Core Pipeline & DB) |
| `[T3-01]` to `[T3-02]` | Bi-directional linkage & ticker normalization in `sync_insights.py` | Implementation Pending | Milestone 1 (Insights Core Pipeline & DB) |
| `[T3-03]` | SQLite DB schemas in `InvestmentPortal/backend/investment_portal.db` | Implementation Pending | Milestone 1 (Insights Core Pipeline & DB) |
| `[T3-04]` | Atomic 4-target distribution in `sync_insights.py` | Implementation Pending | Milestone 1 (Insights Core Pipeline & DB) |
| `[T4-01]` to `[T4-02]` | FastAPI routes in `InvestmentPortal/backend/main.py` | Implementation Pending | Milestone 2 (Backend API Endpoints & Models) |
| `[T4-03]` | CLI `sync_insights.py` execution contract | Implementation Pending | Milestone 1 (Insights Core Pipeline & DB) |
| `[T4-04]` | Offline JSON fallback resilience in `main.py` & `sync_insights.py` | Implementation Pending | Milestone 1 / Milestone 2 |

### Execution Handoff Note
The Testing Track deliverables are complete. The test suite is fully wired into `run_e2e_tests.py` and discoverable by standard `unittest`. As Milestone 1 and Milestone 2 Implementers build `sync_insights.py` and FastAPI endpoints, executing:
```powershell
& "d:\Industry\.venv\Scripts\python.exe" run_e2e_tests.py --feature F10
```
will systematically transition all 21 test cases from red to green, achieving 100% PASS in Milestone 4.
