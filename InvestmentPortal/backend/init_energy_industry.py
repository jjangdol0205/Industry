# -*- coding: utf-8 -*-
"""
에너지 산업 프로젝트 DB 초기화 스크립트
- industry_reports(id=5) 추가
- value_chain_nodes 5개 추가
- companies 9개 추가
"""
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'investment_portal.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("=== 에너지 및 인프라 산업 DB 초기화 ===")

# ─────────────────────────────────────────────
# 1. Industry Report 추가
# ─────────────────────────────────────────────
cur.execute("SELECT id FROM industry_reports WHERE id=5")
if cur.fetchone():
    print("[SKIP] industry_report id=5 already exists")
else:
    cur.execute("""
        INSERT INTO industry_reports (id, title, summary, file_path, tag)
        VALUES (?, ?, ?, ?, ?)
    """, (
        5,
        "AI 에너지 인프라 및 SMR 산업 밸류체인 심층 분석",
        """생성형 AI와 GPU 병렬 연산으로 인한 데이터센터 전력 수요 폭증 현상을 진단하고, 
재생에너지와 천연가스의 현실적 한계를 보완할 SMR(소형모듈원전) 핵심 밸류체인을 분석한 보고서입니다. 
특히 설계 팹리스보다 파운드리(제조) 기업 및 HALEU(차세대 핵연료) 공급망과 
'원가 보상형 계약(Cost-Plus)' 및 '무조건부 인수(Take-or-Pay)' PPA 구조의 경제성을 조망합니다.""",
        "5. 에너지/에너지 산업.pdf",
        "에너지"
    ))
    print("[OK] industry_report id=5 inserted")

