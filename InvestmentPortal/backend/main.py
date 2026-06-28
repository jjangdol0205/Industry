from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import os, json
from dotenv import load_dotenv
load_dotenv()  # .env 파일에서 환경변수 자동 로드

import models, schemas, database, agent_harness
from openai import OpenAI

models.Base.metadata.create_all(bind=database.engine)

# ─────────────────────────────────────────────
# 시작 시 DB 마이그레이션 (Render 영구볼륨 대응)
# ─────────────────────────────────────────────
def run_startup_migrations():
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "investment_portal.db")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 코인 Vol.1 → 통합 리포트로 업데이트
        cur.execute("SELECT title FROM industry_reports WHERE id=4")
        row = cur.fetchone()
        if row and ("Vol.1" in row[0] or "vol.1" in row[0].lower()):
            cur.execute("""
                UPDATE industry_reports SET
                    title     = '코인 & 블록체인 산업 심층 분석',
                    summary   = '비트코인·이더리움을 중심으로 한 암호화폐 생태계의 전방위 밸류체인 완전 분석. 채굴(Mining) 인프라부터 거래소, 결제 플랫폼, 기관 금융, 기업 재무전략까지 디지털 자산 산업의 5개 레이어를 심층 분석합니다. BTC 현물 ETF 승인 이후 기관 자금 유입, 반감기(Halving) 사이클, 미국 친암호화폐 정책 전환이 만드는 구조적 기회를 총 45페이지에 걸쳐 분석합니다.',
                    file_path = '4. 코인/코인 블록체인 산업 심층 분석.pdf',
                    tag       = '코인'
                WHERE id = 4
            """)
            print("[Migration] id=4 title updated to merged coin report")

        # Vol.2(id=5) 중복 코인 리포트 삭제 (태그가 '코인'인 경우만)
        cur.execute("SELECT id FROM industry_reports WHERE id=5 AND tag='코인'")
        if cur.fetchone():
            cur.execute("DELETE FROM industry_reports WHERE id=5")
            print("[Migration] id=5 coin Vol.2 report deleted")

        # ── 에너지 산업 리포트 초기화 (id=5, tag='에너지') ──────────
        cur.execute("SELECT id FROM industry_reports WHERE id=5")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO industry_reports (id, title, summary, file_path, tag)
                VALUES (5, 'AI 에너지 인프라 밸류체인 심층분석',
                '## 1. 산업 개요: AI 전력 위기와 에너지 인프라의 부상\n\n생성형 AI 폭증이 초래한 데이터센터 전력 수요 급증은 전통적인 전력망이 감당할 수 있는 한계를 초과했습니다. 엔비디아 H100 GPU 클러스터 한 랙만으로도 40~100kW의 전력을 소비하며, 2030년까지 미국 데이터센터 전력 수요는 현재의 3배에 달하는 35GW 이상으로 폭증할 전망입니다. 재생에너지의 간헐성과 전력망 확충의 지연이라는 이중 장벽 앞에서, **SMR(소형모듈원전)**과 **가스터빈 분산 발전**이 구조적 해법으로 부상하고 있습니다.\n\n## 2. 핵심 투자 테마: 3개 레이어 밸류체인\n\n**① 가스터빈 발전 (단기: 1~3년)**\n- AI 데이터센터 전력 공급의 브릿지(Bridge) 솔루션\n- 태양광/풍력 간헐성 보완 + 1~2년 내 신속 구축 가능\n- GE Vernova, Siemens Energy, Mitsubishi Heavy Industries 수혜\n\n**② SMR 설계 팹리스 (중기: 3~7년)**\n- 미국 NRC 표준설계인가(SDA) = 규제 해자 독점\n- 24/7 무탄소(CFE) 기저 전원 공급 → 빅테크 직접 PPA 체결\n- NuScale Power, Oklo Inc. 인허가 선점 경쟁\n\n**③ 원자력 파운드리 & 핵연료 (장기: 7년+)**\n- SMR 상용화 시 수혜받는 실물 제조 독점 레이어\n- 수주 즉시 현금 수취(Cost-Plus 계약 구조)\n- BWX Technologies, Doosan Enerbility, Centrus Energy 독점적 위치\n\n## 3. 구조적 전환점: 빅테크 PPA가 만드는 새로운 질서\n\n마이크로소프트-쓰리마일섬 재가동 20년 PPA(2023), 구글-카이로스 파워 500MW PPA(2023), 아마존-탈렌에너지 원전 직결 데이터센터(2023) 체결은 단순한 계약이 아닌 **에너지 인프라 산업의 구조적 패러다임 전환**입니다.\n\n- **전력 구매자가 발전소를 직접 기획·발주**하는 수직통합 모델로 진화\n- Take-or-Pay PPA → 설계사/파운드리에 선수금 지급 구조 고착\n- 탄소국경세(CBAM) + 미국 IRA 인센티브가 원자력 경제성 방어\n\n## 4. 핵심 리스크\n\n* **규제 지연 리스크:** NRC 인허가 평균 소요기간 5~10년\n* **비용 초과 리스크:** SMR의 실제 $/kWh 경쟁력 검증 미완료\n* **핵연료 공급망:** HALEU 농축 시설 용량 부족\n* **빅테크 전략 선회:** 재생에너지 기술 돌파 시 원전 PPA 수요 감소\n\n## 5. 투자 전략: 밸류체인 레이어별 포지셔닝\n\n단기 수혜: GEV, SMEGF | 중기 옵션: SMR, OKLO | 장기 독점: LEU, BWXT, 034020.KS',
                '5. 에너지/에너지 산업.pdf', '에너지')
            """)
            print("[Migration] id=5 energy report inserted")
        else:
            # 에너지 리포트 제목이 구버전이면 업데이트
            cur.execute("SELECT title FROM industry_reports WHERE id=5")
            title_row = cur.fetchone()
            if title_row and 'AI 에너지 인프라' not in title_row[0]:
                cur.execute("""
                    UPDATE industry_reports SET
                        title = 'AI 에너지 인프라 밸류체인 심층분석',
                        tag = '에너지'
                    WHERE id = 5
                """)
                print("[Migration] id=5 energy report title updated")

        # ── 에너지 value_chain_nodes 초기화 ────────────────────
        energy_nodes = [
            (20, 5, '가스터빈 발전 (Gas Turbines)', 'AI 데이터센터 전력 공급의 브릿지 솔루션. 1~2년 내 신속 구축 가능한 분산 전원망.'),
            (21, 5, 'SMR 설계 팹리스 (SMR Fabless)', '24/7 무탄소 CFE 전력을 공급하는 소형모듈원전 설계 전문 기업들.'),
            (22, 5, '원자력 파운드리 및 제조 (Foundry & Manufacturing)', 'SMR 핵심 기자재 실물 제조 독점 레이어.'),
            (23, 5, '차세대 핵연료 가공 (Advanced Nuclear Fuel)', 'HALEU 농축 및 TRISO 안전 연료 제조 독점 공급망.'),
            (24, 5, '원전 운영 및 CFE 서비스 (Nuclear Operations)', '빅테크와 20년 이상 장기 PPA로 무탄소 전력 공급하는 운영 레이어.'),
        ]
        for node in energy_nodes:
            cur.execute("SELECT id FROM value_chain_nodes WHERE id=?", (node[0],))
            if not cur.fetchone():
                cur.execute("INSERT INTO value_chain_nodes (id, industry_id, node_name, description) VALUES (?,?,?,?)", node)
                print(f"[Migration] value_chain_node id={node[0]} inserted")

        # ── 에너지 기업 초기화 (없으면 삽입) ─────────────────────
        energy_companies = [
            ('GE Vernova', 'GEV', 5, 20, 'GE Vernova — 글로벌 대용량 복합화력발전 1위. AI 데이터센터 단기 전력 공급원.', '가스터빈 수요 급증 수혜.', 4),
            ('Siemens Energy', 'SMEGF', 5, 20, 'Siemens Energy — 신재생에너지 간헐성 제어를 위한 유연 가스터빈 세계적 우위.', '유럽 그린딜 및 청정에너지 인프라 수혜.', 6),
            ('Mitsubishi Heavy Industries', 'MHVYF', 5, 20, 'MHI — 1650도 이상 초고효율 가스터빈 + 수소 100% 전소 터빈 상용화.', '수소 발전 프로젝트 수주 확대.', 5),
            ('NuScale Power', 'SMR', 5, 21, 'NuScale — 세계 유일 NRC 표준설계인가(SDA) 획득 SMR 팹리스 선도 기업.', '빅테크 PPA 독식 잠재력.', 8),
            ('Oklo Inc.', 'OKLO', 5, 21, 'Oklo — 샘 올트먼 이사회 의장. 데이터센터 직결 BTM 마이크로 원자로 전문.', '빅테크 직접 PPA 수혜.', 9),
            ('Constellation Energy', 'CEG', 5, 24, 'Constellation Energy — 미국 최대 원자력 운영사. MS와 20년 PPA 쓰리마일섬 재가동.', '무탄소 기저 전원 프리미엄 재평가.', 1),
            ('Centrus Energy', 'LEU', 5, 23, 'Centrus Energy — 미국 내 유일 HALEU 상업 농축 독점 공급사.', 'SMR 상용화 HALEU 수요 기하급수 성장.', 3),
            ('BWX Technologies', 'BWXT', 5, 22, 'BWX Technologies — 미국 해군 원자로 + TRISO 핵연료 가공 독점 파운드리.', 'SMR 수주 즉시 현금 수취 구조.', 2),
            ('Doosan Enerbility', '034020.KS', 5, 22, 'Doosan Enerbility — 글로벌 SMR 핵심 기자재 전담 원자력 파운드리. 17000톤 프레스 보유.', 'SMR 수주잔고 급증으로 매출 성장 보장.', 7),
        ]
        for co in energy_companies:
            cur.execute("SELECT id FROM companies WHERE ticker=? AND industry_id=5", (co[1],))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO companies (name, ticker, industry_id, value_chain_node_id, role_description, future_growth, display_order)
                    VALUES (?,?,?,?,?,?,?)
                """, co)
                print(f"[Migration] company {co[0]} ({co[1]}) inserted")
            else:
                # 기존 기업 display_order 업데이트
                cur.execute("UPDATE companies SET display_order=? WHERE ticker=? AND industry_id=5", (co[6], co[1]))

        # ── 전력 인프라 산업 리포트 초기화 (id=6, tag='전력인프라') ────
        cur.execute("SELECT id FROM industry_reports WHERE id=6")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO industry_reports (id, title, summary, file_path, tag)
                VALUES (6, '전력 인프라 밸류체인 심층분석',
                '## 1. 산업 개요: AI·전기화 시대의 전력 인프라 르네상스\n\nAI 데이터센터 급증, 전기차(EV) 보급 가속, 노후화된 전력망 교체 수요가 동시에 폭발하며 미국과 글로벌 전력 인프라 투자가 역사적 전환점을 맞고 있습니다. 미국 에너지부는 2035년까지 전력망 현대화에 5조 달러 이상의 투자가 필요하다고 추산하며, 바이든-트럼프 초당적 인프라 정책이 수요를 뒷받침합니다. 송·배전 인프라 노후화율 70% 이상, 전력망 연계 대기 프로젝트 1,700GW 이상이 적체된 상황에서 전력 인프라 밸류체인 전반이 수혜를 받고 있습니다.\n\n## 2. 핵심 투자 테마: 4개 레이어 밸류체인\n\n**① 전력 기기 및 설비 (즉각적 수혜)**\n- 변압기, 스위치기어, 배전반, 전력 관리 시스템 등 핵심 하드웨어\n- 공급 병목 심화로 리드타임 2~3년, 가격 프리미엄 지속\n- Eaton, Hubbell, Powell Industries 수혜\n\n**② 전력망 건설 및 엔지니어링 (중장기 성장)**\n- 송배전 선로, 변전소 EPC, 재생에너지 연계 공사\n- 미국 IRA + 인프라법 지원금 수혜 수주잔고 급증\n- Quanta Services, MYR Group, AECOM 수혜\n\n**③ 전기자재 유통 및 솔루션 (안정 성장)**\n- 전력 케이블, 전선관, 전기 보호장비 설계·유통\n- 데이터센터 건설 붐 + 그리드 현대화 동시 수혜\n- Wesco International, Atkore 수혜\n\n**④ 데이터센터 전력 인프라 (고성장)**\n- UPS, 열 관리, 전력 분배 장치(PDU) 등 미션크리티컬 시스템\n- AI 빅테크 하이퍼스케일 투자 직접 연동\n- Vertiv Holdings 수혜\n\n## 3. 구조적 전환점: 세 가지 동시 성장 드라이버\n\n① **AI 데이터센터 전력 수요**: 2030년까지 미국 전체 전력 수요의 8% 이상이 데이터센터에서 발생 예상\n② **전기화(Electrification)**: EV 충전 인프라 + 열펌프 + 산업용 전기화로 피크 전력 수요 2040년까지 30% 증가\n③ **노후망 교체**: 1950~70년대 설치된 변압기·변전소의 대규모 교체 사이클 본격화\n\n## 4. 핵심 리스크\n\n* **금리 민감성**: 인프라 프로젝트 파이낸싱 비용 상승 시 수주 지연\n* **원자재 변동성**: 구리·알루미늄 가격 급등이 마진 압박\n* **정책 불확실성**: IRA 세제혜택 축소 또는 인프라 예산 삭감 리스크\n* **공급망 병목 완화**: 변압기 리드타임 정상화 시 가격 프리미엄 축소\n\n## 5. 투자 전략: 레이어별 포지셔닝\n\n즉시 수혜: ETN, HUBB, POWL | 중기 성장: PWR, MYRG, WCC | 고성장 테마: VRT, ATKR',
                '6. 전력 인프라/전력 인프라 산업.pdf', '전력인프라')
            """)
            print("[Migration] id=6 power infrastructure report inserted")
        else:
            cur.execute("SELECT tag, file_path FROM industry_reports WHERE id=6")
            row = cur.fetchone()
            if row:
                if row[0] != '전력인프라':
                    cur.execute("UPDATE industry_reports SET tag='전력인프라' WHERE id=6")
                    print("[Migration] id=6 tag updated to 전력인프라")
                if 'pptx' in row[1]:
                    cur.execute("UPDATE industry_reports SET file_path='6. 전력 인프라/전력 인프라 산업.pdf' WHERE id=6")
                    print("[Migration] id=6 file_path updated to pdf")

        # ── 전력 인프라 value_chain_nodes 초기화 ──────────────────
        power_nodes = [
            (25, 6, '전력 기기 및 설비 (Power Equipment)', '변압기·스위치기어·배전반·UPS 등 전력망의 핵심 하드웨어를 설계·제조하는 레이어. 공급 병목으로 리드타임 2~3년, 가격 프리미엄 지속.'),
            (26, 6, '전력망 건설 및 EPC (Grid Construction & EPC)', '송배전 선로, 변전소, 재생에너지 연계 공사를 수행하는 엔지니어링·조달·시공(EPC) 기업들. 미국 IRA·인프라법 수주잔고 급증 수혜.'),
            (27, 6, '전기자재 유통 및 솔루션 (Electrical Distribution)', '전력 케이블·전선관·전기 보호장비를 설계·제조·유통하는 레이어. 데이터센터 붐과 그리드 현대화 이중 수혜.'),
            (28, 6, '그리드 연결 및 부품 (Grid Connectivity & Components)', '송전선 연결 클램프, 그리드 커넥터, 전기 인클로저 등 그리드 연결 핵심 부품 제조. 재생에너지 연계 프로젝트 급증 수혜.'),
            (29, 6, '데이터센터 전력 인프라 (Data Center Power)', 'AI 하이퍼스케일 데이터센터용 UPS·열 관리·전력 분배 장치(PDU) 등 미션크리티컬 전력 시스템. 빅테크 CapEx 직접 연동 고성장 레이어.'),
        ]
        for node in power_nodes:
            cur.execute("SELECT id FROM value_chain_nodes WHERE id=?", (node[0],))
            if not cur.fetchone():
                cur.execute("INSERT INTO value_chain_nodes (id, industry_id, node_name, description) VALUES (?,?,?,?)", node)
                print(f"[Migration] value_chain_node id={node[0]} inserted")

        # ── 전력 인프라 기업 초기화 (없으면 삽입) ──────────────────
        power_companies = [
            # (name, ticker, industry_id, vc_node_id, role_description, future_growth, display_order)
            ('Eaton Corporation', 'ETN', 6, 25, 'Eaton — 글로벌 전력 관리 1위. 전기 스위치기어·배전반·UPS·서킷 브레이커 포트폴리오 보유. AI 데이터센터·산업 전기화 전방위 수혜 기업.', '데이터센터 전력 설비 수요 급증으로 수주잔고 사상 최대. EV 충전 인프라·재생에너지 연계 사업 고성장.', 1),
            ('Vertiv Holdings', 'VRT', 6, 29, 'Vertiv — AI 하이퍼스케일 데이터센터 전용 UPS·열 관리·전력 분배 장치(PDU) 글로벌 1위. 미션크리티컬 전력 인프라의 핵심 독점 공급사.', 'AI 빅테크 CapEx 직접 연동. 2030년까지 데이터센터 전력 수요 3배 성장 수혜. 고마진 소프트웨어 서비스 매출 확대.', 2),
            ('Quanta Services', 'PWR', 6, 26, 'Quanta Services — 북미 최대 전력망·재생에너지·광통신 EPC 기업. 고압 송전선로 건설 북미 시장점유율 1위, 수주잔고 300억 달러 이상.', '미국 인프라법·IRA 지원 전력망 현대화 공사 대규모 수주. 재생에너지 연계 공사 및 해상풍력 송전 인프라 고성장.', 3),
            ('Hubbell Incorporated', 'HUBB', 6, 25, 'Hubbell — 전기 인프라용 배선장치·제어 설비·변전소 구조물 전문 제조사. 미국 전력 유틸리티·산업 시장 100년 이상 독점적 브랜드 파워 보유.', '전력망 현대화 교체 사이클 직접 수혜. 전기차 충전 인프라·태양광·풍력 연계 설비 수요 확대.', 4),
            ('Wesco International', 'WCC', 6, 27, 'Wesco — 북미 최대 전기자재·산업재·통신 인프라 유통기업. 연 매출 220억 달러 규모의 B2B 전력 인프라 원스톱 솔루션 제공사.', '전력망 현대화·데이터센터 건설·EV 인프라 확충으로 전기자재 수요 구조적 성장. M&A를 통한 통합 솔루션 확장.', 5),
            ('Atkore', 'ATKR', 6, 27, 'Atkore — 전선관(Conduit)·케이블 트레이·전기 보호 시스템 북미 시장점유율 1위. 데이터센터·태양광 발전소·산업 시설 전기 인프라 핵심 자재 공급사.', '태양광·풍력·데이터센터 건설 붐으로 전선관 수요 급증. IRA 보조금 기반 재생에너지 프로젝트 파이프라인 수혜.', 6),
            ('Powell Industries', 'POWL', 6, 25, 'Powell Industries — 전력 분배용 스위치기어·모터 컨트롤 센터·배전반 전문 미국 제조사. 석유화학·LNG·데이터센터 등 고마진 산업용 전력 시스템 특화.', 'LNG 수출 터미널·정유 시설·데이터센터 전력 시스템 수주 급증. 국내 제조 강점으로 리쇼어링 수혜.', 7),
            ('MYR Group', 'MYRG', 6, 26, 'MYR Group — 미국 전력·통신 인프라 전문 전기 건설 기업. 상업용 건축 전기 공사(C&I)와 송배전 공사(T&D) 두 세그먼트로 안정적 이원화.', '전력망 현대화·재생에너지 연계 공사·데이터센터 전기 시공 수주잔고 사상 최대. 숙련 전기 기술자 확보 경쟁 우위.', 8),
            ('nVent Electric', 'NVT', 6, 28, 'nVent Electric — 전기 인클로저·열 관리·접지 및 접합 시스템 글로벌 제조사. 데이터센터·전력 유틸리티·산업 자동화 전방위 전기 보호 솔루션 제공.', '데이터센터 열 관리 솔루션 수요 폭발적 성장. 전기화 추세로 전기 보호·접지 설비 구조적 수요 증가.', 9),
            ('Preformed Line Products', 'PLPC', 6, 28, 'Preformed Line Products — 송전선 클램프·스플라이스·광섬유 연결 부품 전문 미국 글로벌 기업. 전력 유틸리티의 송전선 연결·보호 시스템 핵심 부품 공급사.', '재생에너지 연계 송전선 증설과 노후 전력망 교체로 연결 부품 수요 고성장. 광섬유·통신 인프라 시장 병행 수혜.', 10),
        ]
        for co in power_companies:
            cur.execute("SELECT id FROM companies WHERE ticker=? AND industry_id=6", (co[1],))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO companies (name, ticker, industry_id, value_chain_node_id, role_description, future_growth, display_order)
                    VALUES (?,?,?,?,?,?,?)
                """, co)
                print(f"[Migration] company {co[0]} ({co[1]}) inserted")
            else:
                cur.execute("UPDATE companies SET display_order=? WHERE ticker=? AND industry_id=6", (co[6], co[1]))

        # ── 이차전지 산업(id=7) 초기화 ────────────────────────────
        try:
            import init_battery_industry
            init_battery_industry.init_battery_industry()
        except Exception as e:
            print(f"[Migration] Battery industry init error: {e}")

        # ── display_order 컬럼 보장 ─────────────────────────────
        cur.execute("PRAGMA table_info(companies)")
        col_names = [r[1] for r in cur.fetchall()]
        if 'display_order' not in col_names:
            cur.execute("ALTER TABLE companies ADD COLUMN display_order INTEGER DEFAULT 999")
            print("[Migration] display_order column added")

        # ── COGS(매출원가) 자동 계산: NULL 또는 0이면 revenue - gross_profit ──
        cur.execute("""
            UPDATE financial_data
            SET cost_of_revenue = revenue - gross_profit
            WHERE (cost_of_revenue IS NULL OR cost_of_revenue = 0)
              AND revenue IS NOT NULL AND revenue > 0
              AND gross_profit IS NOT NULL AND gross_profit > 0
              AND (revenue - gross_profit) > 0
        """)
        cogs_fixed = cur.rowcount
        if cogs_fixed > 0:
            print(f"[Migration] COGS auto-calculated: {cogs_fixed} records fixed")

        conn.commit()
        conn.close()
        print("[Migration] Startup DB migration complete.")
    except Exception as e:
        print(f"[Migration] Warning: {e}")


