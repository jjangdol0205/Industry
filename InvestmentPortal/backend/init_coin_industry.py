# -*- coding: utf-8 -*-
"""
코인 산업 프로젝트 DB 초기화 스크립트
- industry_reports(id=4) 추가
- value_chain_nodes 5개 추가
- companies 14개 추가
"""
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'investment_portal.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=== 코인 산업 DB 초기화 ===")

# ─────────────────────────────────────────────
# 1. Industry Report 추가
# ─────────────────────────────────────────────
cur.execute("SELECT id FROM industry_reports WHERE id=4")
if cur.fetchone():
    print("[SKIP] industry_report id=4 already exists")
else:
    cur.execute("""
        INSERT INTO industry_reports (id, title, summary, file_path, tag)
        VALUES (?, ?, ?, ?, ?)
    """, (
        4,
        "코인 & 블록체인 산업 밸류체인 심층 분석",
        """비트코인·이더리움을 중심으로 한 암호화폐 생태계의 전방위 밸류체인 분석.
채굴(Mining) 인프라부터 거래소, 결제 플랫폼, 기관 금융, 규제 대응까지
디지털 자산 산업의 5개 레이어를 심층 분석합니다.
BTC ETF 승인 이후 기관 자금 유입과 반감기(Halving) 사이클,
미국 친암호화폐 정책 전환이 만드는 구조적 기회를 짚어봅니다.""",
        "4. 코인/코인 산업.pdf",
        "코인"
    ))
    print("[OK] industry_report id=4 inserted")

