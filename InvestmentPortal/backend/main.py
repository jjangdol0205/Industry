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

        # ── 온디바이스 AI 산업(id=8) 초기화 ──────────────────────
        cur.execute("SELECT id FROM industry_reports WHERE id=8")
        if not cur.fetchone():
            try:
                import insert_ondevice_ai  # 직접 import해서 실행
                print("[Migration] On-device AI industry (id=8) inserted via insert_ondevice_ai")
            except Exception as e:
                print(f"[Migration] On-device AI industry init error: {e}")

        # ── 반도체 산업(id=9) 초기화 ──────────────────────────────
        cur.execute("SELECT id FROM industry_reports WHERE id=9")
        if not cur.fetchone():
            try:
                import insert_semiconductor
                print("[Migration] Semiconductor industry (id=9) inserted via insert_semiconductor")
            except Exception as e:
                print(f"[Migration] Semiconductor industry init error: {e}")

        # ── 게임 산업(id=10) 초기화 ───────────────────────────────
        cur.execute("SELECT id FROM industry_reports WHERE id=10")
        if not cur.fetchone():
            try:
                import insert_game_industry
                print("[Migration] Game industry (id=10) inserted via insert_game_industry")
            except Exception as e:
                print(f"[Migration] Game industry init error: {e}")

        # ── 엔터테인먼트 산업(id=11) 초기화 ──────────────────────
        cur.execute("SELECT id FROM industry_reports WHERE id=11")
        if not cur.fetchone():
            try:
                import insert_entertainment
                print("[Migration] Entertainment industry (id=11) inserted via insert_entertainment")
            except Exception as e:
                print(f"[Migration] Entertainment industry init error: {e}")

        # ── 조선 산업(id=12) 초기화 ───────────────────────────────
        cur.execute("SELECT id FROM industry_reports WHERE id=12")
        if not cur.fetchone():
            try:
                import insert_shipbuilding
                print("[Migration] Shipbuilding industry (id=12) inserted via insert_shipbuilding")
            except Exception as e:
                print(f"[Migration] Shipbuilding industry init error: {e}")

        # ── companies & company_profiles 컬럼 보장 ─────────────
        cur.execute("PRAGMA table_info(companies)")
        comp_cols = [r[1] for r in cur.fetchall()]
        if 'display_order' not in comp_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN display_order INTEGER DEFAULT 999")
            print("[Migration] display_order column added to companies")
        if 'portfolio_tier' not in comp_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN portfolio_tier TEXT DEFAULT 'Standard'")
            print("[Migration] portfolio_tier column added to companies")
        if 'principle_reason' not in comp_cols:
            cur.execute("ALTER TABLE companies ADD COLUMN principle_reason TEXT")
            print("[Migration] principle_reason column added to companies")

        cur.execute("PRAGMA table_info(company_profiles)")
        prof_cols = [r[1] for r in cur.fetchall()]
        if prof_cols:
            if 'current_price' not in prof_cols:
                cur.execute("ALTER TABLE company_profiles ADD COLUMN current_price REAL")
            if 'high_52w' not in prof_cols:
                cur.execute("ALTER TABLE company_profiles ADD COLUMN high_52w REAL")
            if 'mdd_pct' not in prof_cols:
                cur.execute("ALTER TABLE company_profiles ADD COLUMN mdd_pct REAL")
            if 'buy_signal' not in prof_cols:
                cur.execute("ALTER TABLE company_profiles ADD COLUMN buy_signal TEXT DEFAULT 'WAIT'")
            if 'last_updated' not in prof_cols:
                cur.execute("ALTER TABLE company_profiles ADD COLUMN last_updated TEXT")

        # ── 4단계 투자원칙 핵심 티어 데이터 자동 업데이트 ───────
        tier_updates = [
            ("ASML", "Core", "EUV 노광장비 100% 독점, GPM 51%+, 전환비용 극상 (Core 1호)"),
            ("NVIDIA", "Core", "AI GPU 시장 80%+ 독점, OPM 55%+, CUDA 생태계 락인 (Core 2호)"),
            ("TSMC", "Core", "5nm 이하 파운드리 90%+ 독점, OPM 42%+, CoWoS 병목 소유 (Core 3호)"),
            ("삼성바이오로직스", "Core", "세계 1위 배양용량 CDMO 독점력, CAPEX 무거운 자본 장벽 (국내 Core 대체)"),
            ("코스맥스", "Core", "글로벌 1위 화장품 ODM, Fast Beauty 밸류체인 핵심 병목 (국내 Core 대체)"),
            ("Rocket Lab USA", "Satellite", "소형 발사체 독보적 2위, 수주잔고 역대 최고치, 위성 SW/시스템 체질개선 (Satellite 1호)"),
            ("Vertiv Holdings", "Satellite", "AI 데이터센터 액체냉각/UPS 1위, 수주잔고 YoY +35%, 고마진 체질개선 (Satellite 2호)"),
            ("삼양식품", "Satellite", "불닭볶음면 글로벌 IP 독점, 수출 비중 70%+, 수주/수출 역대 최고치 (국내 Satellite 대체)"),
            ("HD현대일렉트릭", "Satellite", "글로벌 전력기기 리드타임 2년+ 병목, 수주잔고 최고치 경신 (국내 Satellite 대체)"),
            ("Intuitive Surgical", "Watchlist", "다빈치 수술로봇 독점, OPM 30%+, 소모품 락인 (대체 관심 1호)"),
            ("HD한국조선해양", "Watchlist", "LNG/친환경선 글로벌 1위, 3년치 고가 수주잔고 (대체 관심 2호)"),
            ("브이티", "Watchlist", "마이크로니들(리들샷) 독점 IP, 글로벌 바이럴 고마진 (대체 관심 3호)"),
            ("Palantir Technologies", "Watchlist", "기업/정부 AI 운영체제(AIP) 시장 선도, ARR 구독 성장 (대체 관심 4호)"),
            ("실리콘투", "Watchlist", "K-뷰티 글로벌 풀필먼트 플랫폼 1위, 150개국 직매입 유통 (대체 관심 5호)"),
        ]
        for cname, tier, reason in tier_updates:
            cur.execute("""
                UPDATE companies
                SET portfolio_tier=?, principle_reason=?
                WHERE name LIKE ? OR ticker LIKE ?
            """, (tier, reason, f"%{cname}%", f"%{cname}%"))

        # ── COGS(매출원가) 자동 계산 ──
        cur.execute("""
            UPDATE financial_data
            SET cost_of_revenue = revenue - gross_profit
            WHERE (cost_of_revenue IS NULL OR cost_of_revenue = 0)
              AND revenue IS NOT NULL AND revenue > 0
              AND gross_profit IS NOT NULL AND gross_profit > 0
              AND (revenue - gross_profit) > 0
        """)

        # ── 미비된 52주 최고가 / MDD 데이터 자동 갱신 ──
        cur.execute("SELECT count(*) FROM company_profiles WHERE high_52w IS NULL OR mdd_pct IS NULL")
        missing_count = cur.fetchone()[0]
        if missing_count > 0:
            print(f"[Migration] Found {missing_count} profiles missing 52w high & MDD. Updating...")
            import yfinance as yf
            cur.execute("""
                SELECT c.id, c.ticker, c.portfolio_tier
                FROM companies c
                JOIN company_profiles cp ON c.id = cp.company_id
                WHERE (cp.high_52w IS NULL OR cp.mdd_pct IS NULL) AND c.ticker IS NOT NULL
            """)
            missing_comps = cur.fetchall()
            tickers = list(set([c[1].strip() for c in missing_comps if c[1]]))
            if tickers:
                data = yf.download(tickers, period="1y", progress=False)
                for cid, ticker, tier in missing_comps:
                    clean_t = ticker.strip()
                    try:
                        if clean_t in data['Close'].columns:
                            close_ser = data['Close'][clean_t].dropna()
                            high_ser = data['High'][clean_t].dropna()
                            if not close_ser.empty and not high_ser.empty:
                                curr = float(close_ser.iloc[-1])
                                high52 = float(high_ser.max())
                                mdd = float(((curr - high52) / high52) * 100.0)

                                signal = "WAIT (MDD 미달 - 고점 부근)"
                                if tier in ['Core', 'Satellite']:
                                    if mdd <= -40.0: signal = "DEEP_DISCOUNT (3차 분할매수 -40% 진입)"
                                    elif mdd <= -30.0: signal = "BUY_READY (2차 분할매수 -30% 진입)"
                                    elif mdd <= -20.0: signal = "BUY_READY (1차 분할매수 -20% 진입)"
                                    else: signal = f"WAIT (MDD {mdd:.1f}% > -20% 고점대비 미달)"
                                elif tier == 'Watchlist':
                                    if mdd <= -30.0: signal = "WATCHLIST_BUY_READY (관심종목 -30% 폭락진입)"
                                    else: signal = f"WAIT (MDD {mdd:.1f}% > -30% 폭락대기 미달)"
                                else:
                                    if mdd <= -20.0: signal = "BUY_CANDIDATE (-20% 할인)"

                                cur.execute("""
                                    UPDATE company_profiles 
                                    SET current_price=?, high_52w=?, mdd_pct=?, buy_signal=?, last_updated=datetime('now', 'localtime')
                                    WHERE company_id=?
                                """, (curr, high52, mdd, signal, cid))
                    except Exception:
                        pass

        conn.commit()
        conn.close()
        print("[Migration] Startup DB migration complete.")
    except Exception as e:
        print(f"[Migration] Warning: {e}")


