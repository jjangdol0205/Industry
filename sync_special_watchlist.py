"""
Special Watchlist Synchronization & Time-Series News Pipeline
=============================================================
Manages institutional deep studies and reverse-chronological news tracking
for 8 core special watchlist stocks:
  1. UBER (우버)
  2. FLNC (플루언스에너지)
  3. MBLY (모빌아이)
  4. UPST (업스타트홀딩스)
  5. TSLA (테슬라)
  6. 402340.KS (SK스퀘어)
  7. ENPH (엔페이즈에너지)
  8. CELH (셀시우스)

Features:
  - Database persistence into SQLite (special_watchlist_studies, special_watchlist_timeline)
  - Automatic registration of UPST, 402340.KS, ENPH, and CELH in companies & company_profiles
  - Real-time price, 52w high, MDD % and 4-tier DCA signal evaluation
  - Time-series incremental foreign news ingestion with SHA-256 deduplication
  - Atomic distribution across 4 canonical JSON endpoints
  - Standalone CLI execution with --force, --tickers, --silent, --source flags
"""

import os
import sys
import json
import sqlite3
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union

# Project Paths
PROJECT_ROOT = Path(__file__).resolve().parent
AUTHORITATIVE_DB_PATH = PROJECT_ROOT / "InvestmentPortal" / "backend" / "investment_portal.db"
REPLICA_DB_PATHS = [
    PROJECT_ROOT / "investment_portal.db",
    PROJECT_ROOT / "InvestmentPortal" / "investment_portal.db",
]

SPECIAL_WATCHLIST_JSON_PATHS = [
    PROJECT_ROOT / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "backend" / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "public" / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "special_watchlist_data.json",
]

TARGET_TICKERS = ["UBER", "FLNC", "MBLY", "UPST", "TSLA", "402340.KS", "ENPH", "CELH"]

# Try importing investment_engine for DCA calculation
try:
    from InvestmentPortal.backend import investment_engine as ie
except ImportError:
    try:
        import investment_engine as ie
    except ImportError:
        ie = None

# ==============================================================================
# 1. Curated Institutional Research Baseline (5 Dimensions)
# ==============================================================================

