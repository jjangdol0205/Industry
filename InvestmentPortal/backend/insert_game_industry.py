# -*- coding: utf-8 -*-
"""
게임 산업 (id=10) DB 삽입 스크립트
기존 산업 양식과 동일한 구조로 생성
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'investment_portal.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ─────────────────────────────────────────────
# 1. industry_reports 삽입 (id=10)
# ─────────────────────────────────────────────
cur.execute("SELECT id FROM industry_reports WHERE id=10")
if cur.fetchone():
    cur.execute("DELETE FROM industry_reports WHERE id=10")
    print("[Reset] 기존 id=10 삭제")

SUMMARY = """## 1. 게임 산업: AI·클라우드가 재편하는 엔터테인먼트의 미래

게임 산업은 2024년 기준 글로벌 시장 규모 약 2,200억 달러로, 영화·음악 산업을 합친 것보다 크며 가장 빠르게 성장하는 엔터테인먼트 섹터입니다. AI 생성형 콘텐츠, 클라우드 게이밍, 게임 엔진의 산업 확장, 모바일 게임의 글로벌 보급이 구조적 성장 동인으로 작용하고 있습니다.

게임 산업의 핵심 특징은 **IP(지식재산권) 기반의 네트워크 효과**입니다. 한번 확립된 IP와 플레이어 커뮤니티는 강력한 경제적 해자를 형성하며, 라이브 서비스(Live Service) 모델로의 전환이 반복 구매 → 구독·인게임 결제 구조로 수익성을 높이고 있습니다.

## 2. 핵심 밸류체인: 4개 레이어 구조

**① 퍼블리셔 & 스튜디오 (AAA 타이틀)**
대형 IP를 보유하고 콘텐츠를 직접 개발·배급하는 기업. Microsoft(Xbox·Activision·Bethesda), Sony(PlayStation·Naughty Dog·Bungie), EA(FIFA·Battlefield), Take-Two(GTA·NBA 2K), Ubisoft, Capcom, Konami가 대표적. GTA 6 출시(2025년)가 사이클 전환의 핵심.

**② 모바일 & 소셜 게임**
스마트폰 보급으로 가장 큰 시장(전체 게임 시장의 50%+). Tencent·NetEase(중국 1·2위), Zynga(Take-Two 편입), King(MS 편입)이 선두. 한국의 넥슨·엔씨소프트·넷마블·크래프톤이 글로벌 IP 확장 중. 하이퍼캐주얼 → 미드코어 전환이 ARPU 상승 동인.

**③ 플랫폼 & 배급 (Distribution)**
게임이 유통되는 마켓플레이스. Valve(Steam·75% PC 점유율), Epic Games Store, Sony PlayStation Store, Xbox Game Pass, Apple App Store·Google Play가 플랫폼 게이트키퍼. 구독 모델(Game Pass·PS Plus) 가입자 확대가 핵심 지표.

**④ 게임 엔진 & 인프라 (Tech Stack)**
Unity·Unreal(Epic)이 전체 모바일·인디·AAA 게임의 80%+를 커버. AI 기반 게임 개발 도구(NPC 생성, 자동 레벨 디자인)가 개발비 절감의 핵심. NVIDIA ACE(AI 캐릭터 엔진)가 차세대 NPC 혁신 선도.

## 3. AI가 만드는 게임 산업 혁명

**AI 생성형 콘텐츠**: Procedural Generation + LLM 결합으로 무한한 게임 세계 자동 생성. 개발 인력·비용 30~50% 절감 전망.

**AI NPC**: NVIDIA ACE + LLM 기반 대화형 NPC — 스크립트 없는 자연어 상호작용. 게임 몰입감 혁신.

**클라우드 게이밍**: 5G + 엣지 컴퓨팅으로 스트리밍 게임 현실화. Xbox Cloud Gaming·GeForce NOW·PlayStation Now 가입자 성장. 하드웨어 없는 게임 접근성 확대.

**게임 엔진의 산업 확장**: Unreal Engine이 영화·건축·자동차 시뮬레이션·군사 훈련으로 확장 — 게임을 넘어선 실시간 3D 인프라.