run_startup_migrations()


# ─────────────────────────────────────────────
# EPS 시계열 데이터 로드 (CSV → SQLite)
# Render 배포 환경: eps_data.csv.gz → eps_timeseries 테이블
# ─────────────────────────────────────────────
def load_eps_from_csv_if_needed():
    """
    eps_data.csv.gz 파일이 있고 eps_timeseries 테이블이 비어 있으면
    자동으로 SQLite에 로드합니다.
    """
    import sqlite3, gzip
    db_path  = os.path.join(os.path.dirname(__file__), "investment_portal.db")
    csv_path = os.path.join(os.path.dirname(__file__), "eps_data.csv.gz")

    if not os.path.exists(csv_path):
        print("[EPS] eps_data.csv.gz 파일 없음 - 건너뜀")
        return

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # 테이블 존재 여부 & 데이터 수 확인
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eps_timeseries'")
    table_exists = cur.fetchone() is not None
    if table_exists:
        cur.execute("SELECT COUNT(*) FROM eps_timeseries")
        cnt = cur.fetchone()[0]
        if cnt > 100000:
            print(f"[EPS] eps_timeseries 이미 {cnt:,}행 존재 - 건너뜀")
            conn.close()
            return

    print("[EPS] eps_timeseries 로드 시작...")
    cur.execute("DROP TABLE IF EXISTS eps_timeseries")
    cur.execute("""
        CREATE TABLE eps_timeseries (
            date       TEXT NOT NULL,
            code       TEXT NOT NULL,
            name       TEXT NOT NULL,
            index_type TEXT NOT NULL,
            eps_fwd    REAL,
            price      REAL,
            fwd_per    REAL,
            PRIMARY KEY (date, code)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_eps_date ON eps_timeseries(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_eps_code ON eps_timeseries(code)")

    BATCH   = 30000
    buffer  = []
    total   = 0

    with gzip.open(csv_path, 'rt', encoding='utf-8') as f:
        next(f)  # 헤더 건너뜀
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 7:
                continue
            date, code, name, itype = parts[0], parts[1], parts[2], parts[3]
            try:
                eps   = float(parts[4]) if parts[4] else None
                price = float(parts[5]) if parts[5] else None
                per   = float(parts[6]) if parts[6] else None
            except ValueError:
                continue
            buffer.append((date, code, name, itype, eps, price, per))
            total += 1
            if len(buffer) >= BATCH:
                cur.executemany("INSERT OR REPLACE INTO eps_timeseries VALUES (?,?,?,?,?,?,?)", buffer)
                conn.commit()
                buffer = []
                print(f"[EPS] 진행: {total:,}행 로드")

    if buffer:
        cur.executemany("INSERT OR REPLACE INTO eps_timeseries VALUES (?,?,?,?,?,?,?)", buffer)
        conn.commit()

    conn.close()
    print(f"[EPS] 로드 완료: {total:,}행")

load_eps_from_csv_if_needed()

app = FastAPI(title="Investment Portal API")


# ─────────────────────────────────────────────
# 주도주 스코어 맵 로드 (메모리 캐시)
# ─────────────────────────────────────────────
_LEADING_SCORE_MAP: dict = {}  # ticker -> {score, grade, breakdown}

def _load_leading_scores():
    global _LEADING_SCORE_MAP
    try:
        rank_path = os.path.join(os.path.dirname(__file__), "leading_stock_rankings.json")
        if os.path.exists(rank_path):
            with open(rank_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("rankings", []):
                t = item["ticker"]
                _LEADING_SCORE_MAP[t] = {
                    "leading_score": item["score"],
                    "leading_grade": item["grade"],
                    "leading_breakdown": item.get("breakdown", {}),
                }
            print(f"[LeadingScore] Loaded {len(_LEADING_SCORE_MAP)} ticker scores")
    except Exception as e:
        print(f"[LeadingScore] Warning: {e}")

_load_leading_scores()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
# Debug: DB 상태 확인 (Render 에러 진단용)
# ─────────────────────────────────────────────
@app.get("/api/admin/debug")
def admin_debug():
    import sqlite3, traceback
    db_path = os.path.join(os.path.dirname(__file__), "investment_portal.db")
    result = {"db_path": db_path, "db_exists": os.path.exists(db_path)}
    if result["db_exists"]:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM industry_reports"); result["reports"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM companies"); result["companies"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM financial_data"); result["financials"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM companies WHERE future_growth IS NULL"); result["null_future_growth"] = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            result["db_error"] = str(e)
    try:
        from sqlalchemy.orm import Session as SASession
        db = database.SessionLocal()
        reps = db.query(models.IndustryReport).all()
        result["orm_reports"] = len(reps)
        import schemas as sc
        errors = []
        for r in reps:
            try:
                sc.IndustryReport.model_validate(r)
            except Exception as e:
                errors.append({"id": r.id, "tag": r.tag, "error": str(e)})
        result["schema_errors"] = errors
        db.close()
    except Exception as e:
        result["orm_error"] = str(e)
        result["traceback"] = traceback.format_exc()
    return result

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
    # 주도주 점수 + 업사이드 점수 주입
    for comp in (report.companies or []):
        ls = _LEADING_SCORE_MAP.get(comp.ticker, {})
        comp.leading_score     = ls.get("leading_score")
        comp.leading_grade     = ls.get("leading_grade")
        comp.leading_breakdown = ls.get("leading_breakdown", {})
        # ── 성장성 기반 업사이드 점수 계산 ──────────────────────────────
        # profile 데이터 로드
        profile = db.query(models.CompanyProfile).filter(
            models.CompanyProfile.company_id == comp.id
        ).first()
        upside = 0.0
        if profile:
            # 1. 매출 성장률 (0~40점): 미래 성장의 핵심 지표
            rev_g = profile.revenue_growth or 0
            if rev_g >= 0.5:   upside += 40
            elif rev_g >= 0.25: upside += 32
            elif rev_g >= 0.15: upside += 24
            elif rev_g >= 0.10: upside += 16
            elif rev_g >= 0.05: upside += 8
            elif rev_g >= 0:    upside += 3
            # 음수 성장이면 큰 감점
            else:               upside += max(-20, rev_g * 40)

            # 2. 영업이익률 (0~20점): 수익 확장 여부
            opm = profile.op_margin_ttm or 0
            if opm >= 0.30:    upside += 20
            elif opm >= 0.20:  upside += 16
            elif opm >= 0.10:  upside += 11
            elif opm >= 0.05:  upside += 6
            elif opm >= 0:     upside += 2

            # 3. ROE (0~15점): 자본 효율로 내재가치 상승 가속
            roe = profile.roe or 0
            if roe >= 0.30:    upside += 15
            elif roe >= 0.20:  upside += 11
            elif roe >= 0.10:  upside += 6
            elif roe >= 0:     upside += 2

            # 4. PER 기반 저평가 여부 (0~15점): 낮을수록 상승 여력
            pe = profile.pe_ratio
            if pe is not None and pe > 0:
                if pe <= 15:    upside += 15
                elif pe <= 20:  upside += 12
                elif pe <= 30:  upside += 8
                elif pe <= 50:  upside += 4
                else:           upside += 1
            elif pe is None:    upside += 7  # 데이터 없으면 중립

            # 5. FCF 성장률 가산 (0~10점)
            fcf_g = profile.fcf_growth or 0
            if fcf_g >= 0.30:  upside += 10
            elif fcf_g >= 0.15: upside += 7
            elif fcf_g >= 0:    upside += 3

        comp.upside_score = round(max(0, min(100, upside)), 1)
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

# ─────────────────────────────────────────────
# 4단계 투자원칙 기반 유니버스 팔로잉 API
# ─────────────────────────────────────────────
@app.get("/api/portfolio/universe")
def get_investment_principles_universe(db: Session = Depends(get_db)):
    """4단계 투자원칙(MDD, 독점력, 성장성) 기반 Core/Satellite/Watchlist 팔로잉 유니버스 반환 (Raw SQL)"""
    result = []
    try:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), "investment_portal.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.name, c.ticker, c.industry_id,
                   COALESCE(ir.title, '기타') AS industry_title,
                   c.role_description, c.future_growth,
                   COALESCE(c.portfolio_tier, 'Standard') AS portfolio_tier,
                   c.principle_reason,
                   cp.current_price, cp.high_52w, cp.mdd_pct,
                   COALESCE(cp.buy_signal, 'WAIT (정보 대기)') AS buy_signal,
                   cp.last_updated
            FROM companies c
            LEFT JOIN industry_reports ir ON c.industry_id = ir.id
            LEFT JOIN company_profiles cp ON c.id = cp.company_id
            WHERE c.id IN (
                -- ticker 기준 중복 제거: Core > Satellite > Watchlist > Standard 우선, 같으면 id 최솟값
                SELECT MIN(sub.id)
                FROM (
                    SELECT id, ticker,
                        CASE COALESCE(portfolio_tier, 'Standard')
                            WHEN 'Core'      THEN 1
                            WHEN 'Satellite' THEN 2
                            WHEN 'Watchlist' THEN 3
                            ELSE 4
                        END AS tier_rank
                    FROM companies
                    WHERE ticker IS NOT NULL
                ) sub
                INNER JOIN (
                    SELECT ticker, MIN(CASE COALESCE(portfolio_tier,'Standard')
                        WHEN 'Core' THEN 1 WHEN 'Satellite' THEN 2 WHEN 'Watchlist' THEN 3 ELSE 4 END) AS best_rank
                    FROM companies WHERE ticker IS NOT NULL GROUP BY ticker
                ) best ON sub.ticker = best.ticker AND sub.tier_rank = best.best_rank
                GROUP BY sub.ticker
                UNION
                -- ticker가 NULL인 경우도 포함
                SELECT id FROM companies WHERE ticker IS NULL
            )
            ORDER BY
                CASE COALESCE(c.portfolio_tier, 'Standard')
                    WHEN 'Core'      THEN 1
                    WHEN 'Satellite' THEN 2
                    WHEN 'Watchlist' THEN 3
                    ELSE 4
                END, c.id
        """)
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            result.append({
                "id": r[0],
                "name": r[1],
                "ticker": r[2],
                "industry_id": r[3],
                "industry_title": r[4],
                "role_description": r[5],
                "future_growth": r[6],
                "portfolio_tier": r[7],
                "principle_reason": r[8],
                "current_price": r[9],
                "high_52w": r[10],
                "mdd_pct": r[11],
                "buy_signal": r[12],
                "last_updated": r[13]
            })
        print(f"[Universe API] Raw SQL fetched {len(result)} items (ticker 중복 제거 후)")
    except Exception as e:
        print(f"[Universe API Exception] {e}")
        import traceback; traceback.print_exc()

    return {
        "principles_summary": {
            "title": "4단계 통합 투자원칙 표준 체계",
            "mdd_rule": "Core/Satellite: MDD -20%~-30% 이상 할인 시 1차/2차 분할매수 진입, Watchlist: -30%~-40% 폭락 진입",
            "core_rule": "시장점유율 50%+ (독과점 1~2위), OPM 25%+ / GPM 50%+, 강력한 락인(Switching Cost)",
            "satellite_rule": "글로벌 Top 3 입지, 수주잔고 YoY +30%+ or 최고치, SW/구독 이익률 체질개선",
            "asset_allocation": "주식 70% (Core 3 + Satellite 2) : 현금 30% (3분할 매수 & 반등 시 회수)"
        },
        "universe": result
    }


