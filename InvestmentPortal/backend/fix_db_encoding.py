# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "investment_portal.db")

# 1. Correct Industry Reports (Tag -> (Title, Summary))
reports_data = {
    "자율주행": (
        "자율주행 산업 밸류체인 심층 분석",
        """## 1. 기술 표준화 전쟁: 센서 퓨전 vs 비전 온리
자율주행 기술의 가장 큰 논쟁은 주변 환경을 인식하는 방식에서 출발합니다.
- **센서 퓨전 진영:** 라이다(LiDAR), 레이더, 카메라를 결합하고 고정밀 지도(HD Map)를 활용. 물리적 이중화 설계를 통해 오류를 줄이지만 하드웨어 비용이 높습니다.
- **비전 온리 진영 (Tesla):** 비싼 라이다를 배제하고 오직 카메라(시각)와 거대 AI 신경망 연산(End-to-End AI)으로 인간의 운전 방식을 모방합니다.

## 2. 하드웨어 원가(BOM) 구조의 폭발적 변화
* **센서의 범용화:** 센서 비중은 레벨 2에서 80%를 차지하지만, 레벨 4/5에서는 30% 이하로 하락하며 마진이 줄어듭니다.
* **가치의 집중:** AI 컴퓨팅 및 연산 시스템의 비중은 폭증하며, 미래 투자의 본질적 가치는 'AI 중앙 컴퓨팅 및 냉각 인프라'로 집중됩니다.

## 3. 두뇌 생태계 전쟁: 3대 반도체 플랫폼
* **Nvidia:** 수직적 AI 생태계를 구축하여 데이터센터 학습부터 차량 내 연산까지 장악.
* **Qualcomm:** 스마트폰 기반 저전력 SoC로 인포테인먼트를 선점한 후 자율주행 확장.
* **Mobileye:** 칩과 알고리즘이 결합된 폐쇄형 구조.

## 4. 국가 패권 및 모빌리티 서비스 (MaaS)
하드웨어 판매에서 '마일(Mile) 당 과금'하는 로보택시 서비스 플랫폼으로 시장 규모가 재정의."""
    ),
    "로봇": (
        "로봇 산업 밸류체인 심층 분석",
        """## 1. 산업의 패러다임 변화: 휴머노이드와 AI의 결합
과거의 로봇 산업이 공장 내 고정된 위치에서 반복 작업을 수행하는 산업용 로봇에 국한되었다면, 현재는 AI 알고리즘의 발달로 스스로 인지, 판단, 제어하는 지능형 모바일 로봇과 휴머노이드로 진화하고 있습니다.
- **물리적 AI(Physical AI):** 가상 공간에서 작동하던 AI가 현실 세계의 물리적 법칙을 학습하여 로봇의 두뇌가 되는 시대로 진입했습니다.
- **수혜의 흐름:** 엔비디아의 Omniverse, Jetson과 같은 제어 시뮬레이터 플랫폼이 핵심 역할을 수행하며, 로봇의 학습 속도를 기하급수적으로 끌어올리고 있습니다.

## 2. 밸류체인 내 병목 현상
* **연산 가속화의 한계:** 수십 개의 관절과 다중 센서 입력을 실시간으로 처리하기 위한 초전력/초소형 칩셋 기술이 병목 현상으로 작용합니다.
* **정밀 구동계 (Actuators):** 로봇의 관절 역할을 하는 감속기 및 모터의 기술적 난이도와 원가 비중이 여전히 매우 높습니다.

## 3. 대표 응용 분야의 폭발적 성장
* **물류 및 자동화 (AMRs):** 이커머스와 글로벌 공급망 재편으로 창고 자동화 수요가 폭증 (Symbotic 등).
* **의료 및 특수 로봇:** 미세 수술 로봇 등 초고부가가치 시장의 독점적 지위 강화 (Intuitive Surgical)."""
    ),
    "우주": (
        "우주 산업 밸류체인 심층 분석",
        """## 1. 우주 비즈니스 모델: 위성 통신 및 데이터 플랫폼
민간 주도의 우주 개발(New Space) 시대가 본격화되면서 우주 비즈니스의 중심은 단순 발사체 개발에서 저궤도 위성 통신망(LEO Constellation) 구축 및 초고해상도 위성 영상 데이터 분석 플랫폼으로 전환되고 있습니다.
- **위성통신 대중화:** 스페이스X의 스타링크(Starlink)와 원웹(OneWeb)을 선두로, 전 세계 도서 지역 및 항공기, 선박에 인터넷을 끊김 없이 공급하는 초저지연 광대역 연결 서비스가 대세가 되었습니다.
- **수혜의 흐름:** 수백, 수천 대의 군집 위성을 관제하고 대용량 데이터를 처리하기 위한 클라우드 위성 지상국(Ground Station) 및 인프라의 가상화가 활발히 진행 중입니다.

## 2. 밸류체인 내 핵심 병목
* **발사 용량 및 주기 한계:** 지구 궤도에 올려야 할 위성 수요 대비 상업용 발사체 공급이 턱없이 부족하며, 재사용 로켓 기술(SpaceX, Rocket Lab 등) 유무가 핵심 격차를 가릅니다.
* **우주 파편 및 전파 간섭:** 지구 저궤도의 밀도 증가로 인한 충돌 리스크와 국가 간 주파수 점유권 분쟁이 확대되고 있습니다.

## 3. 우주군(Space Force) 창설 및 안보 자산화
국방 안보에서 저궤도 감시 정찰(ISR) 위성망 구축을 위해 펜타곤(SDA) 중심의 정부 발주 대형 프로젝트가 상업용 우주 기업들의 장기 수익 파이프라인 역할을 수행하고 있습니다."""
    )
}