# ─────────────────────────────────────────────
# 2. Value Chain Nodes 추가
# ─────────────────────────────────────────────
nodes = [
    # (id, industry_id, node_name, description)
    (11, 4, "채굴 인프라 (Mining)",
     "비트코인 채굴을 위한 ASIC 하드웨어, 데이터센터, 전력 인프라를 운영하는 레이어. "
     "네트워크 보안의 핵심이며 반감기 사이클에 따라 수익성이 변동됩니다."),
    (12, 4, "거래소 & 커스터디 (Exchange & Custody)",
     "암호화폐의 매매·보관·결제를 담당하는 중앙화 플랫폼. "
     "거래 수수료, 스테이킹 수익, 기관 커스터디 서비스가 주요 수익원입니다."),
    (13, 4, "비트코인 재무전략 (Bitcoin Treasury)",
     "기업 재무에 비트코인을 전략적으로 보유하는 방식. "
     "MicroStrategy 모델로 대표되며 주가가 비트코인 가격과 높은 연동성을 가집니다."),
    (14, 4, "결제 & 리테일 플랫폼 (Payment & Retail)",
     "일반 소비자가 암호화폐를 구매·결제에 활용할 수 있는 핀테크 플랫폼. "
     "Block/Square, PayPal, Robinhood 등이 대표적입니다."),
    (15, 4, "기관 금융 & ETF (Institutional Finance)",
     "기관투자자를 위한 암호화폐 자산운용, ETF 발행, OTC 데스크, 대출 서비스. "
     "비트코인 현물 ETF 승인 이후 급속히 성장하고 있는 레이어입니다."),
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
    # (name, ticker, industry_id, vc_node_id, role_description, future_growth)
    (
        "Coinbase Global", "COIN", 4, 12,
        "미국 최대 규제 준수 암호화폐 거래소. 리테일 및 기관 고객 대상 매매, 커스터디, 스테이킹 서비스 제공. SEC와의 규제 마찰이 있었으나 친암호화폐 행정부 출범 후 규제 불확실성 해소.",
        "비트코인 현물 ETF 수탁기관으로 선정. USDC 스테이블코인 발행사 Circle과의 파트너십, 해외 시장 확대, Base L2 블록체인 생태계 성장이 핵심 성장 동력."
    ),
    (
        "MicroStrategy (Strategy)", "MSTR", 4, 13,
        "세계 최대 상장사 비트코인 보유 기업. 소프트웨어 사업에서 비트코인 재무전략 기업으로 전환. BTC 현물 매입을 위한 전환사채·주식 발행을 지속적으로 실행.",
        "비트코인 가격과 1:1 이상의 레버리지 수익 구조. 기업 BTC 재무전략의 표준 모델로 자리잡으며 모방 기업 증가. 나스닥100 편입으로 기관 패시브 자금 유입."
    ),
    (
        "Marathon Digital Holdings", "MARA", 4, 11,
        "미국 최대 비트코인 채굴 기업 중 하나. 고성능 ASIC 채굴기로 비트코인 네트워크 해시레이트의 상당 부분 담당. 에너지 효율성 개선을 위한 친환경 전력 확보에 집중.",
        "2024년 반감기 이후 생산 원가 상승에 대응하여 운영 효율화와 해시레이트 확대를 동시 추진. AI 데이터센터 사업으로 사업 다각화 진행 중."
    ),
    (
        "Riot Platforms", "RIOT", 4, 11,
        "텍사스 주 기반 대규모 비트코인 채굴 기업. 자체 전력 조달 능력과 열 재활용 시스템으로 낮은 채굴 비용 유지. Coinbase에 이어 두 번째로 큰 기관 BTC 보유량 보유.",
        "코퍼스 크리스티 데이터센터 확장으로 해시레이트 크게 증가 예정. 저렴한 전력 확보와 규모의 경제가 반감기 이후 경쟁력의 핵심."
    ),
    (
        "CleanSpark", "CLSK", 4, 11,
        "친환경 에너지 특화 비트코인 채굴 기업. 재생에너지 및 탄소중립 전력원으로 ESG 친화적 채굴 모델 구현. 미국 내 여러 주에 채굴 시설 보유.",
        "청정 에너지 기반 채굴로 ESG 투자자 유치 및 규제 리스크 감소. 인수합병을 통한 해시레이트 급속 확장 전략 지속."
    ),
    (
        "Block (Square)", "SQ", 4, 14,
        "Jack Dorsey가 이끄는 핀테크 기업. Cash App을 통한 리테일 비트코인 매매, Bitkey 하드웨어 지갑, TBD 분산 교환 프로토콜을 개발. 비트코인 채굴 칩(3nm) 자체 개발 중.",
        "비트코인 레이어2 기술과 자체 채굴 칩 상용화가 핵심 과제. Cash App의 BTC 월렛 기능 확대로 리테일 수요 지속 확보."
    ),
    (
        "Robinhood Markets", "HOOD", 4, 14,
        "수수료 없는 주식·암호화폐 거래 플랫폼. 미국 밀레니얼 세대의 핵심 투자 플랫폼으로 암호화폐 거래량 급증. Bitstamp 인수로 유럽 암호화폐 거래소 진출.",
        "Bitstamp 인수 완료로 글로벌 암호화폐 거래소 도약. 예측 시장, 토큰화 주식, 암호화폐 파생상품 라인업 확대 중."
    ),
    (
        "PayPal Holdings", "PYPL", 4, 14,
        "글로belts 결제 플랫폼. PYUSD 스테이블코인 발행, 비트코인·이더리움 매매 및 결제 서비스 제공. 4억명의 기존 사용자 기반이 암호화폐 대중화의 강점.",
        "PYUSD 스테이블코인 생태계 확장. 기업 및 개인 대상 온체인 결제 솔루션 고도화. 벤모(Venmo)를 통한 P2P 암호화폐 이체 활성화."
    ),
    (
        "Canaan Inc", "CAN", 4, 11,
        "중국 기반 세계 2위 비트코인 채굴 장비(ASIC) 제조사. Avalon 브랜드 채굴기를 글로벌 채굴 기업에 공급. Bitmain에 이어 시장점유율 2위.",
        "차세대 Avalon A15 시리즈 출시로 에너지 효율 개선. AI 추론 칩 사업 진출로 매출 다각화 추진."
    ),
    (
        "Hut 8 Mining", "HUT", 4, 11,
        "캐나다 기반 비트코인 채굴 및 고성능 컴퓨팅(HPC) 기업. US Bitcoin Corp과 합병 후 미국·캐나다 양국에 데이터센터 운영. AI/HPC 수요로 사업 전환 가속.",
        "AI 데이터센터 임대 사업과 비트코인 채굴의 이중 수익 구조. 엔비디아 GPU 클러스터를 활용한 AI 클라우드 서비스 출시 예정."
    ),
    (
        "Core Scientific", "CORZ", 4, 11,
        "미국 최대 비트코인 자체 채굴 및 공동 채굴 데이터센터 기업. 2023년 파산 후 재상장. CoreWeave와 장기 HPC 임대 계약으로 수익 안정성 확보.",
        "CoreWeave에 데이터센터 공간 임대로 AI 수요 수혜. 비트코인 채굴과 HPC 임대의 하이브리드 모델이 반감기 수익성 방어의 핵심."
    ),
    (
        "Bakkt Holdings", "BKKT", 4, 12,
        "기관 투자자와 기업 대상 디지털 자산 커스터디·거래 플랫폼. NYSE 모기업 ICE가 설립. 규제 준수 커스터디 서비스와 충성 포인트 토큰화 사업 운영.",
        "규제 명확화 이후 기관 커스터디 수요 본격 성장 예상. 기업 B2B 디지털 자산 서비스 확대."
    ),
    (
        "Cipher Mining", "CIFR", 4, 11,
        "텍사스 기반 비트코인 채굴 기업. 저렴한 전력 비용과 확장 가능한 채굴 인프라 보유. Bitmain의 최신 ASIC 칩 우선 공급 계약 체결.",
        "해시레이트 확장을 통한 규모의 경제 달성. 전력 도매 계약으로 채굴 원가 지속 절감."
    ),
    (
        "Galaxy Digital", "BRPHF", 4, 15,
        "Michael Novogratz가 설립한 기관급 디지털 자산 금융 서비스 기업. 자산운용, 트레이딩, 투자은행, 채굴 사업을 망라. 비트코인·이더리움 현물 ETF 론칭 파트너.",
        "나스닥 상장 추진으로 기관 자본 유치 확대. 디지털 자산 ETF 생태계의 핵심 파트너로 AUM 급증 전망."
    ),
]

added = 0
for co in companies:
    cur.execute("SELECT id FROM companies WHERE ticker=? AND industry_id=4", (co[1],))
    if cur.fetchone():
        print(f"[SKIP] {co[0]} ({co[1]}) already exists")
        continue
    cur.execute("""
        INSERT INTO companies (name, ticker, industry_id, value_chain_node_id, role_description, future_growth)
        VALUES (?, ?, ?, ?, ?, ?)
    """, co)
    added += 1
    print(f"[OK] {co[0]} ({co[1]}) inserted")

conn.commit()

# 확인
cur.execute("SELECT id, name, ticker FROM companies WHERE industry_id=4 ORDER BY id")
coin_companies = cur.fetchall()
print(f"\n=== 코인 산업 기업 목록 ({len(coin_companies)}개) ===")
for c in coin_companies:
    print(f"  [{c[0]}] {c[1]} ({c[2]})")

conn.close()
print(f"\n완료! {added}개 기업 추가됨.")
