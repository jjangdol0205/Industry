# -*- coding: utf-8 -*-
"""
반도체 산업 (id=9) DB 삽입 스크립트
기존 산업 양식과 동일한 구조로 생성
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'investment_portal.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ─────────────────────────────────────────────
# 1. industry_reports 삽입 (id=9)
# ─────────────────────────────────────────────
cur.execute("SELECT id FROM industry_reports WHERE id=9")
if cur.fetchone():
    cur.execute("DELETE FROM industry_reports WHERE id=9")
    print("[Reset] 기존 id=9 삭제")

SUMMARY = """## 1. 반도체 산업: AI 시대의 석유

반도체는 현대 문명의 핵심 인프라입니다. AI, 자율주행, 클라우드, 스마트폰, 전기차까지 — 모든 첨단 산업은 반도체 없이는 존재할 수 없습니다. 특히 생성형 AI 폭발이 촉발한 **고성능 AI 반도체** 수요는 산업의 구조적 성장 동인으로 자리잡았습니다.

반도체 산업의 핵심 특징은 **밸류체인의 극단적 분업화**입니다. 설계(Fabless) → 생산(Foundry) → 후공정(OSAT) → 장비(Equipment) → 소재(Materials)로 이어지는 복잡한 공급망은 각 영역에서 독점적 지위를 가진 기업들이 높은 경제적 해자를 형성합니다.

## 2. 핵심 밸류체인: 5개 레이어 구조

**① 설계 (Fabless) — AI 칩 전쟁의 최전선**
생산 시설 없이 설계만 담당. NVIDIA의 H100/B100 GPU는 AI 데이터센터의 표준. AMD MI300X가 추격. Qualcomm·Apple은 스마트폰·PC용 칩 설계. Broadcom·Marvell은 하이퍼스케일러 맞춤 ASIC 설계로 급성장.

**② 파운드리 (Foundry) — 제조 독점**
TSMC가 최첨단 공정(3nm·2nm) 독점. 삼성 파운드리가 2위. Intel Foundry Services(IFS)가 18A 공정으로 재진입 시도. TSMC의 CoWoS HBM 패키징 용량이 AI 반도체 공급 병목의 핵심.

**③ 메모리 (Memory) — AI가 바꾸는 DRAM 패러다임**
HBM(High Bandwidth Memory)이 AI GPU 필수 부품으로 부상. SK하이닉스가 HBM3E 공급에서 NVIDIA와 독점 파트너십. 삼성전자·마이크론이 추격. NAND는 데이터센터 스토리지 수요 지속.

**④ 반도체 장비 (Equipment) — 기술 독점 해자**
ASML의 EUV 노광장치는 전 세계 유일 공급사 — 대체 불가능한 독점. AMAT·Lam Research·KLA가 각각 증착·식각·검사 장비 과점. 미국의 대중국 장비 수출규제로 서방 장비사 수혜.

**⑤ 소재 & 후공정 (Materials & OSAT) — 첨단 패키징 혁명**
AI GPU 성능 한계를 2.5D/3D 패키징으로 극복. 일본 소재사(신에츠, JSR)의 포토레지스트 독점. ASE Group·Amkor가 OSAT 선두. 한국 소부장(동진쎄미켐, SK머티리얼즈) 성장.

## 3. AI가 만드는 구조적 수요 변화

**HBM 수요 폭증**: ChatGPT 등장 이후 AI 서버용 HBM 수요가 연간 +100% 이상 성장. 2024년 HBM 매출 비중: SK하이닉스 35%+, 삼성전자 10%+ → 2026년 50% 목표.

**CoWoS 패키징 병목**: TSMC의 고급 패키징(CoWoS) 용량이 AI GPU 생산을 제약. NVIDIA가 2025년 TSMC CoWoS 용량의 70%+ 선점.

**ASIC 붐**: 구글(TPU), 아마존(Trainium), 메타(MTIA), 마이크로소프트(Maia) 등 빅테크들이 자체 AI 칩 설계 가속. Broadcom·Marvell이 ASIC 설계 수혜.

**지정학적 리스크**: 미-중 반도체 전쟁으로 공급망 재편. CHIPS Act로 미국·일본·유럽 현지화 보조금 지원.

## 4. 시장 규모 & 성장 전망