## 4. 시장 규모 & 성장 전망

- **2024년 글로벌 게임 시장**: 약 2,200억 달러
- **2030년 전망**: 약 3,200억 달러 (CAGR 약 7%)
- **모바일 게임**: 전체의 50%+ → 2030년 55% 전망
- **클라우드 게이밍**: 2024년 약 40억 달러 → 2030년 250억+ 달러
- **AI 게임 개발 도구 시장**: 2024년 약 4억 달러 → 2030년 25억 달러

## 5. 핵심 투자 포인트 & 리스크

**기회**: GTA 6 출시(2025)로 콘솔·PC 게임 사이클 반등 / AI 개발 도구로 인디 게임 폭발적 성장 / 구독 모델(Game Pass·PS Plus) 가입자 확대 / 중국 규제 완화 시 Tencent·NetEase 반등

**리스크**: 대작 타이틀 출시 지연·플롭 리스크 / 중국 규제 불확실성 / 애플·구글 앱스토어 30% 수수료 분쟁 / 게임 산업 구조조정(대규모 해고 지속) / AI로 인한 개발자 수요 감소"""

cur.execute("""
    INSERT INTO industry_reports (id, title, summary, file_path, tag)
    VALUES (10, '게임 산업 밸류체인 심층분석', ?, '10. 게임/게임산업.pdf', '게임')