# ─────────────────────────────────────────────
# 2. Value Chain Nodes 추가
# ─────────────────────────────────────────────
nodes = [
    # (id, industry_id, node_name, description)
    (20, 5, "가스터빈 발전 (Gas Turbines)",
     "빅테크가 전력망 확충 지연을 피하기 위해 선택한 단기 해결책. 1~2년 내 신속하게 구축할 수 있으며 날씨와 무관하게 전력을 공급하는 분산 전원망입니다."),
    (21, 5, "SMR 설계 및 팹리스 (SMR Fabless)",
     "24/7 무탄소 CFE 전력을 공급하는 소형모듈원전의 설계를 전문으로 하는 기업들. 미국 NRC의 표준설계인가(SDA) 등 인허가 장벽을 기반으로 기술 해자를 구축합니다."),
    (22, 5, "원자력 파운드리 및 제조 (Foundry & Manufacturing)",
     "SMR 설계도에 맞춰 압력 용기 및 핵심 기자재를 실제로 제조하는 가공 공장. 대규모 설비 투자를 기반으로 수주 즉시 현금을 창출하는 독점 수혜 구조입니다."),
    (23, 5, "차세대 핵연료 및 가공 (Advanced Nuclear Fuel)",
     "SMR 소형화에 핵심인 HALEU(차세대 고농축 우라늄) 농축 및 멜트다운이 불가능한 TRISO 안전 연료를 제조/가공하는 밸류체인의 핵심 독점 레이어입니다."),
    (24, 5, "원전 운영 및 CFE 서비스 (Nuclear Operations & CFE)",
     "대규모 원전 인프라를 운영하며 빅테크와 20년 이상의 장기 전력구매계약(PPA)을 맺고 무탄소 전력(CFE)을 안정적으로 서빙하는 공급자 레이어입니다."),
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
        "GE Vernova", "GEV", 5, 20,
        "글로벌 대용량 복합화력발전 1위 기업. 터빈 내부 공랭식 냉각 기술의 극한을 실현하고 기성품 형태의 가스터빈을 1~2년 내 신속하게 공급하여 빅테크의 단기 전력 공급원 역할을 수행.",
        "전력망 확충이 지연되는 상황에서 가스 터빈 수요 급증. AI 데이터센터용 분산형 전력 생산 시장 선점 및 수소 혼소 터빈 상용화 추진."
    ),
    (
        "Siemens Energy", "SMNEY", 5, 20,
        "글로벌 발전 설비 거인으로, 신재생에너지의 간헐성(변동성)을 통제하기 위해 빠른 출력 조절(유연성)이 가능한 가스터빈 제어 기술 분야에서 세계적 우위 보유.",
        "유럽 그린딜 정책 수혜 및 전 세계적 청정에너지 인프라 업그레이드 수요. 가스터빈의 빠른 기동 시간과 유연성을 바탕으로 신재생에너지 보완재 시장 장악."
    ),
    (
        "Mitsubishi Heavy Industries", "MHVYF", 5, 20,
        "세계 최고 수준인 1,650도 이상의 연소 온도를 돌파한 초고효율 가스터빈 원천 기술 보유사. 수소 100% 전소 터빈 상용화를 주도하여 가스 발전의 탄소 배출 리스크를 근본적으로 해결하는 기업.",
        "일본 반도체 부활(TSMC 구마모토 등)로 인한 전력 수요 증가 수혜 및 글로벌 친환경 수소 전력 발전 프로젝트 수주 확대."
    ),
    (
        "NuScale Power", "SMR", 5, 21,
        "세계 유일하게 미국 원자력규제위원회(NRC)로부터 소형모듈원전(SMR)의 '표준설계인가(SDA)'를 획득한 팹리스 선도 기업. 상용화 타임라인에서 가장 앞서 있는 기업.",
        "빅테크 기업들과의 장기 전력구매계약(PPA) 체결 기대감. 표준설계인가를 바탕으로 글로벌 SMR 프로젝트 수주를 독식할 잠재력 보유."
    ),
    (
        "Oklo Inc.", "OKLO", 5, 21,
        "샘 올트먼이 이사회 의장으로 있는 소형 고속 원자로 개발사. 국가 전력망을 우회하여 데이터센터 바로 옆에 설치해 전력을 공급하는 BTM(Behind the Meter) 직결 및 무기물 액체 냉각 방식의 원자로 설계 전문.",
        "빅테크와의 직접적인 PPA 및 AI 데이터센터 맞춤형 마이크로 원자로 시장의 독점적 수혜. 규제 당국의 인허가 획득 시 급속한 외형 성장 기대."
    ),
    (
        "Constellation Energy", "CEG", 5, 24,
        "미국 최대 원자력 발전 운영사로, 마이크로소프트와 20년 장기 전력구매계약(PPA)을 체결하고 쓰리마일섬 원전을 재가동하는 등 빅테크 대상 무탄소 에너지(CFE) 공급망의 지배적 위치.",
        "기존 원전의 수명 연장 및 빅테크와의 고마진 장기 고정 가격 PPA 확대. 무탄소 기저 전원(Nuclear)에 대한 프리미엄 가치 부각으로 구조적 재평가."
    ),
    (
        "Centrus Energy", "LEU", 5, 23,
        "SMR의 소형화와 고효율화를 가능하게 하는 차세대 고농축 우라늄 핵연료 'HALEU'의 미국 내 유일한 상업 농축 독점 공급 기업. 러시아 핵연료 의존도를 극복할 국가 안보적 독점 기술 보유.",
        "미국 정부의 HALEU 자국 내 생산 보조금 혜택 및 SMR 상용화 본격화에 따른 HALEU 핵연료 수요의 기하급수적 성장. 영구적 독점 지위의 해자 보유."
    ),
    (
        "BWX Technologies", "BWXT", 5, 22,
        "미국 해군 원자로 및 국가 방산 원자력 연료의 독점 공급 기업. 멜트다운이 불가능한 차세대 'TRISO' 핵연료 가공 및 SMR 핵심 격납 구조물을 공장 규격화 생산하는 대표적인 파운드리 강자.",
        "SMR 설계사들의 수주가 들어오는 즉시 선수금을 수취하여 금속을 가공하는 실질적 밸류체인 수혜 기업. 미 국방부 마이크로 원자로 프로젝트(Project Pele) 핵심 참여."
    ),
    (
        "Doosan Enerbility", "034020.KS", 5, 22,
        "뉴스케일 등 글로벌 SMR 설계사들의 핵심 기자재를 전담 생산하는 세계 최고 수준의 원자력 파운드리. 용접부 없는 대형 압력 용기(원자로 껍데기)를 단번에 찍어내는 초대형 17,000톤 프레스 설비 보유.",
        "글로벌 SMR 및 대형 원전 수주 발주 시 즉시 기계 장비를 대신 제조하고 현금을 수취하는 독점적 수혜 구조. 수주잔고(Backlog)의 급증으로 확실한 매출 성장 보장."
    ),
]

added = 0
for co in companies:
    cur.execute("SELECT id FROM companies WHERE ticker=? AND industry_id=5", (co[1],))
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
cur.execute("SELECT id, name, ticker FROM companies WHERE industry_id=5 ORDER BY id")
energy_companies = cur.fetchall()
print(f"\n=== 에너지 및 인프라 산업 기업 목록 ({len(energy_companies)}개) ===")
for c in energy_companies:
    print(f"  [{c[0]}] {c[1]} ({c[2]})")

conn.close()
print(f"\n완료! {added}개 기업 추가됨.")