run_startup_migrations()

app = FastAPI(title="Investment Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# PDF 정적 파일 서빙 (산업 자료 PDF)
# ─────────────────────────────────────────────
RELATIVE_PDF_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "산업자료"))
WINDOWS_PDF_ROOT = r"D:\Industry\산업자료"

if os.path.exists(RELATIVE_PDF_ROOT):
    PDF_ROOT = RELATIVE_PDF_ROOT
elif os.path.exists(WINDOWS_PDF_ROOT):
    PDF_ROOT = WINDOWS_PDF_ROOT
else:
    PDF_ROOT = None

if PDF_ROOT:
    app.mount("/pdfs", StaticFiles(directory=PDF_ROOT), name="pdfs")


# DeepSeek 설정 (OpenAI 호환 API)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
) if DEEPSEEK_API_KEY else None


# 로컬 미리 생성된 한국어 AI 분석 로드
PREGENERATED_ANALYSES_PATH = os.path.join(os.path.dirname(__file__), "pregenerated_ai_analyses.json")
pregenerated_analyses = {}
if os.path.exists(PREGENERATED_ANALYSES_PATH):
    try:
        with open(PREGENERATED_ANALYSES_PATH, "r", encoding="utf-8") as f:
            pregenerated_analyses = json.load(f)
        print(f"Loaded {len(pregenerated_analyses)} pregenerated company analyses.")
    except Exception as e:
        print("Failed to load pregenerated analyses:", e)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────