# ─────────────────────────────────────────────
# 투자원칙 기반 자동 종목 추천 스캐너
# ─────────────────────────────────────────────
@app.get("/api/portfolio/auto_scan")
def auto_scan_investment_candidates():
    """
    4단계 투자원칙 기반 자동 종목 스캔:
    - 글로벌 독점 우량주 후보군(S&P500 + 코스피 고품질) 대상
    - yfinance로 52주 최고가/MDD/수익성 자동 계산
    - 투자원칙 필터: 시총 10조+ / MDD -15% 이상 할인 / ROE or 영업이익률 우수
    - 이미 유니버스에 있는 종목 제외 후 신규 추천
    """
    import sqlite3, yfinance as yf

    # ── 1) 투자원칙 적합 후보 티커 풀 (독점 우량주 중심) ──
    CANDIDATE_TICKERS = [
        # 🏆 글로벌 독점 플랫폼/인프라
        "META", "GOOGL", "AMZN", "MSFT", "AAPL", "NFLX",
        "V", "MA", "PYPL", "ADBE", "CRM", "NOW", "SNOW",
        # 🔬 반도체/AI 인프라
        "AMD", "AVGO", "QCOM", "AMAT", "KLAC", "LRCX", "MRVL",
        "ARM", "SMCI", "MU",
        # 🏥 헬스케어 독점
        "LLY", "UNH", "ABBV", "TMO", "ISRG", "DXCM",
        "VEEV", "IDXX", "PODD", "ZBH",
        # 🏗️ 산업/방산
        "RTX", "LMT", "NOC", "GD", "HII", "AXON",
        "CAT", "DE", "HON", "GE", "ETN",
        # 💰 금융 독점
        "BRK-B", "JPM", "GS", "BLK", "SPGI", "MCO",
        "ICE", "MSCI", "FDS",
        # 🛒 소비재 독점 브랜드
        "MCD", "SBUX", "NKE", "COST", "TJX",
        "PG", "KO", "PEP", "PM", "MO",
        # ⚡ 에너지/유틸리티 독점
        "NEE", "SO", "AEP", "XEL",
        # 🇰🇷 코스피 우량주 (국내)
        "005380.KS",  # 현대차
        "000660.KS",  # SK하이닉스
        "035720.KS",  # 카카오
        "035420.KS",  # NAVER
        "051910.KS",  # LG화학
        "006400.KS",  # 삼성SDI
        "003670.KS",  # 포스코퓨처엠
        "373220.KS",  # LG에너지솔루션
        "207940.KS",  # 삼성바이오로직스(이미있지만 체크)
        "068270.KS",  # 셀트리온
        "105560.KS",  # KB금융
        "055550.KS",  # 신한지주
        "032830.KS",  # 삼성생명
        "009150.KS",  # 삼성전기
        "028260.KS",  # 삼성물산
    ]

    # ── 2) 이미 유니버스에 등록된 ticker 조회 ──
    try:
        db_path = os.path.join(os.path.dirname(__file__), "investment_portal.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT ticker FROM companies WHERE ticker IS NOT NULL")
        existing_tickers = set(r[0].strip().upper() for r in cur.fetchall())
        conn.close()
    except Exception:
        existing_tickers = set()

    # 후보에서 이미 있는 종목 제외
    new_candidates = [t for t in CANDIDATE_TICKERS if t.upper() not in existing_tickers]

    if not new_candidates:
        return {"scan_count": 0, "recommendations": [], "message": "신규 추천 종목 없음 (모두 유니버스 등록됨)"}

    # ── 3) yfinance 데이터 수집 ──
    results = []
    try:
        data = yf.download(new_candidates, period="1y", progress=False, auto_adjust=True)
        info_cache = {}

        for ticker in new_candidates:
            try:
                clean_t = ticker.strip()
                # 가격 데이터
                if 'Close' in data.columns.names[0] if hasattr(data.columns, 'names') else True:
                    try:
                        close_s = data['Close'][clean_t].dropna() if clean_t in data['Close'].columns else None
                        high_s  = data['High'][clean_t].dropna()  if clean_t in data['High'].columns  else None
                    except Exception:
                        close_s, high_s = None, None
                else:
                    close_s, high_s = None, None

                if close_s is None or close_s.empty or high_s is None or high_s.empty:
                    continue

                curr_price = float(close_s.iloc[-1])
                high_52w   = float(high_s.max())
                if high_52w <= 0 or curr_price <= 0:
                    continue
                mdd = float(((curr_price - high_52w) / high_52w) * 100.0)

                # MDD -15% 이하만 관심 대상 (추천 필터)
                if mdd > -15.0:
                    continue

                # yfinance info (수익성 필터)
                try:
                    t_obj = yf.Ticker(clean_t)
                    info = t_obj.fast_info
                    market_cap = getattr(info, 'market_cap', None) or 0
                    # 시총 1조원(약 $7억) 이상만
                    if market_cap < 700_000_000:
                        continue

                    t_full = t_obj.info
                    roe           = t_full.get('returnOnEquity', None)
                    profit_margin = t_full.get('profitMargins', None)
                    op_margin     = t_full.get('operatingMargins', None)
                    pe_ratio      = t_full.get('trailingPE', None)
                    name          = t_full.get('longName') or t_full.get('shortName') or clean_t
                    sector        = t_full.get('sector', '기타')
                    industry      = t_full.get('industry', '')
                except Exception:
                    roe, profit_margin, op_margin, pe_ratio = None, None, None, None
                    name = clean_t
                    sector = '기타'
                    industry = ''
                    market_cap = 0

                # 투자원칙 점수 산정
                score = 0
                tags = []

                # MDD 할인율별 가점
                if mdd <= -40: score += 40; tags.append("🔥 -40%+ 폭락")
                elif mdd <= -30: score += 30; tags.append("📉 -30%+ 급락")
                elif mdd <= -20: score += 20; tags.append("📊 -20%+ 조정")
                elif mdd <= -15: score += 10; tags.append("📈 -15%+ 주목")

                # 수익성 가점
                if roe and roe > 0.20: score += 20; tags.append(f"ROE {roe*100:.0f}%")
                if op_margin and op_margin > 0.25: score += 15; tags.append(f"OPM {op_margin*100:.0f}%")
                elif op_margin and op_margin > 0.15: score += 8
                if profit_margin and profit_margin > 0.15: score += 10; tags.append(f"순이익률 {profit_margin*100:.0f}%")

                # 섹터 독점 프리미엄
                if any(s in sector for s in ['Technology', 'Healthcare', 'Financial']):
                    score += 10; tags.append(f"독점섹터({sector})")

                # 매수신호 분류
                if mdd <= -40:   signal = "DEEP_DISCOUNT_추천 (3차 분할매수 타이밍)"
                elif mdd <= -30: signal = "BUY_추천 (2차 분할매수 타이밍)"
                elif mdd <= -20: signal = "BUY_주목 (1차 분할매수 고려)"
                else:            signal = "WATCHLIST_주목 (-15% 조정 관심)"

                results.append({
                    "ticker": clean_t,
                    "name": name,
                    "sector": sector,
                    "industry": industry,
                    "current_price": round(curr_price, 2),
                    "high_52w": round(high_52w, 2),
                    "mdd_pct": round(mdd, 2),
                    "roe": round(roe * 100, 1) if roe else None,
                    "op_margin": round(op_margin * 100, 1) if op_margin else None,
                    "profit_margin": round(profit_margin * 100, 1) if profit_margin else None,
                    "pe_ratio": round(pe_ratio, 1) if pe_ratio else None,
                    "market_cap_b": round(market_cap / 1e9, 1) if market_cap else None,
                    "signal": signal,
                    "score": score,
                    "tags": tags,
                    "already_in_universe": False
                })
            except Exception as e:
                print(f"[AutoScan] {ticker} error: {e}")
                continue

    except Exception as e:
        print(f"[AutoScan] yfinance batch error: {e}")

    # ── 4) 점수 내림차순 정렬 ──
    results.sort(key=lambda x: x['score'], reverse=True)

    return {
        "scan_count": len(results),
        "scanned_tickers": len(new_candidates),
        "recommendations": results,
        "criteria": {
            "mdd_threshold": "-15% 이상 고점 대비 조정",
            "market_cap": "시총 $7억 이상",
            "focus": "독점력/수익성/MDD 기반 자동 필터링"
        }
    }


