# -*- coding: utf-8 -*-
"""
식음료 산업 (id=16) DB 삽입 스크립트
K-푸드 레볼루션: 밸류체인 및 핵심 기업 등록
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investment_portal.db")

def insert_fnb_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    industry_id = 16
    title = "식음료"
    summary = "K-푸드 레볼루션: 라면은 어떻게 '테크 주식'이 되었나? (글로벌 F&B 밸류체인 및 투자 지도)"
    file_path = "16. 식음료/식음료.pdf"
    tag = "소비재"

    # 1. 산업 기본 정보 추가
    cursor.execute("""
        INSERT OR IGNORE INTO industry_reports (id, title, summary, file_path, tag)
        VALUES (?, ?, ?, ?, ?)
    """, (industry_id, title, summary, file_path, tag))

    # 기존 노드/기업 삭제 (초기화)
    cursor.execute("DELETE FROM companies WHERE industry_id=?", (industry_id,))
    cursor.execute("DELETE FROM value_chain_nodes WHERE industry_id=?", (industry_id,))

    # 2. 밸류체인 노드 정의
    nodes = [
        (1, "R&D (소재/바이오)", "식품 소재 연구, 바이오 기술 적용 및 대체 소재 개발 (기초 원료 및 바이오)"),
        (2, "제조 (공급망)", "스마트 제조 및 물류, 글로벌 대량 생산 체제 및 가공식품 공급망 확보"),
        (3, "유통 (OSMU/소스)", "무거운 식자재 대신 '핵심 IP/소스' 압축 수출로 물류비 제로화, OSMU(원소스 멀티유즈) 물류 해킹 전략"),
        (4, "마케팅 (독점 IP)", "독점적 스토리텔링과 비주얼을 극대화한 한정판/IP 콜라보 및 용도별 가격 분리(Dual-Pricing)"),
        (5, "소비 (HMR/케어푸드)", "가정간편식(HMR) 및 맞춤형 케어푸드, 편의점 등 오프라인/온라인 최종 소비자 접점")
    ]
    
    node_ids = {}
    for order, name, desc in nodes:
        cursor.execute("""
            INSERT INTO value_chain_nodes (industry_id, node_name, description) 
            VALUES (?, ?, ?)
        """, (industry_id, name, desc))
        node_ids[name] = cursor.lastrowid

    # 3. 기업 정의 (노드 매핑)
    # node_name, display_order, symbol, name, description
    companies = [
        # 1. R&D (소재/바이오)
        ("R&D (소재/바이오)", 1, "097950.KS", "CJ제일제당", "국내 최대 식품/바이오 기업, 글로벌 그린 바이오 및 식품 R&D 선도"),
        ("R&D (소재/바이오)", 2, "001680.KS", "대상", "종합식품 및 바이오 소재, 조미료 및 전분당 글로벌 수출"),
        ("R&D (소재/바이오)", 3, "INGR", "인그리디언", "글로벌 특수 원료 및 식물성 소재 공급업체"),
        ("R&D (소재/바이오)", 4, "ADM", "아처대니얼스미들랜드", "글로벌 최대 농산물 가공 및 식품 소재 기업"),
        
        # 2. 제조 (공급망)
        ("제조 (공급망)", 1, "003230.KS", "삼양식품", "불닭볶음면 글로벌 신드롬 주도, K-라면 수출의 핵심 기업"),
        ("제조 (공급망)", 2, "004370.KS", "농심", "신라면 등 글로벌 라면/스낵 제조 기업, 미주 시장 등 글로벌 공략"),
        ("제조 (공급망)", 3, "TSN", "타이슨 푸즈", "미국 최대 육류 가공 및 단백질 식품 제조사"),
        ("제조 (공급망)", 4, "HSY", "허시", "글로벌 초콜릿 및 스낵 제조 기업"),
        
        # 3. 유통 (OSMU/소스)
        ("유통 (OSMU/소스)", 1, "017810.KS", "풀무원", "건강기능식품 및 신선식품, 해외 시장(미국, 중국 등) 두부/아시안푸드 유통망 확보"),
        ("유통 (OSMU/소스)", 2, "MKC", "맥코믹", "글로벌 1위 향신료, 조미료 및 소스 제조/유통 기업"),
        ("유통 (OSMU/소스)", 3, "SYY", "시스코", "세계 최대 규모의 식자재 유통 기업"),
        
        # 4. 마케팅 (독점 IP)
        ("마케팅 (독점 IP)", 1, "271560.KS", "오리온", "초코파이 등 메가 IP 보유, 철저한 현지화로 글로벌 제과 시장 장악"),
        ("마케팅 (독점 IP)", 2, "MDLZ", "몬델리즈", "오레오, 리츠 등 강력한 글로벌 스낵 IP 보유 기업"),
        ("마케팅 (독점 IP)", 3, "CELH", "셀시우스", "건강 지향성 에너지 드링크, 독보적 마케팅으로 폭발적 성장"),
        
        # 5. 소비 (HMR/케어푸드)
        ("소비 (HMR/케어푸드)", 1, "453340.KS", "현대그린푸드", "단체급식, 식자재 유통 및 프리미엄 HMR/케어푸드 사업 전개"),
        ("소비 (HMR/케어푸드)", 2, "282330.KS", "BGF리테일", "CU 편의점 운영, 즉석식품 및 밀키트 소비자 접점 장악"),
        ("소비 (HMR/케어푸드)", 3, "CAG", "콘아그라 브랜즈", "다수의 유명 HMR/가공식품 브랜드를 보유한 북미 식품 기업")
    ]

    for node_name, disp_order, csymbol, cname, cdesc in companies:
        nid = node_ids[node_name]
        cursor.execute("""
            INSERT INTO companies (industry_id, value_chain_node_id, name, ticker, role_description, display_order) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (industry_id, nid, cname, csymbol, cdesc, disp_order))

    conn.commit()
    conn.close()
    print("식음료 산업 DB 데이터 삽입 완료!")

if __name__ == "__main__":
    insert_fnb_data()