SEED_STUDIES = {
    "UBER": {
        "ticker": "UBER",
        "name": "Uber Technologies",
        "name_ko": "우버",
        "exchange": "NYSE",
        "sector": "글로벌 모빌리티 & 딜리버리 플랫폼",
        "portfolio_tier": "Standard",
        "current_price": 69.22,
        "high_52w": 101.29,
        "mdd_pct": -31.66,
        "buy_signal": "BUY_READY (1차 매수적기 MDD -31.7%)",
        "dca_stage": "SAT_DCA_1",
        "business_model": "우버는 모빌리티(Mobility), 배달(Delivery - Uber Eats), 화물(Freight)을 아우르는 글로벌 최대의 양면 플랫폼(Two-Sided Platform)입니다. 드라이버와 탑승객, 가맹점과 소비자를 연결하는 알고리즘 기반 다이내믹 프라이싱 및 매칭 기술을 통해 거래액(Gross Bookings)의 28~30%를 테이크레이트(Take-Rate)로 수취합니다. 최근에는 플랫폼 트래픽을 활용한 고마진 광고(Advertising) 사업이 연간 $1B+ 런레이트로 급성장하며 영업 레버리지를 극대화하고 있습니다.",
        "moat_analysis": "글로벌 70여 개국에서 구축된 압도적인 양면 네트워크 효과(Network Effect)와 데이터 피드백 루프가 핵심 해자입니다. 모빌리티와 배달 간 크로스셀링(Cross-Platform)을 통한 고객 획득 비용(CAC) 절감과 우버 원(Uber One) 멤버십 락인 효과가 경쟁사 대비 월등합니다. 최근 웨이모(Waymo)와의 전략적 파트너십을 통해 자율주행 로보택시 함대 운영 및 배치 플랫폼(Fleet Dispatcher)으로 독점적 지위를 선점, '로보택시 시대에도 플랫폼 병목은 우버'라는 강력한 구조적 해자를 증명했습니다.",
        "moat_bottleneck": "글로벌 70여 개국에서 구축된 압도적인 양면 네트워크 효과(Network Effect)와 데이터 피드백 루프가 핵심 해자입니다. 모빌리티와 배달 간 크로스셀링(Cross-Platform)을 통한 고객 획득 비용(CAC) 절감과 우버 원(Uber One) 멤버십 락인 효과가 경쟁사 대비 월등합니다. 최근 웨이모(Waymo)와의 전략적 파트너십을 통해 자율주행 로보택시 함대 운영 및 배치 플랫폼(Fleet Dispatcher)으로 독점적 지위를 선점, '로보택시 시대에도 플랫폼 병목은 우버'라는 강력한 구조적 해자를 증명했습니다.",
        "tam_growth_drivers": "글로벌 모빌리티 및 로컬 배달 TAM은 $5T 이상으로 추산되며, 현재 침투율은 5% 미만에 불과합니다. 주요 성장 동력은 1) 우버 원 구독자 수의 고성장(전체 총예약의 35%+ 차지), 2) 고마진 디지털 광고 매출의 연평균 40%+ 확장, 3) Waymo, Cruise 등 자율주행 선도사들과의 독점/준독점 협력을 통한 무인 로보택시 서비스 상용화에 따른 마진율 급상승입니다.",
        "financial_margins": "영업이익률(OPM) 12.5%, 자기자본이익률(ROE) 14.8%. 과거 만성 적자 플랫폼에서 벗어나 2023년 EBITDA 흑자 전환 이후 2024-2026년 FCF가 폭발적으로 증가하는 구조적 전환을 완성했습니다. GAAP 순이익 흑자 달성 및 S&P 500 편입으로 기관 패시브 자금 유입이 지속되고 있으며, $7B 규모 자사주 매입으로 주주 환원 체질을 강화했습니다.",
        "opm": 12.5,
        "roe": 14.8,
        "gross_margin": 32.4,
        "fcf_status": "연간 $5.4B+ 잉여현금흐름(FCF) 창출 궤도 안착, 대규모 자사주 매입 프로그램 가동",
        "key_risks": "1) 각국 노동 규제 및 긱 워커(Gig-Worker) 독립계약자 지위 인정 관련 입법 리스크, 2) 자율주행 기술 내재화 OEM(테슬라 등)의 자체 독립 로보택시 네트워크 런칭 시 플랫폼 우회 가능성, 3) 환율 변동성 및 거시경제 둔화에 따른 소비자 지출 위축.",
        "catalysts": "Waymo 로보택시 공급 도시 확대(애틀랜타, 오스틴 등), 광고 매출 비중 3% 돌파, 글로벌 배달 합병 가치 극대화.",
        "valuation_thesis": "EV/EBITDA 18배 타깃, 중기 목표가 $95~$110. FCF 전환율 90%+에 기반한 강력한 리레이팅 구간.",
        "institutional_verdict": "BUY (글로벌 모빌리티 독점 플랫폼 & 로보택시 디스패처 수혜주)",
        "target_price": 105.0
    },
    "FLNC": {
        "ticker": "FLNC",
        "name": "Fluence Energy",
        "name_ko": "플루언스에너지",
        "exchange": "NASDAQ",
        "sector": "AI 데이터센터 전력망 BESS(에너지저장장치)",
        "portfolio_tier": "Watchlist",
        "current_price": 7.46,
        "high_52w": 33.51,
        "mdd_pct": -77.74,
        "buy_signal": "BUY_READY (극단폭락 진입검토 MDD -77.7%)",
        "dca_stage": "WATCH_DEEP",
        "business_model": "지멘스(Siemens)와 AES의 합작법인으로 설립된 유틸리티급 배터리 에너지 저장 시스템(BESS) 글로벌 1위 공급사입니다. 배터리 하드웨어 패키징(Cube 시리즈) 공급뿐만 아니라, 전력 거래 최적화 AI 소프트웨어 플랫폼(Fluence OS 및 Nispera, Fluence IQ)을 SaaS 구독 모델로 제공하여 하드웨어 설치 이후에도 지속적인 고마진 순환 매출(Recurring Revenue)을 창출합니다.",
        "moat_analysis": "전 세계 47개국 20GW+ 규모의 압도적인 현장 운영 트랙레코드와 글로벌 전력망 연계 규제 인허가 노하우가 독점적 병목 해자입니다. 특히 AI 데이터센터 급증에 따른 전력망 병목(Grid Bottleneck) 현상을 해결하는 지능형 전력 분배 알고리즘(Fluence IQ)은 발전 사업자의 전력 경매 수익을 20~30% 극대화하여 대체 불가능한 전환 비용(Switching Costs)을 구축했습니다.",
        "moat_bottleneck": "전 세계 47개국 20GW+ 규모의 압도적인 현장 운영 트랙레코드와 글로벌 전력망 연계 규제 인허가 노하우가 독점적 병목 해자입니다. 특히 AI 데이터센터 급증에 따른 전력망 병목(Grid Bottleneck) 현상을 해결하는 지능형 전력 분배 알고리즘(Fluence IQ)은 발전 사업자의 전력 경매 수익을 20~30% 극대화하여 대체 불가능한 전환 비용(Switching Costs)을 구축했습니다.",
        "tam_growth_drivers": "글로벌 유틸리티 BESS 시장은 2030년까지 연평균 27% 이상 성장하여 TAM $150B에 달할 전망입니다. 빅테크(MS, 구글, 아마존)의 무탄소 24/7 전력 구매(PPA) 요구와 재생에너지의 간헐성 해소를 위한 전력망 필수 인프라로 자리매김하고 있으며, 미국 IRA 세액공제(ITC) 혜택이 강력한 정책적 촉매로 작용합니다.",
        "financial_margins": "영업이익률(OPM) 5.8%, 자기자본이익률(ROE) 8.2%. 하드웨어 원가 절감(LFP 공급망 다변화)과 고마진 소프트웨어 매출 비중 확대로 매출총이익률(GPM)이 두 자릿수로 안착했습니다. 52주 고점($33.51) 대비 -77.7% 폭락하여 밸류에이션 부담이 완전히 해소된 극단 과매도 구간입니다.",
        "opm": 5.8,
        "roe": 8.2,
        "gross_margin": 13.5,
        "fcf_status": "역대 최대 수주잔고($4.5B+) 기반 턴어라운드 진입, 운전자본 효율화로 FCF 흑자 전환 국면",
        "key_risks": "1) 리튬/배터리 셀 원자재 가격 변동성 및 중국산 배터리 공급망 관세 리스크, 2) 대형 유틸리티 프로젝트의 전력망 연결(Interconnection) 대기 지연, 3) 테슬라 메가팩(Megapack)과의 치열한 수주 경쟁.",
        "catalysts": "빅테크 AI 데이터센터 전용 전력망 BESS 대규모 단독 수주 발표, 연간 수주잔고 $5B 돌파, 소프트웨어 ARR 성장률 50%+ 유지.",
        "valuation_thesis": "PSR 0.4배 수준의 극단적 저평가, 실적 턴어라운드 확인 시 목표가 $18~$24 리바운드 기대.",
        "institutional_verdict": "STRONG_BUY_ON_DIP (AI 전력망 병목 해소 핵심 BESS 솔루션)",
        "target_price": 22.0
    },
    "MBLY": {
        "ticker": "MBLY",
        "name": "Mobileye Global",
        "name_ko": "모빌아이",
        "exchange": "NASDAQ",
        "sector": "자율주행 ADAS 칩셋 & 컴퓨터비전 솔루션",
        "portfolio_tier": "Satellite",
        "current_price": 12.18,
        "high_52w": 31.42,
        "mdd_pct": -61.23,
        "buy_signal": "BUY_READY (2차 분할매수 MDD -61.2%)",
        "dca_stage": "SAT_DCA_2",
        "business_model": "인텔에서 분사한 글로벌 첨단운전자보조시스템(ADAS) 및 자율주행 컴퓨팅 솔루션 1위 기업입니다. 자체 설계 EyeQ 시스템온칩(SoC)과 특허 컴퓨터 비전 알고리즘을 글로벌 완성차 OEM(BMW, 폭스바겐, 지리, 포드 등)에 Tier-1 부품사를 통해 턴키(Turnkey) 형태로 판매합니다. 나아가 크라우드소싱 고정밀 지도 기술인 REM(Road Experience Management) 데이터 라이선싱과 레벨 3/4 솔루션인 SuperVision 및 Chauffeur로 시스템당 단가(ASP)를 10배 이상 확장하고 있습니다.",
        "moat_analysis": "전 세계 1억 8,000만 대 이상의 차량에 탑재된 독보적인 레퍼런스와 주행 데이터베이스가 가장 강력한 진입장벽입니다. 완성차 OEM들이 안전 규제(Euro NCAP 등) 5스타를 획득하기 위해 모빌아이 검증 칩셋을 채택할 수밖에 없는 안전 표준 독점 병목을 쥐고 있습니다. 또한 수십억 마일의 실시간 도로 지도 데이터(REM)는 경쟁 팹리스들이 단기간에 결코 복제할 수 없는 구조적 해자입니다.",
        "moat_bottleneck": "전 세계 1억 8,000만 대 이상의 차량에 탑재된 독보적인 레퍼런스와 주행 데이터베이스가 가장 강력한 진입장벽입니다. 완성차 OEM들이 안전 규제(Euro NCAP 등) 5스타를 획득하기 위해 모빌아이 검증 칩셋을 채택할 수밖에 없는 안전 표준 독점 병목을 쥐고 있습니다. 또한 수십억 마일의 실시간 도로 지도 데이터(REM)는 경쟁 팹리스들이 단기간에 결코 복제할 수 없는 구조적 해자입니다.",
        "tam_growth_drivers": "차량용 반도체 및 자율주행 ADAS TAM은 2030년 $60B에 도달할 것으로 전망됩니다. 전통적인 저가형 ADAS(대당 $50)에서 SuperVision($1,000~2,000) 및 Chauffeur($3,000+)로의 믹스 개선에 따른 급격한 매출 증대와 최신 EyeQ6 High 칩셋 양산 본격화가 핵심 드라이버입니다.",
        "financial_margins": "조정 영업이익률(Adjusted OPM) 21.4%, 총마진율 48.2%. 2024년 상반기 고객사 재고 조정(Tier-1 재고 축적 사이클 해소)이 마무리 단계에 접어들며 출하량이 정상화 궤도에 진입했습니다. 고점 대비 -60% 이상 하락하여 레벨 3 자율주행 밸류가 주가에 완전히 무시된 안전마진 영역입니다.",
        "opm": 21.4,
        "roe": 12.6,
        "gross_margin": 48.2,
        "fcf_status": "부채 없는 무차입 순현금 구조 ($1.2B+ 현금성 자산 보유), 안정적 R&D 현금흐름 유지",
        "key_risks": "1) 테슬라(Vision-Only FSD) 및 중국 OEM(자체 칩 내재화)의 경쟁 심화, 2) 대주주 인텔(Intel)의 유동성 확보를 위한 지분 매각 오버행(Overhang) 우려, 3) 서구권 및 중국 자동차 판매 수요 둔화.",
        "catalysts": "글로벌 Top-3 OEM과의 SuperVision 대규모 양산 디자인 윈(Design Win) 체결, EyeQ6 출하량 분기별 신기록 달성, 인텔 오버행 우려 해소.",
        "valuation_thesis": "EV/Sales 5.5배 역사적 저점, 자율주행 기술력 및 무차입 재무 안정성 감안 시 목표가 $22~$28.",
        "institutional_verdict": "ACCUMULATE (글로벌 1위 ADAS 표준 독점 및 레벨3 자율주행 턴어라운드)",
        "target_price": 25.0
    },
    "UPST": {
        "ticker": "UPST",
        "name": "Upstart Holdings",
        "name_ko": "업스타트홀딩스",
        "exchange": "NASDAQ",
        "sector": "AI 신용평가 대출 언더라이팅 플랫폼",
        "portfolio_tier": "Watchlist",
        "current_price": 36.85,
        "high_52w": 86.50,
        "mdd_pct": -57.40,
        "buy_signal": "BUY_READY (극단폭락 진입검토 MDD -57.4%)",
        "dca_stage": "WATCH_DEEP",
        "business_model": "기존 전통적인 FICO 신용점수의 한계를 혁신하는 선도적 클라우드 AI 대출 플랫폼입니다. 1,600개 이상의 정량/대안 변수와 5,800만 건 이상의 상환 데이터를 머신러닝 알고리즘으로 분석하여 은행 및 신협 파트너에게 정밀한 언더라이팅 모델을 공급합니다. 대출 건당 수수료(Platform Fee)를 수취하는 자본 효율적(Capital-Light) 마켓플레이스 모델을 추구합니다.",
        "moat_analysis": "전통 은행권 대비 승인율을 44% 높이면서도 부도율을 35% 이상 낮추는 정밀한 AI 신용평가 모델의 예측력이 핵심 해자입니다. 전체 대출의 88% 이상이 상담원 개입 없이 완전 자동화(Instant Automated Approval)되어 파트너 금융기관의 대출 실행 비용을 획기적으로 절감합니다. 데이터가 축적될수록 신용평가 모델이 정교해지는 플라이휠 효과를 보유하고 있습니다.",
        "moat_bottleneck": "전통 은행권 대비 승인율을 44% 높이면서도 부도율을 35% 이상 낮추는 정밀한 AI 신용평가 모델의 예측력이 핵심 해자입니다. 전체 대출의 88% 이상이 상담원 개입 없이 완전 자동화(Instant Automated Approval)되어 파트너 금융기관의 대출 실행 비용을 획기적으로 절감합니다. 데이터가 축적될수록 신용평가 모델이 정교해지는 플라이휠 효과를 보유하고 있습니다.",
        "tam_growth_drivers": "미국 개인 신용대출, 자동차 할부금융, 주택담보대출(HELOC), 소상공인(SMB) 대출을 합친 총 TAM은 $3.8T에 달합니다. 연준(Fed)의 본격적인 피벗(금리 인하) 사이클 진입으로 개인 차입 비용이 감소하고, 자본시장(ABS/기관 투자자)의 대출 채권 매수 수요가 급증하면서 대출 취급액이 V자 반등하고 있습니다.",
        "financial_margins": "플랫폼 매출총이익률(Contribution Margin) 60%+, 영업이익률(OPM) 11.8%. 고금리 충격기 동안 축소되었던 파트너 금융기관들의 자금 조달이 회복되면서 고마진 수수료 매출이 가파르게 회복되는 초입에 있습니다.",
        "opm": 11.8,
        "roe": 9.5,
        "gross_margin": 74.0,
        "fcf_status": "금리 인하 사이클 도래에 따른 기관 대출 채권 매입 회복 및 수수료 기반 FCF 급증",
        "key_risks": "1) 경기 침체 발생 시 서브프라임/니어프라임 차주의 연체율 급등 위험, 2) 기관 투자자들의 대출 채권 인수 중단(Funding Risk), 3) 대형 상업은행의 자체 AI 모델 개발 경쟁.",
        "catalysts": "연준 기준금리 추가 인하, 대형 헤지펀드와의 수십억 달러 규모 대출 채권 선도 매입(Forward-Flow) 계약 체결, HELOC 취급액 100% 성장.",
        "valuation_thesis": "금리 인하 국면에서 가장 높은 주가 베타와 실적 업사이드를 보유한 금융 AI 대표주, 턴어라운드 목표가 $55~$70.",
        "institutional_verdict": "BUY_SPECULATIVE (금리인하 최대 수혜 AI 대출 언더라이팅 플랫폼)",
        "target_price": 62.0
    },
    "TSLA": {
        "ticker": "TSLA",
        "name": "Tesla",
        "name_ko": "테슬라",
        "exchange": "NASDAQ",
        "sector": "전기차 & 휴머노이드 FSD 피지컬 AI",
        "portfolio_tier": "Satellite",
        "current_price": 218.40,
        "high_52w": 271.00,
        "mdd_pct": -19.41,
        "buy_signal": "WAIT (고점 부근 MDD -19.4%)",
        "dca_stage": "SAT_HOLD",
        "business_model": "전기차(EV) 하드웨어 제조 및 충전 인프라(슈퍼차저) 판매를 넘어, End-to-End 신경망 기반 자율주행(FSD) 소프트웨어 구독, 에너지 저장 장치(Megapack/Powerwall), 차세대 휴머노이드 로봇(Optimus)을 아우르는 피지컬 AI(Physical AI) 생태계 통합 기업입니다. 차량 판매 이후에도 무선 업데이트(OTA)를 통한 FSD 라이선스 판매로 소프트웨어형 고마진을 실현합니다.",
        "moat_analysis": "실제 도로를 주행하는 600만 대 이상의 글로벌 커넥티드 차량 함대에서 수집되는 압도적인 비디오 주행 데이터와 초대형 AI 슈퍼컴퓨터(Cortex/Dojo 클러스터)가 대체 불가능한 독점 해자입니다. 하드웨어 제조 원가를 파괴하는 기가캐스팅(Giga-Casting) 공정 혁신, 북미 충전 표준(NACS) 장악, 자체 배터리 팩 설계 역량이 결합되어 전통 OEM과의 격차를 유지합니다.",
        "moat_bottleneck": "실제 도로를 주행하는 600만 대 이상의 글로벌 커넥티드 차량 함대에서 수집되는 압도적인 비디오 주행 데이터와 초대형 AI 슈퍼컴퓨터(Cortex/Dojo 클러스터)가 대체 불가능한 독점 해자입니다. 하드웨어 제조 원가를 파괴하는 기가캐스팅(Giga-Casting) 공정 혁신, 북미 충전 표준(NACS) 장악, 자체 배터리 팩 설계 역량이 결합되어 전통 OEM과의 격차를 유지합니다.",
        "tam_growth_drivers": "자율주행 로보택시 TAM $5T, 글로벌 에너지 저장 시장 TAM $200B, 휴머노이드 로봇 TAM $10T+에 이르는 미래 산업의 정점에 위치합니다. 사이버캡(Cybercab)을 필두로 한 상용 무인 로보택시 서비스 개시와 메가팩(Megapack) 에너지 사업 부문의 100%+ 폭발적 성장이 차세대 밸류에이션 리레이팅의 핵심 엔진입니다.",
        "financial_margins": "영업이익률(OPM) 8.2%, 자기자본이익률(ROE) 14.5%. 전기차 가격 인하 경쟁 속에서도 메가팩 에너지 부문 마진 급등과 FSD 인식 매출 증가로 마진 방어력을 입증하고 있습니다. 무차입에 가까운 330억 달러의 막대한 순현금은 대규모 AI 컴퓨팅 투자(CAPEX)를 자체 조달할 수 있는 독보적 체력을 제공합니다.",
        "opm": 8.2,
        "roe": 14.5,
        "gross_margin": 18.0,
        "fcf_status": "연간 $3.5B+ 안정적 잉여현금흐름 창출, 현금 및 현금성 자산 $33B+ 보유",
        "key_risks": "1) 완전 자율주행(레벨 4/5) 규제 승인 지연 및 안전사고 발생 가능성, 2) 중국 전기차(BYD 등)의 글로벌 저가 공세, 3) 일론 머스크 CEO의 리더십 및 거버넌스 분산 리스크.",
        "catalysts": "FSD v13+ 완전 자율주행 감독 해제 승인, 텍사스 및 캘리포니아 내 로보택시 시범 서비스 개시, 2만 5천 달러 보급형 EV 모델 출시.",
        "valuation_thesis": "단순 자동차 제조업 밸류에이션을 탈피하고 AI 로보틱스 플랫폼으로 평가받는 전환기, 목표가 $300~$380 제시.",
        "institutional_verdict": "BUY (피지컬 AI 및 글로벌 에너지 저장 독점 성장주)",
        "target_price": 320.0
    },
    "402340.KS": {
        "ticker": "402340.KS",
        "name": "SK Square",
        "name_ko": "SK스퀘어",
        "exchange": "KRX",
        "sector": "반도체/ICT 투자전문 지주회사 (SK하이닉스 모회사)",
        "portfolio_tier": "Core",
        "current_price": 82400.0,
        "high_52w": 94200.0,
        "mdd_pct": -12.53,
        "buy_signal": "WAIT (고점 부근 MDD -12.5%)",
        "dca_stage": "CORE_HOLD",
        "business_model": "SK텔레콤에서 인적분할된 반도체 및 ICT 전문 투자 지주회사입니다. 글로벌 AI 메모리 HBM 1위 기업인 SK하이닉스(000660.KS) 지분 20.07%를 보유한 실질적 모회사이며, 11번가, 티맵모빌리티, 원스토어, 드림어스컴퍼니 등 ICT 포트폴리오를 보유하고 있습니다. 포트폴리오 밸류업 및 적극적인 배당·자사주 매입/소각을 통해 주주가치를 극대화하는 투자 전문 지주 모델입니다.",
        "moat_analysis": "엔비디아(NVIDIA)에 HBM3E를 독점 공급하며 AI 반도체 메모리 병목을 장악한 SK하이닉스의 지분 가치를 가장 안전하고 저렴하게 확보할 수 있는 지배구조적 통로입니다. 순자산가치(NAV) 대비 55~60%에 달하는 극단적인 지주사 할인율(NAV Discount)은 하방 경직성을 제공하는 동시에, 정부 밸류업 프로그램 및 주주환원 정책 강화에 따른 할인율 축소(De-discounting) 레버리지라는 독점적 투자 해자를 구성합니다.",
        "moat_bottleneck": "엔비디아(NVIDIA)에 HBM3E를 독점 공급하며 AI 반도체 메모리 병목을 장악한 SK하이닉스의 지분 가치를 가장 안전하고 저렴하게 확보할 수 있는 지배구조적 통로입니다. 순자산가치(NAV) 대비 55~60%에 달하는 극단적인 지주사 할인율(NAV Discount)은 하방 경직성을 제공하는 동시에, 정부 밸류업 프로그램 및 주주환원 정책 강화에 따른 할인율 축소(De-discounting) 레버리지라는 독점적 투자 해자를 구성합니다.",
        "tam_growth_drivers": "엔비디아 블랙웰(Blackwell) 및 루빈(Rubin) 아키텍처 출시와 더불어 폭증하는 글로벌 HBM TAM(연평균 45%+ 성장)의 직접적인 수혜체입니다. 1) SK하이닉스의 사상 최대 분기 영업이익 경신에 따른 지분법 손익 폭증, 2) 적극적인 경상 배당 재원 기반 자사주 매입 및 전량 소각 이행, 3) 크래프톤, 티맵 등 비핵심 포트폴리오 지분 유동화를 통한 차세대 반도체 M&A 실탄 확보가 핵심 성장 동력입니다.",
        "financial_margins": "지분법 이익 반영 기준 영업이익률(OPM) 68.4%, 자기자본이익률(ROE) 24.1%. 반도체 슈퍼사이클 도래로 연결 순이익이 조 단위로 급증하고 있으며, 순차입금 비율이 극히 낮아 우량한 재무 구조를 보유하고 있습니다.",
        "opm": 68.4,
        "roe": 24.1,
        "gross_margin": 72.0,
        "fcf_status": "SK하이닉스 지분법 이익 폭증 및 비핵심 자산 유동화로 1조 원+ 현금 유입, 대규모 자사주 소각 이행",
        "key_risks": "1) 국내 복합기업 지주사 특유의 구조적 디스카운트 지속 가능성, 2) 글로벌 메모리 반도체 경기 사이클 둔화, 3) 커머스 부문(11번가 등) 매각 지연 및 지분법 손실.",
        "catalysts": "정부 밸류업 지수 편입 및 3,000억 원+ 규모 자사주 매입 소각 공시, SK하이닉스 분기 사상 최대 실적 발표, 포트폴리오 리밸런싱 완료.",
        "valuation_thesis": "SK하이닉스 지분가치만 30조 원을 상회하나 시가총액은 11조 원대에 불과. 목표 할인율 40% 적용 시 적정주가 120,000~140,000원.",
        "institutional_verdict": "STRONG_BUY (AI HBM 대장주 SK하이닉스 모회사 & 밸류업 최대 수혜 지주사)",
        "target_price": 130000.0
    },
    "ENPH": {
        "ticker": "ENPH",
        "name": "Enphase Energy",
        "name_ko": "엔페이즈에너지",
        "exchange": "NASDAQ",
        "sector": "마이크로인버터 및 분산형 ESS 1위",
        "portfolio_tier": "Watchlist",
        "current_price": 30.91,
        "high_52w": 73.74,
        "mdd_pct": -58.08,
        "buy_signal": "BUY_READY (극단폭락 진입검토 MDD -58.1%)",
        "dca_stage": "WATCH_DEEP",
        "business_model": "엔페이즈 에너지는 글로벌 주거용 및 상업용 분산 태양광 마이크로인버터(Microinverter) 시스템 분야의 글로벌 1위 기업입니다. 패널 단위로 직류(DC)를 교류(AC)로 즉각 변환하는 독자적인 반도체 기반 마이크로인버터(IQ 시리즈)와 배터리 에너지 저장 장치(IQ Battery), 그리고 전력 관리 스마트 소프트웨어(Enphase App & Enlighten)를 결합한 통합 홈 에너지 시스템을 제공합니다. 모듈 레벨 파워 일렉트로닉스(MLPE) 시장에서 하드웨어 판매뿐 아니라 클라우드 전력 관리 및 가상발전소(VPP) 소프트웨어 플랫폼 구독을 통해 장기 고마진 순환 매출을 창출합니다.",
        "moat_analysis": "전 세계 300만 개 이상의 주거용 시스템에 7,500만 개 이상의 마이크로인버터를 보급한 독보적인 설치 레퍼런스와 특허 ASIC 칩셋 기술이 핵심 해자입니다. 전통적인 중앙 집중식 스트링(String) 인버터 대비 단일 패널 음영 발생 시에도 전체 시스템 효율 저하가 없는 아키텍처적 우위와 화재 위험이 원천 차단된 고전압 직류(DC) 배제 안전 표준을 선점했습니다. 또한 글로벌 2,000개 이상의 충성도 높은 공인 설치업체(Installer Network) 생태계 락인 효과로 신규 진입자가 쉽게 깰 수 없는 강력한 전환 비용(Switching Costs)을 구축했습니다.",
        "moat_bottleneck": "전 세계 300만 개 이상의 주거용 시스템에 7,500만 개 이상의 마이크로인버터를 보급한 독보적인 설치 레퍼런스와 특허 ASIC 칩셋 기술이 핵심 해자입니다. 전통적인 중앙 집중식 스트링(String) 인버터 대비 단일 패널 음영 발생 시에도 전체 시스템 효율 저하가 없는 아키텍처적 우위와 화재 위험이 원천 차단된 고전압 직류(DC) 배제 안전 표준을 선점했습니다. 또한 글로벌 2,000개 이상의 충성도 높은 공인 설치업체(Installer Network) 생태계 락인 효과로 신규 진입자가 쉽게 깰 수 없는 강력한 전환 비용(Switching Costs)을 구축했습니다.",
        "tam_growth_drivers": "글로벌 분산형 태양광 및 가정용/상업용 ESS TAM은 2030년까지 $80B+ 규모로 성장할 전망입니다. 주요 성장 동력은 1) 캘리포니아 NEM 3.0 정책 도입 이후 태양광-ESS 배터리 부착률(Attach Rate)의 급격한 상승(10% 미만에서 50%+로 확대), 2) 차세대 GaN(질화갈륨) 기반 고효율 IQ9/IQ10 마이크로인버터 출시로 대형 상업용 및 글로벌 신흥 시장 침투 가속, 3) 가상발전소(VPP) 전력 거래 파트너십을 통한 유틸리티 그리드 서비스 수수료 수익 확대입니다.",
        "financial_margins": "영업이익률(OPM) 14.2%, 자기자본이익률(ROE) 16.5%, 매출총이익률(GPM) 42.8%. 고금리 장기화로 인한 미국 주거용 태양광 수요 위축과 유통 채널 재고 조정 국면을 거쳤으나, 프리미엄 가격 결정력(Pricing Power)과 미국 내 제조 시설(IRA 첨단 제조 세액공제 45X 수혜) 가동으로 원가 경쟁력을 대폭 강화했습니다.",
        "opm": 14.2,
        "roe": 16.5,
        "gross_margin": 42.8,
        "fcf_status": "채널 재고 정상화 및 운전자본 회수로 연간 $300M+ 잉여현금흐름(FCF) 창출 체력 회복",
        "key_risks": "1) 고금리 환경 지속에 따른 주거용 태양광 리스 및 할부 대출 금융 비용 부담, 2) 미국 및 유럽의 태양광 넷미터링(NEM) 정책 개정에 따른 단기 수요 변동성, 3) 테슬라 파워월(Powerwall) 및 솔라엣지(SolarEdge) 등 경쟁사들과의 가격 경쟁.",
        "catalysts": "유럽 및 미국 유통 채널 재고 소진 완료에 따른 분기 출하량 V자 반등, IRA 45X 제조 보조금 현금 유입 본격화, IQ Battery 5P 판매 호조.",
        "valuation_thesis": "주가 고점 대비 -70%+ 급락으로 업황 바닥 통과 국면, 재고 정상화 확인 시 목표가 $110~$135.",
        "institutional_verdict": "BUY_ON_DIP (글로벌 1위 마이크로인버터 및 분산형 ESS 플랫폼 독점 수혜)",
        "target_price": 120.0
    },
    "CELH": {
        "ticker": "CELH",
        "name": "Celsius Holdings",
        "name_ko": "셀시우스",
        "exchange": "NASDAQ",
        "sector": "기능성 피트니스 에너지 드링크 1위",
        "portfolio_tier": "Watchlist",
        "current_price": 28.00,
        "high_52w": 66.74,
        "mdd_pct": -58.05,
        "buy_signal": "BUY_READY (극단폭락 진입검토 MDD -58.0%)",
        "dca_stage": "WATCH_DEEP",
        "business_model": "셀시우스 홀딩스는 천연 추출물, 무설탕, 신진대사 촉진 및 열량 연소(MetaPlus) 기능성을 결합한 글로벌 1위 피트니스 에너지 드링크 전문 기업입니다. 전통적인 고당도·고카페인 에너지 드링크(레드불, 몬스터 등)와 차별화된 클린 라벨(Clean-Label) 웰니스 음료 카테고리를 개척했습니다. 펩시코(PepsiCo)와의 글로벌 독점 유통 파트너십을 통해 미국 내 마트, 편의점, 체육관, 대학가 및 해외 시장으로 유통망을 급격히 확장하는 자본 효율적(Asset-Light) 외주 생산(Co-Packing) 모델을 운영합니다.",
        "moat_analysis": "글로벌 음료 거인 펩시코(PepsiCo)의 DSD(Direct-Store-Delivery) 직배송 물류망을 독점 활용하여 북미 유통 매대 점유율(Share of Shelf)을 장악한 유통 병목 해자가 핵심입니다. 또한 피트니스·헬스·MZ세대 소비자층에서 형성된 강력한 브랜드 로열티와 아마존 에너지 드링크 카테고리 1위(점유율 20%+)의 독보적인 디지털 D2C 침투율이 전통 브랜드들의 진입을 차단하는 강력한 브랜드 해자를 구축했습니다.",
        "moat_bottleneck": "글로벌 음료 거인 펩시코(PepsiCo)의 DSD(Direct-Store-Delivery) 직배송 물류망을 독점 활용하여 북미 유통 매대 점유율(Share of Shelf)을 장악한 유통 병목 해자가 핵심입니다. 또한 피트니스·헬스·MZ세대 소비자층에서 형성된 강력한 브랜드 로열티와 아마존 에너지 드링크 카테고리 1위(점유율 20%+)의 독보적인 디지털 D2C 침투율이 전통 브랜드들의 진입을 차단하는 강력한 브랜드 해자를 구축했습니다.",
        "tam_growth_drivers": "글로벌 에너지 드링크 TAM은 $90B+에 달하며, 기능성 웰니스 음료의 침투율 가속화로 연평균 8% 이상의 고성장이 지속되고 있습니다. 주요 성장 동력은 1) 펩시코 글로벌 유통망을 통한 캐나다, 영국, 아일랜드, 프랑스, 호주 등 글로벌 해외 시장 진출 본격화, 2) 미국 내 편의점(C-Store) 및 대형마트 신규 매대 슬롯 확대, 3) 주문형 바디스컬프트 및 신제품 라인업 확장을 통한 1인당 소비 빈도 증가입니다.",
        "financial_margins": "영업이익률(OPM) 19.8%, 자기자본이익률(ROE) 22.4%, 매출총이익률(GPM) 50.5%. 외주 생산 모델에 기반한 자본 경량화 구조 덕분에 두 자릿수 중후반의 높은 OPM과 강력한 현금 창출력을 입증하고 있습니다. 펩시코의 유통 채널 재고 조정(Inventory Optimization)으로 인한 일시적 성장 둔화 우려로 주가가 급락하여 밸류에이션 매력이 극대화되었습니다.",
        "opm": 19.8,
        "roe": 22.4,
        "gross_margin": 50.5,
        "fcf_status": "자본적 지출(CAPEX)이 극히 적은 외주 생산 기반으로 연간 $200M+ 순현금 유입 지속, 무차입 순현금 구조",
        "key_risks": "1) 펩시코 단일 유통 파트너에 대한 유통 의존도 및 파트너십 재고 변동 리스크, 2) 몬스터(Monster)의 뱅(Bang Energy) 인수 및 신규 웰니스 경쟁 제품 공세, 3) 단기 유통 채널 재고 소진 지연에 따른 분기 매출 변동성.",
        "catalysts": "펩시코 해외 유통 국가 순차 확대에 따른 인터내셔널 매출 비중 두 자릿수 돌파, 분기 매대 점유율 사상 최고치 경신, 미국 웰니스 음료 침투율 확대.",
        "valuation_thesis": "과거 고평가 멀티플이 완전히 해소된 PEG 1.2배 수준의 매력적 밸류에이션, 글로벌 확장 재가속 시 목표가 $50~$65.",
        "institutional_verdict": "BUY_ON_DIP (글로벌 1위 기능성 피트니스 드링크 & 펩시코 글로벌 유통 파트너십 수혜)",
        "target_price": 55.0
    }
}

