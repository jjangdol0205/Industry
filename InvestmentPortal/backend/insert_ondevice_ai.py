# -*- coding: utf-8 -*-
"""
온디바이스 AI 산업 (id=8) DB 삽입 스크립트
기존 산업 양식과 동일한 구조로 생성
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), 'investment_portal.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ─────────────────────────────────────────────
# 1. industry_reports 삽입 (id=8)
# ─────────────────────────────────────────────
cur.execute("SELECT id FROM industry_reports WHERE id=8")
if cur.fetchone():
    cur.execute("DELETE FROM industry_reports WHERE id=8")
    print("[Reset] 기존 id=8 삭제")

SUMMARY = """## 1. 온디바이스 AI 혁명: 클라우드에서 엣지로

생성형 AI의 무게중심이 빠르게 이동하고 있습니다. 수십억 개의 파라미터를 클라우드 서버에서 처리하던 시대에서, **기기 자체(On-Device)**에서 AI 추론(Inference)이 이루어지는 새로운 패러다임이 열리고 있습니다. 스마트폰, 노트북, XR 헤드셋, 자동차, IoT 기기 등 수십억 개의 엔드포인트가 AI 컴퓨팅 노드로 전환되고 있습니다.

이 전환을 이끄는 핵심 동인은 3가지입니다:

**① 프라이버시 & 보안**: 의료 데이터, 금융 정보, 개인 대화 등 민감한 데이터가 서버로 전송되지 않고 기기 내에서 처리됨

**② 레이턴시 & 실시간성**: 클라우드 왕복 시간 없이 밀리초 단위 응답 — AR/VR, 자율주행, 산업용 로봇에서 필수

**③ 비용 & 연결성**: 추론 1회당 API 비용 없음, 오프라인 환경에서도 완전 동작

## 2. 핵심 밸류체인: 4개 레이어 구조

**① AI 프로세서 (NPU/SoC) — 실리콘 경쟁**
온디바이스 AI의 핵심 인프라. Neural Processing Unit(NPU)을 내장한 SoC가 스마트폰·노트북·자동차에 탑재됨. Qualcomm Snapdragon 8 Elite(45 TOPS), Apple A18/M4(38 TOPS), MediaTek Dimensity 9400이 대표적. 차세대 Windows on Arm(Copilot+) PC 시장에서 Qualcomm이 Intel·AMD를 압도.

**② 소프트웨어 & AI 모델 최적화**
대형 LLM을 엣지 기기에서 구동하려면 모델 압축이 필수. 양자화(Quantization), 가지치기(Pruning), 지식 증류(Knowledge Distillation) 기술로 70B → 7B → 1B 파라미터로 경량화. Qualcomm AI Hub, Apple Core ML, Google MediaPipe가 생태계 구축.

**③ 기기 제조사 (OEM 플랫폼 보유사)**
삼성 Galaxy AI, Apple Intelligence, Google Gemini Nano 탑재 Pixel 등 온디바이스 AI를 차별화 포인트로 활용. 프리미엄 스마트폰 업그레이드 사이클 촉진 — 2026~2028년 교체 수요의 핵심 트리거.

**④ XR & 차세대 폼팩터**
Meta Quest, Apple Vision Pro, Samsung XR 헤드셋은 온디바이스 AI 없이는 작동 불가능한 새로운 기기 카테고리. 공간 컴퓨팅 + 실시간 AI 처리의 결합이 XR 생태계의 킬러 앱.

## 3. 시장 규모 & 성장 전망

- **2024년**: 온디바이스 AI 스마트폰 출하량 약 4억대 (전체의 30%)
- **2027년**: 전체 스마트폰의 60%+ NPU 탑재 전망 (IDC)
- **2025~2030 CAGR**: 온디바이스 AI 반도체 시장 연 28% 성장 (Gartner)
- **Copilot+ PC**: 2025년 전체 PC 출하의 20%→ 2027년 50% 전망
- **XR 기기**: 2025년 출하 2천만대 → 2030년 1억대 (Meta·Apple·삼성 3강)

