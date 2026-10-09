# Project: Thought Leaders & Gurus Hub (인사이트 센터)

## Architecture
- **Data Flow & Pipeline**:
  1. `sync_insights.py` ingests, structures, and manages official shareholder letters, investment memos, and key interviews for:
     - 7 Investment Gurus: 하워드 막스 (Howard Marks), 워런 버핏 (Warren Buffett), 테리 스미스 (Terry Smith), 빌 애크먼 (Bill Ackman), 데이비드 아인혼 (David Einhorn), 세스 클라만 (Seth Klarman), 클리프 아스네스 (Cliff Asness).
     - 7 AI & Tech Leaders: 샘 알트만 (Sam Altman), 일론 머스크 (Elon Musk), 젠슨 황 (Jensen Huang), 마크 저커버그 (Mark Zuckerberg), 리사 수 (Lisa Su), 곽노정 (Kwak Noh-jung), 다리오 아모데이 (Dario Amodei).
  2. Applies SHA-256 deduplication and enforces strict reverse-chronological ordering (`publish_date DESC`).
  3. Categorizes each entry under 3 Core Thesis Axes:
     - ① 모델·안전성 (Models & Safety)
     - ② 반도체·에너지 인프라 (Semiconductor & Energy Infrastructure)
     - ③ 플랫폼 비즈니스 (Platform Business)
  4. Provides 16 Institutional Deep Glossaries (8 Financial/Accounting + 8 Technology) with formal mathematical formulas and domain analysis.
  5. Symmetrically executes the Bi-Directional Ticker Linkage Engine between the 14 thought leaders and the 9 universe stocks (`402340.KS`, `000660.KS`, `TSLA`, `UBER`, `CELH`, `ENPH`, `FLNC`, `MBLY`, `UPST`).
  6. Persists records to SQLite DB (`investment_portal.db`) tables `guru_letters` (21 columns) and `tech_leader_interviews` (23 columns).
  7. Atomically distributes `insights_data.json` across 4 canonical paths (Root, Backend, Frontend Public, Frontend Dist) using temporary files and `os.replace`.
  8. FastAPI backend (`InvestmentPortal/backend/main.py`) exposes `/api/v1/insights/feed`, `/api/v1/insights/gurus`, `/api/v1/insights/tech-leaders`, `/api/v1/insights/ticker/{ticker}`, and `/api/v1/insights/refresh` with JSON file fallback resilience.
  9. React frontend (`InvestmentPortal/frontend`) mounts `<InsightCenterView />` in `App.jsx` under `'insights'` view mode, rendering dual sub-tabs (`[투자 거장의 서한]`, `[AI & 테크 리더 레이더]`), term glossary modal, and embeds `<GuruTechInsightsWidget />` in stock detail views (`CompanyView`).
  10. Automated comprehensive test suite in `tests/test_insights_module.py` verifies 100% of pipeline, DB, API, ticker linkage, frontend contracts, and offline fallback (21/21 passed).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | 7 Gurus Letters Data Modeling & Extraction | Complete dataset for Howard Marks, Warren Buffett, Terry Smith, Bill Ackman, David Einhorn, Seth Klarman, Cliff Asness with quotes, Korean summaries, and sources. | M1 | Survey (R1) |
| F2 | 7 AI & Tech Leaders Data Modeling & Extraction | Complete dataset for Sam Altman, Elon Musk, Jensen Huang, Mark Zuckerberg, Lisa Su, Kwak Noh-jung, Dario Amodei with quotes, Korean summaries, YouTube/media links. | M1 | Survey (R1) |
| F3 | 3 Core Thesis Axes Structuring | Categorization into ① 모델·안전성, ② 반도체·에너지 인프라, ③ 플랫폼 비즈니스. | M1 | Survey (R1) |
| F4 | 16 Deep Financial & Technology Glossaries | 8 institutional financial/accounting concepts (ROCE, Owner Earnings, etc.) and 8 deep tech concepts (Advanced MR-MUF, CoWoS, etc.). | M1 | Survey (R1) |
| F5 | Bi-Directional Ticker Linkage Engine | Symmetrical mapping between 14 thought leaders and 9 universe tickers (`402340.KS`, `000660.KS`, `TSLA`, `UBER`, etc.) with actionable implications. | M1 | Survey (R2) |
| F6 | SQLite DB Schema & Atomic Persistence | Create `guru_letters` and `tech_leader_interviews` in `investment_portal.db` with SHA-256 deduplication and reverse-chronological ordering. | M1 | Survey (R1, R3) |
| F7 | 4-Path Atomic JSON Distribution | Synchronize `insights_data.json` atomically across Root, Backend, Frontend Public, and Frontend Dist. | M1 | Survey (R1, R3) |
| F8 | CLI Pipeline & Backend Mirror | CLI script `sync_insights.py` and dynamic mirror `InvestmentPortal/backend/sync_insights.py`. | M1 | Survey (R1, R3) |
| F9 | FastAPI Endpoints & Fallback Resilience | Expose `/api/v1/insights/feed`, `/gurus`, `/tech-leaders`, `/ticker/{ticker}`, `/refresh` with dual route decorators and JSON fallback. | M2 | Survey (R3) |
| F10 | Backend Models & Pydantic Schemas | SQLAlchemy models in `models.py` and Pydantic response schemas in `schemas.py`. | M2 | Survey (R3) |
| F11 | React Navigation & Sub-Tabs Dashboard | Sidebar '인사이트 센터' tab in `App.jsx`, `<InsightCenterView />` with [투자 거장의 서한] and [AI & 테크 리더 레이더] sub-tabs. | M3 | Survey (R4) |
| F12 | Glossary Modal & Interactive Filtering | Deep Term Glossary Modal (`GlossaryModal`), filter buttons, YouTube video external links, and supply chain tags. | M3 | Survey (R4) |
| F13 | Universe Detail View Linkage Widget | Embed `<GuruTechInsightsWidget />` in `CompanyView` for stocks like SK Square, SK Hynix, Tesla, etc. | M3 | Survey (R2, R4) |
| F14 | Comprehensive Test Suite & Runner Integration | Create `tests/test_insights_module.py` (Tiers 1-4) covering all acceptance criteria. | Test Track & M4 | Survey (R5) |
| F15 | Adversarial Coverage Hardening & Integrity Audit | White-box test verification, adversarial coverage audit, and zero-tolerance forensic audit. | M4 | Survey (Final Milestone) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Insights Core Pipeline, Linkage Engine & DB | F1, F2, F3, F4, F5, F6, F7, F8: `sync_insights.py`, SQLite tables, 14 profiles, 3 theses, 16 glossaries, ticker linkage, 4-path JSON distribution | none | DONE |
| M2 | Backend API Endpoints & Models | F9, F10: `models.py`, `schemas.py`, `main.py` endpoints (`/feed`, `/gurus`, `/tech-leaders`, `/ticker/{ticker}`), dynamic mirror, JSON fallback | M1 | DONE |
| M3 | Frontend React Dashboard & Widgets | F11, F12, F13: `InsightCenterView.jsx`, `App.jsx` tab integration, sub-tabs, glossary modal, `CompanyView` linkage widget, Vite build | M1, M2 | DONE |
| M4 | Final Milestone: Test Pass & Adversarial Hardening | F14, F15: 100% E2E test pass (`tests/test_insights_module.py`), Tier 5 Challenger loop, forensic audit | M1, M2, M3 | DONE |