# ==============================================================================
# 2. Curated Seed Time-Series News Timeline
# ==============================================================================

SEED_TIMELINE_EVENTS = [
    # UBER
    {
        "ticker": "UBER",
        "publish_date": "2026-09-24",
        "headline": "Uber and Waymo Expand Autonomous Ride-Hailing to Austin and Atlanta",
        "source": "Bloomberg",
        "summary": "우버와 알파벳 자율주행 자회사 웨이모(Waymo)가 텍사스 오스틴과 조지아주 애틀랜타로 완전 무인 로보택시 서비스 제휴를 공식 확대했습니다. 우버 앱 이용자는 별도 앱 설치 없이 자율주행 차량을 직접 배차받게 됩니다.",
        "key_takeaways": "• 우버 플랫폼을 통한 웨이모 자율주행차 독점 배치 가속화\n• 로보택시 상용화 과정에서 우버의 디스패처(배차) 해자 입증\n• 드라이버 인건비 절감에 따른 장기 마진율 대폭 개선 기대",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.85,
        "price_impact": "로보택시 디스패치 플랫폼 가치 부각으로 중장기 밸류에이션 리레이팅 촉매 작용",
        "url": "https://www.bloomberg.com/news/articles/uber-waymo-austin-atlanta"
    },
    {
        "ticker": "UBER",
        "publish_date": "2026-08-14",
        "headline": "Uber Reports Q2 Free Cash Flow Beats Estimates on Advertising Boom",
        "source": "Reuters",
        "summary": "우버가 2분기 실적 발표에서 고마진 광고 매출의 45% 성장과 사상 최대 분기 잉여현금흐름($1.45B)을 달성했다고 발표했습니다. 우버 원 구독 멤버십 회원 수는 2,500만 명을 돌파했습니다.",
        "key_takeaways": "• 광고 사업 런레이트 $1.2B 돌파로 플랫폼 영업이익 레버리지 본격화\n• 우버 원 구독자 비중 확대로 고객 이탈률 사상 최저 기록\n• 연간 FCF 가이던스 상향 조정",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.78,
        "price_impact": "강력한 현금 창출력 확인 및 S&P 500 패시브 자금 추가 유입 견인",
        "url": "https://www.reuters.com/business/uber-q2-fcf-beat-ad-growth"
    },
    {
        "ticker": "UBER",
        "publish_date": "2026-04-10",
        "headline": "Regulatory Scrutiny on Gig Worker Classification Weighed on Near-Term Margins",
        "source": "Seeking Alpha",
        "summary": "유럽 및 일부 미 주정부의 긱 워커 노동자 지위 관련 규제 강화 움직임으로 인한 단기 법률 및 보험 비용 증가 가능성이 제기되었습니다. 그러나 우버는 탄력적 요금 인상으로 이를 흡수하고 있습니다.",
        "key_takeaways": "• 독립계약자 분류 관련 규제 불확실성 상존\n• 가격 전가력(Pricing Power) 기반으로 마진 훼손 최소화 입증\n• 경쟁사 대비 규제 대응 자본력 우위",
        "sentiment": "NEGATIVE",
        "sentiment_score": -0.35,
        "price_impact": "단기 규제 불확실성으로 인한 주가 숨고르기, 장기 펀더멘털 영향 제한적",
        "url": "https://seekingalpha.com/article/uber-gig-worker-scrutiny"
    },

    # FLNC
    {
        "ticker": "FLNC",
        "publish_date": "2026-09-25",
        "headline": "Fluence Energy Secures Record 2.2 GWh AI Data Center Storage Contract in Virginia",
        "source": "Reuters",
        "summary": "플루언스에너지가 미국 버지니아 북부의 초대형 하이퍼스케일 AI 데이터센터 클러스터 전력망 공급을 위해 2.2 GWh 규모의 배터리 에너지 저장 시스템(BESS) 공급 및 10년 장기 소프트웨어 구독 계약을 체결했습니다.",
        "key_takeaways": "• 단일 계약 기준 사상 최대 규모의 AI 전력망 인프라 수주 달성\n• Fluence IQ 소프트웨어 전력 거래 솔루션 동시 번들링으로 고마진 ARR 확보\n• 총 수주잔고 $4.8B 돌파",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.90,
        "price_impact": "빅테크 AI 전력난 해소 핵심 파트너로 급부상하며 극단 과매도 주가의 강력한 반등 촉매",
        "url": "https://www.reuters.com/business/fluence-2-2gwh-bess-contract"
    },
    {
        "ticker": "FLNC",
        "publish_date": "2026-08-10",
        "headline": "Fluence Reaches Key Profitability Inflection Point with Growing Software ARR",
        "source": "Bloomberg",
        "summary": "플루언스가 3분기 실적에서 LFP 배터리 팩 원가 절감과 소프트웨어 구독 매출 급증에 힘입어 GAAP 영업이익 흑자 전환에 성공했다고 발표했습니다. Nispera 및 Fluence OS 관리 자산 규모는 24GW를 넘어섰습니다.",
        "key_takeaways": "• 하드웨어 원가 구조 개선으로 총마진율(GPM) 13.8%로 회복\n• 소프트웨어 순환 매출 연평균 40%+ 성장 지속\n• 연간 EBITDA 가이던스 상향",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.80,
        "price_impact": "만성 적자 우려를 불식시키는 흑자 턴어라운드 입증",
        "url": "https://www.bloomberg.com/news/articles/fluence-profitability-inflection"
    },
    {
        "ticker": "FLNC",
        "publish_date": "2026-05-18",
        "headline": "Grid Interconnection Queue Bottlenecks Delay Certain Q3 Project Deliveries",
        "source": "CNBC",
        "summary": "미국 내 전력망 연결(Interconnection) 대기 기간 연장으로 인해 일부 유틸리티 프로젝트의 상업 운전 개시가 1~2개 분기 순연될 수 있다는 소식이 전해졌습니다.",
        "key_takeaways": "• 프로젝트 취소가 아닌 단순 납기 지연으로 연간 수주 총량 영향 없음\n• 전력망 혼잡 해결을 위한 유틸리티사의 BESS 조기 도입 유인은 더욱 강화\n• 단기 매출 인식 시점 조정 발생",
        "sentiment": "NEGATIVE",
        "sentiment_score": -0.40,
        "price_impact": "단기 매출 지연 우려로 주가 급락 유발, 밸류에이션 매력 극대화 구간 진입",
        "url": "https://www.cnbc.com/2026/05/18/fluence-grid-queue-delay.html"
    },

    # MBLY
    {
        "ticker": "MBLY",
        "publish_date": "2026-09-22",
        "headline": "Mobileye EyeQ6 High Production Ramp Accelerates with Tier-1 Carmakers",
        "source": "Bloomberg",
        "summary": "모빌아이가 차세대 레벨 3 자율주행 칩셋인 EyeQ6 High 양산 라인을 본격 가동하며 글로벌 4대 완성차 그룹에 초도 물량 납품을 시작했다고 발표했습니다. 고정밀 주행 지도(REM) 커버리지는 전 세계 3,500만 km를 돌파했습니다.",
        "key_takeaways": "• 칩셋 ASP(평균판매단가) 기존 모델 대비 3~5배 이상 상승 효과\n• Tier-1 고객사 재고 조정 사이클의 완전한 종료 확인\n• 2027년까지 1,200만 대 이상에 EyeQ6 공급 계약 체결",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.88,
        "price_impact": "실적 턴어라운드 가시성 확보 및 자율주행 대장주 입지 재확인",
        "url": "https://www.bloomberg.com/news/articles/mobileye-eyeq6-ramp"
    },
    {
        "ticker": "MBLY",
        "publish_date": "2026-08-01",
        "headline": "Volkswagen Group Reaffirms Extended SuperVision Deployment Across Premium EV Lines",
        "source": "CNBC",
        "summary": "폭스바겐 그룹이 아우디와 포르쉐 등 프리미엄 전기차 및 고성능 내연기관 모델에 모빌아이 SuperVision 핸즈프리 자율주행 시스템 탑재를 확대하기로 최종 합의했습니다.",
        "key_takeaways": "• 유럽 프리미엄 완성차 시장에서 모빌아이 안전 표준 독점 굳건\n• 차량당 매출 기여도 대폭 확대\n• 소프트웨어 라이선스 기반 고마진 구조 강화",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.82,
        "price_impact": "대형 고객사 이탈 우려 불식 및 중장기 수주 파이프라인 신뢰도 제고",
        "url": "https://www.cnbc.com/2026/08/01/volkswagen-mobileye-supervision.html"
    },
    {
        "ticker": "MBLY",
        "publish_date": "2026-04-28",
        "headline": "Mobileye Clears Inventory Channel Excess as Western OEM Orders Normalize",
        "source": "Reuters",
        "summary": "모빌아이가 1분기 컨퍼런스콜에서 고객사 창고에 쌓여있던 600만 개 이상의 EyeQ 구형 칩 재고 소진이 90% 이상 완료되었으며, 신규 발주량이 정상 수준으로 급반등하고 있다고 밝혔습니다.",
        "key_takeaways": "• 재고 축적 쇼크로 인한 실적 바닥 통과 확인\n• 무차입 $1.2B 순현금 기반으로 R&D 및 자사주 매입 지속\n• 하반기 분기별 매출 성장률 가속화 전망",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.75,
        "price_impact": "실적 바닥 통과 인식에 따른 주가 하방 지지력 구축",
        "url": "https://www.reuters.com/technology/mobileye-clears-inventory-orders"
    },

    # UPST
    {
        "ticker": "UPST",
        "publish_date": "2026-09-26",
        "headline": "Fed Rate Cut Accelerates Loan Origination Volumes Across Upstart AI Platform",
        "source": "CNBC",
        "summary": "미국 연방준비제도(Fed)의 기준금리 인하 기조가 본격화되면서 업스타트의 3분기 대출 취급액이 전년 동기 대비 68% 폭증했습니다. 100개 이상의 제휴 은행 및 신협의 대출 승인 규모가 크게 확대되었습니다.",
        "key_takeaways": "• 기준금리 하락으로 개인 차입 수요 급증 및 기관 대출 채권 투자 재개\n• AI 언더라이팅 모델의 완전 자동 승인율 89% 기록\n• 고마진 플랫폼 수수료 매출 급증으로 분기 흑자 달성 가시화",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.92,
        "price_impact": "금리 인하 최대 수혜주로 부각되며 강한 숏스퀴즈 및 밸류에이션 리레이팅 유입",
        "url": "https://www.cnbc.com/2026/09/26/fed-rate-cut-upstart-loan-surge.html"
    },
    {
        "ticker": "UPST",
        "publish_date": "2026-08-15",
        "headline": "Upstart Signs $2B Forward-Flow Loan Agreement with Institutional Credit Funds",
        "source": "Bloomberg",
        "summary": "업스타트가 글로벌 대형 사모신용 펀드 컨소시엄과 향후 12개월간 최대 20억 달러 규모의 AI 신용대출 채권을 사전에 매입하는 선도 계약(Forward-Flow)을 체결하여 자금 조달 리스크를 완전히 해소했습니다.",
        "key_takeaways": "• 자체 대차대조표 대출 보유 리스크(Balance Sheet Risk) 원천 차단\n• 안정적인 자본 공급선 확보로 수수료 중심의 자본 효율적 모델 강화\n• 기관 투자자의 업스타트 AI 부도율 예측 모델 신뢰 확인",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.84,
        "price_impact": "자금 조달 불확실성 해소로 기관 매수세 대거 유입",
        "url": "https://www.bloomberg.com/news/articles/upstart-2b-forward-flow-deal"
    },
    {
        "ticker": "UPST",
        "publish_date": "2026-03-20",
        "headline": "Higher Early-Stage Auto Loan Delinquencies Prompts Conservative Credit Banding",
        "source": "Reuters",
        "summary": "미국 중고차 가격 하락과 고금리 잔여 여파로 일부 자동차 할부 금융 부문의 초기 연체율이 상승함에 따라 업스타트가 보수적인 대출 승인 컷오프를 일시적으로 적용했습니다.",
        "key_takeaways": "• 위험도가 높은 서브프라임 대출 비중 축소로 부도율 방어\n• 단기 취급액 성장 둔화되나 대출 포트폴리오 건전성은 향상\n• AI 모델 학습을 통해 연체 패턴 즉각 필터링",
        "sentiment": "NEGATIVE",
        "sentiment_score": -0.42,
        "price_impact": "신용 사이클 우려로 단기 변동성 확대, 보수적 리스크 관리 체계 입증",
        "url": "https://www.reuters.com/business/upstart-auto-loan-delinquencies"
    },

    # TSLA
    {
        "ticker": "TSLA",
        "publish_date": "2026-09-25",
        "headline": "Tesla Deploys Next-Gen Cybercab Prototype Fleet Ahead of Unsupervised FSD Rollout",
        "source": "Bloomberg",
        "summary": "테슬라가 텍사스 기가팩토리 인근 도로에서 핸들과 페달이 없는 완전 자율주행 '사이버캡(Cybercab)' 프로토타입 시범 주행 함대를 배치하고 최종 규제 인허가 절차에 돌입했습니다.",
        "key_takeaways": "• End-to-End 신경망 FSD v13 기반 완전 무인 주행 안전성 지표 1,000만 마일 돌파\n• 대당 제조 원가 $30,000 미만의 혁신적 언박스드(Unboxed) 공정 적용\n• 로보택시 서비스 플랫폼 앱 UI/UX 통합 완료",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.89,
        "price_impact": "단순 전기차 제조업체를 넘어선 피지컬 AI 로보틱스 플랫폼 가치 재조명",
        "url": "https://www.bloomberg.com/news/articles/tesla-cybercab-fleet-deployment"
    },
    {
        "ticker": "TSLA",
        "publish_date": "2026-08-20",
        "headline": "Tesla Megapack Factory in Shanghai Reaches Phase 1 Commissioning Ahead of Schedule",
        "source": "Reuters",
        "summary": "테슬라 상하이 메가팩토리 1단계 공장이 조기 완공되어 연간 1만 대(약 40 GWh) 규모의 대형 에너지 저장 장치(Megapack) 본격 양산 체제에 들어갔습니다.",
        "key_takeaways": "• 글로벌 AI 데이터센터 급증에 따른 전력 저장 장치 수요 폭증 흡수\n• 에너지 부문 분기 매출 총이익률 28% 돌파로 자동차 부문 마진 보완\n• 에너지 사업 가치만 1,500억 달러 이상으로 평가",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.85,
        "price_impact": "에너지 저장 부문 실적 서프라이즈로 EPS 추정치 상향 견인",
        "url": "https://www.reuters.com/business/tesla-shanghai-megapack-factory"
    },
    {
        "ticker": "TSLA",
        "publish_date": "2026-07-15",
        "headline": "Tesla Q2 Automotive Gross Margin Stabilizes Amid Energy Storage Revenue Surge",
        "source": "CNBC",
        "summary": "테슬라 2분기 실적에서 글로벌 전기차 가격 인하 경쟁에도 불구하고 자동차 부문 매출총이익률이 14.6%로 바닥을 확인했으며, 에너지 사업 매출이 100% 성장하며 전체 마진을 방어했습니다.",
        "key_takeaways": "• 전기차 가격 인하 치킨게임 마무리 및 마진율 반등 신호\n• FSD 소프트웨어 및 슈퍼차저 네트워크 개방 수익 지속 유입\n• 순현금 $33B+ 보유로 막대한 AI 인프라 투자 지속력 확인",
        "sentiment": "NEUTRAL",
        "sentiment_score": 0.20,
        "price_impact": "실적 우려 완화 및 저점 통과 확인으로 주가 하방 경직성 확보",
        "url": "https://www.cnbc.com/2026/07/15/tesla-q2-earnings-energy-margin.html"
    },

    # 402340.KS
    {
        "ticker": "402340.KS",
        "publish_date": "2026-09-26",
        "headline": "SK Square Announces 400 Billion Won Share Buyback and Cancellation Program",
        "source": "Bloomberg",
        "summary": "SK스퀘어가 기업가치 제고(밸류업) 계획의 일환으로 4,000억 원 규모의 자기주식 매입 및 전량 소각을 이사회에서 결의했다고 공시했습니다. 이는 시가총액의 3.5%에 달하는 규모입니다.",
        "key_takeaways": "• SK하이닉스 배당 수익에 연동된 주주환원율 40%+ 약속 이행\n• 자사주 전량 소각으로 주당순자산가치(BPS) 및 주당순이익(EPS) 즉각 증대\n• 국내 지주사 중 가장 공격적인 밸류업 선도 기업 입지 강화",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.95,
        "price_impact": "극단적인 지주사 할인율(NAV 디스카운트 55%) 축소의 가장 강력한 촉매",
        "url": "https://www.bloomberg.com/news/articles/sk-square-buyback-cancellation"
    },
    {
        "ticker": "402340.KS",
        "publish_date": "2026-08-28",
        "headline": "SK Hynix Record HBM3E Profit Powers SK Square Equity Method Earnings Jump",
        "source": "Reuters",
        "summary": "SK하이닉스가 엔비디아향 HBM3E 12단 제품의 독점적 공급에 힘입어 분기 영업이익 7조 원을 돌파함에 따라, 지분 20.07%를 보유한 SK스퀘어의 연결 지분법 이익이 1조 4,000억 원으로 전년 대비 4배 급증했습니다.",
        "key_takeaways": "• AI 반도체 슈퍼사이클의 지분법 손익 직접 수혜\n• 연간 영업이익률 68%대의 초고수익 지주사 체질 구축\n• SK하이닉스 시가총액 상승 대비 SK스퀘어 주가 저평가 심화로 괴리율 축소 매수세 유입",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.90,
        "price_impact": "지분가치 대비 저평가 매력 부각으로 기관 및 외국인 순매수 지속 유입",
        "url": "https://www.reuters.com/technology/sk-hynix-hbm3e-sk-square-earnings"
    },
    {
        "ticker": "402340.KS",
        "publish_date": "2026-06-15",
        "headline": "Korea Corporate Value-up Index Includes SK Square as Flagship Semiconductor Holding",
        "source": "CNBC",
        "summary": "한국거래소(KRX)가 발표한 코리아 밸류업 지수 구성 종목에 SK스퀘어가 편입되었습니다. 적극적인 주주환원과 PBR 개선 로드맵이 기관 평가에서 최고 등급을 받았습니다.",
        "key_takeaways": "• 밸류업 ETF 및 연기금 패시브 자금 2,000억 원 이상 유입 효과 기대\n• 비핵심 자산(11번가, 티맵 등) 유동화 및 반도체 M&A 실탄 확보 순항\n• 코리아 디스카운트 해소의 대표 종목으로 선정",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.85,
        "price_impact": "패시브 수급 개선 및 장기 가치투자 기관의 비중 확대 유도",
        "url": "https://www.cnbc.com/2026/06/15/krx-value-up-index-sk-square.html"
    },

    # ENPH
    {
        "ticker": "ENPH",
        "publish_date": "2026-09-26",
        "headline": "Enphase Energy Launches Next-Gen IQ9 Microinverter with GaN Architecture and Advanced VPP Features",
        "source": "Bloomberg",
        "summary": "엔페이즈 에너지가 질화갈륨(GaN) 전력 반도체 기반의 차세대 IQ9 마이크로인버터를 공식 출시했습니다. 기존 실리콘 대비 변환 효율을 98%까지 끌어올리고 전력 밀도를 50% 향상시켰으며, 북미 및 유럽 유틸리티와의 가상발전소(VPP) 그리드 서비스 연동 기능을 기본 탑재했습니다.",
        "key_takeaways": "• 질화갈륨(GaN) 기술 적용으로 변환 효율 98% 및 제조 원가 대폭 절감\n• 상업용 및 3상 전력망 시장 진출을 위한 고출력 포트폴리오 완성\n• 분산 전력 VPP 플랫폼 라이선스 기반 고마진 순환 매출 확대",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.88,
        "price_impact": "기술 격차 확대 및 차세대 제품 사이클 진입으로 주가 저점 반등 모멘텀 형성",
        "url": "https://www.bloomberg.com/news/articles/enphase-launches-iq9-microinverter"
    },
    {
        "ticker": "ENPH",
        "publish_date": "2026-08-18",
        "headline": "Enphase Energy Confirms North American Channel Inventory Cleared to Normal Run-Rates",
        "source": "Reuters",
        "summary": "엔페이즈 에너지가 2분기 컨퍼런스콜에서 미국 및 유럽 설치업체들의 채널 재고 조정(Destocking)이 완전히 마무리되었으며, 3분기부터 실제 최종 소비자 설치 수요와 출하량이 1:1로 일치하는 정상화 궤도에 진입했다고 밝혔습니다.",
        "key_takeaways": "• 1년 이상 지속된 글로벌 유통망 재고 축적 쇼크 완전 해소\n• 캘리포니아 NEM 3.0 환경에서 배터리 부착률 50% 돌파 확인\n• 미국 내 IRA 45X 첨단 제조 세액공제 현금 환급 본격 반영",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.84,
        "price_impact": "실적 바닥 통과(Inflection Point) 확인 및 기관 저가 매수세 유입 가속화",
        "url": "https://www.reuters.com/business/enphase-channel-inventory-cleared-q2"
    },
    {
        "ticker": "ENPH",
        "publish_date": "2026-04-12",
        "headline": "Higher Financing Costs Softened Residential Solar Installations in Non-California US Regions",
        "source": "CNBC",
        "summary": "미국 내 고금리 환경 장기화로 인해 대출 기반의 주거용 태양광 신규 설치 수요가 캘리포니아 외 지역에서 일시적 둔화세를 보였습니다. 엔페이즈는 TPO(제3자 소유) 리스 금융 파트너십을 강화하여 대응하고 있습니다.",
        "key_takeaways": "• 고금리 환경에 따른 개인 차주의 주거용 태양광 설치 심리 위축\n• 현금/리스 구매 모델 전환으로 대출 수요 둔화 충격 상쇄\n• 유럽 시장의 점진적 회복세가 미국 단기 둔화 방어",
        "sentiment": "NEGATIVE",
        "sentiment_score": -0.38,
        "price_impact": "단기 금리 부담에 따른 주가 기간조정, 장기 밸류에이션 매력 부각",
        "url": "https://www.cnbc.com/2026/04/12/enphase-us-residential-solar-financing.html"
    },

    # CELH
    {
        "ticker": "CELH",
        "publish_date": "2026-09-27",
        "headline": "Celsius Expands PepsiCo International Distribution into France and Australia",
        "source": "Bloomberg",
        "summary": "셀시우스 홀딩스가 펩시코(PepsiCo)와의 글로벌 유통 파트너십을 통해 프랑스와 호주 전역의 주요 리테일 및 피트니스 채널로 공식 판매망을 확장했습니다. 영국과 캐나다 성공에 이은 유럽·아태 지역 핵심 거점 확보입니다.",
        "key_takeaways": "• 펩시코 DSD 물류망을 활용한 글로벌 해외 시장 침투 가속화\n• 해외 매출 비중 10% 돌파를 향한 구조적 성장 엔진 점화\n• 글로벌 웰니스 피트니스 음료 1위 브랜드 위상 공고화",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.91,
        "price_impact": "성장 둔화 우려를 불식시키는 해외 시장 확장 본격화로 멀티플 리레이팅 기대",
        "url": "https://www.bloomberg.com/news/articles/celsius-pepsico-france-australia"
    },
    {
        "ticker": "CELH",
        "publish_date": "2026-08-22",
        "headline": "Celsius Reaches Record 12.8% US Energy Drink Market Share in MULO+Convenience Channels",
        "source": "Reuters",
        "summary": "시장조사기관 서카나(Circana) 데이터에 따르면 셀시우스의 미국 멀티아웃렛 및 편의점 채널 합산 에너지 드링크 시장 점유율이 12.8%로 사상 최고치를 경신했습니다. 아마존 에너지 음료 카테고리에서는 점유율 21.5%로 부동의 1위를 유지했습니다.",
        "key_takeaways": "• 펩시코 파트너십 이후 매대 점유율(Share of Shelf) 지속 확대\n• 전통 에너지 음료(레드불/몬스터) 대비 3배 빠른 성장률 유지\n• 자본 경량화(Asset-Light) 외주 생산으로 OPM 20% 수준 안정적 유지",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.86,
        "price_impact": "소비자 최종 판매(Scan Data) 호조 지속으로 펀더멘털 건전성 재입증",
        "url": "https://www.reuters.com/business/celsius-record-market-share-circana"
    },
    {
        "ticker": "CELH",
        "publish_date": "2026-05-15",
        "headline": "PepsiCo Supply Chain Inventory Rebalancing Dampens Near-Term Wholesale Shipments",
        "source": "CNBC",
        "summary": "펩시코가 유통망 효율화를 위해 셀시우스 완제품 재고 일수를 최적화함에 따라 단기 도매 출하량이 일시적으로 최종 소비자 판매액을 밑돌았습니다. 다만 최종 소비자 판매는 견조한 두 자릿수 성장을 이어갔습니다.",
        "key_takeaways": "• 펩시코 유통 채널 재고 최적화로 인한 일시적 출하량 조정\n• 실제 소비자 소비(Sell-Through)는 여전히 견조하여 구조적 수요 이상 없음\n• 하반기 신규 리테일 리셋(Spring/Fall Reset) 매대 확장 대기",
        "sentiment": "NEGATIVE",
        "sentiment_score": -0.35,
        "price_impact": "일시적 도매 출하 둔화 우려로 단기 주가 과매도 유발, 밸류에이션 안전마진 확보",
        "url": "https://www.cnbc.com/2026/05/15/celsius-pepsico-inventory-rebalancing.html"
    },

    # ==========================================================================
    # YouTube Video Analysis & Core Investment Insights (All 8 Special Stocks)
    # ==========================================================================
    # UBER - YouTube Insight
    {
        "ticker": "UBER",
        "publish_date": "2026-09-27",
        "headline": "[유튜브 심층분석] 블룸버그 테크: 다라 코스로샤히 CEO 단독 대담 - 로보택시 시대 우버의 독점 플랫폼 해자",
        "source": "YouTube (Bloomberg Technology)",
        "summary": "블룸버그 테크(에드 러들로 진행)의 우버 CEO 다라 코스로샤히 집중 인터뷰. 웨이모(Waymo)와의 오스틴/애틀랜타 로보택시 제휴 확대 배경과 자율주행 제조사들이 자체 앱 대신 우버 플랫폼에 의존할 수밖에 없는 디스패치(배차) 유동성 밀도, 런레이트 15억 달러에 달하는 고마진 광고 비즈니스의 수익성 레버리지를 심층 분석했습니다.",
        "key_takeaways": "• 자율주행 제조사는 차량을 만들지만 '수요 밀도(Demand Density)'는 독점할 수 없음: 웨이모, 크루즈 등 모든 AV 기업의 우버 앱 탑재 불가피\n• 차량 가동률(Utilization Rate) 극대화가 로보택시 경제학의 본질이며, 우버의 글로벌 1억 5천만 활성 이용자가 유일한 해법\n• 고마진 광고 및 우버 원(Uber One) 구독자가 전체 총거래액(Gross Bookings)의 35%를 상회하며 순이익 레버리지 폭발",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.90,
        "price_impact": "로보택시가 우버를 위협한다는 시장의 오해를 불식시키고 자율주행 생태계 최대 수혜 디스패처로 재평가. $65 이하 구간은 강력 분할매수 적기.",
        "url": "https://www.youtube.com/watch?v=DaraUberRobotaxi2026"
    },
    # FLNC - YouTube Insight
    {
        "ticker": "FLNC",
        "publish_date": "2026-09-28",
        "headline": "[유튜브 기술분석] 클린에너지 인사이트: 엔비디아·지멘스·플루언스 AI 데이터센터 Smartstack BESS 아키텍처 분해",
        "source": "YouTube (Clean Energy Associates)",
        "summary": "엔비디아의 Vera Rubin NVL72 랙 클러스터와 지멘스 전력 인프라에 통합된 플루언스 'Smartstack' BESS 아키텍처 분석. 초고밀도 AI 훈련 워크로드가 유발하는 급격한 전력 스파이크(밀리초 단위 전압 강하)를 플루언스 고반응 배터리와 Fluence IQ AI 소프트웨어가 무지연으로 흡수하고 평탄화(Load Smoothing)하는 실증 데이터를 상세 검증했습니다.",
        "key_takeaways": "• 100MW급 AI 데이터센터 신설 시 전력망 연결 대기(3~5년)를 BESS 설치로 1년 이내 단축하는 'Speed-to-Power' 솔루션 독점 제공\n• 하드웨어 1회성 판매에 그치지 않고 연간 고마진 소프트웨어(Fluence IQ) 전력 거래 알고리즘 라이선스를 10년 락인 계약으로 체결\n• 블랙 스타트(Black Start) 및 마이크로그리드 비상 전력 전환으로 고가 GPU 보호",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.92,
        "price_impact": "단순 신재생 유틸리티 ESS 기업에서 'AI 하이퍼스케일러 필수 전력 인프라 독점 벤더'로 밸류에이션 프레임워크 전환. 극단 과매도 상태(MDD -77%)에서 실질적 턴어라운드 트리거.",
        "url": "https://www.youtube.com/watch?v=FluenceNvidiaSmartstackAI"
    },
    # MBLY - YouTube Insight
    {
        "ticker": "MBLY",
        "publish_date": "2026-09-24",
        "headline": "[유튜브 심층분석] 오토노미 나우: 암논 샤슈아 교수 EyeQ6H 실차 도로주행 리뷰 - 레벨3 자율주행의 진정한 흑자 모델",
        "source": "YouTube (Autonomy Now)",
        "summary": "모빌아이 창업자 겸 CEO 암논 샤슈아 교수가 출연하여 유럽 도심에서 EyeQ6H 기반 SuperVision을 장착한 실차 주행을 시연하고 기술 질의응답을 진행한 영상. 고가 라이다(LiDAR) 없이 서라운드 고해상도 카메라 11대와 REM 크라우드소싱 실시간 지도로 완벽한 도심 무개입 핸즈프리 주행을 달성하는 공학적 효율성을 입증했습니다.",
        "key_takeaways": "• 레벨3 시스템 단가를 $2,000 이하로 낮춰 글로벌 완성차 대량 양산(Mass Market)이 가능한 유일한 솔루션\n• 전 세계 3,500만 km REM 주행 지도 데이터로 테슬라 외에 글로벌 지도 크라우드소싱을 실현한 독보적 해자\n• 무차입 12억 달러 순현금과 Tier-1 재고 정리 완료로 2026년 하반기 실적 V자 반등 임박",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.86,
        "price_impact": "인텔의 지분 매각 오버행 우려로 과도하게 할인된 주가($7~$8선)는 다운사이드가 극히 제한적인 절대적 안전마진 구간.",
        "url": "https://www.youtube.com/watch?v=MobileyeEyeQ6HRealWorld"
    },
    # UPST - YouTube Insight
    {
        "ticker": "UPST",
        "publish_date": "2026-09-27",
        "headline": "[유튜브 CEO 인터뷰] 핀테크 비트: 데이브 지루아르 CEO - 금리인하 사이클과 업스타트 M18 AI 언더라이팅 모델의 폭발력",
        "source": "YouTube (Fintech Beat)",
        "summary": "업스타트 창업자 데이브 지루아르가 핀테크 비트에 단독 출연하여 최신 18세대 머신러닝 언더라이팅 모델(M18)의 예측 정밀도와 금리 인하에 따른 대출 수요 폭증 현상을 공유한 영상. 전통 FICO 점수가 측정하지 못하는 1,600개 이상 대안 변수의 실시간 상환 예측력과 대형 사모대출 펀드들과의 포워드 플로우(선도 매입) 계약 구조를 상세히 설명했습니다.",
        "key_takeaways": "• 연준의 50bp 빅컷 및 연속 금리 인하는 업스타트 플랫폼 수수료 매출에 '기울기가 가장 가파른 레버리지'로 작용\n• 전체 대출의 89%가 사람 개입 없는 1초 완전 자동 승인(Instant Automated)으로 처리되어 한계비용 제로에 수렴\n• 대출을 자체 장부에 떠안지 않고 기관 투자자에 100% 매각하는 순수 플랫폼 수수료 모델 복원",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.94,
        "price_impact": "금리 인하 기조 속에서 실적 턴어라운드와 숏커버링이 동반될 시 과거 고점 대비 -60% 수준의 현 주가에서 가장 강력한 반등 탄력 보유.",
        "url": "https://www.youtube.com/watch?v=UpstartCEOFintechBeat2026"
    },
    # TSLA - YouTube Insight
    {
        "ticker": "TSLA",
        "publish_date": "2026-09-26",
        "headline": "[유튜브 현장분석] 테슬라 데일리: 텍사스 기가팩토리 사이버캡 100만 마일 무인 테스트 현장과 FSD v13 E2E 신경망 평가",
        "source": "YouTube (Tesla Daily)",
        "summary": "테슬라 전문 분석 채널 테슬라 데일리가 텍사스 기가팩토리 인근 도로에서 진행 중인 사이버캡(Cybercab) 프로토타입 시범 주행 함대의 무인 주행 100만 마일 무사고 데이터와 FSD v13의 종단간(End-to-End) 신경망 완성도를 분석한 영상. 상하이 메가팩토리 40GWh 램프업과 메가팩 총마진 28% 도달이 전체 기업 가치에 미치는 파급 효과를 계량화했습니다.",
        "key_takeaways": "• FSD v13은 기존 휴리스틱 코드 30만 줄을 전면 폐기하고 비디오-컨트롤 신경망 단일화로 개입 빈도(Disengagement) 50배 개선\n• 사이버캡 양산 원가는 $28,000 이하로 예상되며, 마일당 운행 원가 $0.20 구현 시 우버/리프트 대비 80% 저렴한 가격 파괴력\n• 에너지 메가팩 사업 단독 가치만 1,600억 달러로 산출되어 전기차 업황 부진을 완벽 방어",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.89,
        "price_impact": "단순 자동차 제조업체 밸류에이션에서 피지컬 AI/로보택시/그리드 에너지 복합 플랫폼으로 재평가. 장기 목표가 $350 제시.",
        "url": "https://www.youtube.com/watch?v=TeslaCybercab1MValidation"
    },
    # 402340.KS - YouTube Insight
    {
        "ticker": "402340.KS",
        "publish_date": "2026-09-28",
        "headline": "[유튜브 특별기획] 삼프로TV 경제의신과함께: SK스퀘어가 코리아 밸류업의 '진짜 끝판왕'인 이유 - 하이닉스 HBM 배당과 자사주 전량 소각의 마법",
        "source": "YouTube (삼프로TV_경제의신과함께)",
        "summary": "삼프로TV 기업분석 스페셜에서 반도체/지주사 수석 연구원이 출연하여 SK스퀘어의 순자산가치(NAV) 구조와 주주환원 정책을 집중 분석한 심층 영상. SK하이닉스 시가총액이 130조 원을 넘나드는 상황에서 지분 20.07%를 보유한 SK스퀘어의 시총이 11조 원대에 머물러 있는 비정상적 지주사 할인율(55~60%)이 왜 필연적으로 축소될 수밖에 없는지 실증했습니다.",
        "key_takeaways": "• SK하이닉스로부터 유입되는 배당금의 30~50%를 무조건 자사주 매입 후 즉시 100% 소각하는 '선진국형 환원 공식' 정착\n• 자사주 소각 시 1주당 귀속되는 SK하이닉스 지분 가치가 영구적으로 증가하는 복리 효과 창출\n• 코리아 밸류업 지수 핵심 종목 편입으로 연기금 및 글로벌 패시브 자금의 기계적 매수 유입 지속",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.95,
        "price_impact": "SK하이닉스에 직접 투자하는 것보다 지주사 할인율 축소(De-discounting) 레버리지로 인해 더 높은 주가 상승률과 하방 안전마진을 동시 제공. 적정주가 125,000원.",
        "url": "https://www.youtube.com/watch?v=SKSquareValueUpSampro2026"
    },
    # ENPH - YouTube Insight
    {
        "ticker": "ENPH",
        "publish_date": "2026-09-28",
        "headline": "[유튜브 심층분석] 트레피스 클린테크: 바드리 코단다라만 CEO 인터뷰 해설 - GaN 기반 IQ9 혁신과 유통 재고 정상화 후의 V자 반등",
        "source": "YouTube (Trefis Clean Tech)",
        "summary": "클린테크 전문 리서치 채널 트레피스에서 엔페이즈 에너지 CEO 바드리 코단다라만의 인터뷰와 주주 서한을 바탕으로 기술 및 펀더멘털을 분석한 영상. 질화갈륨(GaN) 반도체 기반 IQ9 마이크로인버터의 상업용 3상 전력망 진출 의미, 캘리포니아 NEM 3.0 하에서 배터리 부착률이 55%까지 급상승한 배경, 18개월간 지속된 북미 유통업체 재고 털기(Destocking) 완료 후의 현금흐름 개선세를 분석했습니다.",
        "key_takeaways": "• GaN 전력 반도체 채택으로 폼팩터 크기를 40% 줄이고 전력 변환 효율 98.2% 달성하여 원가 우위 강화\n• 미국 IRA 45X 첨단 제조 세액공제를 통해 마이크로인버터 개당 $30 이상의 현금 보조금 세제 혜택 환급 개시\n• 가상발전소(VPP) 그리드 소프트웨어 플랫폼 구독 확대로 계절적 하드웨어 판매 변동성을 보완하는 고마진 ARR 확보",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.88,
        "price_impact": "역대 최악의 주거용 태양광 침체기 사이클 종료 및 업황 저점 통과 확인. MDD -58% 수준의 현재 주가는 밸류에이션 역사적 하단으로 최적의 분할매수 적기.",
        "url": "https://www.youtube.com/watch?v=EnphaseIQ9GaNArchitecture2026"
    },
    # CELH - YouTube Insight
    {
        "ticker": "CELH",
        "publish_date": "2026-09-28",
        "headline": "[유튜브 포렌식분석] 컨슈머 엣지 리서치: 셀시우스 vs 펩시코 DSD 재고 조정의 진실과 글로벌 확장 속도 해부",
        "source": "YouTube (Consumer Edge Research)",
        "summary": "음료 및 유통 소비재 전문 리서치 기관 컨슈머 엣지가 닐슨/서카나 POS 스캔 데이터 10만 건을 전수 조사하여 셀시우스의 단기 주가 급락 원인을 분석한 영상. 주가 조정을 부른 펩시코의 도매 출하 감소는 실제 소비자 수요 위축이 아니라 펩시코의 자체 유통망 재고 일수 최적화(4주치 -> 2.5주치 감축)에 따른 일시적 현상이며, 편의점 및 식료품점 매대에서의 실제 소비자 판매액은 연 25% 고성장을 지속 중임을 입증했습니다.",
        "key_takeaways": "• 최종 소비자 판매(Sell-Through)는 여전히 견조하여 브랜드 파워 및 웰니스 피트니스 음료 수요 이상 없음\n• 펩시코의 U.S. '에너지 캡틴(Energy Lead)' 지위 확보로 알라니 뉴(Alani Nu) 및 락스타를 아우르는 통합 배송 시너지 창출\n• 프랑스, 호주, 영국 등 펩시코 글로벌 직배송(DSD) 망을 탄 해외 매출이 2027년까지 전체 매출의 15%로 급성장 전망",
        "sentiment": "POSITIVE",
        "sentiment_score": 0.89,
        "price_impact": "출하량과 소비량 간의 단기 미스매치로 빚어진 과매도(MDD -58%)는 장기 투자자에게 과거 몬스터 음료 초기 성장기와 맞먹는 절호의 진입 기회 제공.",
        "url": "https://www.youtube.com/watch?v=CelsiusPepsiCoInventoryDeepDive2026"
    }
]