# Keepalive (Render 절전 방지) — GET + HEAD 모두 허용
# ─────────────────────────────────────────────
@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    return {"status": "ok", "message": "pong"}

# ─────────────────────────────────────────────
# Admin: COGS 즉시 수정 (Render DB 직접 적용)
# ─────────────────────────────────────────────
@app.get("/api/admin/fix-cogs")
def admin_fix_cogs():
    """COGS(매출원가) = revenue - gross_profit 즉시 반영"""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "investment_portal.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        UPDATE financial_data
        SET cost_of_revenue = revenue - gross_profit
        WHERE (cost_of_revenue IS NULL OR cost_of_revenue = 0)
          AND revenue IS NOT NULL AND revenue > 0
          AND gross_profit IS NOT NULL AND gross_profit > 0
          AND (revenue - gross_profit) > 0
    """)
    fixed = cur.rowcount
    conn.commit()
    # 검증
    cur.execute("SELECT COUNT(*) FROM financial_data WHERE cost_of_revenue IS NOT NULL AND cost_of_revenue > 0")
    total_ok = cur.fetchone()[0]
    conn.close()
    return {"fixed": fixed, "total_with_cogs": total_ok, "status": "done"}

# ─────────────────────────────────────────────
# Industry Reports
# ─────────────────────────────────────────────
@app.get("/api/reports", response_model=List[schemas.IndustryReport])
def get_reports(db: Session = Depends(get_db)):
    return db.query(models.IndustryReport).all()


@app.get("/api/reports/{report_id}", response_model=schemas.IndustryReport)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.IndustryReport).filter(models.IndustryReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.get("/api/reports/{report_id}/pdf_url")
def get_report_pdf_url(report_id: int, db: Session = Depends(get_db)):
    """산업 PDF URL 반환 — 프론트엔드 iframe 연동용"""
    report = db.query(models.IndustryReport).filter(models.IndustryReport.id == report_id).first()
    if not report or not report.file_path:
        return {"pdf_url": None, "file_name": None}
    fp = report.file_path.replace('\\', '/')
    # 산업자료/ 이후 상대 경로 추출
    marker = '산업자료/'
    idx = fp.find(marker)
    if idx >= 0:
        rel = fp[idx + len(marker):]
        return {"pdf_url": f"/pdfs/{rel}", "file_name": rel.split('/')[-1]}
    return {"pdf_url": None, "file_name": None}


# ─────────────────────────────────────────────
# Companies
# ─────────────────────────────────────────────

@app.get("/api/companies", response_model=List[schemas.Company])
def get_companies(db: Session = Depends(get_db)):
    return db.query(models.Company).order_by(
        models.Company.industry_id,
        models.Company.display_order.asc().nullslast()
    ).all()

@app.get("/api/companies/{company_id}", response_model=schemas.Company)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@app.get("/api/companies/{company_id}/profile")
def get_company_profile(company_id: int, db: Session = Depends(get_db)):
    """
    회사의 기관급 밸류에이션·프로파일 데이터 반환
    P/E, P/B, EV/EBITDA, ROE, ROA, GPM, OPM, 배당수익률 등
    description은 DeepSeek으로 번역 후 DB 캐시
    """
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    profile = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == company_id).first()

    # ── 한국어 번역 (없으면 DeepSeek으로 생성 후 저장) ──────────
    description_ko = None
    if profile and profile.description:
        if profile.description_ko:
            description_ko = profile.description_ko
        elif deepseek_client:
            try:
                trans = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a professional Korean translator. Translate the following company description into natural Korean. Return ONLY the translated text, no explanation."},
                        {"role": "user", "content": profile.description}
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                )
                description_ko = trans.choices[0].message.content.strip()
                # DB에 저장 (캐시)
                profile.description_ko = description_ko
                db.commit()
            except Exception:
                description_ko = None

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "ticker": company.ticker,
            "role_description": company.role_description,
            "future_growth": company.future_growth,
        },
        "profile": {
            # 기본 정보
            "sector": profile.sector if profile else None,
            "industry": profile.industry_classification if profile else None,
            "description": profile.description if profile else None,
            "description_ko": description_ko,
            "ceo": profile.ceo if profile else None,
            "employees": profile.employees if profile else None,
            "website": profile.website if profile else None,
            # 시장 데이터
            "market_cap": profile.market_cap if profile else None,
            "current_price": profile.current_price if profile else None,
            "beta": profile.beta if profile else None,
            # 밸류에이션
            "pe_ratio": profile.pe_ratio if profile else None,
            "pb_ratio": profile.pb_ratio if profile else None,
            "ev_ebitda": profile.ev_ebitda if profile else None,
            "ev_sales": profile.ev_sales if profile else None,
            "dcf_value": profile.dcf_value if profile else None,
            # 수익성
            "roe": profile.roe if profile else None,
            "roa": profile.roa if profile else None,
            "roic": profile.roic if profile else None,
            "gross_margin_ttm": profile.gross_margin_ttm if profile else None,
            "op_margin_ttm": profile.op_margin_ttm if profile else None,
            "net_margin_ttm": profile.net_margin_ttm if profile else None,
            "ebitda_margin_ttm": profile.ebitda_margin_ttm if profile else None,
            # 성장성
            "revenue_growth": profile.revenue_growth if profile else None,
            "eps_growth": profile.eps_growth if profile else None,
            "fcf_growth": profile.fcf_growth if profile else None,
            # 재무건전성
            "current_ratio": profile.current_ratio if profile else None,
            "debt_to_equity": profile.debt_to_equity if profile else None,
            "net_debt_to_ebitda": profile.net_debt_to_ebitda if profile else None,
            # 주주환원
            "dividend_yield": profile.dividend_yield if profile else None,
            "payout_ratio": profile.payout_ratio if profile else None,
            "last_updated": profile.last_updated if profile else None,
        }
    }


@app.get("/api/companies/{company_id}/financials")
def get_company_financials(
    company_id: int,
    period_type: Optional[str] = None,  # "annual" or "quarterly"
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    연간/분기 재무제표 반환 (손익 + 재무상태표 + 현금흐름 통합)
    """
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    query = db.query(models.FinancialData).filter(models.FinancialData.company_id == company_id)
    if period_type:
        query = query.filter(models.FinancialData.period_type == period_type)
    
    financials = query.order_by(models.FinancialData.date.desc()).limit(limit).all()
    financials = list(reversed(financials))  # 차트용 asc 재정렬 (최신 데이터 포함 보장)
    
    result = []
    for f in financials:
        result.append({
            "date": f.date,
            "period_type": f.period_type,
            "fiscal_year": f.fiscal_year,
            # 손익
            "revenue": f.revenue,
            "cost_of_revenue": f.cost_of_revenue if f.cost_of_revenue else (
                (f.revenue - f.gross_profit) if (f.revenue and f.gross_profit and f.revenue > f.gross_profit) else None
            ),  # 매출원가: DB값 우선, 없으면 역산
            "gross_profit": f.gross_profit,
            "operating_income": f.operating_income,
            "ebitda": f.ebitda,
            "net_income": f.net_income,
            "eps": f.eps,
            # 마진율
            "gross_margin": f.gross_margin,
            "op_margin": f.op_margin,
            "net_margin": f.net_margin,
            "ebitda_margin": f.ebitda_margin,
            # 성장률
            "revenue_growth_yoy": f.revenue_growth_yoy,
            "op_income_growth_yoy": f.op_income_growth_yoy,
            "eps_growth_yoy": f.eps_growth_yoy,
            # 재무상태표
            "total_assets": f.total_assets,
            "total_current_assets": f.total_current_assets,
            "cash_and_equivalents": f.cash_and_equivalents,
            "total_debt": f.total_debt,
            "shareholders_equity": f.shareholders_equity,
            "net_debt": f.net_debt,
            # 재무건전성
            "current_ratio": f.current_ratio,
            "debt_to_equity_ratio": f.debt_to_equity_ratio,
            # 현금흐름
            "operating_cash_flow": f.operating_cash_flow,
            "capital_expenditure": f.capital_expenditure,
            "free_cash_flow": f.free_cash_flow,
            # 수익성
            "roe": f.roe,
            "roa": f.roa,
            "fcf_margin": f.fcf_margin,
        })
    
    return {"ticker": company.ticker, "name": company.name, "financials": result}