# 2. Correct Value Chain Nodes (ordered as inserted)
nodes_data = [
    # 1. Autonomous Driving (industry_id = 1)
    ("핵심 기술 및 연산 인프라 (AI/Semiconductor)", "고성능 AI 칩 및 연산 플랫폼."),
    ("모빌리티 서비스 플랫폼 (MaaS)", "로보택시 등 소프트웨어 플랫폼 승자."),
    ("시스템 통합자 (OEM/SDV)", "독자 OS 확보 및 칩셋 결합을 주도하는 완성차/전장 시스템."),
    ("비전 및 센서 (Camera/Sensor)", "주행 데이터를 수집하는 하드웨어 센서류."),
    # 2. Robotics (industry_id = 2)
    ("의료 및 특수 목적 로봇 (Medical & Special Purpose)", "의료용 수술 로봇 등 고부가가치 특수 기기."),
    ("물류 및 공장 자동화 (AMR/Industrial)", "스마트 팩토리 및 자율이동형 물류 로봇 시스템."),
    ("제어 시스템 및 소프트웨어 (Control Systems & AI)", "로봇의 두뇌 및 시뮬레이터, 소프트웨어 플랫폼."),
    ("머신비전 및 인식 센서 (Vision & Sensors)", "로봇의 눈, 3D 카메라 및 시각적 판단."),
    ("무인기 및 드론 (Unmanned Systems)", "항공, 국방 등 특수 지형지물 탐색 및 이동 비행 로봇."),
    # 3. Space (industry_id = 3)
    ("발사체 및 발사 서비스 (Launch Vehicles & Services)", "로켓 설계·제조·발사 운영. 재사용 로켓으로 비용 혁신."),
    ("위성 제조 및 운영 (Satellite Manufacturing & Operations)", "통신·관측·항법 위성 설계·제작 및 군집 운용."),
    ("우주 인프라 및 지상 시스템 (Ground Systems & Infrastructure)", "지상국, 안테나, 네트워크 운영 및 위성 데이터 처리."),
    ("우주 방산 및 정찰 (Space Defense & ISR)", "방위·정보기관용 정찰·감시·정밀유도 위성 시스템."),
    ("우주 탐사 및 자원 개발 (Exploration & Space Resources)", "달·화성 탐사, 우주 정거장, 자원 채굴 프로젝트.")
]