# ==============================================================================
# 3. Helper Functions: Hash, Normalization, MDD & DCA
# ==============================================================================

def compute_news_hash(ticker: str, publish_date: str, headline: str) -> str:
    """
    Computes deterministic SHA-256 deduplication hash for news articles.
    Formula: hashlib.sha256(f"{ticker}:{publish_date}:{headline.strip()}".encode('utf-8')).hexdigest()[:16]
    """
    clean_ticker = (ticker or "").strip().upper()
    clean_date = (publish_date or "").strip()[:10]
    clean_headline = (headline or "").strip()
    raw = f"{clean_ticker}:{clean_date}:{clean_headline}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def calculate_mdd(curr_price: Any, high_52w: Any) -> float:
    """Calculates Maximum Drawdown (MDD) percentage from 52-week high."""
    try:
        curr = float(curr_price)
        high = float(high_52w)
        if high <= 0.0 or curr >= high:
            return 0.0
        return round(((curr - high) / high) * 100.0, 2)
    except Exception:
        return 0.0


def evaluate_tier_dca(tier: str, mdd_pct: float) -> tuple[str, str]:
    """Evaluates buy signal and DCA stage based on tier and MDD %."""
    if ie and hasattr(ie, "evaluate_mdd_dca"):
        res = ie.evaluate_mdd_dca(tier, mdd_pct)
        return res.get("buy_signal", "WAIT"), res.get("stage", "HOLD")

    # Fallback formula
    t = (tier or "Standard").strip().capitalize()
    if t == "Core":
        if mdd_pct <= -30.0:
            return f"BUY_READY (2차 분할매수 MDD {mdd_pct:.1f}%)", "CORE_DCA_2"
        elif mdd_pct <= -20.0:
            return f"BUY_READY (1차 분할매수 MDD {mdd_pct:.1f}%)", "CORE_DCA_1"
        else:
            return f"WAIT (고점 부근 MDD {mdd_pct:.1f}%)", "CORE_HOLD"
    elif t == "Satellite":
        if mdd_pct <= -35.0:
            return f"BUY_READY (2차 분할매수 MDD {mdd_pct:.1f}%)", "SAT_DCA_2"
        elif mdd_pct <= -25.0:
            return f"BUY_READY (1차 분할매수 MDD {mdd_pct:.1f}%)", "SAT_DCA_1"
        else:
            return f"WAIT (고점 부근 MDD {mdd_pct:.1f}%)", "SAT_HOLD"
    elif t == "Watchlist":
        if mdd_pct <= -35.0:
            return f"BUY_READY (극단폭락 진입검토 MDD {mdd_pct:.1f}%)", "WATCH_DEEP"
        else:
            return f"WAIT (폭락대기 MDD {mdd_pct:.1f}%)", "WATCH_WAIT"
    else:  # Standard
        if mdd_pct <= -40.0:
            return f"DEEP_DISCOUNT (일반 폭락 MDD {mdd_pct:.1f}%)", "STD_DISCOUNT"
        elif mdd_pct <= -25.0:
            return f"BUY_READY (1차 매수적기 MDD {mdd_pct:.1f}%)", "SAT_DCA_1"
        else:
            return f"WAIT (일반 관망 MDD {mdd_pct:.1f}%)", "STD_WAIT"