## Interface Contracts

### M1 (Sync Engine) ↔ M2 (Backend API)
- **Database Tables** in `InvestmentPortal/backend/investment_portal.db`:
  - `guru_letters`: columns (`id`, `letter_id`, `guru_name`, `guru_name_en`, `firm`, `title`, `publish_date`, `url`, `summary`, `original_quote`, `original_quote_ko`, `core_thesis`, `thesis_pillar`, `deep_concept_guide`, `related_tickers`, `ticker_implications`, `sentiment`, `sentiment_score`, `source_type`, `created_at`, `updated_at`).
  - `tech_leader_interviews`: columns (`id`, `interview_id`, `leader_name`, `leader_name_en`, `company`, `role`, `title`, `publish_date`, `media_source`, `url`, `summary`, `original_quote`, `original_quote_ko`, `core_thesis`, `thesis_pillar`, `tech_concept_guide`, `supply_chain_impact`, `related_tickers`, `ticker_implications`, `sentiment`, `sentiment_score`, `created_at`, `updated_at`).
- **Python Module Functions**:
  - `sync_insights.run_sync(db_path=None, force=False, silent=False) -> Dict[str, Any]`
  - `sync_insights.get_all_insights_data(db_path=None) -> Dict[str, Any]`
  - `sync_insights.get_insights_by_ticker(ticker: str, db_path=None) -> Dict[str, Any]`

### M1 / M2 ↔ M3 (Frontend)
- **JSON Distribution Paths**:
  1. `d:\Industry\insights_data.json`
  2. `d:\Industry\InvestmentPortal\backend\insights_data.json`
  3. `d:\Industry\InvestmentPortal\frontend\public\insights_data.json`
  4. `d:\Industry\InvestmentPortal\frontend\dist\insights_data.json`
- **FastAPI Endpoints**:
  - `GET /api/v1/insights/feed?pillar=&ticker=&sentiment=&limit=`: returns `{ "status": "success", "total": N, "items": [...] }`
  - `GET /api/v1/insights/gurus?guru=&pillar=&limit=`: returns `{ "status": "success", "total": N, "gurus": [...], "letters": [...] }`
  - `GET /api/v1/insights/tech-leaders?leader=&pillar=&limit=`: returns `{ "status": "success", "total": N, "leaders": [...], "interviews": [...] }`
  - `GET /api/v1/insights/ticker/{ticker}`: returns `{ "status": "success", "ticker": ticker, "total": N, "guru_letters": [...], "tech_interviews": [...], "consolidated": [...] }`
  - `POST /api/v1/insights/refresh`: returns `{ "status": "success", "message": "...", "data": {...} }`

## Code Layout
- Root sync script: `d:\Industry\sync_insights.py`
- Backend sync mirror: `d:\Industry\InvestmentPortal\backend\sync_insights.py`
- Backend models: `d:\Industry\InvestmentPortal\backend\models.py`
- Backend schemas: `d:\Industry\InvestmentPortal\backend\schemas.py`
- Backend endpoints: `d:\Industry\InvestmentPortal\backend\main.py`
- Frontend view component: `d:\Industry\InvestmentPortal\frontend\src\InsightCenterView.jsx`
- Frontend application entry: `d:\Industry\InvestmentPortal\frontend\src\App.jsx`
- Frontend public data: `d:\Industry\InvestmentPortal\frontend\public\insights_data.json`
- Frontend dist data: `d:\Industry\InvestmentPortal\frontend\dist\insights_data.json`
- Test suite: `d:\Industry\tests\test_insights_module.py`
- Test infrastructure docs: `d:\Industry\TEST_INFRA.md`
- Test ready signal: `d:\Industry\TEST_READY.md`