# ── BUY_CANDIDATE → Watchlist 스크리닝 ─────────────────────────────────
@app.post("/api/portfolio/screen_to_watchlist")
def screen_to_watchlist(
    tickers: list[str] | None = None,
    auto_promote: bool = True
):
    """
    BUY_CANDIDATE 종목을 투자원칙으로 스크리닝 → Watchlist 승격
    - tickers: None이면 DB의 모든 BUY_CANDIDATE Standard 종목
    - auto_promote: True이면 통과 종목을 즉시 DB에 Watchlist로 업데이트
    """
    import sqlite3, yfinance as yf
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investment_portal.db")

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # BUY_CANDIDATE 목록 가져오기
    if tickers:
        placeholders = ','.join('?' * len(tickers))
        cur.execute(f"""
            SELECT c.id, c.name, c.ticker, cp.mdd_pct, cp.current_price, cp.high_52w, cp.buy_signal
            FROM companies c
            LEFT JOIN company_profiles cp ON c.id = cp.company_id
            WHERE c.ticker IN ({placeholders})
              AND cp.buy_signal LIKE '%BUY_CANDIDATE%'
        """, tickers)
    else:
        cur.execute("""
            SELECT c.id, c.name, c.ticker, cp.mdd_pct, cp.current_price, cp.high_52w, cp.buy_signal
            FROM companies c
            LEFT JOIN company_profiles cp ON c.id = cp.company_id
            WHERE c.portfolio_tier = 'Standard'
              AND cp.buy_signal LIKE '%BUY_CANDIDATE%'
        """)

    candidates = cur.fetchall()
    conn.close()

    if not candidates:
        return {"message": "스크리닝할 BUY_CANDIDATE 종목이 없습니다.", "promoted": []}

    promoted   = []
    watchlist  = []
    excluded   = []

    for cid, name, ticker, mdd, curr_price, high52, buy_sig in candidates:
        result = {
            "id": cid, "name": name, "ticker": ticker,
            "mdd_pct": mdd, "current_price": curr_price,
            "score": 0, "tags": [], "decision": "EXCLUDE",
            "roe": None, "opm": None, "market_cap_b": None
        }

        # ── yfinance 데이터 조회 ──
        try:
            import time; time.sleep(0.3)
            t = yf.Ticker(ticker)
            info = t.info
            roe        = info.get('returnOnEquity')       # 0.25 = 25%
            opm        = info.get('operatingMargins')     # 0.18 = 18%
            market_cap = info.get('marketCap', 0)
            sector     = info.get('sector', '')
            industry   = info.get('industry', '')
            eps_fwd    = info.get('forwardEps')
            eps_trail  = info.get('trailingEps')
            revenue_gr = info.get('revenueGrowth')
            ps_ratio   = info.get('priceToSalesTrailingMomonths12')
            beta       = info.get('beta', 1.0)

            result['roe']          = round(roe * 100, 1) if roe else None
            result['opm']          = round(opm * 100, 1) if opm else None
            result['market_cap_b'] = round(market_cap / 1e9, 1) if market_cap else None
            result['sector']       = sector
            result['industry']     = industry
            result['eps_fwd']      = eps_fwd
            result['revenue_growth_pct'] = round(revenue_gr * 100, 1) if revenue_gr else None

        except Exception as e:
            print(f"[Screen] {ticker} info error: {e}")
            info = {}
            roe = opm = market_cap = None

        # ── 투자원칙 점수 산정 ──
        score = 0; tags = []

        # 1. 시총 기준 ($70억 = 약 10조원)
        mc = result.get('market_cap_b') or 0
        if mc >= 70:
            score += 20; tags.append(f"💰 시총 ${mc:.0f}B")
        elif mc >= 10:
            score += 10; tags.append(f"시총 ${mc:.0f}B")
        else:
            tags.append(f"⚠️ 시총 소형 ${mc:.1f}B")

        # 2. 수익성
        r_roe = result.get('roe') or 0
        r_opm = result.get('opm') or 0
        if r_roe >= 20 or r_opm >= 20:
            score += 30; tags.append(f"✅ 고수익 ROE={r_roe}% OPM={r_opm}%")
        elif r_roe >= 12 or r_opm >= 12:
            score += 15; tags.append(f"ROE={r_roe}% OPM={r_opm}%")
        else:
            tags.append(f"❌ 수익성 부족 ROE={r_roe}% OPM={r_opm}%")

        # 3. MDD 할인율
        mdd_v = mdd or 0
        if mdd_v <= -40:
            score += 35; tags.append(f"🔥 -40%+ 폭락 ({mdd_v:.1f}%)")
        elif mdd_v <= -30:
            score += 25; tags.append(f"📉 -30%+ 급락 ({mdd_v:.1f}%)")
        elif mdd_v <= -20:
            score += 15; tags.append(f"📊 -20%+ 조정 ({mdd_v:.1f}%)")

        # 4. 섹터별 독점력 프리미엄 (수동 매핑)
        MONOPOLY_BOOST = {
            'QCOM': (25, '모바일 AP/5G 모뎀 독점', True),
            'RKLB': (25, '소형 발사체 2위 독점', True),
            'ISRG': (30, '수술로봇 다빈치 독점', True),
            'PALNT': (20, 'AI 운영체제 AIP 독점', True),
            'NXPI': (15, '자동차용 SoC 상위권', True),
            'HUBB': (15, '전력기기 북미 시장 선도', True),
            'POWL': (20, '전력배전 설비 틈새 독점', True),
            'ON':   (10, '전력반도체 상위권', False),
            'KLIC': (10, '반도체 본딩장비 선도', False),
            'MBLY': (5,  'ADAS 센서 기술 보유하나 경쟁 심화', False),
            'APTV': (0,  '자동차 전장 범용, 업황 부진', False),
            'STM':  (0,  '범용 반도체, 업황 부진', False),
            'GFS':  (5,  '2nd tier 파운드리', False),
            'SHLS': (5,  '태양광 BOS 틈새', False),
            'MYRG': (10, '전력망 EPC 틈새', False),
            'WCC':  (5,  '전기자재 유통 경쟁 시장', False),
            'ATKR': (5,  '전선관 북미 시장 선도', False),
            'ACM':  (5,  '인프라 엔지니어링 다수 경쟁사', False),
            'ADMA': (10, '혈액제제 CDMO 틈새', False),
            'CBRE': (10, '글로벌 부동산 서비스 1위', False),
        }
        tk_upper = ticker.upper().replace('.', '')
        boost_info = MONOPOLY_BOOST.get(tk_upper)
        if boost_info:
            bscore, breason, is_monopoly = boost_info
            score += bscore
            if bscore > 0:
                tags.append(f"{'🏆' if is_monopoly else '📌'} {breason}")

        result['score'] = score
        result['tags']  = tags

        # ── 최종 판단 ──
        # 기준: score >= 50 + 수익성 충족 + 시총 $70B+
        profitable = (r_roe >= 12 or r_opm >= 12)
        large_cap  = mc >= 10
        has_moat   = (boost_info[0] if boost_info else 0) >= 15

        if score >= 55 and profitable and (large_cap or has_moat):
            result['decision'] = 'WATCHLIST'
            watchlist.append(result)
        elif score >= 35 and (profitable or large_cap):
            result['decision'] = 'WATCH'
        else:
            result['decision'] = 'EXCLUDE'
            excluded.append(result)

    # ── DB 업데이트 ──
    promoted_names = []
    if auto_promote and watchlist:
        conn2 = sqlite3.connect(db_path)
        cur2  = conn2.cursor()
        for item in watchlist:
            reason = f"BUY_CANDIDATE 자동스크리닝 통과 (점수={item['score']}, ROE={item.get('roe')}%, OPM={item.get('opm')}%)"
            cur2.execute("""
                UPDATE companies SET portfolio_tier='Watchlist', principle_reason=?
                WHERE id=?
            """, (reason, item['id']))
            # buy_signal도 업데이트
            cur2.execute("""
                UPDATE company_profiles
                SET buy_signal='WATCHLIST_BUY_READY (스크리닝 통과 → 관심종목 등재)'
                WHERE company_id=?
            """, (item['id'],))
            promoted_names.append(item['name'])
            promoted.append(item)
        conn2.commit()
        conn2.close()
        print(f"[Screen] Watchlist 승격: {promoted_names}")

    return {
        "total_screened": len(candidates),
        "promoted_count": len(watchlist),
        "promoted": [{"name": w['name'], "ticker": w['ticker'],
                      "score": w['score'], "tags": w['tags'],
                      "roe": w.get('roe'), "opm": w.get('opm'),
                      "mdd_pct": w.get('mdd_pct'), "market_cap_b": w.get('market_cap_b')}
                     for w in watchlist],
        "watch_list": [{"name": w['name'], "ticker": w['ticker'],
                        "score": w['score'], "tags": w['tags']}
                       for w in watchlist if w.get('decision') == 'WATCH'],
        "excluded_count": len(excluded),
        "auto_promoted_to_watchlist": promoted_names
    }


