# -*- coding: utf-8 -*-
"""
전력 인프라 산업 프로젝트 DB 초기화 스크립트
- industry_reports(id=6) 추가
- value_chain_nodes 5개 추가 (id: 25-29)
- companies 10개 추가
"""
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'investment_portal.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=== 전력 인프라 산업 DB 초기화 ===")

# ─────────────────────────────────────────────
# 1. Industry Report 추가
# ─────────────────────────────────────────────
cur.execute("SELECT id FROM industry_reports WHERE id=6")
if cur.fetchone():
    print("[SKIP] industry_report id=6 already exists")
else:
    cur.execute("""
        INSERT INTO industry_reports (id, title, summary, file_path, tag)
        VALUES (?, ?, ?, ?, ?)
    """, (
        6,
        "전력 인프라 밸류체인 심층분석",
        """## 1. 산업 개요: AI·전기화 시대의 전력 인프라 르네상스

AI 데이터센터 급증, 전기차(EV) 보급 가속, 노후화된 전력망 교체 수요가 동시에 폭발하며 미국과 글로벌 전력 인프라 투자가 역사적 전환점을 맞고 있습니다. 미국 에너지부는 2035년까지 전력망 현대화에 5조 달러 이상의 투자가 필요하다고 추산하며, 바이든-트럼프 초당적 인프라 정책이 수요를 뒷받침합니다. 송·배전 인프라 노후화율 70% 이상, 전력망 연계 대기 프로젝트 1,700GW 이상이 적체된 상황에서 전력 인프라 밸류체인 전반이 수혜를 받고 있습니다.

## 2. 핵심 투자 테마: 4개 레이어 밸류체인

**① 전력 기기 및 설비 (즉각적 수혜)**
- 변압기, 스위치기어, 배전반, 전력 관리 시스템 등 핵심 하드웨어
- 공급 병목 심화로 리드타임 2~3년, 가격 프리미엄 지속
- Eaton, Hubbell, Powell Industries 수혜

**② 전력망 건설 및 엔지니어링 (중장기 성장)**
- 송배전 선로, 변전소 EPC, 재생에너지 연계 공사
- 미국 IRA + 인프라법 지원금 수혜 수주잔고 급증
- Quanta Services, MYR Group 수혜

**③ 전기자재 유통 및 솔루션 (안정 성장)**
- 전력 케이블, 전선관, 전기 보호장비 설계·유통
- 데이터센터 건설 붐 + 그리드 현대화 동시 수혜
- Wesco International, Atkore 수혜

**④ 데이터센터 전력 인프라 (고성장)**
- UPS, 열 관리, 전력 분배 장치(PDU) 등 미션크리티컬 시스템
- AI 빅테크 하이퍼스케일 투자 직접 연동
- Vertiv Holdings 수혜

## 3. 구조적 전환점: 세 가지 동시 성장 드라이버

① **AI 데이터센터 전력 수요**: 2030년까지 미국 전체 전력 수요의 8% 이상이 데이터센터에서 발생 예상
② **전기화(Electrification)**: EV 충전 인프라 + 열펌프 + 산업용 전기화로 피크 전력 수요 2040년까지 30% 증가
③ **노후망 교체**: 1950~70년대 설치된 변압기·변전소의 대규모 교체 사이클 본격화

## 4. 핵심 리스크

* **금리 민감성**: 인프라 프로젝트 파이낸싱 비용 상승 시 수주 지연
* **원자재 변동성**: 구리·알루미늄 가격 급등이 마진 압박
* **정책 불확실성**: IRA 세제혜택 축소 또는 인프라 예산 삭감 리스크
* **공급망 병목 완화**: 변압기 리드타임 정상화 시 가격 프리미엄 축소

## 5. 투자 전략: 레이어별 포지셔닝

즉시 수혜: ETN, HUBB, POWL | 중기 성장: PWR, MYRG, WCC | 고성장 테마: VRT, ATKR""",
        "6. 전력 인프라/전력 인프라.pptx",
        "전력인프라"
    ))
    print("[OK] industry_report id=6 inserted")

