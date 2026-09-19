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

