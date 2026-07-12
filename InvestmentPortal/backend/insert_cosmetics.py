# -*- coding: utf-8 -*-
"""
화장품 산업 (id=15) DB 삽입 스크립트
K-뷰티 밸류체인 및 핵심 기업 등록
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investment_portal.db")

def insert_cosmetics_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    industry_id = 15
    title = "화장품"
    summary = "생태계의 청사진: K-뷰티 밸류체인 해체 분석 및 자본을 이기는 생존 전략"
    file_path = "15. 화장품/화장품.pdf"
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
        (1, "원료 및 R&D", "바이오 특허 원료 개발, PDRN, 시카, 엑소좀 등 핵심 성분 및 딜리버리 기술 연구"),
        (2, "제조 및 생산 (ODM)", "글로벌 TOP ODM 제조 플랫폼, 제형 혁신 및 다품종 소량 생산 시스템"),
        (3, "브랜드 및 마케팅", "데이터 마케팅, 팬덤 관리, 니치 카테고리(K-Body, 롱제비티) 및 TPO 혁신 기획"),
        (4, "유통 및 리테일", "글로벌 풀필먼트, 직매입 유통, 미국/유럽/신흥시장 리테일 채널")
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
        # 원료 및 R&D
        ("원료 및 R&D", 1, "086710.KQ", "선진뷰티사이언스", "화장품 원료(자외선 차단제, 마이크로비드 등) 제조 및 글로벌 수출"),
        ("원료 및 R&D", 2, "078140.KQ", "대봉엘에스", "화장품 소재 및 원료의약품 전문 기업"),
        ("원료 및 R&D", 3, "214370.KQ", "케어젠", "펩타이드 기반 바이오 원료 및 화장품/의료기기 개발"),
        
        # 제조 및 생산
        ("제조 및 생산 (ODM)", 1, "192820.KS", "코스맥스", "글로벌 1위 화장품 ODM 전문 기업"),
        ("제조 및 생산 (ODM)", 2, "161890.KS", "한국콜마", "화장품, 제약, 건강기능식품 글로벌 ODM 기업"),
        ("제조 및 생산 (ODM)", 3, "352480.KQ", "씨앤씨인터내셔널", "포인트 메이크업 색조 화장품 글로벌 ODM 기업"),
        
        # 브랜드 및 마케팅
        ("브랜드 및 마케팅", 1, "018290.KQ", "브이티", "리들샷 등 마이크로니들 기반 화장품 브랜드, 일본 등 글로벌 흥행"),
        ("브랜드 및 마케팅", 2, "237880.KQ", "클리오", "색조 전문 뷰티 브랜드, K-뷰티 글로벌 확산 선도"),
        ("브랜드 및 마케팅", 3, "439090.KQ", "마녀공장", "클렌징 오일 등 자연주의 스킨케어 브랜드"),
        ("브랜드 및 마케팅", 4, "114840.KQ", "아이패밀리에스씨", "색조 브랜드 '롬앤' 운영, MZ세대 타겟 글로벌 팬덤 확보"),
        ("브랜드 및 마케팅", 5, "ELF", "엘프뷰티", "미국 가성비 색조 화장품 및 스킨케어 브랜드, GenZ 인기"),
        ("브랜드 및 마케팅", 6, "EL", "에스티로더", "글로벌 럭셔리 뷰티 브랜드 포트폴리오 보유"),
        ("브랜드 및 마케팅", 7, "COTY", "코티", "글로벌 향수 및 색조 화장품 전문 기업"),
        
        # 유통 및 리테일
        ("유통 및 리테일", 1, "257720.KQ", "실리콘투", "K-뷰티 글로벌 이커머스 및 풀필먼트 유통 플랫폼(StyleKorean)"),
        ("유통 및 리테일", 2, "ULTA", "울타뷰티", "미국 최대 뷰티 전문 오프라인 리테일러"),
        ("유통 및 리테일", 3, "AMZN", "아마존", "글로벌 최대 이커머스, K-뷰티 핵심 온라인 유통 채널"),
        ("유통 및 리테일", 4, "TGT", "타겟", "미국 주요 대형 마트, 대중적 뷰티 브랜드 유통"),
        ("유통 및 리테일", 5, "WMT", "월마트", "미국 최대 할인점, 가성비 뷰티 제품 유통")
    ]

    for node_name, disp_order, csymbol, cname, cdesc in companies:
        nid = node_ids[node_name]
        cursor.execute("""
            INSERT INTO companies (industry_id, value_chain_node_id, name, ticker, role_description, display_order) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (industry_id, nid, cname, csymbol, cdesc, disp_order))

    conn.commit()
    conn.close()
    print("화장품 산업 DB 데이터 삽입 완료!")

if __name__ == "__main__":
    insert_cosmetics_data()