# ═══════════════════════════════════════════════════════
#  EPS 분석 API 엔드포인트 (SQLite eps_timeseries 기반)
# ═══════════════════════════════════════════════════════

def _eps_db():
    """eps_timeseries SQLite 연결"""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "investment_portal.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def _check_eps_table(cur) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eps_timeseries'")
    return cur.fetchone() is not None


# ── 1) 시장 밸류에이션 온도계 ───────────────────────────
@app.get("/api/eps/market_valuation")
def get_market_valuation():
    """
    KOSPI200 전체 중앙값 Forward PER 시계열 반환
    - 현재값, 1년 시계열(차트용), 10년 히스토리 기반 분위수
    """
    conn = _eps_db()
    cur  = conn.cursor()

    if not _check_eps_table(cur):
        conn.close()
        return {"error": "EPS 데이터가 아직 로드되지 않았습니다. 관리자에게 문의하세요."}

    # 1년치 일별 중앙값 PER (KOSPI200)
    cur.execute("""
        SELECT date,
               ROUND(AVG(fwd_per), 2)      AS avg_per,
               COUNT(*)                    AS stock_count
        FROM eps_timeseries
        WHERE index_type='KOSPI200'
          AND fwd_per IS NOT NULL
          AND fwd_per > 0
          AND fwd_per < 200
          AND date >= date('now', '-400 days')
        GROUP BY date
        ORDER BY date
    """)
    rows_1y = cur.fetchall()

    # 전체 10년 히스토리 (분위수 계산용)
    cur.execute("""
        SELECT fwd_per FROM eps_timeseries
        WHERE index_type='KOSPI200'
          AND fwd_per IS NOT NULL
          AND fwd_per > 0
          AND fwd_per < 200
        ORDER BY fwd_per
    """)
    all_pers = [r[0] for r in cur.fetchall()]

    # KOSDAQ150
    cur.execute("""
        SELECT date,
               ROUND(AVG(fwd_per), 2) AS avg_per,
               COUNT(*) AS stock_count
        FROM eps_timeseries
        WHERE index_type='KOSDAQ150'
          AND fwd_per IS NOT NULL
          AND fwd_per > 0
          AND fwd_per < 200
          AND date >= date('now', '-400 days')
        GROUP BY date
        ORDER BY date
    """)
    rows_kq = cur.fetchall()

    conn.close()

    # 분위수 계산
    import statistics
    def percentile(data, p):
        if not data: return None
        idx = int(len(data) * p / 100)
        return round(data[min(idx, len(data)-1)], 1)

    hist_min  = round(min(all_pers), 1) if all_pers else None
    hist_max  = round(max(all_pers), 1) if all_pers else None
    hist_avg  = round(sum(all_pers)/len(all_pers), 1) if all_pers else None
    p10 = percentile(all_pers, 10)
    p25 = percentile(all_pers, 25)
    p50 = percentile(all_pers, 50)
    p75 = percentile(all_pers, 75)
    p90 = percentile(all_pers, 90)

    # 현재 PER (최신 날짜 기준)
    current = {"kospi200": None, "kosdaq150": None}
    if rows_1y:
        current["kospi200"] = rows_1y[-1]["avg_per"]
    if rows_kq:
        current["kosdaq150"] = rows_kq[-1]["avg_per"]

    # 현재 위치 분위수
    curr_per = current["kospi200"]
    if curr_per and all_pers:
        curr_pct = round(sum(1 for x in all_pers if x <= curr_per) / len(all_pers) * 100, 1)
    else:
        curr_pct = None

    # 온도계 레벨 판단
    if curr_pct is not None:
        if curr_pct <= 20:  level = "매우 저평가 🟢 (역사적 저점)"
        elif curr_pct <= 35: level = "저평가 🟢 (매수 적극 고려)"
        elif curr_pct <= 55: level = "적정 🟡 (중립)"
        elif curr_pct <= 75: level = "다소 고평가 🟠 (신중)"
        else:                level = "과열 🔴 (현금 비중 확대)"
    else:
        level = "데이터 없음"

    return {
        "current": current,
        "current_percentile": curr_pct,
        "level": level,
        "history": {
            "min": hist_min, "max": hist_max, "avg": hist_avg,
            "p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90
        },
        "chart_kospi200": [{"date": r["date"], "per": r["avg_per"], "count": r["stock_count"]}
                           for r in rows_1y],
        "chart_kosdaq150": [{"date": r["date"], "per": r["avg_per"], "count": r["stock_count"]}
                            for r in rows_kq],
    }


