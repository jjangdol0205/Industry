import sys, os, warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'InvestmentPortal', 'backend')))

import database, models

def init_battery_industry():
    db = database.SessionLocal()

    # 1. Add IndustryReport
    ind_id = 7
    report = db.query(models.IndustryReport).filter(models.IndustryReport.id == ind_id).first()
    if not report:
        report = models.IndustryReport(
            id=ind_id,
            title='이차전지 산업 완벽 가이드',
            summary='''## 1. 산업 개요: 이차전지 밸류체인과 글로벌 패권 전쟁\n\n이차전지 산업은 단순한 제조업을 넘어 '미래 인류의 에너지 플랫폼'으로 진화하고 있습니다. 과거 에너지 공급원(Commodity)이었던 배터리는 이제 전기차(EV), ESS(에너지저장장치), AI 데이터센터를 구동하는 핵심 자산이 되었습니다. 광물 채굴에서 시작해 핵심 소재 합성, 배터리 셀 제조, 그리고 리사이클링으로 이어지는 강력한 수직계열화 생태계가 구축되고 있으며, IRA와 FEOC 등 지정학적 안보 규제가 진입 장벽(해자)으로 작용하고 있습니다.\n\n## 2. 4단계 밸류체인 생태계\n\n**① 업스트림 (광물 채굴 및 정·제련)**\n- 리튬, 니켈 등 배터리 원가의 40~50%를 차지하는 원자재 확보 레이어\n- 중국의 정제련 독점을 탈피하기 위한 공급망 독립(De-risking)이 핵심\n- 포스코홀딩스, 고려아연 중심의 비중국산 핵심 광물 허브\n\n**② 미드스트림 (4대 핵심 소재)**\n- 양극재(연료통), 음극재(엔진), 전해액(혈액), 분리막(방패) 제조\n- 기술 진입장벽과 특허가 집중된 고부가가치 구간\n- 에코프로비엠, 포스코퓨처엠, LG화학, 엔켐 등 글로벌 탑티어 소재 기업 포진\n\n**③ 다운스트림 (배터리 셀/ESS/소프트웨어)**\n- 대규모 자본력과 수율(불량률 최소화)이 마진을 결정하는 완성품 제조 레이어\n- 46시리즈 폼팩터 혁신, AI 데이터센터용 ESS 수요 폭증 수혜\n- LG에너지솔루션, 삼성SDI, SK온의 글로벌 생산 거점 장악\n\n**④ 리사이클링 (순환 경제)**\n- 폐배터리에서 니켈, 리튬, 코발트를 95% 이상 고순도로 회수하는 Closed Loop\n- IRA 글로벌 규제를 완벽히 통과하는 '100% 비중국산' 광물 조달 창구\n- 성일하이텍, 새빗켐 중심의 도시광산 생태계\n\n## 3. 핵심 생존 전략 및 기술 혁신\n\n① **폼팩터 및 소재 혁신**: 46시리즈 원통형과 탭리스(Tab-less) 공정으로 원가 15~20% 절감. 단결정 양극재와 하이볼티지 미드니켈로 삼원계(NCM)의 약점 극복.\n② **캐즘 돌파구, ESS**: 전기차 일시적 수요 둔화(Chasm)를 AI 데이터센터 전력난을 해결하는 ESS 전력망 장악으로 돌파.\n③ **소프트웨어 전환**: 단순 하드웨어를 넘어 BMTS(배터리 관리 토탈 솔루션)와 BaaS(서비스형 배터리)로 고마진 플랫폼 수익 창출.\n④ **차세대 전고체**: 화재 제로, 에너지 밀도 2배의 '꿈의 배터리' 상용화 경쟁.\n\n## 4. 핵심 리스크\n\n* **전기차 캐즘 장기화**: 완성차 수요 둔화에 따른 배터리 셀 및 소재 출하량 감소\n* **보조금 정책 변동성**: 미국 대선 및 정권 교체에 따른 IRA 세액공제(AMPC) 축소 가능성\n* **중국 LFP의 침투**: 저가형 LFP 배터리의 글로벌 점유율 확대로 인한 삼원계 마진 압박\n* **광물 가격 변동성**: 리튬 등 핵심 광물 가격 하락 시 래깅 효과에 따른 단기 수익성 악화\n\n## 5. 투자 전략: 밸류체인 내 포지셔닝\n\n글로벌 1급 벤더와 수직계열화를 구축한 기업, 미국 현지 AMPC 수혜를 온전히 누리는 기업, 그리고 AI ESS 시장을 선점하는 기업에 집중 투자가 필요합니다.''',
            file_path='7. 이차전지/이차전지 산업.pdf',
            tag='이차전지'
        )
        db.add(report)
        print("[Migration] IndustryReport id=7 (이차전지) inserted.")
    else:
        report.tag = '이차전지'
        report.file_path = '7. 이차전지/이차전지 산업.pdf'
        print("[Migration] IndustryReport id=7 already exists, updated.")
    db.commit()

    # 2. Add ValueChainNodes
    nodes = [
        (30, ind_id, '업스트림 (정·제련)', '리튬, 니켈 등 배터리 원가의 40~50%를 차지하는 원자재 확보 및 가공. 중국 독점을 탈피하는 비중국산 핵심 광물 정제련 허브.'),
        (31, ind_id, '미드스트림 (4대 소재)', '양극재, 음극재, 전해액, 분리막 등 화학적 합성을 통해 배터리 성능을 좌우하는 고부가가치 핵심 소재 제조 레이어.'),
        (32, ind_id, '다운스트림 (배터리 셀 및 ESS)', '대규모 자본력과 수율을 바탕으로 완성된 배터리 팩을 제조하여 EV 및 AI 데이터센터(ESS)에 탑재하는 글로벌 셀 메이커.'),
        (33, ind_id, '리사이클링 (순환 경제)', '수명이 다한 폐배터리에서 니켈, 리튬 등 핵심 광물을 회수하여 IRA 규제를 통과하는 100% 비중국산 자원을 재투입하는 도시광산 레이어.'),
    ]
    for node_data in nodes:
        node = db.query(models.ValueChainNode).filter(models.ValueChainNode.id == node_data[0]).first()
        if not node:
            db.add(models.ValueChainNode(id=node_data[0], industry_id=node_data[1], node_name=node_data[2], description=node_data[3]))
            print(f"[Migration] ValueChainNode id={node_data[0]} inserted.")
    db.commit()

    # 3. Add Companies (Korean Battery Value Chain)
    companies = [
        ('포스코홀딩스', '005490.KS', ind_id, 30, '글로벌 비중국 핵심 광물 제련 허브. 아르헨티나 염호와 호주 광산을 소유하여 리튬/니켈부터 양음극재까지 완벽한 수직계열화 구축.', 'IRA 수혜를 극대화하는 탈중국 원소재 밸류체인 완성 및 풀 밸류체인 통합 마진 창출.', 1),
        ('고려아연', '010130.KS', ind_id, 30, '세계 1위 비철금속 제련 기술을 바탕으로 황산니켈, 동박 등 이차전지 핵심 원소재 밸류체인 진입 및 올인원 제련소 운영.', '독보적 제련 기술력을 기반으로 한 폐배터리 리사이클링 고순도 광물 회수 및 IRA 우회 공급망의 핵심 조력자.', 2),
        ('에코프로비엠', '247540.KQ', ind_id, 31, '글로벌 1위 하이니켈 양극재 제조사. 전구체부터 양극재, 리사이클링까지 에코프로 그룹 내 클로즈드 루프 생태계 핵심 기업.', '하이니켈 양극재 압도적 점유율 유지 및 단결정 양극재, 하이볼티지 미드니켈 등 차세대 제품 믹스 다변화.', 3),
        ('포스코퓨처엠', '003670.KS', ind_id, 31, '국내 유일의 양·음극재 동시 생산 기업. 그룹사 내 광물 자원 내재화를 통해 가장 안정적인 원가 경쟁력 확보.', '북미 현지 JV 공장 본격 가동을 통한 IRA 인센티브 수혜 및 실리콘 음극재/전고체 소재 상용화 주도.', 4),
        ('LG화학', '051910.KS', ind_id, 31, '글로벌 탑티어 종합 전지 소재 회사. 양극재를 넘어 분리막, 탄소나노튜브(CNT) 등 4대 핵심 소재 전반의 포트폴리오 다각화.', 'LG에너지솔루션이라는 안정적 캡티브 마켓 확보 및 북미 대규모 양극재 공장 가동으로 첨단제조생산세액공제(AMPC) 수혜.', 5),
        ('엔켐', '348370.KQ', ind_id, 31, '글로벌 4위권의 전해액 전문 기업. 전해액 특성상 유통기한이 짧아 고객사 배터리 공장 바로 옆에 온사이트(On-site) 생산 인프라 구축 필수.', '북미 전해액 공장 선점 효과 및 IRA/FEOC 규제 반사이익으로 중국 경쟁사 배제에 따른 북미 시장 점유율 폭발적 확대.', 6),
        ('LG에너지솔루션', '373220.KS', ind_id, 32, '전 세계 최대 규모의 글로벌 생산 캐파와 다수의 완성차 합작법인(JV)을 보유한 글로벌 1위 배터리 셀 메이커.', '압도적 AMPC 수령을 통한 현금 창출력, 46시리즈 원통형 배터리 양산 및 AI 데이터센터용 북미 ESS 시장 장악.', 7),
        ('삼성SDI', '006400.KS', ind_id, 32, '수익성 우위의 질적 성장 전략을 추구하는 배터리 셀 메이커. 프리미엄 젠(Gen) 시리즈 및 각형 배터리 기술력 선도.', '미국 내 신규 JV 가동으로 AMPC 수혜 본격화 및 화재 위험 없는 꿈의 배터리 전고체 상용화 로드맵 가장 앞선 기업.', 8),
        ('성일하이텍', '365340.KQ', ind_id, 33, '국내 최초 배터리 리사이클링 전문 기업. 블랙파우더에서 니켈, 코발트, 리튬을 95% 이상 고순도로 추출하는 독보적 습식 제련 기술 보유.', '유럽/북미 현지 리사이클링 파크 확장을 통해 폐배터리 도시광산 자원을 내재화하여 글로벌 셀 메이커에 비중국산 원료 직공급.', 9),
    ]

    for c_data in companies:
        comp = db.query(models.Company).filter(models.Company.ticker == c_data[1]).first()
        if not comp:
            comp = models.Company(
                name=c_data[0],
                ticker=c_data[1],
                industry_id=c_data[2],
                value_chain_node_id=c_data[3],
                role_description=c_data[4],
                future_growth=c_data[5],
                display_order=c_data[6]
            )
            db.add(comp)
            print(f"[Migration] Company {c_data[1]} inserted.")
        else:
            comp.display_order = c_data[6]
    db.commit()

    db.close()
    print("이차전지 산업 DB 초기화 완료.")

if __name__ == "__main__":
    init_battery_industry()