## 4. 구조적 투자 포인트

**실리콘 전쟁(Silicon War)**: NPU 성능이 프리미엄 기기 교체 사이클의 핵심 변수. Qualcomm vs Apple vs MediaTek vs Intel의 아키텍처 경쟁.

**AI PC 업그레이드 사이클**: 기업용 PC 교체 주기(4~5년)와 Copilot+ 요구사양이 맞물려 2026~2028년 대규모 수요 촉발.

**엣지 AI 데이터센터화**: 스마트폰 10억대 = 분산형 AI 추론 클러스터. 클라우드 API 비용 절감 → 앱 개발사 수익성 개선.

## 5. 핵심 리스크

- **모델 크기 한계**: 현 엣지 하드웨어로 처리 가능한 모델 크기의 물리적 상한
- **배터리 제약**: 고강도 NPU 연산은 발열 및 배터리 소모 급증
- **생태계 파편화**: Qualcomm/Apple/Google이 각자 독자 SDK → 개발자 부담
- **클라우드 하이브리드 의존**: 완전 온디바이스 구현까지 클라우드 보조 필요"""

cur.execute("""
    INSERT INTO industry_reports (id, title, summary, file_path, tag)
    VALUES (8, '온디바이스 AI 산업 밸류체인 심층분석', ?, '8. 온디바이스ai/온디바이스ai 산업.pdf', '온디바이스AI')
