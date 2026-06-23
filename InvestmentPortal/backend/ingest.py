import json
import datetime
from database import SessionLocal, engine
import models
from comprehensive_fetcher import fetch_full_company_data

models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)

def populate_db():
    db = SessionLocal()
    
    # Check if already populated
    if db.query(models.IndustryReport).count() > 0:
        print("Database already populated. Skipping.")
        # We dropped everything above, so it will be 0.
    
    # ==========================================
    # 1. Autonomous Driving (자율주행)
    # ==========================================
    ad_markdown = """
## 1. 기술 표준화 전쟁: 센서 퓨전 vs 비전 온리
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
하드웨어 판매에서 '마일(Mile) 당 과금'하는 로보택시 서비스 플랫폼으로 시장 규모가 재정의.
    """

    ad_report = models.IndustryReport(
        title="자율주행 산업 밸류체인 심층 분석",
        summary=ad_markdown,
        file_path="D:\\Industry\\산업자료\\1. 자율주행\\자율주행 산업 분석.pdf",
        tag="자율주행"
    )
    db.add(ad_report)
    db.commit()
    db.refresh(ad_report)

    ad_nodes = [
        {"name": "핵심 기술 및 연산 인프라 (AI/Semiconductor)", "desc": "고성능 AI 칩 및 연산 플랫폼."},
        {"name": "모빌리티 서비스 플랫폼 (MaaS)", "desc": "로보택시 등 소프트웨어 플랫폼 승자."},
        {"name": "시스템 통합자 (OEM/SDV)", "desc": "독자 OS 확보 및 칩셋 결합을 주도하는 완성차/전장 시스템."},
        {"name": "비전 및 센서 (Camera/Sensor)", "desc": "주행 데이터를 수집하는 하드웨어 센서류."}
    ]
    
    ad_node_objs = {}
    for nd in ad_nodes:
        node = models.ValueChainNode(industry_id=ad_report.id, node_name=nd["name"], description=nd["desc"])
        db.add(node)
        db.commit()
        db.refresh(node)
        ad_node_objs[nd["name"]] = node

    # ==========================================
    # 2. Robotics (로봇)
    # ==========================================
    robotics_markdown = """
## 1. 산업의 패러다임 변화: 휴머노이드와 AI의 결합
과거의 로봇 산업이 공장 내 고정된 위치에서 반복 작업을 수행하는 산업용 로봇에 국한되었다면, 현재는 AI 알고리즘의 발달로 스스로 인지, 판단, 제어하는 지능형 모바일 로봇과 휴머노이드로 진화하고 있습니다.
- **물리적 AI(Physical AI):** 가상 공간에서 작동하던 AI가 현실 세계의 물리적 법칙을 학습하여 로봇의 두뇌가 되는 시대로 진입했습니다.
- **수혜의 흐름:** 엔비디아의 Omniverse, Jetson과 같은 제어 시뮬레이터 플랫폼이 핵심 역할을 수행하며, 로봇의 학습 속도를 기하급수적으로 끌어올리고 있습니다.

## 2. 밸류체인 내 병목 현상
* **연산 가속화의 한계:** 수십 개의 관절과 다중 센서 입력을 실시간으로 처리하기 위한 초전력/초소형 칩셋 기술이 병목 현상으로 작용합니다.
* **정밀 구동계 (Actuators):** 로봇의 관절 역할을 하는 감속기 및 모터의 기술적 난이도와 원가 비중이 여전히 매우 높습니다.

## 3. 대표 응용 분야의 폭발적 성장
* **물류 및 자동화 (AMRs):** 이커머스와 글로벌 공급망 재편으로 창고 자동화 수요가 폭증 (Symbotic 등).
* **의료 및 특수 로봇:** 미세 수술 로봇 등 초고부가가치 시장의 독점적 지위 강화 (Intuitive Surgical).
    """

    robot_report = models.IndustryReport(
        title="로봇 산업 밸류체인 심층 분석",
        summary=robotics_markdown,
        file_path="D:\\Industry\\산업자료\\2. 로봇\\로봇 산업.pdf",
        tag="로봇"
    )
    db.add(robot_report)
    db.commit()
    db.refresh(robot_report)

    robot_nodes = [
        {"name": "의료 및 특수 목적 로봇 (Medical & Special Purpose)", "desc": "의료용 수술 로봇 등 고부가가치 특수 기기."},
        {"name": "물류 및 공장 자동화 (AMR/Industrial)", "desc": "스마트 팩토리 및 자율이동형 물류 로봇 시스템."},
        {"name": "제어 시스템 및 소프트웨어 (Control Systems & AI)", "desc": "로봇의 두뇌 및 시뮬레이터, 소프트웨어 플랫폼."},
        {"name": "머신비전 및 인식 센서 (Vision & Sensors)", "desc": "로봇의 눈, 3D 카메라 및 시각적 판단."},
        {"name": "무인기 및 드론 (Unmanned Systems)", "desc": "항공, 국방 등 특수 지형지물 탐색 및 이동 비행 로봇."}
    ]

    robot_node_objs = {}
    for nd in robot_nodes:
        node = models.ValueChainNode(industry_id=robot_report.id, node_name=nd["name"], description=nd["desc"])
        db.add(node)
        db.commit()
        db.refresh(node)
        robot_node_objs[nd["name"]] = node


    # ==========================================
    # 3. Companies Definition
    # ==========================================
    companies_data = [
        # Autonomous Driving
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "Nvidia", "ticker": "NVDA", "role": "고성능 GPU 기반(Drive Orin) 플랫폼", "growth": "데이터센터 및 자율주행 연산 생태계 독점", "node": "핵심 기술 및 연산 인프라 (AI/Semiconductor)"},
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "Tesla", "ticker": "TSLA", "role": "비전 온리, End-to-End AI 기반 자율주행 선도", "growth": "로보택시 전환 시 압도적 마진 창출", "node": "시스템 통합자 (OEM/SDV)"},
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "Alphabet (Waymo)", "ticker": "GOOGL", "role": "센서 퓨전 진영의 대표 B2B 자율주행 솔루션", "growth": "글로벌 로보택시 네트워크 확장", "node": "모빌리티 서비스 플랫폼 (MaaS)"},
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "Uber", "ticker": "UBER", "role": "모빌리티 수요 플랫폼", "growth": "MaaS 전환 시 유동성 장악", "node": "모빌리티 서비스 플랫폼 (MaaS)"},
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "Qualcomm", "ticker": "QCOM", "role": "차량용 인포테인먼트 및 Snapdragon Ride", "growth": "저전력 SoC 기반의 ADAS 침투", "node": "핵심 기술 및 연산 인프라 (AI/Semiconductor)"},
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "Mobileye", "ticker": "MBLY", "role": "ADAS 시장 지배적 시각 처리 알고리즘", "growth": "보급형 자율주행 시장 확대 수혜", "node": "핵심 기술 및 연산 인프라 (AI/Semiconductor)"},
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "Aptiv", "ticker": "APTV", "role": "차량용 전장 시스템 및 SDV 솔루션 통합", "growth": "차량 아키텍처 중앙 집중화 트렌드 수혜", "node": "시스템 통합자 (OEM/SDV)"},
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "NXP Semiconductors", "ticker": "NXPI", "role": "자동차 레이더, V2X, ADAS 범용 칩", "growth": "완성차 내 반도체 탑재량 증가 구조적 수혜", "node": "핵심 기술 및 연산 인프라 (AI/Semiconductor)"},
        {"ind": ad_report, "node_dict": ad_node_objs, "name": "ON Semiconductor", "ticker": "ON", "role": "차량용 이미지 센서 및 SiC 전력 반도체", "growth": "자율주행용 카메라 센서 고사양화 수혜", "node": "비전 및 센서 (Camera/Sensor)"},
        
        # Robotics
        {"ind": robot_report, "node_dict": robot_node_objs, "name": "Intuitive Surgical", "ticker": "ISRG", "role": "다빈치 수술 로봇 시스템 독점적 지위", "growth": "최소침습수술 트렌드 확대로 지속 성장", "node": "의료 및 특수 목적 로봇 (Medical & Special Purpose)"},
        {"ind": robot_report, "node_dict": robot_node_objs, "name": "Symbotic", "ticker": "SYM", "role": "물류 창고 자동화 및 AI 분류 로봇 시스템", "growth": "이커머스 물류망 대형 고객사 락인 효과", "node": "물류 및 공장 자동화 (AMR/Industrial)"},
        {"ind": robot_report, "node_dict": robot_node_objs, "name": "Teradyne", "ticker": "TER", "role": "Universal Robots(협동로봇), MiR(물류로봇) 모회사", "growth": "중소형 공장들의 협동로봇 도입률 급증", "node": "물류 및 공장 자동화 (AMR/Industrial)"},
        {"ind": robot_report, "node_dict": robot_node_objs, "name": "Rockwell Automation", "ticker": "ROK", "role": "산업용 제어 시스템, 소프트웨어 및 스마트팩토리", "growth": "리쇼어링 및 공장 자동화 소프트웨어 구독 수익", "node": "물류 및 공장 자동화 (AMR/Industrial)"},
        {"ind": robot_report, "node_dict": robot_node_objs, "name": "Zebra Technologies", "ticker": "ZBRA", "role": "창고 내 물류 추적 및 바코드 머신 비전 시스템", "growth": "공급망 현대화 및 재고 관리 스마트화", "node": "물류 및 공장 자동화 (AMR/Industrial)"},
        {"ind": robot_report, "node_dict": robot_node_objs, "name": "UiPath", "ticker": "PATH", "role": "업무 자동화를 위한 RPA (소프트웨어 로보틱스)", "growth": "사무 인프라 자동화 및 AI 워크플로우 도입 팽창", "node": "제어 시스템 및 소프트웨어 (Control Systems & AI)"},
        {"ind": robot_report, "node_dict": robot_node_objs, "name": "Cognex", "ticker": "CGNX", "role": "제조 라인 결함 탐지 및 부품 인식용 2D/3D 머신 비전", "growth": "품질 관리 고도화에 따른 센서 수요 증가", "node": "머신비전 및 인식 센서 (Vision & Sensors)"},
        {"ind": robot_report, "node_dict": robot_node_objs, "name": "AeroVironment", "ticker": "AVAV", "role": "드론, 무인기기 시스템 및 전술 로봇 솔루션", "growth": "국방 무인화 및 전술형 비행 로봇 수요 증가", "node": "무인기 및 드론 (Unmanned Systems)"}
    ]

    for cd in companies_data:
        comp = models.Company(
            industry_id=cd["ind"].id,
            value_chain_node_id=cd["node_dict"][cd["node"]].id,
            name=cd["name"],
            ticker=cd["ticker"],
            role_description=cd["role"],
            future_growth=cd["growth"]
        )
        db.add(comp)
        db.commit()
        db.refresh(comp)
        
        # 4. Fetch Full Institutional-Grade Data
        print(f"Fetching full data for {cd['ticker']} ({cd['ind'].tag})...")
        try:
            full_data = fetch_full_company_data(cd["ticker"])

            # 4a. Save CompanyProfile (valuation + profitability)
            if full_data["profile"]:
                profile_data = full_data["profile"]
                # Remove keys that aren't in the model (e.g. analyst_target)
                allowed_keys = {c.name for c in models.CompanyProfile.__table__.columns} - {'id', 'company_id'}
                clean_profile = {k: v for k, v in profile_data.items() if k in allowed_keys}
                prof_obj = models.CompanyProfile(company_id=comp.id, **clean_profile)
                db.add(prof_obj)

            # 4b. Save FinancialData records
            for f in full_data["financials"]:
                allowed_fin_keys = {c.name for c in models.FinancialData.__table__.columns} - {'id', 'company_id'}
                clean_f = {k: v for k, v in f.items() if k in allowed_fin_keys}
                fin = models.FinancialData(company_id=comp.id, **clean_f)
                db.add(fin)
            db.commit()
        except Exception as e:
            print(f"Error fetching {cd['ticker']}: {e}")
            import traceback; traceback.print_exc()


    # Don't forget NVDA for Robotics!
    nvda_robot = models.Company(
        industry_id=robot_report.id,
        value_chain_node_id=robot_node_objs["제어 시스템 및 소프트웨어 (Control Systems & AI)"].id,
        name="Nvidia",
        ticker="NVDA",
        role_description="Omniverse 및 Jetson 플랫폼 등 물리적 AI 시뮬레이터 제공",
        future_growth="로봇 두뇌 및 개발 훈련 인프라 독점으로 폭발적 마진 기대"
    )
    db.add(nvda_robot)
    db.commit()
    db.refresh(nvda_robot)
    print(f"Fetching full data for NVDA (로봇)...")
    try:
        full_data = fetch_full_company_data("NVDA")
        if full_data["profile"]:
            allowed_keys = {c.name for c in models.CompanyProfile.__table__.columns} - {'id', 'company_id'}
            clean_profile = {k: v for k, v in full_data["profile"].items() if k in allowed_keys}
            db.add(models.CompanyProfile(company_id=nvda_robot.id, **clean_profile))
        for f in full_data["financials"]:
            allowed_fin_keys = {c.name for c in models.FinancialData.__table__.columns} - {'id', 'company_id'}
            clean_f = {k: v for k, v in f.items() if k in allowed_fin_keys}
            db.add(models.FinancialData(company_id=nvda_robot.id, **clean_f))
        db.commit()
    except Exception as e:
        print(f"Error fetching NVDA: {e}")
        import traceback; traceback.print_exc()

    print("Database populated successfully.")
    db.close()

if __name__ == "__main__":
    populate_db()
