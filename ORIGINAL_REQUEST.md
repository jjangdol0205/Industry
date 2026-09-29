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
