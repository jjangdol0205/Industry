# -*- coding: utf-8 -*-
"""
엔터테인먼트 산업 (id=11) DB 삽입 스크립트
기존 산업 양식과 동일한 구조로 생성
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'investment_portal.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ─────────────────────────────────────────────
# 1. industry_reports 삽입 (id=11)
# ─────────────────────────────────────────────
cur.execute("SELECT id FROM industry_reports WHERE id=11")
if cur.fetchone():
    cur.execute("DELETE FROM industry_reports WHERE id=11")
    print("[Reset] 기존 id=11 삭제")

SUMMARY = """## 1. 엔터테인먼트 산업: 스트리밍·AI·한류가 재편하는 글로벌 콘텐츠 시장

엔터테인먼트 산업은 2024년 기준 글로벌 시장 규모 약 2조 5천억 달러로, 스트리밍 혁명과 한류(K-Content)의 글로벌 확산, AI 기반 콘텐츠 제작 혁신이 산업 구조를 근본적으로 변화시키고 있습니다. 선형 TV(케이블·방송)에서 OTT 스트리밍으로의 급격한 이동과 함께, 콘텐츠 IP의 전방위적 수익화(영화→시리즈→테마파크→머천다이즈→게임)가 핵심 비즈니스 모델로 부상했습니다.

## 2. 핵심 밸류체인: 4개 레이어 구조

**① 스트리밍 & OTT 플랫폼**
구독 기반 반복 수익 모델의 핵심. Netflix가 글로벌 가입자 3억 명으로 1위. Disney+·Hulu·ESPN+의 번들 전략, Amazon Prime Video, Apple TV+가 경쟁. 광고 지원 구독 티어(AVOD) 확대로 수익성 개선 중. 한국에서는 웨이브·티빙·시즌이 경쟁.

**② 스튜디오 & 콘텐츠 IP**
콘텐츠를 직접 제작하고 IP를 보유하는 핵심 레이어. Disney(Marvel·Star Wars·Pixar), Warner Bros. Discovery, Paramount, NBCUniversal이 할리우드 메이저. SM·HYBE·JYP·YG가 K-Pop IP 글로벌 확산. 웹툰·웹소설 IP의 영상화가 한국 콘텐츠 경쟁력의 원천.

**③ 음악 & 라이브 엔터테인먼트**
스트리밍(Spotify·Apple Music)으로 음악 시장 부활. Universal Music Group·Sony Music·Warner Music이 글로벌 3대 메이저 레이블. 라이브 이벤트(콘서트·페스티벌)는 COVID 이후 역대 최대 수요. Ticketmaster(Live Nation)가 티켓팅 독점.

**④ 미디어 & 광고 (전통→디지털 전환)**
YouTube·Meta·TikTok이 디지털 광고 기반 엔터테인먼트 소비를 주도. 전통 미디어(Disney·Comcast·Warner)는 스트리밍 전환 중. 숏폼 콘텐츠(Reels·Shorts·TikTok)가 시청 시간 잠식.

## 3. 한류(K-Content)의 구조적 성장

BTS·블랙핑크·아이브 등 K-Pop 아티스트의 글로벌 팬덤은 단순 음악 소비를 넘어 MD·팬미팅·IP 라이센싱으로 수익 다각화. Netflix 오징어게임 시즌2, 더 글로리 등 K-드라마의 글로벌 흥행이 한국 콘텐츠의 위상을 공고히 했습니다. HYBE의 멀티 레이블 전략과 위버스 플랫폼은 K-Pop IP 생태계의 새로운 표준.

## 4. AI가 바꾸는 콘텐츠 산업

**AI 기반 콘텐츠 제작**: Sora·Runway·Pika 등 AI 영상 생성 도구로 영상 제작 비용 30~60% 절감. 할리우드 작가·배우 파업의 핵심 쟁점.

**AI 더빙·자막**: 넷플릭스·아마존이 AI 자동 더빙으로 콘텐츠 현지화 비용 절감 — K-드라마 글로벌 확산 가속.

**개인화 추천 알고리즘**: 넷플릭스의 80%+ 시청이 알고리즘 추천 기반 → 구독 유지율(Retention) 핵심.

## 5. 시장 규모 & 성장 전망