# ─────────────────────────────────────────────
# 2. Value Chain Nodes 추가
# ─────────────────────────────────────────────
nodes = [
    # (id, industry_id, node_name, description)
    (25, 6, "전력 기기 및 설비 (Power Equipment)",
     "변압기·스위치기어·배전반·UPS 등 전력망의 핵심 하드웨어를 설계·제조하는 레이어. 공급 병목으로 리드타임 2~3년, 가격 프리미엄 지속."),
    (26, 6, "전력망 건설 및 EPC (Grid Construction & EPC)",
     "송배전 선로, 변전소, 재생에너지 연계 공사를 수행하는 엔지니어링·조달·시공(EPC) 기업들. 미국 IRA·인프라법 수주잔고 급증 수혜."),
    (27, 6, "전기자재 유통 및 솔루션 (Electrical Distribution)",
     "전력 케이블·전선관·전기 보호장비를 설계·제조·유통하는 레이어. 데이터센터 붐과 그리드 현대화 이중 수혜."),
    (28, 6, "그리드 연결 및 부품 (Grid Connectivity & Components)",
     "송전선 연결 클램프, 그리드 커넥터, 전기 인클로저 등 그리드 연결 핵심 부품 제조. 재생에너지 연계 프로젝트 급증 수혜."),
    (29, 6, "데이터센터 전력 인프라 (Data Center Power)",
     "AI 하이퍼스케일 데이터센터용 UPS·열 관리·전력 분배 장치(PDU) 등 미션크리티컬 전력 시스템. 빅테크 CapEx 직접 연동 고성장 레이어."),
]

for node in nodes:
    cur.execute("SELECT id FROM value_chain_nodes WHERE id=?", (node[0],))
    if cur.fetchone():
        print(f"[SKIP] node id={node[0]} '{node[2]}' already exists")
    else:
        cur.execute("""
            INSERT INTO value_chain_nodes (id, industry_id, node_name, description)
            VALUES (?, ?, ?, ?)
        """, node)
        print(f"[OK] node id={node[0]} '{node[2]}' inserted")