@app.post("/api/companies/{company_id}/sync")
def sync_company_full(company_id: int, db: Session = Depends(get_db)):
    """
    기관급 데이터 최신화 (프로파일 + 풀 재무제표 재수집)
    """
    from comprehensive_fetcher import fetch_full_company_data
    
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    full_data = fetch_full_company_data(company.ticker)
    
    # Update profile
    db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == company_id).delete()
    if full_data["profile"]:
        allowed_keys = {c.name for c in models.CompanyProfile.__table__.columns} - {'id', 'company_id'}
        clean_profile = {k: v for k, v in full_data["profile"].items() if k in allowed_keys}
        db.add(models.CompanyProfile(company_id=company_id, **clean_profile))
    
    # Update financials
    db.query(models.FinancialData).filter(models.FinancialData.company_id == company_id).delete()
    for f in full_data["financials"]:
        allowed_fin = {c.name for c in models.FinancialData.__table__.columns} - {'id', 'company_id'}
        clean_f = {k: v for k, v in f.items() if k in allowed_fin}
        db.add(models.FinancialData(company_id=company_id, **clean_f))
    
    db.commit()
    return {"message": f"Synced {company.ticker} with institutional-grade data", "source": full_data["source"]}


@app.get("/api/companies/{company_id}/price")
def get_company_price(company_id: int, db: Session = Depends(get_db)):
    """
    실시간 주가 조회 (yfinance) — 빠른 가격 갱신 전용
    DB의 CompanyProfile을 업데이트하고 현재 가격 반환
    """
    import yfinance as yf
    
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        ticker = yf.Ticker(company.ticker)
        info = ticker.info
        
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        market_cap = info.get("marketCap")
        pe_ratio = info.get("trailingPE")
        
        # DB 업데이트
        profile = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == company_id).first()
        if profile and price:
            profile.current_price = price
            if market_cap:
                profile.market_cap = market_cap
            if pe_ratio:
                profile.pe_ratio = pe_ratio
            from datetime import datetime
            profile.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
            db.commit()
        
        return {
            "ticker": company.ticker,
            "name": company.name,
            "current_price": price,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "updated": True,
        }
    except Exception as e:
        return {"ticker": company.ticker, "error": str(e), "updated": False}


