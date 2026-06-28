# -*- coding: utf-8 -*-
"""
전 산업 누락 종목 일괄 추가 스크립트
각 산업별 빠진 미국/한국 상장 종목 추가
"""
import sqlite3
from datetime import datetime

DB_PATH = 'investment_portal.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ================================================================
    # 현재 등록된 ticker 목록 조회
    # ================================================================
    cur.execute("SELECT ticker FROM companies")
    existing_tickers = {row[0] for row in cur.fetchall()}
    print(f"현재 등록 종목 수: {len(existing_tickers)}")

    new_companies = []

    # ================================================================
    # [id=1] 자율주행 (Autonomous Driving)
    # value_chain_nodes: 기존 node_id 확인 필요
    # ================================================================
    cur.execute("SELECT id, node_name FROM value_chain_nodes WHERE industry_id=1")
    nodes_1 = {row[1]: row[0] for row in cur.fetchall()}
    print(f"\n[자율주행] 노드: {list(nodes_1.keys())}")

    # 노드 이름으로 매핑 (기존 노드에서 적합한 것 선택)
    def get_node_1(keyword):
        for name, nid in nodes_1.items():
            if keyword.lower() in name.lower():
                return nid
        return list(nodes_1.values())[0]  # fallback: 첫번째 노드

    # 추가할 자율주행 종목 (미국 & 한국)
    additions_1 = [
        # 한국 - 현대차 그룹 (자율주행 투자 핵심)
        ('현대자동차', '005380.KS', 1, None, '국내 1위 완성차 기업. 보스턴다이나믹스·앱티브 합작 목티오날 등 대규모 자율주행 투자. 레벨3 자율주행 기능을 탑재한 G90 출시.', '아이오닉 브랜드 EV 라인업 확대와 함께 자율주행 레벨4 상용화 로드맵 가속. 소프트웨어 중심 자동차(SDV) 전환 주도.', 45),
        ('현대모비스', '012330.KS', 1, None, '현대차그룹 핵심 부품·모듈 계열사. 레이더·라이다·카메라 기반 자율주행 센서퓨전 시스템 및 코너 모듈 원천 기술 보유.', '전장 부품 및 자율주행 모듈 글로벌 독립 수주 확대. 레벨4 자율주행용 통합 소프트웨어 아키텍처 개발 선도.', 46),
        # 미국 - 빠진 핵심 자율주행 종목
        ('Luminar Technologies', 'LAZR', 1, None, '차량용 라이다(LiDAR) 전문기업. 볼보·Mercedes-Benz·NVIDIA 등과 공급 계약. 장거리 고정밀 라이다 원가경쟁력 우위.', '완성차 OEM 시리즈 생산 양산 전환으로 라이다 수익화 본격화. 자율주행 레벨3~4 확산 시 필수 센서 공급업체 지위 확립.', 47),
        ('Innoviz Technologies', 'INVZ', 1, None, '고성능 고체 라이다 전문기업. BMW iX 최초 양산 탑재. 저전력·소형화 InnovizOne/Two 센서 글로벌 공급.', 'BMW·Volkswagen·Baidu와 장기 공급 계약 기반 양산 매출 확대. 저비용 솔리드스테이트 라이다로 대중 시장 침투.', 48),
        ('Ceridian', 'AUR', 1, None, 'Aurora Innovation — 자율주행 트럭 상용화 1호 기업. 오로라 드라이버 상업 운행 개시.', 'Amazon·FedEx 화물 자율주행 파트너십으로 조기 수익화. Uber Freight와의 협력으로 물류 자율주행 선점.', 49),
    ]

    # ================================================================
    # [id=2] 로봇 (Robotics)
    # ================================================================
    cur.execute("SELECT id, node_name FROM value_chain_nodes WHERE industry_id=2")
    nodes_2 = {row[1]: row[0] for row in cur.fetchall()}
    print(f"\n[로봇] 노드: {list(nodes_2.keys())}")

    additions_2 = [
        # 한국 - 빠진 로봇 종목
        ('두산로보틱스', '454910.KQ', 2, None, '국내 1위 협동로봇(코봇) 기업. 산업용·서비스용·물류용 전 분야 라인업 보유. 두산그룹 계열 제조 노하우 기반.', '제조업 자동화 수요 급증 및 서비스 로봇 시장 진입으로 매출 다변화. 해외 수출 비중 확대 및 소프트웨어 플랫폼 수익 창출.', 40),
        ('레인보우로보틱스', '277810.KQ', 2, None, '삼성전자가 대주주인 이족보행·협동로봇 전문 기업. 국내 최초 이족보행 로봇 휴보 개발사 KAIST 출신.', '삼성전자 스마트 팩토리 자동화 프로젝트 수주 및 협동로봇 라인업 확장. 인간형 로봇(휴머노이드) 기술력 기반 차세대 성장 동력 확보.', 41),
        # 미국 - 빠진 로봇 종목
        ('ABB Ltd', 'ABB', 2, None, '글로벌 1위 산업용 로봇 제조사. 자동차·전자·식품 업종 핵심 로봇 팔 공급. AI 기반 로봇 통합 소프트웨어 YuMi 플랫폼.', '제조업 리쇼어링 및 노동력 부족으로 산업용 로봇 수요 구조적 증가. 전동화·자동화 복합 수혜.', 42),
        ('Agility Robotics', 'AGIX', 2, None, '아마존 투자 인간형 로봇(휴머노이드) 전문기업. 물류 창고용 이족보행 로봇 Digit 상용화 1호.', '아마존 물류 네트워크 내 Digit 대규모 도입으로 조기 수익화. 반복 작업 자동화를 통한 로봇-인간 협업 산업 창출.', 43),
        ('Serve Robotics', 'SERV', 2, None, 'Uber 스핀오프 라스트마일 배달 로봇 전문기업. Uber Eats·Shake Shack 등과 배달 로봇 파트너십. NVIDIA 투자사.', '자율배달 로봇 배포 확대 및 NVIDIA 파트너십 기반 AI 고도화. 도시 배달 자동화 선점 플레이.', 44),
    ]

    # ================================================================
    # [id=3] 우주 (Space)
    # ================================================================
    cur.execute("SELECT id, node_name FROM value_chain_nodes WHERE industry_id=3")
    nodes_3 = {row[1]: row[0] for row in cur.fetchall()}
    print(f"\n[우주] 노드: {list(nodes_3.keys())}")

    additions_3 = [
        # 한국 - 우주 관련 상장사
        ('한국항공우주', '047810.KS', 3, None, 'KAI — 국내 유일 완제기(T-50·FA-50·KF-21) 및 위성체 개발·생산 기업. 한국형 발사체 누리호 위성 탑재부 제작 참여.', '수리온 헬기·KF-21 전투기 양산 수주 급증. 한국형 정찰위성·초소형 SAR 위성 군집 프로젝트 및 민간 위성 수출 확대.', 45),
        ('LIG넥스원', '079550.KS', 3, None, '정밀유도무기·전자전·우주방위 전문 방산기업. 국내 최초 SAR 위성 개발 참여 및 위성 기반 정밀 항법 시스템 공급.', '한국형 3축 체계(Kill Chain) 전력화 수혜 및 중동·동남아 방산 수출 확대. 위성 기반 감시정찰 시스템 사업 본격화.', 46),
        # 미국 - 빠진 우주 종목
        ('Redwire', 'RDW', 3, None, '우주 인프라·위성 부품·우주 제조 전문기업. NASA·DoD 위성 구조물·태양광 패널·3D 프린팅 공급사.', 'LEO·달·화성 탐사 인프라 수요 증가로 우주 제조 수혜. ISAM(궤도 위성 서비스·조립·수리) 사업 선점.', 47),
        ('Sidus Space', 'SIDU', 3, None, '초소형 위성 제조·발사 서비스 기업. LizzieSat 군집 위성 배치를 통한 데이터 서비스 제공.', '초소형 위성 군집 기반 실시간 지구 관측 데이터 상업화. 방산·기후 모니터링 고부가 데이터 판매 수익 모델.', 48),
    ]

    # ================================================================
    # [id=4] 코인 & 블록체인 (Crypto)
    # ================================================================
    cur.execute("SELECT id, node_name FROM value_chain_nodes WHERE industry_id=4")
    nodes_4 = {row[1]: row[0] for row in cur.fetchall()}
    print(f"\n[코인] 노드: {list(nodes_4.keys())}")

    additions_4 = [
        # 미국 - 빠진 코인 종목
        ('Robinhood Crypto', 'HOOD', 4, None, '이미 있음', '', 0),  # 이미 있음
    ]
    # 코인은 이미 20개로 충분 - 추가 없음
    additions_4 = []

    # ================================================================
    # [id=5] 에너지 (AI Energy)
    # ================================================================
    cur.execute("SELECT id, node_name FROM value_chain_nodes WHERE industry_id=5")
    nodes_5 = {row[1]: row[0] for row in cur.fetchall()}
    print(f"\n[에너지] 노드: {list(nodes_5.keys())}")

    additions_5 = [
        # 한국 - 에너지/원전 관련 빠진 종목
        ('LS ELECTRIC', '010120.KS', 5, None, '변압기·배전반·에너지관리시스템(EMS) 국내 1위 전력 기기 기업. 국내외 데이터센터·재생에너지 연계 전력 기기 핵심 공급사.', '미국·중동 변압기 수출 급증 및 AI 데이터센터 전력 설비 수주 확대. 그리드 현대화 수혜로 해외 매출 비중 급성장.', 35),
        ('HD현대일렉트릭', '267260.KS', 5, None, '변압기·차단기·배전반 글로벌 수출 특화 전력 기기 기업. 미국 전력망 현대화 프로젝트 핵심 한국 공급업체.', 'GE/SIEMENS 대비 경쟁력 있는 가격의 고전압 변압기 미국 수출 최대 수혜주. 수주잔고 역대 최고 경신.', 36),
        ('효성중공업', '298040.KS', 5, None, '초고압 변압기·차단기·STATCOM 전력 기기 전문 기업. 국내 최초 초전도 한류기 개발 및 친환경 가스절연개폐장치(GIS) 수출.', '미국·유럽·중동 초고압 변압기 수출 급증. 재생에너지 연계 STATCOM 수주 확대 및 에너지저장장치(ESS) 사업 확장.', 37),
    ]

    # ================================================================
    # [id=6] 전력 인프라 (Power Infrastructure)
    # ================================================================
    cur.execute("SELECT id, node_name FROM value_chain_nodes WHERE industry_id=6")
    nodes_6 = {row[1]: row[0] for row in cur.fetchall()}
    print(f"\n[전력인프라] 노드: {list(nodes_6.keys())}")

    additions_6 = [
        # 한국 - 전력 인프라 빠진 종목
        ('제룡전기', '033100.KQ', 6, None, '국내 중소형 변압기 전문 제조사. 미국 수출 급증으로 K-변압기 붐의 최대 수혜 소형주. 생산 캐파 대비 수주잔고 급증.', '미국 전력망 현대화 수요 폭발로 변압기 리드타임 2~3년. 중소형 변압기 긴급 수요 집중 수혜 및 북미 법인 설립으로 직판 체계 구축.', 45),
        ('비에이치아이', '083650.KQ', 6, None, '폐열회수보일러(HRSG)·일반산업 열교환기 전문 제조사. 가스터빈·복합화력발전소 핵심 기자재 공급.', 'AI 데이터센터 전력 수요 급증으로 가스터빈 복합화력 발전소 건설 수요 폭증. 국내·미국·중동 복합화력 프로젝트 수주 급증.', 46),
    ]

    # ================================================================
    # [id=7] 이차전지 (Battery) - 미국 상장 추가
    # ================================================================
    cur.execute("SELECT id, node_name FROM value_chain_nodes WHERE industry_id=7")
    nodes_7 = {row[1]: row[0] for row in cur.fetchall()}
    print(f"\n[이차전지] 노드: {list(nodes_7.keys())}")

    # 노드 ID 가져오기
    upstream_7 = None
    mid_7 = None
    down_7 = None
    recycle_7 = None
    for name, nid in nodes_7.items():
        if '업스트림' in name or '정·제련' in name or '채굴' in name:
            upstream_7 = nid
        elif '미드' in name or '소재' in name:
            mid_7 = nid
        elif '다운' in name or '셀' in name or 'ESS' in name:
            down_7 = nid
        elif '리사이클' in name or '순환' in name:
            recycle_7 = nid

    # fallback
    node_ids_7 = list(nodes_7.values())
    if upstream_7 is None: upstream_7 = node_ids_7[0]
    if mid_7 is None: mid_7 = node_ids_7[1] if len(node_ids_7) > 1 else node_ids_7[0]
    if down_7 is None: down_7 = node_ids_7[2] if len(node_ids_7) > 2 else node_ids_7[0]
    if recycle_7 is None: recycle_7 = node_ids_7[3] if len(node_ids_7) > 3 else node_ids_7[0]

    additions_7 = [
        # 미국 상장 - 업스트림 (광물)
        ('Albemarle', 'ALB', 7, upstream_7, 'Albemarle — 글로벌 1위 리튬 생산업체. 칠레 아타카마 염호, 호주 그린부시스 광산 보유. 전기차 배터리 핵심 리튬 화합물 독과점 공급.', '리튬 가격 반등 시 대규모 레버리지. 북미 IRA 수혜 배터리 제조 확대로 리튬 수요 구조적 성장 수혜. 리사이클 리튬 사업 확장.', 10),
        ('Lithium Americas', 'LAC', 7, upstream_7, 'Lithium Americas — 미국 네바다주 세계급 리튬 광상(Thacker Pass) 개발사. GM 전략적 투자 유치. 비중국 북미 최대 리튬 공급원.', 'Thacker Pass 1단계 생산 개시 시 GM 장기 공급 계약으로 즉각 수익화. 북미 배터리 공급망 IRA 수혜 핵심 원자재 공급사.', 11),
        # 미국 상장 - 다운스트림 (ESS)
        ('Fluence Energy', 'FLNC', 7, down_7, 'Fluence Energy — AES·Siemens 합작 그리드 규모 ESS 전문기업. AI 데이터센터 전력 안정화 및 재생에너지 저장 시스템 글로벌 1위 솔루션.', 'AI 데이터센터 전력 수요 폭증으로 그리드 ESS 수요 역대 최고. 수주잔고 급증 및 소프트웨어 기반 고마진 Fluence IQ 플랫폼 수익 확대.', 12),
        # 미국 상장 - 차세대 (전고체)
        ('QuantumScape', 'QS', 7, mid_7, 'QuantumScape — 폭스바겐(VW) 투자 고체 전해질 전고체 배터리 전문 스타트업. 화재 없는 리튬 금속 전고체 배터리 상용화 최전선.', '전고체 배터리 상용화 성공 시 10~20배 주가 상승 잠재력. 에너지 밀도 2배·안전성·수명 압도적 우위로 EV 배터리 판도 전환 주도.', 13),
        # 미국 상장 - 리사이클링
        ('Li-Cycle', 'LICY', 7, recycle_7, 'Li-Cycle — 북미 최대 배터리 리사이클링 전문기업. 습식 제련(Hydromet) 기술로 니켈·코발트·리튬 95% 이상 고순도 회수. IRA 수혜.', 'IRA 비중국산 광물 조달 요건 강화로 재활용 광물 수요 급증. 로체스터 허브 가동 시 대규모 흑자 전환 및 GM·LG에너지솔루션 파트너십 수익화.', 14),
        # 한국 상장 추가
        ('에코프로', '086520.KQ', 7, upstream_7, '에코프로비엠의 모회사. 에코프로그룹 지주사로 양극재 사업 외에도 환경 플랜트, 대기오염 방지 사업 보유. 에코프로 밸류체인 종합 투자 수단.', '에코프로비엠 고성장 낙수 효과 및 에코프로머티리얼즈(전구체) IPO로 그룹 밸류에이션 리레이팅 기대.', 15),
        ('새빗켐', '256840.KQ', 7, recycle_7, '폐배터리 전처리(블랙파우더 제조) 전문기업. 성일하이텍과 함께 국내 배터리 리사이클링 투트랙 생태계 구성. 저비용 전처리 공정 특화.', '이차전지 생산 증가에 비례한 폐배터리 발생량 급증으로 전처리 수요 폭증. 유럽·미국 현지 거점 확대 및 완성차·배터리사 직계약 확대.', 16),
    ]

    # ================================================================
    # 실제 DB 삽입
    # ================================================================
    all_additions = [
        (1, additions_1),
        (2, additions_2),
        (3, additions_3),
        (5, additions_5),
        (6, additions_6),
        (7, additions_7),
    ]

    # 각 산업 노드 기본값 조회
    def get_default_node(industry_id):
        cur.execute("SELECT id FROM value_chain_nodes WHERE industry_id=? ORDER BY id LIMIT 1", (industry_id,))
        row = cur.fetchone()
        return row[0] if row else None

    inserted_count = 0
    for ind_id, additions in all_additions:
        default_node = get_default_node(ind_id)
        for comp in additions:
            name, ticker, iid, node_id, role, growth, disp = comp
            if ticker in existing_tickers:
                print(f"  [SKIP] {ticker} already exists")
                continue
            if node_id is None:
                node_id = default_node
            try:
                cur.execute("""
                    INSERT INTO companies (name, ticker, industry_id, value_chain_node_id, role_description, future_growth, display_order)
                    VALUES (?,?,?,?,?,?,?)
                """, (name, ticker, iid, node_id, role, growth, disp))
                existing_tickers.add(ticker)
                print(f"  [INSERT] {ticker} ({name}) -> industry_id={iid}")
                inserted_count += 1
            except Exception as e:
                print(f"  [ERROR] {ticker}: {e}")

    conn.commit()
    print(f"\n총 {inserted_count}개 신규 종목 삽입 완료!")

    # 삽입된 종목 확인
    cur.execute("SELECT id, name, ticker, industry_id FROM companies WHERE industry_id IN (1,2,3,5,6,7) ORDER BY industry_id, display_order, id")
    all_comps = cur.fetchall()
    print(f"\n전체 종목 수: {len(all_comps)}")

    conn.close()

if __name__ == "__main__":
    main()