# ─────────────────────────────────────────────
# 3. Companies 추가
# ─────────────────────────────────────────────
companies = [
    # (name, ticker, industry_id, vc_node_id, role_description, future_growth, display_order)
    (
        "Eaton Corporation", "ETN", 6, 25,
        "글로벌 전력 관리 1위 기업. 전기 스위치기어·배전반·UPS·서킷 브레이커 등 폭넓은 전력 하드웨어 포트폴리오 보유. AI 데이터센터·산업 전기화 전방위 수혜 기업으로 공급 병목 리드타임 2년 이상 지속.",
        "데이터센터 전력 설비 수요 급증으로 수주잔고 사상 최대. EV 충전 인프라·재생에너지 연계 사업 고성장. IRA 보조금 수혜로 미국 내 제조·판매 확대.",
        1
    ),
    (
        "Vertiv Holdings", "VRT", 6, 29,
        "AI 하이퍼스케일 데이터센터 전용 UPS(무정전전원장치)·액체 냉각·전력 분배 장치(PDU) 글로벌 1위. 마이크로소프트·구글·아마존 등 빅테크 하이퍼스케일 데이터센터의 미션크리티컬 전력 인프라 핵심 독점 공급사.",
        "AI 빅테크 CapEx 직접 연동 고성장. 2030년까지 데이터센터 전력 수요 3배 성장 전망. 소프트웨어 서비스 기반 구독형 수익 모델로 전환해 마진 구조적 개선 중.",
        2
    ),
    (
        "Quanta Services", "PWR", 6, 26,
        "북미 최대 전력망·재생에너지·광통신 인프라 EPC 기업. 고압 송전선로 건설 북미 시장점유율 1위, 수주잔고 300억 달러 이상의 대형 EPC 계약 전문사. 전력망 연계 대기 프로젝트 해소의 최대 수혜주.",
        "미국 인프라법·IRA 지원 전력망 현대화 공사 대규모 수주. 재생에너지 연계 공사 및 해상풍력 송전 인프라 고성장. 수주잔고 기반 안정적 매출 가시성 확보.",
        3
    ),
    (
        "Hubbell Incorporated", "HUBB", 6, 25,
        "전기 인프라용 배선장치·제어 설비·변전소 구조물 전문 제조사. 미국 전력 유틸리티·산업 시장에서 100년 이상 독점적 브랜드 파워를 보유. 전력 유틸리티 솔루션(HUS)과 전기 솔루션(HES) 두 세그먼트로 구성.",
        "전력망 현대화 교체 사이클 직접 수혜. 전기차 충전 인프라·태양광·풍력 연계 설비 수요 확대. 스마트그리드 모니터링 장비 및 자동화 솔루션 매출 급증.",
        4
    ),
    (
        "Wesco International", "WCC", 6, 27,
        "북미 최대 전기자재·산업재·통신 인프라 유통기업. 연 매출 220억 달러 규모의 B2B 전력 인프라 원스톱 솔루션 제공사. 공급망 복잡성을 단순화하는 통합 유통 플랫폼 운영.",
        "전력망 현대화·데이터센터 건설·EV 인프라 확충으로 전기자재 수요 구조적 성장. 대형 M&A(Anixter 인수)로 통신 인프라 유통 역량 강화. 마진 개선 중.",
        5
    ),
    (
        "Atkore", "ATKR", 6, 27,
        "전선관(Electrical Conduit)·케이블 트레이·전기 보호 시스템 북미 시장점유율 1위. 데이터센터·태양광 발전소·산업 시설 전기 인프라의 핵심 자재인 금속·PVC 전선관 독점적 공급사.",
        "태양광·풍력·데이터센터 건설 붐으로 전선관 수요 급증. IRA 보조금 기반 재생에너지 프로젝트 파이프라인 수혜. 국내 제조 경쟁 우위로 리쇼어링 수혜.",
        6
    ),
    (
        "Powell Industries", "POWL", 6, 25,
        "전력 분배용 스위치기어·모터 컨트롤 센터·배전반 전문 미국 제조사. 석유화학·LNG·데이터센터·유틸리티 등 고마진 산업용 전력 시스템 특화. 텍사스 주요 석유화학 단지 핵심 납품처.",
        "LNG 수출 터미널·정유 시설·데이터센터 전력 시스템 수주 급증. 국내 제조 강점으로 리쇼어링·에너지 독립 정책 수혜. 수주잔고 사상 최대치 경신 중.",
        7
    ),
    (
        "MYR Group", "MYRG", 6, 26,
        "미국 전력·통신 인프라 전문 전기 건설 기업. 상업용 건축 전기 공사(C&I)와 송배전 공사(T&D) 두 세그먼트로 안정적 이원화. 대형 유틸리티·연방정부 인프라 프로젝트 선도 시공사.",
        "전력망 현대화·재생에너지 연계 공사·데이터센터 전기 시공 수주잔고 사상 최대. 숙련 전기 기술자 인력 확보 경쟁 우위. IRA 지원 태양광·풍력 연계 공사 급증.",
        8
    ),
    (
        "nVent Electric", "NVT", 6, 28,
        "전기 인클로저·열 관리·접지 및 접합 시스템 글로벌 제조사. 데이터센터·전력 유틸리티·산업 자동화 전방위 전기 보호 솔루션 제공. 인클로저 및 정밀 냉각 분야 특허 기술 보유.",
        "데이터센터 열 관리 솔루션 수요 폭발적 성장. 전기화 추세로 전기 보호·접지 설비 구조적 수요 증가. 고성장 데이터센터 냉각 세그먼트의 매출 비중 확대 추세.",
        9
    ),
    (
        "Preformed Line Products", "PLPC", 6, 28,
        "송전선 클램프·스플라이스·광섬유 연결 부품 전문 미국 글로벌 기업. 전력 유틸리티의 송전선 연결·보호 시스템 핵심 부품 공급사. 전 세계 30개국 이상 현지 생산 네트워크 보유.",
        "재생에너지 연계 송전선 증설과 노후 전력망 교체로 연결 부품 수요 고성장. 광섬유·통신 인프라 시장 병행 수혜. 글로벌 전력망 현대화 수요 다변화.",
        10
    ),
]

added = 0
for co in companies:
    cur.execute("SELECT id FROM companies WHERE ticker=? AND industry_id=6", (co[1],))
    if cur.fetchone():
        print(f"[SKIP] {co[0]} ({co[1]}) already exists")
        continue
    cur.execute("""
        INSERT INTO companies (name, ticker, industry_id, value_chain_node_id, role_description, future_growth, display_order)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, co)
    added += 1
    print(f"[OK] {co[0]} ({co[1]}) inserted")

conn.commit()

# 확인
cur.execute("SELECT id, name, ticker FROM companies WHERE industry_id=6 ORDER BY display_order")
power_companies = cur.fetchall()
print(f"\n=== 전력 인프라 산업 기업 목록 ({len(power_companies)}개) ===")
for c in power_companies:
    print(f"  [{c[0]}] {c[1]} ({c[2]})")

conn.close()
print(f"\n완료! {added}개 기업 추가됨.")