@app.get("/api/companies/{company_id}/ai-analysis")
def get_company_ai_analysis(company_id: int, db: Session = Depends(get_db)):
    """Gemini AI 심층 기업 분석: 비즈니스 모델 / 수익 구조 / 비용 구조 / 해자 / 리스크 / 투자 포인트"""
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # 1. 로컬에 미리 생성된 데이터가 있으면 즉시 반환
    cid_str = str(company_id)
    if cid_str in pregenerated_analyses:
        res = dict(pregenerated_analyses[cid_str])
        res["ticker"] = company.ticker
        res["company_name"] = company.name
        res["generated_by"] = "antigravity"
        return res

    profile = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == company_id).first()
    industry = db.query(models.IndustryReport).filter(models.IndustryReport.id == company.industry_id).first()
    vc_node = db.query(models.ValueChainNode).filter(models.ValueChainNode.id == company.value_chain_node_id).first()

    p = profile
    gpm = f"{(p.gross_margin_ttm*100):.1f}%" if p and p.gross_margin_ttm is not None else "N/A"
    opm = f"{(p.op_margin_ttm*100):.1f}%" if p and p.op_margin_ttm is not None else "N/A"
    npm = f"{(p.net_margin_ttm*100):.1f}%" if p and p.net_margin_ttm is not None else "N/A"
    roe = f"{(p.roe*100):.1f}%" if p and p.roe is not None else "N/A"
    rev_growth = f"{(p.revenue_growth*100):.1f}%" if p and p.revenue_growth is not None else "N/A"
    is_krw = company.ticker.endswith('.KS') or company.ticker.endswith('.KQ')
    if p and p.market_cap:
        if is_krw:
            mktcap = f"₩{(p.market_cap/1e8):.0f}억"
        else:
            mktcap = f"${(p.market_cap/1e9):.1f}B"
    else:
        mktcap = "N/A"

    industry_title = industry.title if industry else "해당 산업"
    vc_name = vc_node.node_name if vc_node else "N/A"

    context = (
        f"기업명: {company.name} ({company.ticker})\n"
        f"산업: {industry_title}\n"
        f"밸류체인 포지션: {vc_name}\n"
        f"섹터: {p.sector if p else 'N/A'} / 업종: {p.industry_classification if p else 'N/A'}\n"
        f"임직원: {p.employees if p else 'N/A'}명 | 시가총액: {mktcap}\n\n"
        f"[회사 설명]\n{p.description[:1000] if p and p.description else 'N/A'}\n\n"
        f"[밸류체인 내 역할]\n{company.role_description}\n\n"
        f"[미래 성장 포인트]\n{company.future_growth}\n\n"
        f"[핵심 재무 지표 TTM]\n"
        f"GPM: {gpm} / OPM: {opm} / NPM: {npm} / ROE: {roe} / 매출성장률: {rev_growth}"
    )

    json_template = """{{
  "what_they_sell": "핵심 제품/서비스를 구체적으로 설명. 주력 제품명, 고객층(정부/기업/개인), 시장 포지셔닝, 차별화 포인트를 4-5문장.",
  "revenue_model": "수익원을 구분(하드웨어/SW 라이선스/구독/정부 계약/데이터 판매 등). 각 수익원 비중과 마진, 반복수익 비율, 계약 구조, 고객 락인 구조를 4-5문장.",
  "cost_structure": "COGS, R&D, SG&A, CapEx 각각의 비중과 특성 서술. 고정비 vs 변동비, 핵심 원가 드라이버, 규모 성장 시 마진 개선 가능성을 4-5문장.",
  "how_they_profit": "이익을 남기는 구조 설명. 핵심 마진 드라이버, 영업 레버리지 작동 방식, FCF 전환율, ROIC/ROE 관점 자본효율성을 4-5문장.",
  "competitive_moat": "경제적 해자 유형(특허/IP, 네트워크 효과, 규모의 경제, 전환비용, 브랜드, 규제 라이선스)을 명시. 해자 강도와 경쟁사가 극복 어려운 이유를 구체적 수치/사례로 5문장 이상.",
  "key_segments": [
    {{"name": "사업부 명칭", "description": "매출 비중 추정, 성장률, 마진 특성 한 문장"}}
  ],
  "risk_factors": "3가지 핵심 리스크를 유형(경쟁/규제/기술/매크로/재무) 명시하며 구분. 각 리스크 실현 시 기업가치 영향과 대응 가능성 포함 5-6문장.",
  "investment_thesis": "왜 지금 매력적인가? 산업 트렌드(TAM 성장/정책 수혜/기술 전환)와 시장 지위 연결. 구체적 촉매(신제품/수주/규제/M&A)와 Risk/Reward 밸류에이션 논거 5-6문장.",
  "industry_connection": "INDUSTRY_TITLE_PLACEHOLDER 구조적 성장 트렌드(시장 규모/성장률/정책 동향) 제시 후, 이 기업의 밸류체인 포지션과 산업 성장 수혜 방식, 경쟁사 대비 우위를 5문장."
}}"""

    json_template = json_template.replace("INDUSTRY_TITLE_PLACEHOLDER", industry_title)

    prompt = (
        "You are a senior Wall Street equity analyst specializing in deep-dive business model analysis.\n"
        "Analyze the company below and produce a DETAILED structured report entirely in KOREAN.\n"
        "Each text field must be 4-6 sentences minimum with specifics. No vague generic statements.\n\n"
        + context
        + "\n\nOutput ONLY valid JSON (no markdown, no code block):\n"
        + json_template
    )

    try:
        if not deepseek_client:
            raise ValueError("DEEPSEEK_API_KEY not set")
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a senior Wall Street equity analyst. Always respond in valid JSON format only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        text = response.choices[0].message.content.strip()
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if part.startswith("json"):
                    text = part[4:].strip()
                    break
                elif "{" in part:
                    text = part.strip()
                    break
        result = json.loads(text)
        result["ticker"] = company.ticker
        result["company_name"] = company.name
        result["generated_by"] = "deepseek"
        return result
    except Exception as e:
        return {
            "ticker": company.ticker,
            "company_name": company.name,
            "generated_by": "fallback",
            "what_they_sell": (p.description[:800] + "...") if p and p.description else company.role_description,
            "revenue_model": company.role_description,
            "cost_structure": f"GPM {gpm} / OPM {opm} 기준. R&D 집중 투자 기업으로 영업비용 비중이 높습니다.",
            "how_they_profit": f"순이익률 {npm}, ROE {roe} 수준의 수익성을 유지하고 있습니다.",
            "competitive_moat": company.future_growth,
            "key_segments": [{"name": p.industry_classification if p else "핵심사업", "description": company.role_description}],
            "risk_factors": "시장 경쟁 심화, 매크로 경기 변동, 기술 전환 리스크가 존재합니다.",
            "investment_thesis": company.future_growth,
            "industry_connection": f"{industry_title} 성장의 핵심 수혜주로 포지셔닝되어 있습니다.",
            "error": str(e)
        }


