"""
우주 산업을 기존 DB에 추가하는 스크립트 (기존 데이터 보존)
"""
from database import SessionLocal, engine
import models
from comprehensive_fetcher import fetch_full_company_data

models.Base.metadata.create_all(bind=engine)

def add_space_industry():
    db = SessionLocal()

    # 이미 추가됐는지 확인
    existing = db.query(models.IndustryReport).filter(models.IndustryReport.tag == "우주").first()
    if existing:
        print("우주 산업이 이미 DB에 있습니다. 중복 추가 방지로 종료합니다.")
        db.close()
        return

    # ==========================================
    # 우주 산업 리포트
    # ==========================================
    space_markdown = """
## 1. 뉴 스페이스 시대의 개막: 민간 주도 우주 경제

냉전 시대 국가 주도 방식에서 벗어나, SpaceX·블루오리진 등 민간기업이 우주 산업의 혁신을 이끄는 '뉴 스페이스(New Space)' 시대가 도래했습니다.
- **재사용 로켓의 혁신:** SpaceX의 팰컨9·스타십이 발사 비용을 수십분의 1로 낮추며 상업 우주 경제의 문을 열었습니다.
- **시장 규모:** 글로벌 우주 경제는 2024년 약 6,300억 달러 규모이며, 2040년까지 1.8조 달러 이상으로 성장 전망(Morgan Stanley).

## 2. 위성 인터넷과 저궤도(LEO) 위성 혁명

- **저궤도 위성 군집:** 스타링크(SpaceX), 아마존 카이퍼(AMZN) 등 수천 개 위성으로 이루어진 LEO 군집이 글로벌 인터넷 인프라를 재편합니다.
- **군사·상업 이중 수요:** 통신·지구 관측·항법 위성의 수요가 정부와 민간 양측에서 동시에 폭발하며, 위성 제조 및 발사체 공급망 전반의 수혜가 예상됩니다.

## 3. 우주 방위·정찰 위성의 급성장

- **방산·정보기관 수요:** 지구 관측·정찰 위성의 해상도가 비약적으로 높아지며, 정부·국방 계약이 민간 기업의 안정적 수익원이 됩니다.
- **우주군 창설:** 미국, 중국, 유럽 등 주요국이 우주군을 창설하거나 확충하며 우주 방위 예산이 급증하고 있습니다.

## 4. 달·화성 탐사 및 우주 자원 개발

- **아르테미스 프로그램:** NASA의 유인 달 복귀 프로그램이 다수 민간기업의 달 착륙선·물자 수송 수주를 촉발합니다.
- **소행성·달 자원:** 헬륨-3, 희토류 등 우주 자원 추출 기술 개발이 차세대 성장 동력으로 주목받고 있습니다.
    """

    space_report = models.IndustryReport(
        title="우주 산업 밸류체인 심층 분석",
        summary=space_markdown,
        file_path="D:\\Industry\\산업자료\\3. 우주\\우주 산업.pdf",
        tag="우주"
    )
    db.add(space_report)
    db.commit()
    db.refresh(space_report)
    print(f"우주 산업 리포트 생성 완료 (id={space_report.id})")

    # ==========================================
    # 밸류체인 노드
    # ==========================================
    space_nodes = [
        {"name": "발사체 및 발사 서비스 (Launch Vehicles & Services)",
         "desc": "로켓 설계·제조·발사 운영. 재사용 로켓으로 비용 혁신."},
        {"name": "위성 제조 및 운영 (Satellite Manufacturing & Operations)",
         "desc": "통신·관측·항법 위성 설계·제작 및 군집 운용."},
        {"name": "우주 인프라 및 지상 시스템 (Ground Systems & Infrastructure)",
         "desc": "지상국, 안테나, 네트워크 운영 및 위성 데이터 처리."},
        {"name": "우주 방산 및 정찰 (Space Defense & ISR)",
         "desc": "방위·정보기관용 정찰·감시·정밀유도 위성 시스템."},
        {"name": "우주 탐사 및 자원 개발 (Exploration & Space Resources)",
         "desc": "달·화성 탐사, 우주 정거장, 자원 채굴 프로젝트."},
    ]

    space_node_objs = {}
    for nd in space_nodes:
        node = models.ValueChainNode(
            industry_id=space_report.id,
            node_name=nd["name"],
            description=nd["desc"]
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        space_node_objs[nd["name"]] = node
    print(f"밸류체인 노드 {len(space_node_objs)}개 생성 완료")

    # ==========================================
    # 우주 산업 핵심 기업
    # ==========================================
    companies_data = [
        # 발사체
        {
            "node": "발사체 및 발사 서비스 (Launch Vehicles & Services)",
            "name": "Rocket Lab USA", "ticker": "RKLB",
            "role": "소형 위성 전용 일렉트론 로켓 및 중형 뉴트론 개발 중",
            "growth": "소형 LEO 위성 발사 수요 급증으로 시장 점유율 확대"
        },
        # 위성 제조·운영
        {
            "node": "위성 제조 및 운영 (Satellite Manufacturing & Operations)",
            "name": "Planet Labs", "ticker": "PL",
            "role": "매일 전 지구를 촬영하는 초소형 위성 군집 지구 관측 서비스",
            "growth": "농업·환경·정부 수요 확대 및 AI 분석 플랫폼 고부가가치화"
        },
        {
            "node": "위성 제조 및 운영 (Satellite Manufacturing & Operations)",
            "name": "Viasat", "ticker": "VSAT",
            "role": "정지궤도(GEO) 위성 기반 광대역 인터넷 및 정부 통신",
            "growth": "군용 위성통신 및 항공기 내 인터넷 서비스 확장"
        },
        # 지상 인프라
        {
            "node": "우주 인프라 및 지상 시스템 (Ground Systems & Infrastructure)",
            "name": "Kratos Defense & Security", "ticker": "KTOS",
            "role": "위성 지상국 솔루션, 우주 전자전 및 드론 시스템",
            "growth": "우주군 확장 및 위성 지상 인프라 투자 급증 수혜"
        },
        {
            "node": "우주 인프라 및 지상 시스템 (Ground Systems & Infrastructure)",
            "name": "Maxar Technologies", "ticker": "MAXR",
            "role": "고해상도 위성 영상 및 지리공간 정보 플랫폼",
            "growth": "정부·국방 수요 및 상업용 지구 관측 시장 독점적 지위"
        },
        # 우주 방산
        {
            "node": "우주 방산 및 정찰 (Space Defense & ISR)",
            "name": "L3Harris Technologies", "ticker": "LHX",
            "role": "우주 센서, 정찰 위성 탑재체 및 통신 시스템 제공",
            "growth": "우주군 ISR 위성 프로그램 수주 증가 및 방산 예산 확대"
        },
        {
            "node": "우주 방산 및 정찰 (Space Defense & ISR)",
            "name": "Northrop Grumman", "ticker": "NOC",
            "role": "제임스웹 우주망원경 제작사이자 핵심 우주 방산 시스템 통합자",
            "growth": "아르테미스 달 착륙선 및 차세대 ICBM 사업 수주"
        },
        # 탐사·자원
        {
            "node": "우주 탐사 및 자원 개발 (Exploration & Space Resources)",
            "name": "Virgin Galactic", "ticker": "SPCE",
            "role": "민간 우주여행(서브오비탈) 및 초음속 이동 서비스",
            "growth": "우주관광 수요 개척 및 유인 우주 경험 프리미엄 시장 선점"
        },
        {
            "node": "우주 탐사 및 자원 개발 (Exploration & Space Resources)",
            "name": "Intuitive Machines", "ticker": "LUNR",
            "role": "NASA 아르테미스용 달 착륙선 개발 및 달 물자 수송 서비스(CLPS)",
            "growth": "달 경제 개막에 따른 NASA·ESA 장기 계약 및 달 자원 탐사 참여"
        },
        # 방산(대형)
        {
            "node": "우주 방산 및 정찰 (Space Defense & ISR)",
            "name": "Lockheed Martin", "ticker": "LMT",
            "role": "정찰·통신·기상 위성 및 발사체 시스템 통합(ULA 지분 보유)",
            "growth": "국가 안보 우주(NatSec Space) 장기 계약 및 GPS 위성 현대화"
        },
    ]

    for cd in companies_data:
        comp = models.Company(
            industry_id=space_report.id,
            value_chain_node_id=space_node_objs[cd["node"]].id,
            name=cd["name"],
            ticker=cd["ticker"],
            role_description=cd["role"],
            future_growth=cd["growth"]
        )
        db.add(comp)
        db.commit()
        db.refresh(comp)

        print(f"  [{cd['ticker']}] 재무 데이터 수집 중...")
        try:
            full_data = fetch_full_company_data(cd["ticker"])

            if full_data.get("profile"):
                allowed_keys = {c.name for c in models.CompanyProfile.__table__.columns} - {'id', 'company_id'}
                clean_profile = {k: v for k, v in full_data["profile"].items() if k in allowed_keys}
                db.add(models.CompanyProfile(company_id=comp.id, **clean_profile))

            for f in full_data.get("financials", []):
                allowed_fin_keys = {c.name for c in models.FinancialData.__table__.columns} - {'id', 'company_id'}
                clean_f = {k: v for k, v in f.items() if k in allowed_fin_keys}
                db.add(models.FinancialData(company_id=comp.id, **clean_f))

            db.commit()
            print(f"  [{cd['ticker']}] 완료")
        except Exception as e:
            print(f"  [{cd['ticker']}] 오류: {e}")
            import traceback; traceback.print_exc()

    print("\n✅ 우주 산업 추가 완료!")
    db.close()

if __name__ == "__main__":
    add_space_industry()
