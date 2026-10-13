# Original User Request

## 2026-09-18T07:16:59Z

PC 부팅(로그인) 및 포털 실행 시 개별기업 주가와 4단계 투자원칙 기반 유니버스 모니터링을 자동으로 최신화하고, 전문 펀드매니저 관점에서 MDD 분할매수 적기 및 과매도 반등 시그널을 정량화하여 의사결정 신뢰도를 극대화한다.

Working directory: D:\Industry
Integrity mode: development

## Requirements

### R1. 부팅 및 포털 구동 연동 무중단 주가 자동 동기화
- Windows 로그인 시 백그라운드 무소음(Silent) 자동 갱신(작업 스케줄러/시작프로그램)과 웹서버 실행(`run.bat`) 시 사전 최신화 파이프라인을 구축한다.
- 당일 이미 갱신되었거나 장 휴장일인 경우 불필요한 반복 호출을 방지하는 스마트 캐싱 메커니즘을 적용한다.
- 야후 파이낸스/네트워크 일시 오류 시에도 직전 캐시 데이터를 유지하며 graceful하게 복구한다.

### R2. 4단계 투자원칙 엔진 고도화: MDD 분할매수 및 과매도 반등 시그널 정량화
- 단순 텍스트 키워드 매칭을 지양하고, 실제 재무 마진(OPM/ROE)과 비즈니스 해자 지표를 결합하여 유니버스 종목(Core / Satellite / Watchlist / Standard)을 객관적으로 분류한다.
- 티어별 특성에 맞춘 정량적 분할매수 시그널을 체계화한다:
  - **Core**: 52주 최고가 대비 MDD -20% (1차 분할매수), -30% (2차 분할매수)
  - **Satellite**: MDD -25% (1차 분할매수), -35% (2차 분할매수)
  - **Watchlist**: MDD -35% 이상 극단적 폭락 시에만 제한적 진입 검토
- 과매도 구간에서의 기술적/펀더멘털 반등 가능 시그널(단기 낙폭 과대, 가격 하방 지지력)을 산출하여 매수 우선순위를 제공한다.

### R3. DB 및 프론트엔드/백엔드 데이터 완전 정합성 보장
- 주가 및 지표 갱신 즉시 SQLite DB(`company_profiles`), `universe_evaluated.json`, `universal_deepdive_data.json` 전반에 즉각 반영한다.
- 웹 포털 대시보드(FastAPI 백엔드 및 React 프론트엔드)에서 갱신된 최신 주가, MDD, 분할매수 단계가 새로고침 없이도 즉시 정합성을 유지하도록 연동한다.

### R4. 프로덕션 환경 제약 및 인프라
- 시스템 구동 환경은 Windows 10/11 환경의 기존 Python 가상환경(`.venv`) 및 FastAPI/React 스택을 기준으로 한다.
- 백그라운드 자동 갱신 작업은 사용자 화면을 방해하지 않는 무소음(Silent/Headless) 백그라운드 프로세스로 동작해야 한다.

## Acceptance Criteria

### 자동화 파이프라인 무결성
- [ ] 윈도우 스케줄러 등록 스크립트 실행 후, 스케줄된 태스크가 백그라운드에서 정상 트리거되어 오류 없이 최신 주가를 갱신함
- [ ] `run.bat` 실행 시 주가 및 유니버스 지표가 갱신된 상태로 FastAPI 서버가 정상 가동됨
- [ ] 당일 장마감 후 재실행 시 스마트 캐시가 동작하여 3초 이내에 동기화 완료 판정됨

### 4단계 투자원칙 시그널 정밀도
- [ ] 전 유니버스 종목에 대해 Core / Satellite / Watchlist / Standard 분류 및 티어별 MDD 분할매수 상태(1차 매수적기, 2차 매수적기, 관망, 홀딩)가 일관된 수식에 의해 자동 계산됨
- [ ] 계산된 결과가 `investment_portal.db` 및 `universe_evaluated.json`에 결측치(NULL) 없이 기록됨
- [ ] 웹 대시보드 유니버스 화면에서 최신 주가와 4단계 매수 시그널 배지가 실시간으로 정확히 표시됨

## 2026-09-19T07:03:13Z

This is a single self-contained fix; keep it small and focused.
투자 포털(TrendPulse)의 최신 종가 동기화 반영 누락 및 SK하이닉스를 비롯한 유니버스 종목들의 '원칙 근거' 인코딩 깨짐(`??`)과 미갱신 문제를 해결하고 데이터베이스와 프론트엔드 전반의 데이터 정합성을 확보합니다.

Working directory: d:\Industry
Integrity mode: development

## Requirements

### R1. 최신 거래일 종가 및 투자 지표 동기화 정상화
- 2026-09-18 등 최신 거래일 종가 기준으로 유니버스 전체 종목의 주가, 52주 최고가, MDD 및 DCA 분할매수 시그널이 온전히 계산되고 갱신되어야 합니다.
- SQLite 데이터베이스(`company_profiles`), `universe_evaluated.json`의 4개 배포 경로, `universal_deepdive_data.json`의 3개 배포 경로에 최신 종가가 즉각 누락 없이 반영되어야 합니다.

### R2. SK하이닉스 및 유니버스 종목 '원칙 근거' 인코딩 복원 및 갱신 파이프라인 수립
- SK하이닉스를 포함해 데이터베이스와 JSON 내에 물음표(`??`)로 깨져 있는 `principle_reason` 필드를 올바른 UTF-8 한국어 텍스트(예: "NVIDIA HBM3E 독점 공급, OPM 71.5%, ROE 61.2% (Core)")로 복구합니다.
- 주가 동기화 엔진(`sync_stocks.py` / `investment_engine.py`) 실행 시 기존 원칙 근거가 손실되거나 왜곡되지 않고 온전하게 보존 및 동기화되도록 조치합니다.