# ─────────────────────────────────────────────
# PDF 파일 목록 스캔 API
# ─────────────────────────────────────────────

@app.get("/api/pdfs")
def list_pdfs():
    """산업자료 폴더를 스캔하여 카테고리별 PDF 목록 반환"""
    result = []
    if not os.path.exists(PDF_ROOT):
        return result
    for category in sorted(os.listdir(PDF_ROOT)):
        cat_path = os.path.join(PDF_ROOT, category)
        if not os.path.isdir(cat_path):
            continue
        files = []
        for fname in sorted(os.listdir(cat_path)):
            if fname.lower().endswith(".pdf"):
                from urllib.parse import quote
                rel = f"{category}/{fname}"
                url = f"/pdfs/{quote(rel)}"
                files.append({
                    "name": fname.replace(".pdf", ""),
                    "filename": fname,
                    "url": url,
                    "category": category,
                })
        if files:
            result.append({"category": category, "files": files})
    return result


# ─────────────────────────────────────────────

@app.get("/api/agents")
def get_agents(db: Session = Depends(get_db)):
    agent_harness.initialize_agents(db)
    return db.query(models.Agent).all()


def run_simulation_bg():
    db = database.SessionLocal()
    try:
        agent_harness.run_agent_simulation(db)
    finally:
        db.close()


@app.post("/api/agents/run")
def run_simulation(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_simulation_bg)
    return {"status": "running", "message": "Multi-agent analysis triggered."}


@app.get("/api/agents/messages")
def get_agent_messages(db: Session = Depends(get_db)):
    return db.query(models.AgentMessage).order_by(models.AgentMessage.id.asc()).all()


@app.get("/api/orchestration/report")
def get_latest_report(db: Session = Depends(get_db)):
    report = db.query(models.OrchestrationReport).order_by(models.OrchestrationReport.id.desc()).first()
    if not report:
        return {"title": "보고서 없음", "content": "* 분석 시뮬레이션을 가동하면 여기에 결과 리포트가 생성됩니다."}
    return report
