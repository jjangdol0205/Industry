"""
운송 산업 (ID=13) 데이터 삽입 스크립트
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), 'investment_portal.db')

SUMMARY = """## 글로벌 운송 & 물류 산업 밸류체인 심층 분석

글로벌 물류·운송 산업은 2024년 기준 약 **8.4조 달러** 규모로, 2030년까지 연평균 **6.5~7%** 성장이 전망됩니다. 해운·항공·육상·3PL·라스트마일까지 광범위한 하위 섹터를 포함하며, 팬데믹 이후 공급망 재편으로 **'비용 효율'에서 '공급망 회복탄력성(Resilience)'** 중심으로 패러다임이 전환되고 있습니다.

## 한국 운송 산업 현황

한국은 수출 주도형 경제 특성상 **해운·항공화물**이 핵심 인프라 역할을 합니다. HMM(컨테이너 해운), 대한항공(항공화물·여객), 현대글로비스(완성차 해상운송 PCC), CJ대한통운(종합물류)이 4대 핵심 기업입니다. 2024~2025년에는 홍해 갈등으로 인한 운임 급등, 대한항공-아시아나 합병(2026년 예정) 등 구조적 변화가 가속화되었습니다.

## 주요 성장 동력

- **E-커머스 폭발적 성장**: 글로벌 온라인 쇼핑 성장으로 택배·특송·라스트마일 수요가 연 12~15% 증가
- **공급망 재편(Reshoring/Friendshoring)**: 미중 갈등·지정학 리스크로 물류 다변화 수요 급증
- **친환경 규제 강화**: IMO 탄소중립·EU ETS 적용으로 신조선 수요 증가
- **항공화물 강세**: 반도체·바이오·전기차 배터리 고부가 화물 수요 증가
- **AI·디지털 물류**: TMS·WMS 자동화·드론 배송 파일럿 확산

## 핵심 리스크

| 리스크 | 내용 |
|--------|------|
| 운임 변동성 | SCFI/BDI 급락 시 선사 수익 직격 |
| 지정학 리스크 | 홍해·대만해협 분쟁 항로 차질 |
| 공급 과잉 | 2023~2025년 대규모 신조선 발주 |
| 아마존 내재화 | 자체 물류망 확장으로 FedEx·UPS 위협 |

## 투자 포인트