# 3. Correct Companies (Ticker, Industry_ID) -> (Role, Growth)
companies_data = {
    # Autonomous Driving (industry_id = 1)
    ("NVDA", 1): (
        "고성능 GPU 기반(Drive Orin) 플랫폼",
        "데이터센터 및 자율주행 연산 생태계 독점"
    ),
    ("TSLA", 1): (
        "비전 온리, End-to-End AI 기반 자율주행 선도",
        "로보택시 전환 시 압도적 마진 창출"
    ),
    ("GOOGL", 1): (
        "센서 퓨전 진영의 대표 B2B 자율주행 솔루션",
        "글로벌 로보택시 네트워크 확장"
    ),
    ("UBER", 1): (
        "모빌리티 수요 플랫폼",
        "MaaS 전환 시 유동성 장악"
    ),
    ("QCOM", 1): (
        "차량용 인포테인먼트 및 Snapdragon Ride",
        "저전력 SoC 기반의 ADAS 침투"
    ),
    ("MBLY", 1): (
        "ADAS 시장 지배적 시각 처리 알고리즘",
        "보급형 자율주행 시장 확대 수혜"
    ),
    ("APTV", 1): (
        "차량용 전장 시스템 및 SDV 솔루션 통합",
        "차량 아키텍처 중앙 집중화 트렌드 수혜"
    ),
    ("NXPI", 1): (
        "자동차 레이더, V2X, ADAS 범용 칩",
        "완성차 내 반도체 탑재량 증가 구조적 수혜"
    ),
    ("ON", 1): (
        "차량용 이미지 센서 및 SiC 전력 반도체",
        "자율주행용 카메라 센서 고사양화 수혜"
    ),

    # Robotics (industry_id = 2)
    ("ISRG", 2): (
        "다빈치 수술 로봇 시스템 독점적 지위",
        "최소침습수술 트렌드 확대로 지속 성장"
    ),
    ("SYM", 2): (
        "물류 창고 자동화 및 AI 분류 로봇 시스템",
        "이커머스 물류망 대형 고객사 락인 효과"
    ),
    ("TER", 2): (
        "Universal Robots(협동로봇), MiR(물류로봇) 모회사",
        "중소형 공장들의 협동로봇 도입률 급증"
    ),
    ("ROK", 2): (
        "산업용 제어 시스템, 소프트웨어 및 스마트팩토리",
        "리쇼어링 및 공장 자동화 소프트웨어 구독 수익"
    ),
    ("ZBRA", 2): (
        "창고 내 물류 추적 및 바코드 머신 비전 시스템",
        "공급망 현대화 및 재고 관리 스마트화"
    ),
    ("PATH", 2): (
        "업무 자동화를 위한 RPA (소프트웨어 로보틱스)",
        "사무 인프라 자동화 및 AI 워크플로우 도입 팽창"
    ),
    ("CGNX", 2): (
        "제조 라인 결함 탐지 및 부품 인식용 2D/3D 머신 비전",
        "품질 관리 고도화에 따른 센서 수요 증가"
    ),
    ("AVAV", 2): (
        "드론, 무인기기 시스템 및 전술 로봇 솔루션",
        "국방 무인화 및 전술형 비행 로봇 수요 증가"
    ),
    ("NVDA", 2): (
        "Omniverse 및 Jetson 플랫폼 등 물리적 AI 시뮬레이터 제공",
        "로봇 두뇌 및 개발 훈련 인프라 독점으로 폭발적 마진 기대"
    ),

    # Space (industry_id = 3)
    ("RKLB", 3): (
        "소형 위성 전용 일렉트론 로켓 및 중형 뉴트론 개발 중",
        "소형 LEO 위성 발사 수요 급증으로 시장 점유율 확대"
    ),
    ("PL", 3): (
        "매일 전 지구를 촬영하는 초소형 위성 군집 지구 관측 서비스",
        "농업·환경·정부 수요 확대 및 AI 분석 플랫폼 고부가가치화"
    ),
    ("VSAT", 3): (
        "정지궤도(GEO) 위성 기반 광대역 인터넷 및 정부 통신",
        "군용 위성통신 및 항공기 내 인터넷 서비스 확장"
    ),
    ("KTOS", 3): (
        "위성 지상국 솔루션, 우주 전자전 및 드론 시스템",
        "우주군 확장 및 위성 지상 인프라 투자 급증 수혜"
    ),
    ("MAXR", 3): (
        "고해상도 위성 영상 및 지리공간 정보 플랫폼",
        "정부·국방 수요 및 상업용 지구 관측 시장 독점적 지위"
    ),
    ("LHX", 3): (
        "우주 센서, 정찰 위성 탑재체 및 통신 시스템 제공",
        "우주군 ISR 위성 프로그램 수주 증가 및 방산 예산 확대"
    ),
    ("NOC", 3): (
        "제임스웹 우주망원경 제작사이자 핵심 우주 방산 시스템 통합자",
        "아르테미스 달 착륙선 및 차세대 ICBM 사업 수주"
    ),
    ("SPCE", 3): (
        "민간 우주여행(서브오비탈) 및 초음속 이동 서비스",
        "우주관광 수요 개척 및 유인 우주 경험 프리미엄 시장 선점"
    ),
    ("LUNR", 3): (
        "NASA 아르테미스용 달 착륙선 개발 및 달 물자 수송 서비스(CLPS)",
        "달 경제 개막에 따른 NASA·ESA 장기 계약 및 달 자원 탐사 참여"
    ),
    ("LMT", 3): (
        "정찰·통신·기상 위성 및 발사체 시스템 통합(ULA 지분 보유)",
        "국가 안보 우주(NatSec Space) 장기 계약 및 GPS 위성 현대화"
    )
}

def fix_encoding():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Fix industry_reports
    print("Fixing industry_reports table...")
    for tag, (title, summary) in reports_data.items():
        cursor.execute(
            "UPDATE industry_reports SET title = ?, summary = ? WHERE tag = ?",
            (title, summary, tag)
        )
    conn.commit()

    # 2. Fix value_chain_nodes
    print("Fixing value_chain_nodes table...")
    cursor.execute("SELECT id FROM value_chain_nodes ORDER BY id")
    node_ids = [r[0] for r in cursor.fetchall()]
    
    if len(node_ids) == len(nodes_data):
        for node_id, (name, desc) in zip(node_ids, nodes_data):
            cursor.execute(
                "UPDATE value_chain_nodes SET node_name = ?, description = ? WHERE id = ?",
                (name, desc, node_id)
            )
        conn.commit()
    else:
        print(f"Warning: Node count mismatch (DB has {len(node_ids)}, expected {len(nodes_data)})")

    # 3. Fix companies
    print("Fixing companies table...")
    cursor.execute("SELECT id, ticker, industry_id FROM companies")
    companies = cursor.fetchall()
    for comp_id, ticker, ind_id in companies:
        key = (ticker, ind_id)
        if key in companies_data:
            role, growth = companies_data[key]
            cursor.execute(
                "UPDATE companies SET role_description = ?, future_growth = ? WHERE id = ?",
                (role, growth, comp_id)
            )
    conn.commit()

    print("Database encoding fix complete!")
    conn.close()

if __name__ == "__main__":
    fix_encoding()