# ── 2) 주가-EPS 괴리 스크리너 ───────────────────────────
@app.get("/api/eps/spread_screen")
def get_spread_screen(period_days: int = 252, top_n: int = 20):
    """
    주가 성장률 vs EPS 성장률 괴리 기반 저평가/과열 종목 스크리닝
    - period_days: 비교 기간 (기본 252일=1년)
    - top_n: 반환 종목 수
    """
    conn = _eps_db()
    cur  = conn.cursor()

    if not _check_eps_table(cur):
        conn.close()
        return {"error": "EPS 데이터 없음"}

    # 최신 날짜와 N일 전 날짜 구하기
    cur.execute("SELECT MAX(date) FROM eps_timeseries WHERE fwd_per IS NOT NULL")
    latest_date = cur.fetchone()[0]

    cur.execute(f"""
        SELECT date FROM eps_timeseries
        WHERE fwd_per IS NOT NULL
          AND date <= '{latest_date}'
        GROUP BY date
        ORDER BY date DESC
        LIMIT {period_days + 10}
    """)
    date_rows = cur.fetchall()
    if len(date_rows) < period_days:
        conn.close()
        return {"error": "데이터 부족"}

    past_date = date_rows[period_days - 1]["date"]

    # 현재 & 과거 데이터 조인
    cur.execute(f"""
        SELECT
            n.code, n.name, n.index_type,
            n.eps_fwd   AS eps_now,
            n.price     AS price_now,
            n.fwd_per   AS per_now,
            o.eps_fwd   AS eps_past,
            o.price     AS price_past,
            ROUND((n.price   - o.price)   / o.price   * 100, 1) AS price_growth,
            ROUND((n.eps_fwd - o.eps_fwd) / ABS(o.eps_fwd) * 100, 1) AS eps_growth,
            ROUND(
                ((n.price - o.price)/o.price) - ((n.eps_fwd - o.eps_fwd)/ABS(o.eps_fwd)),
                3
            ) * 100 AS spread_pct
        FROM
            (SELECT code, name, index_type, eps_fwd, price, fwd_per
             FROM eps_timeseries WHERE date='{latest_date}' AND fwd_per IS NOT NULL) n
        JOIN
            (SELECT code, eps_fwd, price
             FROM eps_timeseries WHERE date='{past_date}' AND eps_fwd > 0 AND price > 0) o
            ON n.code = o.code
        WHERE
            o.eps_fwd > 0
            AND o.price > 0
            AND n.eps_fwd > 0
            AND n.price > 0
        ORDER BY spread_pct ASC
    """)
    all_rows = cur.fetchall()
    conn.close()

    undervalued = []  # 저평가: EPS가 주가보다 훨씬 많이 오름 (spread 음수)
    overheated  = []  # 과열: 주가가 EPS보다 훨씬 많이 오름 (spread 양수)

    for r in all_rows:
        obj = {
            "code": r["code"],
            "name": r["name"],
            "index_type": r["index_type"],
            "eps_fwd": round(r["eps_now"], 0) if r["eps_now"] else None,
            "price": round(r["price_now"], 0) if r["price_now"] else None,
            "fwd_per": round(r["per_now"], 1) if r["per_now"] else None,
            "eps_growth_pct": r["eps_growth"],
            "price_growth_pct": r["price_growth"],
            "spread_pct": round(r["spread_pct"], 1) if r["spread_pct"] else None,
        }
        if len(undervalued) < top_n:
            undervalued.append(obj)

    # 과열 = 역순
    for r in reversed(all_rows):
        obj = {
            "code": r["code"],
            "name": r["name"],
            "index_type": r["index_type"],
            "eps_fwd": round(r["eps_now"], 0) if r["eps_now"] else None,
            "price": round(r["price_now"], 0) if r["price_now"] else None,
            "fwd_per": round(r["per_now"], 1) if r["per_now"] else None,
            "eps_growth_pct": r["eps_growth"],
            "price_growth_pct": r["price_growth"],
            "spread_pct": round(r["spread_pct"], 1) if r["spread_pct"] else None,
        }
        if len(overheated) < top_n // 2:
            overheated.append(obj)

    return {
        "latest_date": latest_date,
        "past_date": past_date,
        "period_days": period_days,
        "undervalued": undervalued,
        "overheated": overheated,
        "total_screened": len(all_rows),
    }