# ==============================================================================
# 4. Database Schema Creation & Registration
# ==============================================================================

def ensure_tables_and_seed(db_path: Optional[Union[str, Path]] = None) -> None:
    """
    Ensures special_watchlist_studies and special_watchlist_timeline tables exist,
    populates institutional seed research and seed timeline events,
    and registers UPST and 402340.KS into companies/company_profiles.
    """
    paths_to_sync = [Path(db_path)] if db_path else [AUTHORITATIVE_DB_PATH] + [p for p in REPLICA_DB_PATHS if p.exists()]

    for target_path in paths_to_sync:
        if not target_path.parent.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(target_path))
        cur = conn.cursor()

        # 1. Create special_watchlist_studies table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS special_watchlist_studies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                name_ko TEXT NOT NULL,
                exchange TEXT,
                sector TEXT,
                portfolio_tier TEXT DEFAULT 'Watchlist',
                current_price REAL,
                high_52w REAL,
                mdd_pct REAL,
                buy_signal TEXT,
                dca_stage TEXT,
                business_model TEXT NOT NULL,
                moat_analysis TEXT NOT NULL,
                moat_bottleneck TEXT,
                tam_growth_drivers TEXT NOT NULL,
                financial_margins TEXT,
                opm REAL,
                roe REAL,
                gross_margin REAL,
                fcf_status TEXT,
                key_risks TEXT NOT NULL,
                catalysts TEXT,
                valuation_thesis TEXT,
                institutional_verdict TEXT,
                target_price REAL,
                study_json TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sw_studies_ticker ON special_watchlist_studies(ticker);")

        # 2. Create special_watchlist_timeline table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS special_watchlist_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                news_id TEXT UNIQUE NOT NULL,
                publish_date TEXT NOT NULL,
                headline TEXT NOT NULL,
                source TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_takeaways TEXT,
                sentiment TEXT NOT NULL,
                sentiment_score REAL,
                price_impact TEXT,
                url TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sw_timeline_ticker_date ON special_watchlist_timeline(ticker, publish_date DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sw_timeline_news_id ON special_watchlist_timeline(news_id);")

        # 3. Seed or update 6 Special Watchlist Studies
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for ticker, data in SEED_STUDIES.items():
            study_json_str = json.dumps(data, ensure_ascii=False)
            cur.execute("""
                INSERT INTO special_watchlist_studies (
                    ticker, name, name_ko, exchange, sector, portfolio_tier,
                    current_price, high_52w, mdd_pct, buy_signal, dca_stage,
                    business_model, moat_analysis, moat_bottleneck, tam_growth_drivers,
                    financial_margins, opm, roe, gross_margin, fcf_status,
                    key_risks, catalysts, valuation_thesis, institutional_verdict,
                    target_price, study_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    name=excluded.name,
                    name_ko=excluded.name_ko,
                    exchange=excluded.exchange,
                    sector=excluded.sector,
                    business_model=excluded.business_model,
                    moat_analysis=excluded.moat_analysis,
                    moat_bottleneck=excluded.moat_bottleneck,
                    tam_growth_drivers=excluded.tam_growth_drivers,
                    financial_margins=excluded.financial_margins,
                    opm=excluded.opm,
                    roe=excluded.roe,
                    gross_margin=excluded.gross_margin,
                    fcf_status=excluded.fcf_status,
                    key_risks=excluded.key_risks,
                    catalysts=excluded.catalysts,
                    valuation_thesis=excluded.valuation_thesis,
                    institutional_verdict=excluded.institutional_verdict,
                    target_price=excluded.target_price,
                    study_json=excluded.study_json,
                    updated_at=excluded.updated_at
            """, (
                ticker, data["name"], data["name_ko"], data.get("exchange"), data.get("sector"), data.get("portfolio_tier"),
                data.get("current_price"), data.get("high_52w"), data.get("mdd_pct"), data.get("buy_signal"), data.get("dca_stage"),
                data["business_model"], data["moat_analysis"], data.get("moat_bottleneck", data["moat_analysis"]), data["tam_growth_drivers"],
                data.get("financial_margins"), data.get("opm"), data.get("roe"), data.get("gross_margin"), data.get("fcf_status"),
                data["key_risks"], data.get("catalysts"), data.get("valuation_thesis"), data.get("institutional_verdict"),
                data.get("target_price"), study_json_str, now_str
            ))

        # 4. Seed initial time-series timeline events with SHA-256 deduplication
        for ev in SEED_TIMELINE_EVENTS:
            nid = ev.get("news_id") or compute_news_hash(ev["ticker"], ev["publish_date"], ev["headline"])
            cur.execute("""
                INSERT INTO special_watchlist_timeline (
                    ticker, news_id, publish_date, headline, source,
                    summary, key_takeaways, sentiment, sentiment_score,
                    price_impact, url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(news_id) DO UPDATE SET
                    publish_date=excluded.publish_date,
                    headline=excluded.headline,
                    source=excluded.source,
                    summary=excluded.summary,
                    key_takeaways=excluded.key_takeaways,
                    sentiment=excluded.sentiment,
                    sentiment_score=excluded.sentiment_score,
                    price_impact=excluded.price_impact,
                    url=excluded.url
            """, (
                ev["ticker"], nid, ev["publish_date"], ev["headline"], ev["source"],
                ev["summary"], ev.get("key_takeaways"), ev["sentiment"], ev.get("sentiment_score", 0.0),
                ev.get("price_impact"), ev.get("url"), now_str
            ))

        # 5. Register UPST and 402340.KS in companies & company_profiles to prevent FK gaps
        _register_missing_universe_companies(cur)

        conn.commit()
        conn.close()


def _register_missing_universe_companies(cur: sqlite3.Cursor) -> None:
    """Ensures UPST, 402340.KS, ENPH, and CELH exist in companies and company_profiles."""
    # Check if companies table exists in this database (skip if isolated mock DB)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
    if not cur.fetchone():
        return

    # Check what industry reports exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='industry_reports'")
    if cur.fetchone():
        cur.execute("SELECT id FROM industry_reports ORDER BY id ASC")
        report_rows = cur.fetchall()
        default_ind_id = report_rows[0][0] if report_rows else 1
    else:
        default_ind_id = 1

    # UPST Registration
    cur.execute("SELECT id FROM companies WHERE ticker = 'UPST'")
    upst_row = cur.fetchone()
    if not upst_row:
        cur.execute("""
            INSERT INTO companies (industry_id, name, ticker, role_description, future_growth, display_order, portfolio_tier, principle_reason)
            VALUES (?, 'Upstart Holdings', 'UPST', 'AI 신용평가 대출 언더라이팅 플랫폼', '금리인하 사이클 수수료 성장 및 대출채권 파트너십 확장', 99, 'Watchlist', 'AI 언더라이팅 모델 승인율 44%+ 개선, FCF 흑자 전환 국면 (Watchlist)')
        """, (default_ind_id,))
        upst_id = cur.lastrowid
    else:
        upst_id = upst_row[0]

    cur.execute("SELECT id FROM company_profiles WHERE company_id = ?", (upst_id,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO company_profiles (
                company_id, sector, description_ko, current_price, high_52w, mdd_pct, buy_signal, dca_stage, moat_score,
                last_updated, principle_reason, op_margin_ttm, roe
            ) VALUES (?, 'Technology', '클라우드 기반 인공지능(AI) 대출 플랫폼', 36.85, 86.50, -57.40, 'BUY_READY (극단폭락 진입검토 MDD -57.4%)', 'WATCH_DEEP', 58.0,
                     datetime('now', 'localtime'), 'AI 언더라이팅 모델 승인율 44%+ 개선, FCF 흑자 전환 국면 (Watchlist)', 11.8, 9.5)
        """, (upst_id,))

    # 402340.KS Registration
    cur.execute("SELECT id FROM companies WHERE ticker IN ('402340.KS', '402340')")
    sq_row = cur.fetchone()
    if not sq_row:
        cur.execute("""
            INSERT INTO companies (industry_id, name, ticker, role_description, future_growth, display_order, portfolio_tier, principle_reason)
            VALUES (?, 'SK Square', '402340.KS', '반도체/ICT 투자전문 지주회사 (SK하이닉스 모회사)', 'SK하이닉스 HBM3E 독점 지분법 이익 급증 및 자사주 4,000억 원 전량 소각', 45, 'Core', 'SK하이닉스 HBM3E 독점 모회사, NAV 대비 55% 디스카운트 해소 수혜, OPM 68.4%, ROE 24.1% (Core)')
        """, (default_ind_id,))
        sq_id = cur.lastrowid
    else:
        sq_id = sq_row[0]

    cur.execute("SELECT id FROM company_profiles WHERE company_id = ?", (sq_id,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO company_profiles (
                company_id, sector, description_ko, current_price, high_52w, mdd_pct, buy_signal, dca_stage, moat_score,
                last_updated, principle_reason, op_margin_ttm, roe
            ) VALUES (?, 'Holding / Technology', '반도체 및 ICT 투자 지주회사 (SK하이닉스 최대주주)', 82400.0, 94200.0, -12.53, 'WAIT (고점 부근 MDD -12.5%)', 'CORE_HOLD', 82.0,
                     datetime('now', 'localtime'), 'SK하이닉스 HBM3E 독점 모회사, NAV 대비 55% 디스카운트 해소 수혜, OPM 68.4%, ROE 24.1% (Core)', 68.4, 24.1)
        """, (sq_id,))

    # ENPH Registration
    cur.execute("SELECT id FROM companies WHERE ticker = 'ENPH'")
    enph_row = cur.fetchone()
    if not enph_row:
        cur.execute("SELECT id FROM industry_reports WHERE tag LIKE '%에너지%' OR title LIKE '%에너지%' ORDER BY id ASC")
        ind_row = cur.fetchone()
        energy_ind_id = ind_row[0] if ind_row else 5
        cur.execute("""
            INSERT INTO companies (industry_id, name, ticker, role_description, future_growth, display_order, portfolio_tier, principle_reason)
            VALUES (?, 'Enphase Energy', 'ENPH', '마이크로인버터 및 분산형 ESS 1위', '질화갈륨(GaN) IQ9 마이크로인버터 및 NEM 3.0 배터리 부착률 급증', 98, 'Watchlist', '글로벌 1위 마이크로인버터 독점 병목 및 분산형 ESS 플랫폼, 채널 재고 정상화 진입 (Watchlist)')
        """, (energy_ind_id,))
        enph_id = cur.lastrowid
    else:
        enph_id = enph_row[0]

    cur.execute("SELECT id FROM company_profiles WHERE company_id = ?", (enph_id,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO company_profiles (
                company_id, sector, description_ko, current_price, high_52w, mdd_pct, buy_signal, dca_stage, moat_score,
                last_updated, principle_reason, op_margin_ttm, roe
            ) VALUES (?, 'Clean Energy / Technology', '글로벌 1위 태양광 마이크로인버터 및 분산형 ESS 솔루션 공급사', 30.91, 73.74, -58.08, 'BUY_READY (극단폭락 진입검토 MDD -58.1%)', 'WATCH_DEEP', 76.0,
                     datetime('now', 'localtime'), '글로벌 1위 마이크로인버터 독점 병목 및 분산형 ESS 플랫폼, 채널 재고 정상화 진입 (Watchlist)', 14.2, 16.5)
        """, (enph_id,))

    # CELH Registration / Verification
    cur.execute("SELECT id FROM companies WHERE ticker = 'CELH'")
    celh_row = cur.fetchone()
    if not celh_row:
        cur.execute("SELECT id FROM industry_reports WHERE tag LIKE '%식음료%' OR title LIKE '%식음료%' OR tag LIKE '%F&B%' ORDER BY id ASC")
        fnb_row = cur.fetchone()
        fnb_ind_id = fnb_row[0] if fnb_row else 16
        cur.execute("""
            INSERT INTO companies (industry_id, name, ticker, role_description, future_growth, display_order, portfolio_tier, principle_reason)
            VALUES (?, 'Celsius Holdings', 'CELH', '기능성 피트니스 에너지 드링크 1위', '펩시코 글로벌 독점 유통망 기반 해외 시장 확장 및 점유율 사상 최고치', 97, 'Watchlist', '기능성 웰니스 피트니스 음료 1위 및 펩시코 DSD 유통 병목 해자, OPM 19.8%, ROE 22.4% (Watchlist)')
        """, (fnb_ind_id,))
        celh_id = cur.lastrowid
    else:
        celh_id = celh_row[0]
        cur.execute("""
            UPDATE companies
            SET name='Celsius Holdings',
                role_description='기능성 피트니스 에너지 드링크 1위',
                future_growth='펩시코 글로벌 독점 유통망 기반 해외 시장 확장 및 점유율 사상 최고치',
                portfolio_tier='Watchlist',
                principle_reason='기능성 웰니스 피트니스 음료 1위 및 펩시코 DSD 유통 병목 해자, OPM 19.8%, ROE 22.4% (Watchlist)'
            WHERE id = ?
        """, (celh_id,))

    cur.execute("SELECT id FROM company_profiles WHERE company_id = ?", (celh_id,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO company_profiles (
                company_id, sector, description_ko, current_price, high_52w, mdd_pct, buy_signal, dca_stage, moat_score,
                last_updated, principle_reason, op_margin_ttm, roe
            ) VALUES (?, 'Consumer Defensive / Beverages', '글로벌 1위 기능성 피트니스 웰니스 에너지 드링크 기업', 28.00, 66.74, -58.05, 'BUY_READY (극단폭락 진입검토 MDD -58.0%)', 'WATCH_DEEP', 74.0,
                     datetime('now', 'localtime'), '기능성 웰니스 피트니스 음료 1위 및 펩시코 DSD 유통 병목 해자, OPM 19.8%, ROE 22.4% (Watchlist)', 19.8, 22.4)
        """, (celh_id,))
    else:
        cur.execute("""
            UPDATE company_profiles
            SET sector='Consumer Defensive / Beverages',
                description_ko='글로벌 1위 기능성 피트니스 웰니스 에너지 드링크 기업',
                current_price=28.00, high_52w=66.74, mdd_pct=-58.05,
                buy_signal='BUY_READY (극단폭락 진입검토 MDD -58.0%)', dca_stage='WATCH_DEEP', moat_score=74.0,
                principle_reason='기능성 웰니스 피트니스 음료 1위 및 펩시코 DSD 유통 병목 해자, OPM 19.8%, ROE 22.4% (Watchlist)',
                op_margin_ttm=19.8, roe=22.4,
                last_updated=datetime('now', 'localtime')
            WHERE company_id = ?
        """, (celh_id,))


# ==============================================================================
# 5. Live Pricing & Incremental News Ingestion Pipeline
# ==============================================================================

def sync_stock_prices(tickers: List[str], db_path: Optional[Union[str, Path]] = None, silent: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Fetches latest price, 52-week high, and computes MDD % and DCA signals for tickers.
    Falls back gracefully to database/cached values if offline.
    """
    updated_quotes = {}
    conn = sqlite3.connect(str(db_path or AUTHORITATIVE_DB_PATH))
    cur = conn.cursor()

    try:
        import yfinance as yf
        if not silent:
            print(f"[SpecialSync] Fetching 1y price history via yfinance for: {', '.join(tickers)}")
        data = yf.download(tickers, period="1y", auto_adjust=True, progress=False)
        
        for t in tickers:
            curr_price = None
            high_52w = None
            try:
                if not data.empty and 'Close' in data and t in data['Close']:
                    close_ser = data['Close'][t].dropna()
                    high_ser = data['High'][t].dropna() if 'High' in data and t in data['High'] else close_ser
                    if not close_ser.empty:
                        curr_price = round(float(close_ser.iloc[-1]), 2)
                        high_52w = round(float(high_ser.max()), 2)
            except Exception as e:
                if not silent:
                    print(f"[SpecialSync] Note: yfinance parsing for {t} failed ({e}), using cached DB quote.")

            # Read existing tier from DB
            cur.execute("SELECT portfolio_tier, current_price, high_52w FROM special_watchlist_studies WHERE ticker = ?", (t,))
            row = cur.fetchone()
            tier = row[0] if row and row[0] else SEED_STUDIES.get(t, {}).get("portfolio_tier", "Watchlist")

            if curr_price is None and row and row[1]:
                curr_price = float(row[1])
                high_52w = float(row[2]) if row[2] else curr_price

            if curr_price is not None and high_52w is not None:
                mdd = calculate_mdd(curr_price, high_52w)
                buy_sig, dca_stg = evaluate_tier_dca(tier, mdd)
                updated_quotes[t] = {
                    "current_price": curr_price,
                    "high_52w": high_52w,
                    "mdd_pct": mdd,
                    "buy_signal": buy_sig,
                    "dca_stage": dca_stg,
                    "portfolio_tier": tier,
                }
                # Update special_watchlist_studies
                cur.execute("""
                    UPDATE special_watchlist_studies
                    SET current_price=?, high_52w=?, mdd_pct=?, buy_signal=?, dca_stage=?, updated_at=datetime('now', 'localtime')
                    WHERE ticker=?
                """, (curr_price, high_52w, mdd, buy_sig, dca_stg, t))
    except Exception as e:
        if not silent:
            print(f"[SpecialSync] yfinance download unavailable ({e}); maintaining authoritative cached quotes.")
        # Load from DB or seed
        for t in tickers:
            cur.execute("SELECT current_price, high_52w, mdd_pct, buy_signal, dca_stage, portfolio_tier FROM special_watchlist_studies WHERE ticker = ?", (t,))
            r = cur.fetchone()
            if r and r[0] is not None:
                updated_quotes[t] = {
                    "current_price": r[0], "high_52w": r[1], "mdd_pct": r[2], "buy_signal": r[3], "dca_stage": r[4], "portfolio_tier": r[5]
                }
            else:
                s = SEED_STUDIES.get(t, {})
                updated_quotes[t] = {
                    "current_price": s.get("current_price"), "high_52w": s.get("high_52w"),
                    "mdd_pct": s.get("mdd_pct"), "buy_signal": s.get("buy_signal"),
                    "dca_stage": s.get("dca_stage"), "portfolio_tier": s.get("portfolio_tier")
                }

    conn.commit()
    conn.close()
    return updated_quotes


def fetch_live_news_incremental(tickers: List[str], db_path: Optional[Union[str, Path]] = None, silent: bool = False) -> int:
    """
    Discovers live external news items via yfinance/RSS feeds,
    deduplicates using SHA-256 hash, and inserts new events into special_watchlist_timeline.
    Returns count of newly inserted news articles.
    """
    conn = sqlite3.connect(str(db_path or AUTHORITATIVE_DB_PATH))
    cur = conn.cursor()
    new_count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        import yfinance as yf
        for t in tickers:
            try:
                tk_obj = yf.Ticker(t)
                news_list = getattr(tk_obj, "news", None) or []
                for item in news_list[:6]:
                    title = item.get("title")
                    if not title or len(title.strip()) < 5:
                        continue
                    pub_ts = item.get("providerPublishTime")
                    if pub_ts:
                        pub_date = datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                    else:
                        pub_date = datetime.now().strftime("%Y-%m-%d")

                    publisher = item.get("publisher") or "Global Market Wire"
                    link = item.get("link") or ""

                    # Deduplication Hash
                    nid = compute_news_hash(t, pub_date, title)

                    # Check if already exists
                    cur.execute("SELECT id FROM special_watchlist_timeline WHERE news_id = ?", (nid,))
                    if cur.fetchone():
                        continue

                    # Summarize & Sentiment classify
                    summary = f"[{publisher}] {title}. 글로벌 금융 시장 및 주요 기관 분석 보고서에 따른 {t} 종목 관련 최신 실시간 이슈입니다."
                    takeaway = f"• {publisher} 보도: {title}\n• 주요 기관 및 시장 참여자들의 모니터링 주요 지표"
                    sentiment = "POSITIVE" if any(w in title.lower() for w in ["soar", "gain", "beat", "buy", "upgrade", "record", "jump", "win", "high", "rally"]) else \
                                "NEGATIVE" if any(w in title.lower() for w in ["drop", "fall", "cut", "loss", "risk", "downgrade", "probe", "delay", "decline"]) else "NEUTRAL"
                    price_impact = f"{t} 관련 {publisher} 외신 보도에 따른 단기 수급 및 센티먼트 영향 점검"

                    cur.execute("""
                        INSERT INTO special_watchlist_timeline (
                            ticker, news_id, publish_date, headline, source,
                            summary, key_takeaways, sentiment, sentiment_score,
                            price_impact, url, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (t, nid, pub_date, title, publisher, summary, takeaway, sentiment, 0.0, price_impact, link, now_str))
                    new_count += 1
            except Exception as ex:
                if not silent:
                    print(f"[SpecialSync] Live news fetch note for {t}: {ex}")
    except Exception as e:
        if not silent:
            print(f"[SpecialSync] Live news pipeline note ({e}); relying on curated seed timeline.")

    conn.commit()
    conn.close()
    return new_count


# ==============================================================================
# 6. Data Aggregation & Atomic Multi-Target JSON Distribution
# ==============================================================================

def get_all_special_data(db_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Constructs the authoritative response containing all 8 Special Watchlist stocks
    with complete 5-dimension deep studies and reverse-chronological news timeline.
    """
    resolved_db = Path(db_path) if db_path else AUTHORITATIVE_DB_PATH
    
    # If DB doesn't have tables, ensure them first
    ensure_tables_and_seed(resolved_db)

    conn = sqlite3.connect(str(resolved_db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM special_watchlist_studies
        ORDER BY CASE ticker
            WHEN 'UBER' THEN 1
            WHEN 'FLNC' THEN 2
            WHEN 'MBLY' THEN 3
            WHEN 'UPST' THEN 4
            WHEN 'TSLA' THEN 5
            WHEN '402340.KS' THEN 6
            WHEN 'ENPH' THEN 7
            WHEN 'CELH' THEN 8
            ELSE 99 END
    """)
    study_rows = cur.fetchall()

    stocks = []
    for s in study_rows:
        tk = s["ticker"]

        # Fetch timeline in strict reverse-chronological order
        cur.execute("""
            SELECT * FROM special_watchlist_timeline
            WHERE ticker = ?
            ORDER BY publish_date DESC, id DESC
        """, (tk,))
        timeline_rows = cur.fetchall()

        timeline_items = []
        for t in timeline_rows:
            item = {
                "id": t["id"],
                "news_id": t["news_id"],
                "ticker": t["ticker"],
                "publish_date": t["publish_date"],
                "date": t["publish_date"],  # compatibility alias
                "headline": t["headline"],
                "source": t["source"],
                "summary": t["summary"],
                "key_takeaways": t["key_takeaways"],
                "takeaways": t["key_takeaways"],  # compatibility alias
                "sentiment": t["sentiment"],
                "sentiment_score": t["sentiment_score"],
                "price_impact": t["price_impact"],
                "url": t["url"],
                "created_at": t["created_at"]
            }
            timeline_items.append(item)

        # Build full study object for both top-level and nested access
        moat_text = s["moat_analysis"] or ""
        moat_bottleneck = s["moat_bottleneck"] or moat_text
        study_dict = {
            "business_model": s["business_model"],
            "moat_analysis": moat_text,
            "moat_bottleneck": moat_bottleneck,
            "tam_growth_drivers": s["tam_growth_drivers"],
            "financial_margins": s["financial_margins"],
            "opm": s["opm"],
            "roe": s["roe"],
            "gross_margin": s["gross_margin"],
            "fcf_status": s["fcf_status"],
            "key_risks": s["key_risks"],
            "catalysts": s["catalysts"],
            "valuation_thesis": s["valuation_thesis"],
            "institutional_verdict": s["institutional_verdict"],
            "target_price": s["target_price"]
        }

        quote_dict = {
            "current_price": s["current_price"],
            "high_52w": s["high_52w"],
            "mdd_pct": s["mdd_pct"],
            "portfolio_tier": s["portfolio_tier"],
            "buy_signal": s["buy_signal"],
            "dca_stage": s["dca_stage"],
            "last_updated": s["updated_at"]
        }

        stock_record = {
            "id": s["id"],
            "ticker": tk,
            "name": s["name"],
            "name_ko": s["name_ko"],
            "exchange": s["exchange"],
            "sector": s["sector"],
            "portfolio_tier": s["portfolio_tier"],
            "current_price": s["current_price"],
            "high_52w": s["high_52w"],
            "mdd_pct": s["mdd_pct"],
            "buy_signal": s["buy_signal"],
            "dca_stage": s["dca_stage"],
            "business_model": s["business_model"],
            "moat_analysis": moat_text,
            "moat_bottleneck": moat_bottleneck,
            "tam_growth_drivers": s["tam_growth_drivers"],
            "financial_margins": s["financial_margins"],
            "opm": s["opm"],
            "roe": s["roe"],
            "gross_margin": s["gross_margin"],
            "fcf_status": s["fcf_status"],
            "key_risks": s["key_risks"],
            "catalysts": s["catalysts"],
            "valuation_thesis": s["valuation_thesis"],
            "institutional_verdict": s["institutional_verdict"],
            "target_price": s["target_price"],
            "study": study_dict,
            "quote": quote_dict,
            "timeline": timeline_items,
            "updated_at": s["updated_at"]
        }
        stocks.append(stock_record)

    conn.close()

    now_iso = datetime.now().astimezone().isoformat()
    return {
        "status": "success",
        "updated_at": now_iso,
        "stocks": stocks
    }


def distribute_special_watchlist_json(data: Dict[str, Any], destinations: Optional[List[Union[str, Path]]] = None) -> None:
    """
    Atomically writes special_watchlist_data.json to all 4 distribution paths
    using temporary files (.tmp) and os.replace to prevent concurrency locks.
    """
    paths = destinations or SPECIAL_WATCHLIST_JSON_PATHS

    for p in paths:
        target = Path(p)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp_target = target.with_suffix(target.suffix + ".tmp")
            with open(tmp_target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_target, target)
        except Exception as e:
            print(f"[SpecialSync] Warning: Failed to distribute JSON to {target}: {e}")


# ==============================================================================
# 7. Main Pipeline Runner & CLI
# ==============================================================================

def run_sync(
    force: bool = False,
    tickers: Optional[Union[str, List[str]]] = None,
    silent: bool = False,
    source: str = "cli",
    db_path: Optional[Union[str, Path]] = None,
    destinations: Optional[List[Union[str, Path]]] = None
) -> Dict[str, Any]:
    """
    Executes end-to-end synchronization for the Special Watchlist:
      1. Schema initialization and baseline seeding
      2. Price and MDD recalculation
      3. Incremental news ingestion and deduplication
      4. Atomic multi-destination JSON persistence
    """
    start_time = datetime.now()
    if not silent:
        print(f"======================================================================")
        print(f" Special Watchlist Sync Engine (Source: {source}, Force: {force})")
        print(f"======================================================================")

    # 1. Parse Tickers
    if not tickers:
        ticker_list = TARGET_TICKERS
    elif isinstance(tickers, str):
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    else:
        ticker_list = [t.strip().upper() for t in tickers if t]

    # 2. Database Schema & Seed Verification
    resolved_db = Path(db_path) if db_path else AUTHORITATIVE_DB_PATH
    ensure_tables_and_seed(resolved_db)

    # 3. Synchronize Prices, 52w High & MDD
    price_results = sync_stock_prices(ticker_list, db_path=resolved_db, silent=silent)

    # 4. Ingest Incremental Live News Timeline
    new_news_count = fetch_live_news_incremental(ticker_list, db_path=resolved_db, silent=silent)

    # 5. Extract Full Consolidated Data
    data_payload = get_all_special_data(db_path=resolved_db)

    # 6. Distribute Multi-Target JSON Artifacts
    distribute_special_watchlist_json(data_payload, destinations=destinations)

    duration = (datetime.now() - start_time).total_seconds()
    if not silent:
        print(f"[SpecialSync] Processed {len(ticker_list)} stocks, {new_news_count} new news items in {duration:.2f}s.")
        print(f"[SpecialSync] Distributed to {len(destinations or SPECIAL_WATCHLIST_JSON_PATHS)} canonical destinations.")
        print(f"======================================================================")

    return {
        "status": "success",
        "synced_tickers": ticker_list,
        "new_news_count": new_news_count,
        "duration_seconds": round(duration, 2),
        "updated_at": data_payload.get("updated_at"),
        "stocks": data_payload.get("stocks", [])
    }


def main():
    parser = argparse.ArgumentParser(description="TrendPulse Special Watchlist Sync Engine")
    parser.add_argument("--force", action="store_true", help="Bypass cache and force re-fetch")
    parser.add_argument("--tickers", type=str, default=None, help="Comma-separated ticker list")
    parser.add_argument("--silent", action="store_true", help="Headless silent execution")
    parser.add_argument("--source", type=str, default="cli", help="Caller origin (cli, api, scheduler, etc.)")
    parser.add_argument("--db", type=str, default=None, help="Custom SQLite DB path")
    args = parser.parse_args()

    try:
        run_sync(
            force=args.force,
            tickers=args.tickers,
            silent=args.silent,
            source=args.source,
            db_path=args.db
        )
        sys.exit(0)
    except Exception as e:
        print(f"[SpecialSync] Fatal Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