### R3. 백엔드 API 및 프론트엔드 대시보드 정합성 검증
- 웹 포털 대시보드(http://localhost:8000) 및 FastAPI API(`/api/v1/companies`, `/universe_evaluated.json`)에서 SK하이닉스의 최신 종가와 정상 복원된 원칙 근거 카드가 정확히 렌더링되는지 확인합니다.
- Windows 환경에서 포털 구동(`run.ps1`/`run.bat`) 및 백그라운드 동기화 스케줄 태스크가 오류 없이 최신 데이터를 로드하는지 확인합니다.

## Acceptance Criteria

### 최신 종가 및 유니버스 데이터 정합성
- [ ] SK하이닉스(000660.KS)의 주가가 최신 종가(1,857,000원)로 갱신되어 있고, NULL 또는 0원인 종목이 없어야 함
- [ ] SQLite DB `company_profiles`와 4개 경로의 `universe_evaluated.json` 간 주가 및 MDD 데이터가 100% 일치해야 함

### 원칙 근거 및 텍스트 인코딩 무결성
- [ ] `universe_evaluated.json` 및 DB `companies`/`company_profiles`에서 SK하이닉스의 `principle_reason`에 깨진 물음표(`??`)가 전혀 없어야 함
- [ ] SK하이닉스의 원칙 근거에 HBM 독점 및 OPM/ROE 이익 체질 내용이 명확한 한글 문장으로 기재되어 있어야 함

### 동기화 자동화 및 시스템 검증
- [ ] `python sync_stocks.py` 실행 시 오류 없이 정상 완료되며, 모든 배포 대상 JSON 파일이 원자적으로 갱신되어야 함
- [ ] 기존 E2E 테스트 스위트(`pytest tests/e2e/test_f1_sync_engine.py` 등)가 에러 없이 통과해야 함

## 2026-09-27T07:19:03Z

우버(UBER), 플루언스에너지(FLNC), 모빌아이(MBLY), 업스타트홀딩스(UPST), 테슬라(TSLA), SK스퀘어(402340.KS) 6개 종목을 위한 '특별 관심종목 전용 심층 스터디 & 시계열 외신 리포트 추적 시스템'을 구축하고, 온디맨드 갱신 파이프라인 및 포털 전용 대시보드를 제공합니다.

Working directory: d:\Industry
Integrity mode: development

## Requirements

### R1. 특별 관심종목 6선 심층 스터디 아키텍처 및 데이터 영속화
- 6개 종목(우버, 플루언스에너지, 모빌아이, 업스타트, 테슬라, SK스퀘어)의 독점 병목 해자, 비즈니스 모델, TAM 및 성장 동력, 재무 마진(OPM/ROE), 핵심 투자 리스크를 포괄하는 전문 기관 수준의 고품질 심층 스터디 데이터를 구축하고 SQLite DB(`special_watchlist_studies`) 및 JSON 저장소에 영속화합니다.

### R2. 온디맨드 시계열 외신 리포트 & 뉴스 증분(Incremental) 추적 파이프라인
- 사용자가 갱신을 요청할 때마다 직전 갱신 시점 이후의 최신 글로벌 외신(Bloomberg, Reuters, CNBC, Seeking Alpha 등), 실적 발표, 월가 애널리스트 리포트 핵심 내용을 자동으로 수집·요약하여 종목별 시계열 타임라인(일자, 헤드라인, 핵심 시사점, 센티먼트, 주가 영향 분석)으로 누적 적재합니다.
- 동일 뉴스 중복 적재 방지(deduplication) 및 역연대순(최신순) 시계열 히스토리 일관성을 보장합니다.

### R3. 양방향 갱신 인터페이스 지원 (웹 대시보드 원클릭 & CLI 스크립트)
- 웹 대시보드 화면 내 "🔄 시계열 외신 최신화 (특별 관심종목 돌려줘)" 원클릭 버튼을 구현하여 브라우저에서 즉시 갱신할 수 있도록 지원합니다.
- 터미널 CLI 환경에서도 독립적으로 실행 가능한 파이썬 스크립트(`sync_special_watchlist.py`) 및 FastAPI 백엔드 엔드포인트(`/api/v1/special-watchlist/refresh`)를 제공합니다.

### R4. 전용 웹 포털 대시보드 뷰 신설 및 인터랙티브 시계열 렌더링
- TrendPulse React 프론트엔드에 '🌟 특별 관심종목 (Special Watchlist)' 전용 메뉴/뷰를 신설하여 6개 종목의 심층 스터디 카드, 핵심 투자 논거, 그리고 클릭 시 확장되는 시계열 타임라인 피드를 미려하고 반응형으로 시각화합니다.
- 기존 유니버스 모니터링 화면과의 데이터 정합성을 유지합니다.

## Acceptance Criteria

### 심층 스터디 데이터 무결성
- [ ] 6개 특별 관심종목 각각에 대해 BM, 밸류체인 해자, 재무 지표가 포함된 심층 분석 데이터가 DB 및 JSON에 온전한 UTF-8 한국어로 등록되어야 함
- [ ] 6개 종목의 최신 주가, 52주 최고가, MDD 및 4단계 투자원칙 배지가 정상 연동되어야 함

### 시계열 외신/뉴스 갱신 및 히스토리 누적
- [ ] `python sync_special_watchlist.py` 실행 시 6개 종목의 최신 외신 및 리포트 요약이 일자별 시계열 레코드로 정상 적재되어야 함
- [ ] 재실행 시 기존 타임라인 항목을 덮어쓰거나 중복 생성하지 않고 신규 발생 건만 증분 추가되어야 함

### 웹 대시보드 및 양방향 트리거 동작 검증
- [ ] 웹 대시보드(http://localhost:8000) 상단 또는 사이드바에서 '특별 관심종목' 화면으로 즉시 전환 가능해야 함
- [ ] 화면 내 "시계열 외신 최신화" 버튼 클릭 시 백엔드 API가 정상 호출되고 로딩 인디케이터 후 새 타임라인 항목이 실시간 반영되어야 함
- [ ] E2E 검증 테스트 스위트를 작성하여 파이프라인의 종단 간 무결성이 검증되어야 함

## 2026-09-29T07:54:46Z

This is a single self-contained fix; keep it small and focused.
기존 구축된 특별 관심종목(Special Watchlist) 시스템에 엔페이즈 에너지(ENPH)와 셀시우스(CELH) 2개 종목을 추가 확장(총 8선)하여, 5대 차원 심층 스터디 데이터 구축, 시계열 외신 리포트/뉴스 수집 파이프라인 확장 및 포털 대시보드 시각화를 완비합니다.

Working directory: d:\Industry
Integrity mode: development

## Requirements

### R1. 엔페이즈 에너지(ENPH) 및 셀시우스(CELH) 심층 스터디 데이터 구축 및 영속화
- 엔페이즈 에너지(ENPH: 마이크로인버터 및 분산형 ESS 1위)와 셀시우스(CELH: 기능성 피트니스 에너지 드링크 1위)의 독점 병목 해자, 비즈니스 모델, TAM 및 성장 동력, 재무 마진(OPM/ROE), 핵심 투자 리스크를 포괄하는 전문 기관 리서치 스터디를 구축합니다.
- SQLite DB(`special_watchlist_studies`, `companies`) 및 4개 표준 배포 경로의 `special_watchlist_data.json`에 영속화하고, 실시간 주가, 52주 최고가, MDD 및 4단계 투자원칙 분할매수 시그널을 연동합니다.

### R2. 8선 시계열 외신 리포트 & 뉴스 증분 수집 파이프라인 확장
- `sync_special_watchlist.py` 및 백엔드 파이프라인의 타겟 종목 목록에 ENPH와 CELH를 추가하여, 글로벌 외신(Bloomberg, Reuters, CNBC 등), 실적 발표 및 애널리스트 리포트를 일자별 역연대순 시계열 타임라인으로 누적 적재합니다.
- SHA-256 해시 기반 중복 적재 방지 메커니즘을 동일하게 적용합니다.

### R3. 양방향 갱신 인터페이스 및 백엔드 API 연동
- 웹 대시보드 "🔄 시계열 외신 최신화 (특별 관심종목 돌려줘)" 원클릭 버튼 및 CLI 스크립트 실행 시 8개 전 종목이 누락 없이 원자적으로 갱신되도록 합니다.
- FastAPI 엔드포인트(`/api/v1/special-watchlist`, `/api/v1/special-watchlist/refresh`)에서 8개 종목 데이터를 정상 응답하도록 유지합니다.

### R4. React 포털 대시보드 뷰 8선 확장 및 프로덕션 빌드
- React 대시보드 사이드바 네비게이션을 '🌟 특별 관심종목 (8선)'으로 갱신하고, `<SpecialWatchlistView />`에서 8개 종목의 심층 스터디 카드 및 시계열 타임라인 아코디언 피드가 반응형으로 정상 렌더링되도록 구현합니다.
- 프로덕션 번들 빌드(`npm run build` -> `frontend/dist`)를 성공적으로 완료합니다.

### R5. E2E 테스트 스위트 확장 및 전체 무결성 검증
- `tests/e2e/test_f8_special_watchlist.py`를 8개 종목 기준으로 확장 갱신하고, 전체 회귀 테스트 스위트(89개 테스트)가 100% 완전 통과하도록 검증합니다.

## Acceptance Criteria

### 심층 스터디 및 데이터 무결성
- [ ] ENPH와 CELH를 포함한 8개 특별 관심종목 모두 BM, 해자, 재무 지표가 포함된 심층 분석 데이터가 DB 및 JSON에 온전한 UTF-8 한국어로 등록되어야 함
- [ ] 8개 종목 모두 최신 주가, 52주 최고가, MDD 및 4단계 투자원칙 배지가 정상 계산되어야 함

### 시계열 외신 및 중복 방지
- [ ] `python sync_special_watchlist.py` 실행 시 ENPH와 CELH를 포함한 8개 종목의 시계열 타임라인에 최신 외신/리포트 항목이 정상 적재되어야 함
- [ ] 재실행 시 기존 타임라인 항목을 덮어쓰거나 중복 생성하지 않고 신규 발생 건만 증분 추가되어야 함 (SHA-256 디둡 검증)

### 웹 대시보드 및 전체 E2E 테스트 검증
- [ ] 웹 대시보드에서 8개 종목의 심층 스터디 카드 및 시계열 타임라인 피드가 정상 표시되어야 함
- [ ] "시계열 외신 최신화" 버튼 클릭 시 8개 종목에 대한 실시간 갱신이 성공해야 함
- [ ] 전체 E2E 테스트 스위트가 에러 없이 100% 통과해야 함

## 2026-09-29T08:03:00Z

특별 관심종목(Special Watchlist)에 대해 관련 유튜브 링크를 검색하여 영상의 핵심 내용을 추출하고, 투자 판단에 직결되는 핵심 인사이트(Catalyst, 리스크/보상, 밸류에이션, 진입/익절 전략)를 도출하여 기업별 시계열(Time-series) 타임라인으로 통합 정리 및 시각화합니다.

Working directory: d:\Industry
Integrity mode: development

## Requirements

### R1. 특별 관심종목 8선 전용 유튜브 영상 링크 검색 및 콘텐츠/인사이트 데이터 수집
- 특별 관심종목 8선(UBER, FLNC, MBLY, UPST, TSLA, 402340.KS, ENPH, CELH) 각각에 대해 기관급 심층 분석, CEO 인터뷰, 실적 컨퍼런스콜 브리핑, 기술 로드맵을 다룬 핵심 유튜브 영상 링크(`https://www.youtube.com/watch?v=...`)를 수집·검색합니다.
- 영상의 핵심 발표 내용(발표 요약, 실적·수주 현황, 기술 진척)을 추출(`summary`)하고, 투자 판단에 직접적으로 도움이 되는 핵심 시사점(`key_takeaways` / `insight`) 및 주가 영향 분석(`price_impact`)을 도출합니다.

### R2. 시계열 타임라인 SQLite DB 및 JSON 파이프라인 통합 영속화
- 수집된 유튜브 인사이트를 기존 외신 리포트와 함께 SQLite DB `special_watchlist_timeline` 및 4개 표준 배포 경로의 `special_watchlist_data.json`에 시계열 역연대순(최신순)으로 통합 적재합니다.
- 고유 식별자(`news_id`) 및 SHA-256 해시를 적용하여 중복 적재를 원천 방지하고, 출처 표기(`source: "YouTube (<채널명>)"`) 및 비디오 링크(`url`)를 완벽히 보존합니다.

### R3. 백엔드 및 CLI 온디맨드 갱신 동기화 연동
- CLI 스크립트(`sync_special_watchlist.py`) 및 FastAPI 엔드포인트(`/api/v1/special-watchlist/refresh`) 호출 시 외신 기사뿐만 아니라 유튜브 영상 분석 인사이트도 함께 온디맨드로 최신화되도록 파이프라인을 연동합니다.

### R4. React 웹 대시보드 유튜브 전용 UI & 시계열 투자판단 뷰 강화
- `<SpecialWatchlistView />` 내 타임라인 카드에 유튜브 전용 배지(`▶️ YouTube · <채널명>`)와 클릭 시 해당 유튜브 영상으로 바로 이동하는 `▶️ 유튜브 영상 바로가기` 버튼을 제공합니다.
- "💡 핵심 투자 인사이트" 박스를 시각적으로 강조 렌더링하여 투자 판단 정보를 한눈에 파악할 수 있도록 구현합니다.
- 타임라인 필터에 `전체 (All) | 📰 외신 뉴스 | 🎥 유튜브 인사이트` 탭을 추가하여 사용자가 원하는 미디어 유형만 필터링하여 시계열로 비교·분석할 수 있도록 지원합니다.

### R5. E2E 테스트 및 빌드 무결성 검증
- E2E 테스트(`tests/e2e/test_f8_special_watchlist.py`)에 유튜브 링크 유효성, 인사이트 데이터 무결성, 미디어 필터링 계약 검증을 추가하고 전체 89개 회귀 테스트 통과 및 프론트엔드 빌드(`npm run build`)를 완수합니다.

## Acceptance Criteria

### 유튜브 링크 및 인사이트 데이터 무결성
- [ ] 8개 특별 관심종목 모두 유튜브 링크(`https://www.youtube.com/watch?v=...`) 및 영상 추출 내용, 핵심 투자 인사이트가 DB 및 JSON에 온전한 UTF-8 한국어로 등록되어야 함
- [ ] 타임라인 내 모든 유튜브 항목에 대해 `source`에 채널명이 명시되고, `key_takeaways`에 실질적인 투자 판단 근거가 포함되어야 함

### 시계열 타임라인 역연대순 정렬 및 디둡
- [ ] 유튜브 항목과 외신 기사가 일자(`publish_date`) 기준 역연대순으로 일관되게 정렬되어야 함
- [ ] 중복 링크 또는 중복 해시가 생성되지 않고 멱등성(Idempotency)이 보장되어야 함

### 웹 대시보드 UI 및 사용자 경험
- [ ] 웹 대시보드 타임라인에서 유튜브 배지와 바로가기 링크 버튼이 정상 동작해야 함
- [ ] 미디어 필터 탭(`전체 | 외신 뉴스 | 유튜브 인사이트`) 클릭 시 해당 미디어 항목만 즉각 필터링되어야 함
- [ ] 전체 E2E 테스트 89개 100% 통과 및 프로덕션 빌드 성공

## 2026-09-30T08:14:05Z

This is a single self-contained feature; keep it small and focused.
특별 관심종목 8개 기업의 산업별 시장 규모(TAM), 2030년 예상 연평균 성장률(CAGR), 현재 시장 점유율(Market Share) 및 향후 점유율 확대(Expand) vs 축소(Contract) 경쟁 역학 분석을 데이터베이스, 4대 정규 JSON, 그리고 포털 프론트엔드 대시보드(상단 8선 한눈에 보는 비교 매트릭스 표 + 각 기업별 상세 카드 전용 위젯)에 완벽하게 구축하고 E2E 회귀 테스트를 완료합니다.

Working directory: d:\Industry
Integrity mode: development

## Requirements

### R1. 8개 특별 관심종목 산업 규모(TAM) 및 예상 성장률(CAGR) 정량 데이터 모델링
- 8개 종목(UBER, FLNC, MBLY, UPST, TSLA, 402340.KS, ENPH, CELH) 각각의 주력 산업 카테고리에 대해 현재 글로벌 시장 규모(TAM, USD/KRW)와 2030년까지의 예상 연평균 성장률(CAGR %)을 공신력 있는 시장조사기관(Bloomberg, Goldman Sachs, Gartner, TrendForce 등) 데이터에 기반하여 정량 수치로 모델링합니다.

### R2. 현재 시장 점유율(Market Share) 및 경쟁 순위(Rank) 정량화
- 각 기업의 주력 시장/핵심 세그먼트 내 실질 시장 점유율(Market Share %)과 시장 내 지위(글로벌 1위, 과점 지배자 등)를 정량 필드로 명시합니다.

### R3. 점유율 향방(확대 우세 vs 축소 우려) 및 경쟁 역학(Dynamics) 분석
- 점유율 전망 판정: `확대 우세 (Expanding)` / `현상 유지 및 수성 (Defending)` / `잠식 리스크 (Contracting Risk)`
- 점유율 확대 요인(기술적 병목 해자, 네트워크 효과, 원가 파괴, 배타적 파트너십)과 점유율 위협 요인(빅테크/OEM 자체 내재화, 가격 출혈 경쟁, 규제 및 대체재)을 대조 분석하여 종합 방어력을 도출합니다.

### R4. DB 영속화, 4대 정규 JSON 동기화 및 React UI 대시보드 연동
- `sync_special_watchlist.py`에 산업 동학(`industry_dynamics`) 스키마를 영속화하고, `special_watchlist_studies.study_json` 및 4대 배포 경로(`special_watchlist_data.json` Root, Backend, Frontend Public, Frontend Dist)에 원자적으로 동기화합니다.
- `App.jsx` 내 `<SpecialWatchlistView />`에:
  1. 상단에 **[📊 8선 한눈에 보는 산업 규모·성장률·점유율 비교 매트릭스 표]**를 배치하여 8개 기업의 시장 지위와 성장성을 한눈에 조망하도록 합니다.
  2. 각 기업별 카드 내에 **[📊 산업 규모·성장률 & 시장 점유율 동학 분석기]** 전용 위젯을 추가하여 점유율 프로그레스 게이지, 확대/축소 판정 배지, 확대 동인 및 위협 요인을 상세 시각화합니다.

### R5. E2E 회귀 테스트 스위트 및 프로덕션 빌드 검증
- `test_f8_special_watchlist.py` 및 전체 E2E 테스트(89개 테스트)가 100% 완전 통과(`OK`)하도록 보장하고, Vite 프로덕션 빌드(`npm run build`)를 성공적으로 완료합니다.

## Acceptance Criteria

### 데이터 완성도 및 무결성
- [ ] 8개 전 종목에 대해 산업 규모(TAM), 예상 성장률(CAGR), 현재 시장 점유율(%), 점유율 전망 판정(`확대 우세`/`수성`/`축소 우려`), 확대 동인 및 위협 요인이 누락 없이 구축되어야 함
- [ ] `special_watchlist_data.json` 4개 정규 경로(Root, Backend, Frontend Public, Frontend Dist)에 오류 없이 동기화되어야 함

### UI 시각화 및 인터랙션
- [ ] 웹 대시보드 특별 관심종목 뷰 상단에 8개 기업의 산업 규모, CAGR, 점유율, 전망 판정을 비교하는 요약 매트릭스 표가 표시되어야 함
- [ ] 각 기업별 카드 내에 산업 규모, CAGR, 점유율 게이지, 점유율 확대/축소 판정 배지가 직관적으로 렌더링되어야 함
- [ ] 단독 기업 집중 모드 및 전체 8선 보기 모드 모두에서 깨짐 없이 반응형으로 표시되어야 함

### 빌드 및 테스트 통과
- [ ] `npm run build` 번들링이 에러 없이 완료되어야 함
- [ ] 전체 E2E 회귀 테스트(`run_e2e_tests.py`)가 89/89 ALL PASS를 유지해야 함



## 2026-10-09T08:08:19Z

투자 분석 포털(`TrendPulse` / `d:\Industry`) 내에 연준(FOMC) 공식 발표 자료, 뉴욕·세인트루이스 연은 리서치, 거시 유동성 및 국채금리 지표를 자동으로 수집·구조화하고, 주식 시장 할인율, 팩터(퀄리티 대형주 vs 중소형주) 및 섹터 영향도를 시각화하는 풀스택 **'매크로 인텔리전스 모듈(Macro Intelligence Module)'**을 구축한다.

Working directory: d:\Industry
Integrity mode: development

## Requirements

### R1. 연준(Fed/FOMC) 및 뉴욕·세인트루이스 연은 리서치 수집 및 주식 영향도 구조화 파이프라인
- 연방준비제도(Board of Governors), FOMC 성명서/의사록/경제전망(SEP), 뉴욕연은(Liberty Street Economics), 세인트루이스연은(FRED/Economic Synopses)의 최신 연구 보고서와 의사록을 수집하고, 중복 수집 방지(SHA-256 해시) 메커니즘을 적용한다.
- 수집된 보고서마다 주식 시장 중심의 4대 핵심 관점(① 매크로 할인율 및 증시 밸류에이션, ② 스타일/팩터 영향, ③ 주요 섹터 및 산업 영향, ④ 외환 및 외국인 수급)으로 분석·구조화하여 SQLite DB에 영속화한다.

### R2. 거시 유동성 및 금리 지표 정량화 엔진
- 미 국채 10년물/2년물 금리 및 스프레드, 재무부 일반계정(TGA), 역레포(ON RRP) 잔고, 실질 중립금리(r*) 추정치 등 핵심 거시 유동성 지표를 정량화한다.
- 켄 피셔(Ken Fisher) 100년 백테스트 및 최신 연은 연구(기업 이질성 RIMP 모델)를 기반으로, 거시 환경 국면(Macro Regime)에 따른 주식 시장 멀티플(PER 확장/압축) 및 팩터(대형 퀄리티 우량주 vs 중소형 한계기업) 기대 수익률을 산출한다.

### R3. 백엔드 API 및 정합성 보장 파이프라인
- SQLite DB 내 매크로 전용 테이블(`macro_reports`, `macro_indicators`, `macro_regime`)을 구축하고, 독립 실행 가능한 CLI 동기화 스크립트(`sync_macro.py`) 및 배포용 JSON(`macro_intelligence_data.json`) 갱신 파이프라인을 제공한다.
- FastAPI 백엔드에 매크로 종합 요약(`/api/v1/macro/summary`), 시계열 리서치 타임라인(`/api/v1/macro/timeline`), 금리/유동성 지표(`/api/v1/macro/indicators`) 엔드포인트를 구현하고 기존 포털 API와 정합성을 유지한다.

### R4. 프론트엔드 React 대시보드 ('매크로 인텔리전스' 탭) 구현
- 기존 유니버스 및 특별 관심종목 네비게이션에 신규 **'매크로 인텔리전스'** 탭을 추가한다.
- 대시보드 화면에 ① 거시 유동성 및 금리 상태 게이지(Rate & Liquidity Dashboard), ② 연은 리서치 시계열 피드(최신순 카드 뷰), ③ 스타일·팩터 및 섹터 영향도 매트릭스(Heatmap/Card)를 직관적이고 반응형으로 렌더링한다.

## Acceptance Criteria

### 매크로 데이터 수집 및 DB 무결성
- [ ] `sync_macro.py` 실행 시 오류 없이 동작하며, SQLite DB(`investment_portal.db`) 내 `macro_reports` 및 `macro_indicators` 테이블에 데이터가 정상 적재됨
- [ ] 수집된 리서치 데이터에 4대 관점(할인율, 팩터, 섹터, 외환/수급) 분석 필드가 결측치(NULL) 없이 기록됨
- [ ] 배포용 JSON(`macro_intelligence_data.json`)이 4개 대상 경로에 원자적으로 동기화됨

### 백엔드 엔드포인트 무결성
- [ ] FastAPI 서버 구동 시 `/api/v1/macro/summary` 및 `/api/v1/macro/timeline` 요청이 200 OK와 함께 유효한 스키마의 JSON을 반환함
- [ ] 신규 데이터 갱신 시 캐시 무효화 및 실시간 최신 데이터 조회가 보장됨

### 프론트엔드 UI 대시보드 완성도
- [ ] React 빌드(`pnpm run build` 또는 `npm run build`)가 타입/린트 오류 없이 통과함
- [ ] 브라우저에서 '매크로 인텔리전스' 탭 클릭 시 거시 지표 게이지와 연은 리서치 카드 타임라인이 시각적으로 올바르게 표출됨
- [ ] 기존 유니버스 모니터링 및 특별 관심종목 기능과 간섭 없이 매끄럽게 동작함

### 회귀 및 통합 테스트
- [ ] 매크로 모듈 단위 및 통합 테스트 스위트(`pytest tests/test_macro_module.py`)가 작성되어 100% 통과함


## 2026-10-09T08:24:50Z

투자 분석 포털(`TrendPulse` / `d:\Industry`) 내에 세계적인 **투자 거장 7인**(하워드 막스, 워런 버핏, 테리 스미스, 빌 애크먼, 데이비드 아인혼, 세스 클라만, 클리프 아스네스)의 공식 서한과 **글로벌 AI & 테크 리더 7인**(샘 알트만, 일론 머스크, 젠슨 황, 마크 저커버그, 리사 수, 곽노정, 다리오 아모데이)의 핵심 인터뷰를 실시간 수집·분석하고, 유니버스 종목(SK스퀘어, SK하이닉스, 테슬라, 우버 등)과 연계하는 풀스택 **'인사이트 센터(Thought Leaders & Gurus Hub)'**를 구축한다.

Working directory: d:\Industry
Integrity mode: development

## Requirements

### R1. 투자 거장 서한 및 AI·테크 리더 인터뷰 듀얼 수집 파이프라인
- 투자 거장 7인의 공식 서한/메모 및 테크 리더 7인의 공식 인터뷰(유튜브, 테크 팟캐스트, 백악관 회동, 경제 방송)를 모니터링하여 수집하는 통합 파이프라인(`sync_insights.py`)을 구축한다.
- SHA-256 해시 기반의 중복 수집 방지 메커니즘을 적용하고, 역연대순 시계열 타임라인으로 적재한다.
- 각 콘텐츠마다 원문 인용 및 한글 요약과 함께, ① 서한/인터뷰 개요, ② 핵심 테제(3대 축: 모델·안전성/반도체·에너지 인프라/플랫폼 비즈니스), ③ 심층 금융·회계 및 기술 개념 해설서, ④ 포털 종목별 시사점을 정형화 추출한다.

### R2. 포털 유니버스 종목 간의 양방향 연동 엔진
- 투자 거장들의 핵심 철학(자본배치, ROCE/FCF, 사이클, 안전마진) 및 테크 리더들의 발언(HBM 공급 부족, 에너지 스케일링, FSD, Llama 오픈소스 등)을 포털 내 보유 및 관심 종목(SK스퀘어, SK하이닉스, 테슬라, 우버, 셀시우스 등)의 평가 데이터와 상호 매핑한다.
- 종목별 상세 화면 조회 시 관련 거장 및 테크 리더의 최신 인사이트가 자동으로 결합되어 표출되도록 한다.

### R3. 백엔드 API 및 SQLite DB 무결성 영속화
- SQLite DB(`investment_portal.db`) 내 `guru_letters` 및 `tech_leader_interviews` 테이블을 구축하고, 배포용 JSON(`insights_data.json`) 4개 경로 원자적 갱신 파이프라인을 지원한다.
- FastAPI 백엔드에 통합 인사이트 피드(`/api/v1/insights/feed`), 거장 서한 목록(`/api/v1/insights/gurus`), 테크 리더 인터뷰 목록(`/api/v1/insights/tech-leaders`), 종목별 연관 발언(`/api/v1/insights/ticker/{ticker}`) 엔드포인트를 구현한다.

### R4. 프론트엔드 React 대시보드 ('인사이트 센터' 탭) 구현
- 포털 메인 네비게이션에 신규 **'인사이트 센터(Thought Leaders)'** 탭을 신설한다.
- 내부 서브 탭 전환 UI를 제공한다:
  - 서브 탭 1: **[투자 거장의 서한]** (구루별 필터, 서한 타임라인 카드, 심층 용어 해설 모달)
  - 서브 탭 2: **[AI & 테크 리더 레이더]** (리더별 프로필 필터, 인터뷰 핵심 발언 카드, 영상/원문 링크, 공급망 영향도 태그)
- 유니버스 모니터링 및 특별 관심종목 상세 모달/패널 내에 '거장 & 테크 리더 인사이트' 연동 위젯을 렌더링한다.

## Acceptance Criteria

### 데이터 파이프라인 및 DB 영속화 무결성
- [ ] `sync_insights.py` 실행 시 7대 거장의 기발표 서한 및 테크 리더들의 최신 인터뷰 데이터가 SQLite DB(`investment_portal.db`)에 정상 적재됨
- [ ] 수집된 데이터에 원문 인용, 핵심 테제, 개념 해설, 종목 시사점 필드가 결측치(NULL) 없이 파싱됨
- [ ] 배포용 JSON(`insights_data.json`)이 4개 대상 경로에 원자적으로 동기화됨

### 백엔드 엔드포인트 무결성
- [ ] FastAPI 서버 구동 시 `/api/v1/insights/feed`, `/api/v1/insights/gurus`, `/api/v1/insights/tech-leaders` 요청이 200 OK와 함께 유효한 JSON을 반환함
- [ ] 특정 종목 조회 시(예: `/api/v1/insights/ticker/402340.KS` 또는 `000660.KS`) 관련 코멘트(곽노정 사장 2030 메모리 공급 부족, 하워드 막스 사이클 원칙 등)가 정상 반환됨

### 프론트엔드 UI 대시보드 완성도
- [ ] React 빌드(`pnpm run build` 또는 `npm run build`)가 타입/린트 오류 없이 통과함
- [ ] 브라우저에서 '인사이트 센터' 탭 진입 시 [투자 거장 서한]과 [AI & 테크 리더] 서브 탭 전환이 매끄럽게 동작하고 카드가 직관적으로 표출됨
- [ ] 기존 유니버스 모니터링 및 매크로 인텔리전스 기능과 간섭 없이 일관된 테마 디자인을 유지함

### 회귀 및 통합 테스트
- [ ] 단위 및 통합 테스트 스위트(`pytest tests/test_insights_module.py`)가 작성되어 100% 통과함


## 2026-10-12T12:49:12Z

A quantitative research and production-ready algorithmic trading system that simulates and optimizes an investment strategy combining QQQ, SOXX, and opportunistic 52-week-low turnaround stocks from July 2001 to present, optimizing return relative to annual MDD, proposing an enhanced alternative strategy, and delivering an interactive deployed Streamlit dashboard.

Working directory: D:\Industry\quant_turnaround_strategy
Integrity mode: development

## Requirements

### R1. Data Pipeline & Turnaround Stock Screening
- Ingest daily adjusted price data for QQQ and SOXX starting from the later inception date (SOXX launch: July 10, 2001) to the present.
- Define a candidate stock universe (S&P 500 and NASDAQ 100 components) and identify stocks hitting 52-week lows at historical decision points.
- Screen for 1~2 year forward revenue and operating profit turnaround potential using point-in-time financial/consensus indicators to strictly eliminate lookahead bias.
- Support weekly candidate evaluation: select at most 1 optimal stock per week, maintaining a maximum portfolio capacity of 3 individual stocks, with discretionary inclusion/exclusion based on risk-reward (can hold 0 to 3 stocks).

### R2. Trial-and-Error Optimization Engine (Return vs. Annual MDD)
- Implement a modular backtesting simulator supporting dynamic rebalancing between QQQ, SOXX, selected individual turnaround stocks, and cash.
- Conduct systematic trial-and-error optimization (parameter grid search / walk-forward analysis) over allocation ratios, entry/exit thresholds, and stop-loss / profit-taking rules.
- Explicitly evaluate risk using annual Maximum Drawdown (calendar year MDD) and optimize the objective function: Maximize Return relative to Annual MDD (Calmar / MAR ratio).
- Formulate a superior alternative strategy (e.g., trend-following regime filter, volatility-targeted allocation, or dynamic dual-momentum), provide rigorous comparative metrics, and detail the economic and empirical reasons for its outperformance.

### R3. Interactive Streamlit Dashboard & Deployment
- Build a Python Streamlit web dashboard featuring:
  - Interactive cumulative return curves (Strategy vs. QQQ vs. SOXX vs. Enhanced Strategy).
  - Year-by-year performance breakdown (Annual Return, Annual MDD, Return/MDD ratio).
  - Historical trade log, dynamic asset allocation heatmaps, and weekly stock selection explanations.
  - Live simulation view and parameter tuning interface for future operational use.
- Initialize Git repository, commit clean versioned source code, and set up deployment configuration (GitHub repository push & deployment ready).

## Acceptance Criteria

### Simulation & Quantitative Rigor
- [ ] Simulation timeline strictly begins on July 10, 2001 (SOXX inception) and runs to current date.
- [ ] Backtest guarantees zero lookahead bias in 52-week low screening and financial forecast proxy metrics.
- [ ] Trial-and-error parameter search produces an optimal configuration with full documentation of searched parameter spaces.
- [ ] Annual MDD and annual return are tabulated for every calendar year from 2001 to present.
- [ ] An enhanced alternative strategy is backtested alongside the base strategy with a written comparative justification.

### Automated Verification
- [ ] Programmatic verification script executes cleanly and validates data integrity, metric calculations, and strategy comparison results.
- [ ] Streamlit web application launches without error and renders all charts, tables, and filters.
- [ ] Git repository is initialized with meaningful commit history and ready for deployment.


## 2026-10-12T13:28:11Z

[CRITICAL USER REQUIREMENT UPDATE - REAL-WORLD EXECUTION & REPORTING]

The user has explicitly added the following critical requirements for real-world production usability:

1. Real-World Execution Costs & Frictions:
   - Must model realistic transaction costs: Brokerage commissions (e.g., 0.05% ~ 0.1%) and bid-ask spread / market impact slippage (e.g., 0.05% ~ 0.1%) on every rebalance trade.
   - Must model capital gains taxation: Korean overseas stock investment tax (해외주식 양도소득세 22% with annual 2.5 million KRW basic deduction, applied at calendar year-end on net realized gains). Provide toggle/comparison between Gross Returns and Net After-Tax/After-Cost Returns.

2. Dual-Currency Returns (USD & KRW):
   - Ingest daily USD/KRW exchange rates (e.g., USDKRW=X from Yahoo Finance) from July 10, 2001 to present.
   - Calculate and display performance metrics (Cumulative Return, CAGR, Annual Return, Annual MDD, Calmar Ratio) in BOTH USD and KRW.
   - The interactive Streamlit dashboard must feature a seamless toggle / side-by-side view for USD vs. KRW performance, including FX impact analysis on drawdown and returns.

3. Practical Usability & Robustness:
   - Ensure the optimized strategy is practically executable (realistic rebalance frequency, avoidance of extreme micro-turnover, clear rules for live trading going forward).

Please immediately update PROJECT.md, the backtest engine contracts, the metrics pipeline, and the Streamlit dashboard requirements to incorporate these items into the current build and verification tracks.

## 2026-10-12T20:33:38Z

A quantitative portfolio optimization and visualization module determining the mathematically and empirically optimal fixed allocation weights among S&P 500 ETF (SPY), QQQ, and SOXX with periodic rebalancing from July 10, 2001 to present, maximizing CAGR across four distinct Annual MDD risk tolerance tiers (<=20%, <=30%, <=40%, and Unconstrained Calmar), integrated into the Streamlit dashboard and pushed to GitHub.

Working directory: D:\Industry\quant_turnaround_strategy
Integrity mode: development

## Requirements

### R1. Tri-Asset Historical Ingestion & Full Simplex Grid Evaluation
- Ingest daily adjusted total return price series for SPY, QQQ, and SOXX from July 10, 2001 (SOXX inception) to the present, alongside daily USD/KRW exchange rates.
- Model the complete 3-asset allocation simplex:
  $$w_{\text{SPY}} + w_{\text{QQQ}} + w_{\text{SOXX}} = 1.0, \quad w_i \ge 0$$
  evaluating all valid combinations (1% step resolution: 5,151 weight triplets) across periodic rebalancing frequencies (Quarterly, Annual, Monthly).
- Incorporate realistic transaction friction (0.05% commission + 0.02% slippage per rebalance) and track performance in both USD and KRW.

### R2. Calmar & Constrained-MDD Optimization Engine Across 4 Risk Tiers
- Calculate institutional calendar year intra-year MDD for each year (2001-2026), CAGR, Sharpe Ratio, and Calmar Ratio ($\text{CAGR} / \max_Y |\text{Annual MDD}_Y|$).
- Derive the mathematically optimal weights and Pareto-efficient allocation for four distinct risk tiers:
  1. **Tier 1 (Conservative)**: Maximize CAGR subject to Worst Annual MDD $\le 20\%$.
  2. **Tier 2 (Moderate Growth)**: Maximize CAGR subject to Worst Annual MDD $\le 30\%$.
  3. **Tier 3 (Aggressive Compounder)**: Maximize CAGR subject to Worst Annual MDD $\le 40\%$.
  4. **Tier 4 (Pure Max Calmar)**: Unconstrained global maximization of Calmar Ratio.
- Provide a rigorous crisis resilience stress breakdown for each optimal weight tier across 2001-2003 (Dot-com), 2008 (GFC), 2020 (COVID), and 2022 (Tech Bear).

### R3. Streamlit Dashboard Integration & Git Push
- Add a dedicated 6th tab to `app.py`: **"🏆 3대 ETF 최적 비중 분석 (Tri-Asset Optimizer)"** featuring:
  - Interactive ternary contour / risk-return frontier chart (CAGR vs. Worst Annual MDD).
  - 4-Tier summary comparison cards and year-by-year performance matrix table.
  - Interactive weight slider for custom user experimentation with instant metric updates.
  - USD ↔ KRW currency toggle.
- Create automated test verification script ensuring mathematical precision and 100% test pass rate.
- Commit all changes cleanly to Git and push to GitHub repository `jjangdol0205/Industry` (`main` branch).

## Acceptance Criteria

### Quantitative Rigor & Accuracy
- [ ] 100% of the 5,151 weight triplets are evaluated over the entire 2001-07-10 to present period.
- [ ] Optimal weights, CAGR, Worst Annual MDD, Calmar Ratio, and Sharpe Ratio are precisely identified and documented for all 4 risk tiers.
- [ ] Historical drawdowns during 2002, 2008, 2020, and 2022 are tabulated for each optimal tier.

### Software Quality & Deployment
- [ ] Tab 6 renders cleanly in Streamlit without syntax, layout, or runtime errors.
- [ ] Automated verification script validates data integrity, non-negativity of weights, and Calmar formulas.
- [ ] All code is committed and pushed to `https://github.com/jjangdol0205/Industry` (`main` branch).

## 2026-10-13T07:08:00Z

A deep, real-world actionable quantitative analysis and execution tool determining: (1) the exact optimal annual-rebalancing weights between QQQ and SOXX from 2001 to present, (2) the optimal hybrid allocation combining QQQ, SOXX, and up to 2 individual 52-week-low turnaround stocks with strict -10% stop-loss, auto-replacement with next-best candidate, and +25% partial profit-taking, and (3) a rigorous valuation, NAV discount, and holding decision analysis for 76 shares of SK Square (402340.KS), integrated into the Streamlit dashboard and pushed to GitHub.

Working directory: D:\Industry\quant_turnaround_strategy
Integrity mode: development

## Requirements

### R1. QQQ vs. SOXX Annual Rebalancing Optimal Weights (2001–2026)
- Model annual rebalancing on the first trading day of January across all 26 calendar years (2001-07-10 to present), factoring in 0.07% rebalance friction.
- Conduct a 1D grid search from 0% QQQ / 100% SOXX to 100% QQQ / 0% SOXX in 1% increments (101 allocations).
- Derive the exact mathematical peak for Calmar Ratio ($\text{CAGR} / \max_Y |\text{Annual MDD}_Y|$), Sharpe Ratio, and compound return across USD and KRW.
- Provide a sensitivity table around the optimal peak and document year-by-year returns and drawdowns during historical crises (2002, 2008, 2020, 2022).

### R2. Hybrid QQQ + SOXX + 2-Stock Turnaround Engine (-10% Stop & Auto-Replacement)
- Implement a 4-asset backtesting engine: QQQ, SOXX, and up to 2 individual 52-week-low turnaround stocks screened point-in-time without lookahead bias.
- Execution parameters:
  - Max capacity: 2 individual stocks concurrently.
  - Strict daily **-10% hard stop-loss**: immediately exit upon closing at or below -10% from entry, and automatically buy the next-in-line qualified candidate on the following trading day (or hold cash/ETF if no candidate passes gates).
  - Profit-taking: +25% gain triggers 50% partial exit; remainder held until annual rebalancing or stop trigger.
  - Annual rebalancing of core ETF weights on the first trading day of January.
- Search the weight space ($w_{\text{QQQ}}, w_{\text{SOXX}}, w_{\text{Stocks}}$ where $w_{\text{Stocks}} \in [0\%, 30\%]$ split equally between 2 stocks) to determine the optimal allocation maximizing Return relative to Annual MDD.

### R3. SK Square (402340.KS, 76 Shares) Valuation & Holding Decision
- Perform a thorough fundamental valuation of SK Square:
  - Net Asset Value (NAV) and current NAV discount calculation based on its 20.07% stake in SK Hynix (000660.KS) plus unlisted investment assets (Tmap Mobility, 11st, Content Wavve, SK Shieldus proceeds).
  - Assessment of Corporate Value-up policies (share cancellations, dividend yields, capital return).
  - Comparison of risk-return profile: Expected upside of holding SK Square vs. reallocating capital into the QQQ/SOXX quant portfolio.
  - Clear, actionable recommendation for the user's 76-share position (Hold vs. Reallocate/Trim).

### R4. Streamlit Dashboard Integration & Git Push
- Add a dedicated view/tab in `app.py`: **"🎯 실전 투자 포트폴리오 & SK스퀘어 진단 (Real Investment & SK Square)"** displaying:
  - Annual QQQ/SOXX optimal weight curve and sensitivity table.
  - 2-Stock turnaround trade log with stop-loss and auto-replacement timestamps.
  - SK Square NAV discount barometer and holding recommendation card.
  - USD ↔ KRW toggle.
- Verify through automated verification scripts.
- Commit all code cleanly and push to GitHub repository `jjangdol0205/Industry` (`main` branch).

## Acceptance Criteria

### Quantitative Rigor & Accuracy
- [ ] R1 annual rebalancing evaluates all 101 weight combinations with exact Calmar and annual MDD tabulated.
- [ ] R2 backtester strictly enforces the -10% stop-loss and next-candidate auto-replacement logic with zero lookahead bias.
- [ ] R3 provides exact mathematical NAV discount calculations and an objective recommendation on holding 76 shares of SK Square.

### Verification & Delivery
- [ ] Dedicated Streamlit UI components render cleanly with zero exceptions.
- [ ] Automated verification script confirms mathematical precision and 100% test pass rate.
- [ ] All code and documentation are committed and pushed to `https://github.com/jjangdol0205/Industry` on `main` branch.

## 2026-10-13T07:08:47Z

[CRITICAL USER REQUIREMENT UPDATE - YEAR-END VS. YEAR-BEGINNING AFTER-TAX REBALANCING STUDY]

The user has added a crucial real-world requirement regarding taxation and rebalancing timing:
"리밸런싱을 연말에 하는게 좋을지 연초에 하는게 좋을지도 알려줘 결국 세후 수익률이 가장 중요하자나"

Please expand Requirement R1 and the tax engine to comprehensively compare:
1. Year-End Rebalancing (연말 12월 하순 리밸런싱) vs. Year-Beginning Rebalancing (연초 1월 초순 리밸런싱).
2. Korean overseas stock tax dynamics:
   - Annual 2.5M KRW basic deduction utilization ("Use it or lose it" each calendar year).
   - Tax-loss harvesting opportunities at year-end vs. Tax payment deferral advantage of year-beginning (delaying tax liability payment by up to 16 months, compounding capital).
3. Exact quantitative comparison:
   - Final Net After-Tax NAV (세후 순자산).
   - Total taxes paid over the 2001-2026 period.
   - After-Tax CAGR, After-Tax Annual MDD, and After-Tax Calmar ratio for Year-End vs. Year-Beginning.
4. Deliver a definitive practical recommendation in the report and dashboard for maximizing after-tax returns.

## 2026-10-13T07:09:37Z

[CRITICAL USER REQUIREMENT UPDATE - HIGHER-YIELD ETF ALTERNATIVES STUDY]

The user has explicitly requested:
"그리고 qqq랑 soxx말고 더 같은 전략인데 더 수익률이 잘나올수 있는 etf로도 진행해줘"

Please expand the project requirements to evaluate alternative high-yield ETF pairs using the exact same strategy:

1. Unlevered High-Octane Tech/Semi Candidates:
   - SMH (VanEck Semiconductor, higher Nvidia/TSMC concentration) vs. SOXX
   - XLK (Tech SPDR) or VGT (Vanguard Info Tech, pure software+hardware without retail/telecom drag) vs. QQQ

2. Leveraged Compounders with Rebalancing & Risk Control:
   - 2x Leveraged pairs: QLD (2x Nasdaq) + USD (2x Semiconductor) or selective leverage overlays.
   - 3x pairs: TQQQ + SOXL (evaluate whether annual rebalancing with risk control can tame the volatility decay).

3. Quantitative Comparative Matrix:
   - Evaluate CAGR, Worst Annual MDD, Sharpe, and Calmar ratio.
   - Determine which ETF combination genuinely delivers the absolute highest return while respecting drawdown limits.
   - Incorporate these findings and interactive comparisons into the dashboard and final report.

## 2026-10-13T07:11:02Z

[CRITICAL USER REQUIREMENT UPDATE - REAL-WORLD ACTIVE TRADING FRICTION & TAXATION REALISM]

The user has explicitly mandated:
"액티브 매매 같은경우엔 실전투자와 똑같이 해야해 그냥 기계적으로 말고 거래비용이랑 세금 등을 전부다 고려해서"

For all active trades (the 52-week low turnaround stock selections, -10% stop-loss executions, automatic replacements, and +25% profit-taking):
1. Realistic Execution & Slippage on Stops:
   - Do NOT assume fills at exact round prices. Stop-loss executions must include market slippage (e.g., 10-15 bps or gap-down slippage).
   - Brokerage commissions on both entry and exit (5-8 bps).
   - Regulatory fees (SEC fee and FINRA TAF on sells).

2. Trade-by-Trade Capital Gains Realization & Tax Modeling:
   - Track realized gain/loss per closed trade lot (FIFO basis).
   - Aggregate annual net realized capital gains from active trades + ETF rebalances.
   - Deduct 2.5M KRW basic deduction, calculate 22% Korean overseas capital gains tax, and deduct it from portfolio cash at year-end.
   - Account for settlement timing (T+1 cash availability).

3. Friction Drag & Turnover Analysis:
   - The report and dashboard MUST explicitly display:
     * Annual Turnover Rate (%)
     * Total Transaction Costs Paid ($ / KRW)
     * Total Overseas Stock Taxes Paid ($ / KRW)
     * Gross Strategy Return vs. Net After-Tax/After-Cost Return.
   - Show whether active trading truly adds net alpha over passive ETF holding after all real-world frictions!

## 2026-10-13T07:12:52Z

[CRITICAL USER DIRECTIVE - ACTIONABLE TODAY PLAYBOOK MANDATE]

The user has explicitly instructed:
"지금 현재 상황에서 내가 할 가장 최적의 방안으로 진행해야 해"

In addition to the historical simulation and mathematical proofs, the deliverables MUST include a concrete, definitive "Executive Action Playbook for Today":
1. Immediate Decision on SK Square (76 Shares):
   - Clear, unambiguous verdict: Sell & Reallocate NOW vs. Hold until X price/date vs. Partial trim.
   - Specific rationale based on current market price, SK Hynix valuation, and opportunity cost.
2. Exact Starting Portfolio Allocation for Day 1:
   - Specific dollar / percentage weights to execute right now in the user's brokerage account (e.g. QQQ %, SOXX/SMH %, Cash/Turnaround slot %).
3. Practical Step-by-Step Operating Manual:
   - Weekly checklist: What to check every Friday (screening, stop-loss check).
   - Annual checklist: Exact date to rebalance in December/January for maximum tax efficiency.
   - Stop-loss execution checklist: What exact order type to place (Stop Limit vs. Market) upon triggering -10%.

Ensure this practical playbook is prominently highlighted in the executive summary, README, and Streamlit dashboard.