# ── 3) 팔로잉 종목 EPS 트래커 ────────────────────────────
@app.get("/api/eps/universe_tracker")
def get_universe_tracker():
    """
    현재 유니버스(Core/Satellite/Watchlist) 종목 중
    KOSPI200/KOSDAQ150에 있는 종목의 EPS 트래커 반환
    - FWD EPS 최근 1년 추이 + 주가 추이 + 현재 FWD PER + MDD
    """
    conn = _eps_db()
    cur  = conn.cursor()

    if not _check_eps_table(cur):
        conn.close()
        return {"tracker": []}

    # 유니버스 종목 조회 (KS/KQ 티커)
    cur.execute("""
        SELECT DISTINCT c.id, c.name, c.ticker, c.portfolio_tier,
               cp.current_price, cp.high_52w, cp.mdd_pct, cp.buy_signal
        FROM companies c
        LEFT JOIN company_profiles cp ON c.id = cp.company_id
        WHERE (c.ticker LIKE '%.KS' OR c.ticker LIKE '%.KQ')
          AND c.portfolio_tier IN ('Core','Satellite','Watchlist')
    """)
    universe_stocks = cur.fetchall()

    tracker = []
    for u in universe_stocks:
        ticker = u["ticker"]
        # yfinance 티커 → DataGuide 코드 변환 (예: 005930.KS → A005930)
        raw_code = ticker.replace('.KS','').replace('.KQ','').zfill(6)
        dg_code  = f"A{raw_code}"

        # 1년 시계열 (날짜, EPS, 주가, FWD PER)
        cur.execute(f"""
            SELECT date, eps_fwd, price, fwd_per
            FROM eps_timeseries
            WHERE code = '{dg_code}'
              AND date >= date('now', '-400 days')
              AND eps_fwd IS NOT NULL
              AND price IS NOT NULL
            ORDER BY date
        """)
        ts_rows = cur.fetchall()

        if not ts_rows:
            continue

        # 1년 전 vs 현재 비교
        latest = ts_rows[-1]
        past   = ts_rows[0]

        eps_change = None
        if past["eps_fwd"] and abs(past["eps_fwd"]) > 0:
            eps_change = round((latest["eps_fwd"] - past["eps_fwd"]) / abs(past["eps_fwd"]) * 100, 1)

        price_change = None
        if past["price"] and past["price"] > 0:
            price_change = round((latest["price"] - past["price"]) / past["price"] * 100, 1)

        spread = None
        if eps_change is not None and price_change is not None:
            spread = round(price_change - eps_change, 1)

        tracker.append({
            "id": u["id"],
            "name": u["name"],
            "ticker": ticker,
            "dg_code": dg_code,
            "portfolio_tier": u["portfolio_tier"],
            "current_price_db": u["current_price"],
            "high_52w": u["high_52w"],
            "mdd_pct": u["mdd_pct"],
            "buy_signal": u["buy_signal"],
            "eps_latest": round(latest["eps_fwd"], 0) if latest["eps_fwd"] else None,
            "price_latest": round(latest["price"], 0) if latest["price"] else None,
            "fwd_per_latest": round(latest["fwd_per"], 1) if latest["fwd_per"] else None,
            "eps_change_1y": eps_change,
            "price_change_1y": price_change,
            "spread_1y": spread,
            "chart": [
                {
                    "date": r["date"],
                    "eps": round(r["eps_fwd"], 0) if r["eps_fwd"] else None,
                    "price": round(r["price"], 0) if r["price"] else None,
                    "per": round(r["fwd_per"], 1) if r["fwd_per"] else None
                }
                for r in ts_rows[::5]  # 5일 간격으로 샘플링 (차트 최적화)
            ]
        })

    conn.close()

    # 티어별 정렬
    tier_order = {"Core": 1, "Satellite": 2, "Watchlist": 3}
    tracker.sort(key=lambda x: tier_order.get(x["portfolio_tier"], 4))

    return {"tracker": tracker}