""", (SUMMARY,))
print("[OK] industry_reports id=10 삽입")

# ─────────────────────────────────────────────
# 2. value_chain_nodes 삽입
# ─────────────────────────────────────────────
cur.execute("DELETE FROM value_chain_nodes WHERE industry_id=10")

nodes = [
    (10, '퍼블리셔 & AAA 스튜디오',   'GTA·Call of Duty·FIFA 등 대형 IP를 보유하고 개발·배급하는 메이저 게임사.'),
    (10, '모바일 & 글로벌 게임사',     '스마트폰 기반 게임 + 한국·중국 글로벌 IP 보유 퍼블리셔.'),
    (10, '플랫폼 & 배급 (Distribution)', 'PC·콘솔·모바일 마켓플레이스. 구독 모델로 전환 중인 게임 유통 플랫폼.'),
    (10, '게임 엔진 & AI 인프라',      'Unreal·Unity 등 게임 개발 플랫폼 및 AI NPC·생성형 콘텐츠 기술.'),
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
cur.execute("DELETE FROM companies WHERE industry_id=10")

companies = [
    # ── 퍼블리셔 & AAA 스튜디오 ──
    (10, '퍼블리셔 & AAA 스튜디오',
     'Microsoft (Xbox)', 'MSFT',
     'Xbox·Activision·Blizzard·Bethesda 통합. Call of Duty·Diablo·Elder Scrolls IP + Game Pass 구독 4,500만+ 가입자.',
     'GTA 6 이후 AAA 사이클 수혜. Game Pass 구독 성장이 반복 수익 구조 강화. Copilot AI 게임 개발 도구 통합.',
     1),
    (10, '퍼블리셔 & AAA 스튜디오',
     'Take-Two Interactive', 'TTWO',
     'GTA(Rockstar)·NBA 2K·BioShock·Borderlands 대형 IP. GTA 6(2025) 출시가 역사적 수익 이벤트 전망.',
     'GTA 6 출시 후 GTA 온라인 생태계 재활성화. Zynga 모바일 사업부와 콘솔 IP 시너지.',
     2),
    (10, '퍼블리셔 & AAA 스튜디오',
     'Electronic Arts', 'EA',
     'EA Sports FC(前FIFA)·Battlefield·The Sims·Apex Legends. 스포츠 게임 글로벌 1위, 라이브 서비스 수익 50%+.',
     'EA Sports FC 구독 서비스 전환. AI 기반 게임 개발로 비용 절감. 모바일 스포츠 게임 확장.',
     3),
    (10, '퍼블리셔 & AAA 스튜디오',
     'Sony Group', 'SONY',
     'PlayStation 5·Sony 1st-party 스튜디오(Naughty Dog·Insomniac·Bungie). PS Plus 프리미엄 가입자 5,000만+.',
     'PS5 소프트웨어 사이클 성숙기. PC·모바일 멀티플랫폼 전환으로 IP 수익 극대화.',
     4),
    (10, '퍼블리셔 & AAA 스튜디오',
     'Capcom', '9697.T',
     'Monster Hunter·Resident Evil·Street Fighter·Devil May Cry. 멀티플랫폼 전략으로 높은 수익성.',
     'Monster Hunter Wilds(2025) 출시 — 시리즈 사상 최대 기대작. RE 엔진 기반 지속 신작 출시.',
     5),

    # ── 모바일 & 글로벌 게임사 ──
    (10, '모바일 & 글로벌 게임사',
     'Tencent', '0700.HK',
     '글로벌 최대 게임사(매출 기준). Honor of Kings·PUBG Mobile·League of Legends(Riot 지분). Supercell·Epic 지분 보유.',
     '중국 게임 규제 완화 수혜. 글로벌 게임사 M&A 전략으로 IP 다각화. 클라우드 게이밍·AI NPC 투자.',
     6),
    (10, '모바일 & 글로벌 게임사',
     'NetEase', 'NTES',
     '블리자드 중국 파트너(복귀). 오버워치·디아블로 중국 배급 재개. 자체 IP Naraka: Bladepoint 글로벌 성장.',
     '블리자드 파트너십 재개로 안정적 수익 복귀. 해외 시장 자체 IP 확장 가속.',
     7),
    (10, '모바일 & 글로벌 게임사',
     'Krafton', '259960.KS',
     'PUBG 개발사 — 배틀그라운드 PC·모바일 글로벌 1위. 인도 BGMI, 중동·동남아 강세.',
     'PUBG 신규 모드·콘텐츠로 라이브 서비스 유지. 신작 다크앤다커 모바일 + 딥다이브 글로벌 출시.',
     8),
    (10, '모바일 & 글로벌 게임사',
     'Nexon', '3659.T',
     '던전앤파이터·메이플스토리 IP. 중국 던파 모바일이 단일 타이틀 최대 매출. 일본 상장.',
     '던전앤파이터 모바일 글로벌 확장. 메이플스토리 유니버스(블록체인·Web3) 생태계 구축.',
     9),

    # ── 플랫폼 & 배급 ──
    (10, '플랫폼 & 배급 (Distribution)',
     'Apple', 'AAPL',
     'App Store — 모바일 게임 최대 유통 플랫폼(30% 수수료). Apple Arcade 구독 + Vision Pro 공간 게임.',
     'Vision Pro 기반 몰입형 게임 플랫폼 확대. 애플 수수료 규제 변화 리스크 관리 필요.',
     10),
    (10, '플랫폼 & 배급 (Distribution)',
     'Alphabet (Google)', 'GOOGL',
     'Google Play Store — Android 게임 1위 유통망. YouTube Gaming·Google Stadia(종료) 경험 기반 클라우드 재도전.',
     'YouTube Gaming 광고 수익 성장. Android 생태계에서 게임 구독 서비스 확장 가능성.',
     11),

    # ── 게임 엔진 & AI 인프라 ──
    (10, '게임 엔진 & AI 인프라',
     'NVIDIA', 'NVDA',
     'GeForce GPU 게임 시장 80%+ 점유. DLSS·RTX·ACE(AI NPC 엔진) — 게임 AI 인프라 선도.',
     'NVIDIA ACE로 AI NPC 표준 확립. GeForce NOW 클라우드 게이밍 성장. 게임 개발용 Omniverse 확산.',
     12),
    (10, '게임 엔진 & AI 인프라',
     'Unity Software', 'U',
     '모바일·인디 게임 엔진 70%+ 점유. 게임 광고 네트워크(ironSource 통합). 런타임 수수료 논란 후 정책 변경.',
     '게임 광고 플랫폼 수익 안정화. AI 게임 개발 도구(Sentis·Muse) 확장. 에디터 유료화 전략.',
     13),
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
print("\n✅ 게임 산업 (id=10) 삽입 완료!")