""", (SUMMARY,))
print("[OK] industry_reports id=8 삽입")

# ─────────────────────────────────────────────
# 2. value_chain_nodes 삽입
# ─────────────────────────────────────────────
cur.execute("DELETE FROM value_chain_nodes WHERE industry_id=8")

nodes = [
    (8, 'AI 프로세서 & NPU (실리콘 레이어)', 'NPU 내장 SoC를 설계·생산하는 팹리스/IDM. 온디바이스 AI의 핵심 인프라.'),
    (8, '소프트웨어 & AI 최적화 플랫폼', 'AI 모델 경량화(양자화·증류), SDK, AI Hub 등 소프트웨어 생태계 구축.'),
    (8, '기기 제조사 & OEM 플랫폼', '온디바이스 AI를 차별화 무기로 탑재하는 스마트폰·노트북·웨어러블 OEM.'),
    (8, 'XR & 차세대 폼팩터', '공간 컴퓨팅·AR·VR 기기. 온디바이스 AI 없이는 구동 불가능한 신규 카테고리.'),
]

node_ids = {}
for industry_id, node_name, desc in nodes:
    cur.execute(
        "INSERT INTO value_chain_nodes (industry_id, node_name, description) VALUES (?,?,?)",
        (industry_id, node_name, desc)
    )
    nid = cur.lastrowid
    node_ids[node_name] = nid
    print(f"[OK] node id={nid}: {node_name}")

# ─────────────────────────────────────────────
# 3. companies 삽입
# ─────────────────────────────────────────────
cur.execute("DELETE FROM companies WHERE industry_id=8")

companies = [
    # (industry_id, node_name, name, ticker, role_description, future_growth, display_order)
    (8, 'AI 프로세서 & NPU (실리콘 레이어)',
     'Qualcomm', 'QCOM',
     'Snapdragon 8 Elite(45 TOPS NPU) 탑재 스마트폰·Copilot+ PC 플랫폼 주도. 온디바이스 AI의 실리콘 표준.',
     'AI Hub 생태계 확장, 자동차·XR 칩 사업 다변화. Snapdragon X Elite로 PC 시장 공략 가속.',
     1),
    (8, 'AI 프로세서 & NPU (실리콘 레이어)',
     'Apple', 'AAPL',
     'A18 Bionic·M4 칩의 Neural Engine으로 Apple Intelligence 구동. 실리콘-소프트웨어-서비스 수직통합.',
     '애플 인텔리전스 기반 아이폰 업그레이드 사이클 촉진. Vision Pro 2세대 AI 강화.',
     2),
    (8, 'AI 프로세서 & NPU (실리콘 레이어)',
     'MediaTek', '2454.TW',
     'Dimensity 9400(35 TOPS) — 삼성·중화권 플래그십 탑재. 미드레인지 온디바이스 AI 대중화 선도.',
     '중저가 스마트폰 AI 보급 → 총 TAM 급속 확대. 자동차용 AI 칩 Dimensity Auto 확장.',
     3),
    (8, 'AI 프로세서 & NPU (실리콘 레이어)',
     'Intel', 'INTC',
     'Core Ultra 2(Lunar Lake) NPU 47 TOPS. Copilot+ PC 요구사양 충족으로 PC AI 시장 재진입 시도.',
     '아키텍처 혁신(18A 공정)으로 Qualcomm 추격. 파운드리 분리 전략의 성공 여부가 핵심 변수.',
     4),
    (8, '소프트웨어 & AI 최적화 플랫폼',
     'Alphabet (Google)', 'GOOGL',
     'Gemini Nano 온디바이스 모델, MediaPipe·TensorFlow Lite로 Android AI 생태계 구축. Pixel AI 직접 운영.',
     'Android 기기 20억대 생태계로 온디바이스 AI 표준화. TPU·Axion 칩으로 하드웨어-소프트웨어 통합 강화.',
     5),
    (8, '소프트웨어 & AI 최적화 플랫폼',
     'Microsoft', 'MSFT',
     'Copilot+ PC 플랫폼 정의. Windows AI API로 온디바이스 AI 앱 생태계 주도. Azure Edge AI 서비스.',
     'Phi-3/4 경량 모델로 엣지 AI 표준 구축. Copilot+ PC 기업 교체 사이클 수혜.',
     6),
    (8, '기기 제조사 & OEM 플랫폼',
     'Samsung Electronics', '005930.KS',
     '갤럭시 AI(Galaxy AI) 탑재 플래그십. Exynos 2500 NPU + 삼성 파운드리 수직통합 전략.',
     '갤럭시 AI 기능 확대로 S25 시리즈 판매 촉진. XR 헤드셋(Galaxy XR) 2025년 출시 예정.',
     7),
    (8, '기기 제조사 & OEM 플랫폼',
     'Lenovo', '0992.HK',
     '세계 최대 PC 제조사. Copilot+ PC 라인업(ThinkPad X1 Fold AI 등) 가장 빠른 전환.',
     'AI PC 전환 사이클에서 B2B 기업 교체 수요 수혜. AI 에지 서버(ThinkEdge) 사업 병행 성장.',
     8),
    (8, 'XR & 차세대 폼팩터',
     'Meta Platforms', 'META',
     'Quest 3/4 — 가장 대중적 XR 플랫폼. 온디바이스 AI로 공간 인식·번역·아바타 실시간 처리.',
     '레이밴 스마트 안경 + AI 어시스턴트로 스마트폰 이후 폼팩터 선점. 2030년 XR 1위 목표.',
     9),
    (8, 'XR & 차세대 폼팩터',
     'Snap', 'SNAP',
     'Spectacles AR 글라스 5세대 — 온디바이스 AR AI 처리. 개발자 생태계 구축로 AR OS 플랫폼 지향.',
     'AR 글라스 대중화 초기 시장 개척자. 소셜 AR과 온디바이스 AI 결합이 차별화 포인트.',
     10),
]

for ind_id, node_name, name, ticker, role, growth, order in companies:
    node_id = node_ids.get(node_name)
    cur.execute("""
        INSERT INTO companies (industry_id, value_chain_node_id, name, ticker, role_description, future_growth, display_order)
        VALUES (?,?,?,?,?,?,?)
    """, (ind_id, node_id, name, ticker, role, growth, order))
    print(f"[OK] company: {name} ({ticker})")

conn.commit()
conn.close()
print("\n✅ 온디바이스 AI 산업 (id=8) 삽입 완료!")