- **2024년 글로벌 반도체 시장**: 약 6,280억 달러 (WSTS)
- **2030년 전망**: 약 1조 달러 (연 CAGR 8~10%)
- **AI 반도체 (GPU+ASIC+HBM)**: 2024년 약 1,000억 달러 → 2028년 3,000억+ 달러
- **TSMC 수익**: 2024년 약 900억 달러, AI 매출 비중 40%+ (2025년)

## 5. 핵심 투자 포인트 & 리스크

**기회**: AI 인프라 투자 지속 → GPU·HBM·패키징 슈퍼사이클 / CHIPS Act 보조금으로 미국·일본 fab 건설 붐 / 대중국 규제로 서방 장비·소재 기업 독점 강화

**리스크**: 반도체 업황 사이클 (Boom-Bust) / 미-중 무역분쟁 격화 시 공급망 충격 / AI 버블 우려 시 설비투자 급감 / TSMC 지정학 리스크 (대만 리스크)"""

cur.execute("""
    INSERT INTO industry_reports (id, title, summary, file_path, tag)
    VALUES (9, '반도체 산업 밸류체인 심층분석', ?, '9. 반도체/반도체 산업.pdf', '반도체')
""", (SUMMARY,))
print("[OK] industry_reports id=9 삽입")

# ─────────────────────────────────────────────
# 2. value_chain_nodes 삽입
# ─────────────────────────────────────────────
cur.execute("DELETE FROM value_chain_nodes WHERE industry_id=9")

nodes = [
    (9, '설계 (Fabless / IDM)',     'AI GPU·ASIC·모바일 SoC 등 반도체 설계 전문 기업. 생산 없이 IP와 설계 역량이 핵심 해자.'),
    (9, '파운드리 (Foundry)',        '웨이퍼 위탁 생산. TSMC의 최첨단 공정 독점이 AI 반도체 공급망의 핵심 병목.'),
    (9, '메모리 (Memory)',           'DRAM·NAND·HBM. AI GPU 필수 부품 HBM에서 SK하이닉스가 선두.'),
    (9, '반도체 장비 (Equipment)',   'EUV·CVD·Etch·Inspection 장비. ASML EUV 독점 + 대중국 규제 수혜 구조.'),
    (9, '소재 & 후공정 (OSAT)',      '포토레지스트·CMP 슬러리·첨단 패키징(CoWoS·HBM). 일본 소재 독점 + OSAT 성장.'),
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
cur.execute("DELETE FROM companies WHERE industry_id=9")

companies = [
    # (industry_id, node_name, name, ticker, role_description, future_growth, display_order)

    # ── 설계 (Fabless/IDM) ──
    (9, '설계 (Fabless / IDM)',
     'NVIDIA', 'NVDA',
     'H100·B100·B200 AI GPU 시장 독점(80%+). CUDA 생태계가 소프트웨어 해자. 데이터센터 AI 인프라의 사실상 표준.',
     'Blackwell(B200) → Rubin(R100) 로드맵으로 AI GPU 세대교체 가속. NIM·Omniverse 소프트웨어 플랫폼 확장.',
     1),
    (9, '설계 (Fabless / IDM)',
     'AMD', 'AMD',
     'MI300X AI GPU로 NVIDIA 추격. EPYC 서버 CPU에서 Intel 시장 점유율 지속 탈취. 데이터센터 듀얼 공급자.',
     'MI350·MI400 로드맵으로 AI GPU 시장 점유율 15%+ 목표. ZT Systems 인수로 AI 서버 통합.',
     2),
    (9, '설계 (Fabless / IDM)',
     'Broadcom', 'AVGO',
     '구글·메타·애플 등 하이퍼스케일러 맞춤 ASIC 설계 1위. 네트워킹 칩(Tomahawk, Jericho) AI 데이터센터 필수품.',
     'XPU(Custom AI ASIC) 수요 폭증 — 2027년 ASIC 시장 600억 달러 전망. VMware 인수 시너지.',
     3),
    (9, '설계 (Fabless / IDM)',
     'Marvell Technology', 'MRVL',
     '아마존·MS 맞춤 AI ASIC 설계 2위. 5G 기지국 칩 + 데이터센터 광인터커넥트 솔루션.',
     'AI ASIC 비중 2024년 30% → 2026년 60%+ 전망. 맞춤 칩 설계 시장의 구조적 수혜.',
     4),
    (9, '설계 (Fabless / IDM)',
     'Intel', 'INTC',
     'x86 CPU 강자이나 AI 전환기 고전 중. Gaudi3 AI 가속기 + IFS 파운드리 양립 전략. 18A 공정 성공이 관건.',
     '18A 공정(2025년 후반) 성공 시 파운드리 재진입. CHIPS Act 보조금 85억 달러 수령 확정.',
     5),

    # ── 파운드리 ──
    (9, '파운드리 (Foundry)',
     'TSMC', 'TSM',
     '세계 최첨단 파운드리 독점(3nm·2nm). AI GPU의 90%+ 위탁 생산. CoWoS 패키징 용량이 AI 공급 병목.',
     'N2(2nm) 2025년 양산. 미국·일본·유럽 fab 건설로 지정학 리스크 분산. 2026년 A16(1.6nm) 로드맵.',
     6),
    (9, '파운드리 (Foundry)',
     'Samsung Electronics', '005930.KS',
     '파운드리 2위 + HBM3E 양산. GAA(Gate-All-Around) 3nm 공정 가동 중. 온디바이스 AI Exynos 2500.',
     'HBM4 2025년 양산으로 SK하이닉스 추격. 파운드리 수율 개선이 단기 주가 촉매.',
     7),

    # ── 메모리 ──
    (9, '메모리 (Memory)',
     'SK Hynix', '000660.KS',
     'HBM3E 세계 최초 양산 + NVIDIA 독점 공급. D램 시장 점유율 2위. AI 붐의 최대 수혜 메모리 기업.',
     'HBM4(2025), HBM4E(2026) 로드맵. TSMC와 HBM 패키징 협력으로 시너지. 청주 M15X 증설.',
     8),
    (9, '메모리 (Memory)',
     'Micron Technology', 'MU',
     'HBM3E 양산 NVIDIA 공급 개시(2024). NAND TLC → QLC 전환으로 원가 절감. 美 유일 DRAM 기업.',
     'CHIPS Act 보조금 61억 달러 수령. 아이다호·뉴욕 fab 건설로 HBM 생산 확대. 2026년 HBM 점유율 20%+.',
     9),

    # ── 장비 ──
    (9, '반도체 장비 (Equipment)',
     'ASML', 'ASML',
     'EUV 노광장치 세계 유일 공급사 — 대체 불가 독점. 첨단 반도체 생산의 필수 병목. 대중국 수출 금지 수혜.',
     'High-NA EUV(2025년~) 독점 공급으로 독점 심화. TSMC·삼성 fab 확장에 비례 수혜.',
     10),
    (9, '반도체 장비 (Equipment)',
     'Applied Materials', 'AMAT',
     'CVD·PVD·ALD 증착 장비 세계 1위. 첨단 패키징(CoWoS) 장비 수혜. 연간 장비 매출 280억달러+.',
     '3D IC·HBM 패키징 장비 수요 급증. ICAPS(성숙 공정) 사업부로 대중국 일부 물량 유지.',
     11),
    (9, '반도체 장비 (Equipment)',
     'Lam Research', 'LRCX',
     '플라즈마 식각(Etch) + ALD 장비 세계 1위. NAND 레이어 증가에 비례 장비 수요 증가.',
     'NAND 256단→512단 전환이 장비 투자 촉발. 메모리 업황 회복 시 최대 수혜.',
     12),
    (9, '반도체 장비 (Equipment)',
     'KLA Corporation', 'KLAC',
     '웨이퍼 검사(Inspection)·측정(Metrology) 장비 세계 1위 — 수율 관리 필수. 대체재 없는 독점.',
     '공정 복잡도 증가(High-NA EUV·3D패키징)로 검사 장비 수요 구조적 증가.',
     13),

    # ── 소재 & 후공정 ──
    (9, '소재 & 후공정 (OSAT)',
     'ASE Technology', 'ASX',
     '세계 최대 OSAT(후공정 패키징·테스트). CoWoS·SiP 첨단 패키징 수혜. 연간 매출 250억달러+.',
     'AI 반도체 첨단 패키징(CoWoS·HBM 적층) 수요 폭증. 2025~2027년 캐파 2배 확장 계획.',
     14),
    (9, '소재 & 후공정 (OSAT)',
     'Shin-Etsu Chemical', '4063.T',
     '반도체급 실리콘 웨이퍼 세계 1위 + 포토레지스트 주요 공급사. 소재 독점으로 고마진 유지.',
     'EUV 포토레지스트 수요 증가로 고부가 소재 비중 확대. 웨이퍼 200mm→300mm 전환 수혜.',
     15),
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
print("\n✅ 반도체 산업 (id=9) 삽입 완료!")