def refresh_universe_prices(db: Session = Depends(get_db)):
    """Yahoo Finance를 통해 실시간 현재가, 52주 최고가, MDD 및 BUY_READY 신호 일괄 갱신"""
    try:
        import sqlite3, yfinance as yf
        db_path = os.path.join(os.path.dirname(__file__), "investment_portal.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT c.id, c.name, c.ticker, c.portfolio_tier
            FROM companies c
            WHERE c.ticker IS NOT NULL AND length(c.ticker) > 0
        """)
        companies = cur.fetchall()
        tickers = [c[2].strip() for c in companies if c[2]]

        if tickers:
            print(f"[RefreshPrices] Fetching live yfinance data for {len(tickers)} tickers...")
            data = yf.download(tickers, period="1y", progress=False)

            for cid, cname, ticker, tier in companies:
                clean_t = ticker.strip()
                try:
                    if len(tickers) == 1:
                        close_ser = data['Close']
                        high_ser = data['High']
                    else:
                        close_ser = data['Close'][clean_t] if clean_t in data['Close'].columns else None
                        high_ser = data['High'][clean_t] if clean_t in data['High'].columns else None

                    if close_ser is not None and not close_ser.dropna().empty:
                        curr = float(close_ser.dropna().iloc[-1])
                        high52 = float(high_ser.dropna().max())
                        mdd = float(((curr - high52) / high52) * 100.0)

                        signal = "WAIT (MDD 미달 - 고점 부근)"
                        if tier in ['Core', 'Satellite']:
                            if mdd <= -40.0:
                                signal = "DEEP_DISCOUNT (3차 분할매수 -40% 진입)"
                            elif mdd <= -30.0:
                                signal = "BUY_READY (2차 분할매수 -30% 진입)"
                            elif mdd <= -20.0:
                                signal = "BUY_READY (1차 분할매수 -20% 진입)"
                            else:
                                signal = f"WAIT (MDD {mdd:.1f}% > -20% 고점대비 미달)"
                        elif tier == 'Watchlist':
                            if mdd <= -30.0:
                                signal = "WATCHLIST_BUY_READY (관심종목 -30% 폭락진입)"
                            else:
                                signal = f"WAIT (MDD {mdd:.1f}% > -30% 폭락대기 미달)"
                        else:
                            if mdd <= -20.0:
                                signal = "BUY_CANDIDATE (-20% 할인)"

                        cur.execute("""
                            UPDATE company_profiles 
                            SET current_price=?, high_52w=?, mdd_pct=?, buy_signal=?, last_updated=datetime('now', 'localtime')
                            WHERE company_id=?
                        """, (curr, high52, mdd, signal, cid))
                except Exception as ex:
                    pass

            conn.commit()
            conn.close()
            print("[RefreshPrices] Successfully updated price & MDD data.")
    except Exception as e:
        print(f"[RefreshPrices Error] {e}")

    return get_investment_principles_universe(db)

