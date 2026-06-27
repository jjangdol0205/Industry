# -*- coding: utf-8 -*-
"""
에너지 산업 보고서 제목 및 summary 업데이트
"""
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'investment_portal.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

NEW_TITLE = "AI 에너지 인프라 밸류체인 심층분석"

NEW_SUMMARY = """## 1. 산업 개요: AI 전력 위기와 에너지 인프라의 부상

생성형 AI 폭증이 초래한 데이터센터 전력 수요 급증은 전통적인 전력망이 감당할 수 있는 한계를 초과했습니다. 엔비디아 H100 GPU 클러스터 한 랙만으로도 40~100kW의 전력을 소비하며, 2030년까지 미국 데이터센터 전력 수요는 현재의 3배에 달하는 35GW 이상으로 폭증할 전망입니다. 재생에너지의 간헐성과 전력망 확충의 지연이라는 이중 장벽 앞에서, **SMR(소형모듈원전)**과 **가스터빈 분산 발전**이 구조적 해법으로 부상하고 있습니다.

## 2. 핵심 투자 테마: 3개 레이어 밸류체인

**① 가스터빈 발전 (단기: 1~3년)**
- AI 데이터센터 전력 공급의 브릿지(Bridge) 솔루션
- 태양광/풍력 간헐성 보완 + 1~2년 내 신속 구축 가능
- GE Vernova, Siemens Energy, Mitsubishi Heavy Industries 수혜

**② SMR 설계 팹리스 (중기: 3~7년)**
- 미국 NRC 표준설계인가(SDA) = 규제 해자 독점
- 24/7 무탄소(CFE) 기저 전원 공급 → 빅테크 직접 PPA 체결
- NuScale Power, Oklo Inc. 인허가 선점 경쟁

**③ 원자력 파운드리 & 핵연료 (장기: 7년+)**
- SMR 상용화 시 수혜받는 실물 제조 독점 레이어
- 수주 즉시 현금 수취(Cost-Plus 계약 구조)
- BWX Technologies, Doosan Enerbility, Centrus Energy 독점적 위치

## 3. 구조적 전환점: 빅테크 PPA가 만드는 새로운 질서

마이크로소프트-쓰리마일섬 재가동 20년 PPA(2023), 구글-카이로스 파워 500MW PPA(2023), 아마존-탈렌에너지 원전 직결 데이터센터(2023) 체결은 단순한 계약이 아닌 **에너지 인프라 산업의 구조적 패러다임 전환**입니다.

- **전력 구매자가 발전소를 직접 기획·발주**하는 수직통합 모델로 진화
- 'Take-or-Pay' PPA → 설계사/파운드리에 선수금 지급 구조 고착
- 탄소국경세(CBAM) + 미국 IRA 인센티브가 원자력 경제성 방어

## 4. 핵심 리스크

* **규제 지연 리스크:** NRC 인허가 평균 소요기간 5~10년. 정치적 환경 변화에 민감
* **비용 초과 리스크:** 대형 원전 대비 SMR의 실제 $/kWh 경쟁력 검증 미완료
* **핵연료 공급망:** HALEU 농축 시설 용량 부족 → 상용화 병목
* **빅테크 전략 선회:** 재생에너지 기술 돌파 시 원전 PPA 수요 감소 가능성

## 5. 투자 전략: 밸류체인 레이어별 포지셔닝

현재 가장 확실한 단기 수혜는 **가스터빈 파운드리(GEV, SMNEY)**이며, 중기 SMR 인허가 레이스에서는 **NuScale(SMR), Oklo(OKLO)** 옵션가치가 핵심입니다. 장기 구조적 독점은 **HALEU 독점 Centrus(LEU)**와 **원자력 파운드리 BWXT·두산에너빌리티**가 차지합니다. 분산투자 관점에서 레이어별 포지션 분배 전략이 권장됩니다."""

cur.execute("""
    UPDATE industry_reports
    SET title = ?, summary = ?
    WHERE id = 5
""", (NEW_TITLE, NEW_SUMMARY))

conn.commit()

# 확인
cur.execute("SELECT id, title, length(summary) FROM industry_reports WHERE id=5")
row = cur.fetchone()
print(f"[OK] Updated report id={row[0]}")
print(f"     Title: {row[1]}")
print(f"     Summary length: {row[2]} chars")

conn.close()
print("Done!")