- **글로벌 스트리밍 시장**: 2024년 약 1,140억 달러 → 2030년 약 2,500억 달러 (CAGR 14%)
- **음악 스트리밍**: 2024년 약 280억 달러 → 2030년 약 450억 달러
- **K-Pop 글로벌 시장**: 2024년 약 130억 달러 → 2030년 약 400억 달러
- **라이브 엔터**: 2024년 약 320억 달러 (코로나 이전 최고치 갱신)

## 6. 핵심 리스크

- **콘텐츠 비용 인플레이션**: AAA급 시리즈 제작비 1편당 100~200억원 → 수익성 압박
- **구독 포화**: 미국 가구당 평균 4.5개 OTT 구독 → 해지(Churn) 증가
- **광고 경기 민감도**: 광고 기반 수익 모델은 경기 침체에 취약
- **AI 저작권 분쟁**: 배우·작가 조합과의 갈등 지속"""

cur.execute("""
    INSERT INTO industry_reports (id, title, summary, file_path, tag)
    VALUES (11, '엔터테인먼트 산업 밸류체인 심층분석', ?, '11. 엔터테인먼트/엔터테인먼트.pdf', '엔터테인먼트')
""", (SUMMARY,))
print("[OK] industry_reports id=11 삽입")

# ─────────────────────────────────────────────
# 2. value_chain_nodes 삽입
# ─────────────────────────────────────────────
cur.execute("DELETE FROM value_chain_nodes WHERE industry_id=11")

nodes = [
    (11, '스트리밍 & OTT 플랫폼',        '구독 기반 글로벌 OTT 서비스. 가입자 수·ARPU·콘텐츠 투자가 핵심 지표.'),
    (11, '스튜디오 & 콘텐츠 IP',          '영화·시리즈·K-Pop IP를 제작·보유하는 콘텐츠 기업. IP의 멀티 플랫폼 수익화가 핵심.'),
    (11, '음악 & 라이브 엔터테인먼트',     '음악 스트리밍·레이블·공연·티켓팅. 라이브 이벤트 반등 및 K-Pop 글로벌 팬덤 수혜.'),
    (11, '미디어 & 디지털 광고 플랫폼',   '숏폼·유튜브·SNS 기반 광고 수익 엔터테인먼트. 전통 미디어의 디지털 전환.'),
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
cur.execute("DELETE FROM companies WHERE industry_id=11")

companies = [
    # ── 스트리밍 & OTT ──
    (11, '스트리밍 & OTT 플랫폼',
     'Netflix', 'NFLX',
     '글로벌 OTT 1위 — 가입자 3억 명+. 광고 지원 티어(AVOD) 도입으로 수익 다각화. 오징어게임 등 글로벌 오리지널 IP 확보.',
     '광고 티어 ARPU 성장 + 계정 공유 유료화 완료로 수익성 개선. AI 더빙·자막으로 글로벌 현지화 비용 절감.',
     1),
    (11, '스트리밍 & OTT 플랫폼',
     'Walt Disney', 'DIS',
     'Disney+·Hulu·ESPN+ 번들. Marvel·Star Wars·Pixar IP 보유. 테마파크·크루즈 라인 연계 수익화.',
     'Disney+ 흑자 전환 완료(2024). ESPN 스포츠 스트리밍 독립화. 테마파크 수요 견조로 복합 수익 구조 강화.',
     2),
    (11, '스트리밍 & OTT 플랫폼',
     'Amazon', 'AMZN',
     'Prime Video — Prime 멤버십 번들. Thursday Night Football·반지의 제왕 오리지널 제작. MGM 스튜디오 보유.',
     'Prime Video 광고 티어 도입. AWS 인프라와 AI 콘텐츠 추천 시너지. Twitch 라이브 스트리밍 게임 연계.',
     3),

    # ── 스튜디오 & 콘텐츠 IP ──
    (11, '스튜디오 & 콘텐츠 IP',
     'Warner Bros. Discovery', 'WBD',
     'HBO·Max·CNN·Warner Bros. 스튜디오. DC·Harry Potter·Game of Thrones IP. Max 글로벌 가입자 1억+.',
     'Max 글로벌 확장 + 스포츠 중계권 강화. DC Universe 리빌드(제임스 건 감독)로 마블과 재경쟁.',
     4),
    (11, '스튜디오 & 콘텐츠 IP',
     'HYBE', '352820.KS',
     'BTS·세븐틴·뉴진스 등 멀티 레이블. 위버스 팬 플랫폼 글로벌 MAU 1,000만+. 아티스트 IP 360도 수익화.',
     'BTS 완전체 복귀(2025) 대기 — 역대 최대 투어 예상. 위버스 플랫폼 B2B 확장. 미국·일본 현지 레이블 성장.',
     5),
    (11, '스튜디오 & 콘텐츠 IP',
     'SM Entertainment', '041510.KS',
     'EXO·aespa·NCT 등 글로벌 K-Pop IP. 카카오엔터 지분 연계. SM 3.0 멀티 프로덕션 센터 전략.',
     'aespa 글로벌 팬덤 확대. SM 유니버스(SM 세계관) 웹툰·영화 확장. 카카오엔터와 IP 시너지.',
     6),
    (11, '스튜디오 & 콘텐츠 IP',
     'JYP Entertainment', '035900.KS',
     'TWICE·Stray Kids·ITZY·NiziU. 일본 NiziU·현지 레이블 성공 사례. 북미·동남아 레이블 확장 중.',
     '글로벌 오디션 기반 현지 아티스트 발굴. K-Pop 비즈니스 모델의 현지화 표준 구축.',
     7),

    # ── 음악 & 라이브 ──
    (11, '음악 & 라이브 엔터테인먼트',
     'Spotify', 'SPOT',
     '글로벌 음악 스트리밍 1위 — MAU 6억 8천만+. 팟캐스트·오디오북 확장. 아티스트 직접 배급 플랫폼.',
     'AI DJ·AI 플레이리스트로 개인화 강화. 팟캐스트 수익화 가속. 유료 구독자 3억 돌파 로드맵.',
     8),
    (11, '음악 & 라이브 엔터테인먼트',
     'Live Nation Entertainment', 'LYV',
     'Ticketmaster 독점 + 전 세계 공연 기획. 라이브 이벤트 역대 최대 수요 수혜. 콘서트 경제 독점 플랫폼.',
     '콘서트 티켓 수요 사상 최대 지속. 동적 가격제(Dynamic Pricing)로 ARPU 상승. 반독점 소송 리스크 관리.',
     9),
    (11, '음악 & 라이브 엔터테인먼트',
     'Universal Music Group', 'UMG.AS',
     '글로벌 음악 레이블 1위 — Taylor Swift·Drake·BTS 등 보유. 스트리밍 로열티 최대 수혜사.',
     'AI 기반 음악 생성 저작권 수익화. 스트리밍 단가 인상 협상력 보유. K-Pop·라틴 팝 레이블 확장.',
     10),

    # ── 미디어 & 디지털 광고 ──
    (11, '미디어 & 디지털 광고 플랫폼',
     'Alphabet (YouTube)', 'GOOGL',
     'YouTube — 글로벌 최대 동영상 플랫폼. 광고 연 400억 달러+. YouTube Shorts·Music·Premium 다각화.',
     'Shorts 광고 수익 분배 확대. YouTube TV 라이브 스포츠 강화. AI 기반 광고 타겟팅 개선.',
     11),
    (11, '미디어 & 디지털 광고 플랫폼',
     'Meta Platforms', 'META',
     'Facebook·Instagram·Reels — 숏폼 콘텐츠 플랫폼. 크리에이터 이코노미 + AI 광고 최적화.',
     'Reels 수익화 가속. AI 광고 ROAS(광고 수익률) 업계 최고 수준. 스레드 성장으로 트위터 대안 자리매김.',
     12),
    (11, '미디어 & 디지털 광고 플랫폼',
     'Comcast', 'CMCSA',
     'NBC·Universal·Sky·Peacock OTT. 케이블 인터넷 인프라 + 미디어 컨버전스. 올림픽 중계권 보유.',
     'Peacock 스포츠 중계 + 올림픽으로 가입자 성장. 케이블 인터넷 수익 안정성이 미디어 투자 재원.',
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
print("\n✅ 엔터테인먼트 산업 (id=11) 삽입 완료!")