1. **운임 사이클 저점 매수 전략**: HMM·Maersk 등 해운주는 사이클 저점에서 매수 후 피크에 매도
2. **다각화 종합물류 선호**: 해운+포워딩+3PL 통합형 기업(현대글로비스, CJ대한통운)
3. **구조적 성장 수혜**: 항공화물(대한항공), E-커머스 물류(CJ대한통운)
4. **대한항공-아시아나 합병** 완료(2026년) → 국내 항공 독과점 체계로 수익성 개선 기대
"""

VALUE_CHAINS = [
    {
        'node_name': '업스트림: 항만·인프라',
        'description': '항만 터미널 운영, 물류 거점 인프라, 컨테이너 야드·창고 운영. 운송 전체 공급망의 출발점이자 핵심 허브.',
    },
    {
        'node_name': '미드스트림: 해상·항공 운송',
        'description': '컨테이너·벌크·탱커 해운 및 항공화물 운송. 글로벌 교역의 80% 이상을 처리하며 운임 사이클에 따라 수익성이 크게 변동.',
    },
    {
        'node_name': '미드스트림: 육상·복합 운송',
        'description': '도로·철도 화물, 인터모달(철도+트럭) 복합운송. 항만에서 내륙 물류센터까지 연결하는 중간 운송 링크.',
    },
    {
        'node_name': '다운스트림: 3PL·라스트마일',
        'description': '종합물류(3PL), 택배·특송, 라스트마일 배송. E-커머스 성장에 따라 가장 빠르게 확장 중인 섹터.',
    },
]

COMPANIES = [
    # ── 한국 기업 ──────────────────────────────────────────
    {
        'name': 'HMM',
        'ticker': '011200.KS',
        'role_description': '국내 최대 컨테이너 선사. THE Alliance 가입, 아시아-유럽·아시아-미주 주요 항로 운영. 2024년 운임 급등 사이클 수혜.',
        'future_growth': '신조선 추가 발주로 선대 확장, 친환경(LNG) 선박 전환, 홍해 항로 우회 수요 지속. 민영화 이후 경영 효율화 기대.',
        'value_chain_node': '미드스트림: 해상·항공 운송',
        'display_order': 1,
    },
    {
        'name': '대한항공',
        'ticker': '003490.KS',
        'role_description': '국내 FSC(대형항공사) 1위. 여객·화물 복합 운영으로 반도체·바이오·전기차 배터리 항공화물 수요 강세 수혜.',
        'future_growth': '아시아나 합병(2026년 완료 목표) 후 국내 항공 독과점 체계 → 여객·화물 수익성 대폭 개선. 글로벌 항공화물 수요 구조적 성장.',
        'value_chain_node': '미드스트림: 해상·항공 운송',
        'display_order': 2,
    },
    {
        'name': '현대글로비스',
        'ticker': '086280.KS',
        'role_description': '현대기아차 완성차 전용선(PCC) 운영, 세계 PCC 시장 점유율 1위권. 자동차 해상운송·종합물류 통합 사업자.',
        'future_growth': '전기차 수출 급증에 따른 PCC 운송 수요 확대, 현대기아차 글로벌 판매 증가와 직결. 종합물류 솔루션 확장으로 수익 다변화.',
        'value_chain_node': '미드스트림: 해상·항공 운송',
        'display_order': 3,
    },
    {
        'name': 'CJ대한통운',
        'ticker': '000120.KS',
        'role_description': '국내 택배시장 점유율 1위(약 40%). 국내 택배·해외 포워딩·3PL 종합물류 통합 사업자.',
        'future_growth': 'E-커머스 성장으로 택배 물동량 연 5~8% 증가 지속. 해외 물류(동남아·미국 거점) 확장 전략, AI 자동화 물류센터 투자.',
        'value_chain_node': '다운스트림: 3PL·라스트마일',
        'display_order': 4,
    },
    # ── 미국 기업 ──────────────────────────────────────────
    {
        'name': 'FedEx',
        'ticker': 'FDX',
        'role_description': '글로벌 항공특송(Express) 및 육상택배(Ground) 1위. 220개국에 익일·2일 배송 네트워크 보유.',
        'future_growth': '2024~2026 DRIVE 비용 절감 프로그램으로 연 22억달러 비용 절감 목표. 의료물류·E-커머스 B2B 특송 수요 확대.',
        'value_chain_node': '다운스트림: 3PL·라스트마일',
        'display_order': 5,
    },
    {
        'name': 'UPS',
        'ticker': 'UPS',
        'role_description': '글로벌 택배·특송 2위. B2B 의료물류·헬스케어 전문화 전략 추진 중. 220개국 네트워크 보유.',
        'future_growth': '의료·바이오 냉장물류 특화 전략으로 고마진 사업 확대. 미국 내 SMB(중소기업) 고객 확보 전략. 배당 수익률 5%+ 유지.',
        'value_chain_node': '다운스트림: 3PL·라스트마일',
        'display_order': 6,
    },
    {
        'name': 'J.B. Hunt Transport',
        'ticker': 'JBHT',
        'role_description': '미국 최대 인터모달(철도+트럭) 운송사. 장거리 복합운송·트럭운송·최종 배송 통합 솔루션 제공.',
        'future_growth': '철도-트럭 인터모달 수요 증가(탄소 감축 규제 수혜), 360box 디지털 마켓플레이스 성장, 자동화 최종 배송 확대.',
        'value_chain_node': '미드스트림: 육상·복합 운송',
        'display_order': 7,
    },
    {
        'name': 'Old Dominion Freight Line',
        'ticker': 'ODFL',
        'role_description': '미국 LTL(소화물 트럭운송) 시장 점유율 1위. 고품질 서비스·낮은 화물 손상률로 프리미엄 가격 유지.',
        'future_growth': '미국 LTL 시장 구조적 과점화로 가격 결정력 유지. 수익성 업계 최상위. Yellow Freight 파산(2023년) 이후 시장 점유율 추가 흡수.',
        'value_chain_node': '미드스트림: 육상·복합 운송',
        'display_order': 8,
    },
    {
        'name': 'XPO Logistics',
        'ticker': 'XPO',
        'role_description': '북미+유럽 LTL 화물운송 전문. 기술 투자 선도형 트럭운송사. 2023년 RXO·GXO 분사 후 LTL 핵심 집중.',
        'future_growth': '유럽 LTL 시장 확대, LTL 수익성 개선(OR 개선 목표), 기술 기반 생산성 향상 투자로 마진 확대 기대.',
        'value_chain_node': '미드스트림: 육상·복합 운송',
        'display_order': 9,
    },
    {
        'name': 'A.P. Moller-Maersk',
        'ticker': 'AMKBY',
        'role_description': '세계 1~2위 컨테이너 선사. 컨테이너해운에서 포워딩·3PL·라스트마일까지 통합 물류사업자로 전환 추진 중.',
        'future_growth': '종합물류사업(Integrator 전략) 매출 비중 확대 → 운임 사이클 변동 완충. M&A 통해 3PL·항공화물 역량 강화.',
        'value_chain_node': '미드스트림: 해상·항공 운송',
        'display_order': 10,
    },
    {
        'name': '팬오션',
        'ticker': '028670.KS',
        'role_description': '국내 1위 벌크선사. 철광석·석탄·곡물 등 건화물 벌크운송 전문. 하림그룹 계열.',
        'future_growth': '신에너지(암모니아·LNG) 원료 해상운송 수요 증가, 인도·동남아 인프라 투자 확대로 철광석·석탄 물동량 지속. 배당주로서 매력 유지.',
        'value_chain_node': '미드스트림: 해상·항공 운송',
        'display_order': 11,
    },
]

def insert_transport():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. 산업 리포트 삽입 (이미 있으면 스킵)
    cur.execute("SELECT id FROM industry_reports WHERE id=13")
    if cur.fetchone():
        print("[운송] industry_reports id=13 already exists, skipping.")
        conn.close()
        return

    cur.execute("""
        INSERT INTO industry_reports (id, title, summary, file_path, tag)
        VALUES (13, ?, ?, ?, ?)
    """, (
        '운송 & 물류 산업 밸류체인 심층 분석: 해운·항공·육상·3PL',
        SUMMARY,
        r'D:\Industry\산업자료\13. 운송\운송.pdf',
        '운송',
    ))
    print("[운송] industry_reports id=13 inserted.")

    # 2. 밸류체인 노드 삽입
    node_name_to_id = {}
    for vc in VALUE_CHAINS:
        cur.execute("""
            INSERT INTO value_chain_nodes (industry_id, node_name, description)
            VALUES (13, ?, ?)
        """, (vc['node_name'], vc['description']))
        node_name_to_id[vc['node_name']] = cur.lastrowid
    print(f"[운송] {len(VALUE_CHAINS)} value_chain_nodes inserted.")

    # 3. 기업 삽입
    for comp in COMPANIES:
        vc_node_id = node_name_to_id.get(comp['value_chain_node'])
        cur.execute("""
            INSERT INTO companies
              (industry_id, name, ticker, role_description, future_growth, value_chain_node_id, display_order)
            VALUES (13, ?, ?, ?, ?, ?, ?)
        """, (
            comp['name'], comp['ticker'],
            comp['role_description'], comp['future_growth'],
            vc_node_id, comp['display_order'],
        ))
    print(f"[운송] {len(COMPANIES)} companies inserted.")

    conn.commit()
    conn.close()
    print("[운송] Done!")

if __name__ == '__main__':
    insert_transport()
