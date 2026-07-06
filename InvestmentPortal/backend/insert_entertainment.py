# -*- coding: utf-8 -*-
"""
음악 산업 (id=11) DB 재구성 스크립트
엔터테인먼트(광범위) → 음악 산업(레이블·스트리밍·라이브·굿즈 밸류체인) 전면 교체
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'investment_portal.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ─────────────────────────────────────────────
# 1. 기존 id=11 완전 초기화
# ─────────────────────────────────────────────
cur.execute("SELECT id FROM companies WHERE industry_id=11")
old_ids = [r[0] for r in cur.fetchall()]
if old_ids:
    placeholders = ','.join(['?']*len(old_ids))
    cur.execute(f"DELETE FROM financial_data WHERE company_id IN ({placeholders})", old_ids)
    cur.execute(f"DELETE FROM financial_data_history WHERE company_id IN ({placeholders})", old_ids)
    cur.execute(f"DELETE FROM company_profiles WHERE company_id IN ({placeholders})", old_ids)
    cur.execute("DELETE FROM companies WHERE industry_id=11")
    print(f"[Reset] 기존 id=11 기업 {len(old_ids)}개 + 재무데이터 삭제")

cur.execute("DELETE FROM value_chain_nodes WHERE industry_id=11")
cur.execute("DELETE FROM industry_reports WHERE id=11")
print("[Reset] id=11 industry_reports, value_chain_nodes 삭제")

# ─────────────────────────────────────────────
# 2. industry_reports 재삽입 (id=11) — 음악 산업
# ─────────────────────────────────────────────
SUMMARY = """## 1. 음악 산업: 스트리밍 부활과 K-Pop이 만드는 제2의 황금기

글로벌 음악 시장은 2024년 기준 약 480억 달러 규모로, 스트리밍의 폭발적 성장과 K-Pop 글로벌 팬덤, 라이브 공연 역대 최대 수요가 동시에 맞물리며 역사상 최고 성장 국면에 진입했습니다. 2000년대 초 불법 다운로드로 붕괴됐던 음악 산업은 Spotify가 이끈 스트리밍 혁명으로 완전히 부활했고, 이제는 K-Pop·라틴·아프리카 비트 등 비영어권 음악의 글로벌화가 새로운 성장 동력입니다.

## 2. 핵심 밸류체인: 4개 레이어 구조

**① 음악 레이블 (Major Labels)**
음악 IP를 소유하고 아티스트를 관리하는 핵심 레이어. Universal Music Group(시장점유율 32%)·Sony Music(24%)·Warner Music(18%)이 글로벌 3대 메이저로 전체 스트리밍 로열티의 75%를 수령. 레이블은 마스터 저작권과 퍼블리싱 저작권 양방향으로 수익화. K-Pop에서는 HYBE·SM·JYP·YG가 독자 레이블 생태계를 구축.

**② 스트리밍 & 디지털 배급**
음악 소비의 패러다임을 바꾼 플랫폼. Spotify(MAU 6억 8천만)가 1위, Apple Music·Amazon Music·YouTube Music·Tidal이 경쟁. 스트리밍 수익은 2023년 처음으로 음악 총 매출의 70% 돌파. 아티스트 직접 배급(DistroKid·TuneCore)으로 인디 아티스트 권한 강화 중. 스트리밍 단가 인상(스포티파이 2023년 인상)이 레이블·아티스트 수익 개선의 핵심.

**③ 라이브 & 이벤트**
디지털 스트리밍이 대체할 수 없는 유일한 실물 경험. COVID 이후 억눌린 수요 폭발로 2022~2024년 글로벌 공연 시장 역대 최고치 연속 경신. Live Nation·Ticketmaster 독점 구조. K-Pop 콘서트의 글로벌 투어(BTS·BLACKPINK 등)가 아시아 라이브 시장을 견인. 팬미팅·팬콘서트 등 K-Pop 전용 포맷이 ARPU를 극대화.

**④ 팬 플랫폼 & 굿즈 (IP 수익화)**
음악 IP를 360도로 수익화하는 레이어. HYBE의 위버스(팬 커뮤니티·MD·영상·굿즈 통합 플랫폼)가 K-Pop 팬 이코노미의 표준. 포토카드·앨범·한정판 MD가 K-Pop 팬덤의 핵심 소비. SM·JYP·YG도 자체 팬 플랫폼 구축 중. 음악 IP의 영화·드라마·웹툰·게임 확장이 수익 다각화 핵심.

## 3. K-Pop의 구조적 성장 동인

K-Pop은 단순 음악 장르를 넘어 **체계화된 IP 비즈니스 모델**로 진화했습니다:
- **트레이닝 시스템**: 수년간 체계적 훈련으로 글로벌 경쟁력 있는 아티스트 양성
- **멀티 레이블**: HYBE의 빅히트·쏘스뮤직·어도어·빌리프랩 등 다양한 색깔의 서브 레이블
- **팬덤 경제**: 앨범 수집·포토카드 수집·공식 MD 소비로 팬당 수익(ARPU) 극대화
- **글로벌 오디션**: 현지 아티스트 발굴(NiziU·NEXZ 등)로 일본·미국 시장 직공략

## 4. 시장 규모 & 성장 전망

- **글로벌 음악 시장(2024년)**: 약 480억 달러 (IFPI 기준)
- **2030년 전망**: 약 750억 달러 (CAGR 약 8%)
- **스트리밍 비중**: 2024년 70% → 2030년 80%+ 예상
- **라이브 공연 시장(2024년)**: 약 320억 달러 (역대 최고)
- **K-Pop 글로벌 시장(2024년)**: 약 130억 달러 → 2030년 400억 달러

## 5. 핵심 투자 포인트 & 리스크

**기회**: 스트리밍 단가 인상 사이클 진입 → 레이블 로열티 상승 / BTS 완전체 복귀(2025) → HYBE 사상 최대 매출 기대 / 라이브 공연 슈퍼사이클 지속 / AI 기반 음악 제작 도구로 인디 아티스트 폭발적 성장

**리스크**: AI 생성 음악의 저작권 위협 / Spotify 아티스트 수익 배분 구조 갈등 / K-Pop 아이돌 그룹 활동 중단·멤버 탈퇴 리스크 / 공연 티켓 가격 인상에 따른 수요 저항"""

cur.execute("""
    INSERT INTO industry_reports (id, title, summary, file_path, tag)
    VALUES (11, '음악 산업 밸류체인 심층분석 (글로벌 레이블·스트리밍·라이브·K-Pop)', ?, '11. 엔터테인먼트/엔터테인먼트.pdf', '음악')
""", (SUMMARY,))
print("[OK] industry_reports id=11 (음악 산업) 삽입")

# ─────────────────────────────────────────────
# 3. value_chain_nodes 재삽입
# ─────────────────────────────────────────────
nodes = [
    (11, '음악 레이블 (Major Labels & K-Pop)', 'UMG·Sony·Warner 3대 메이저 + HYBE·SM·JYP·YG. 마스터·퍼블리싱 저작권으로 스트리밍 로열티 수령.'),
    (11, '스트리밍 & 디지털 배급',              'Spotify·Apple Music 등 구독형 스트리밍 플랫폼. 음악 소비의 70%+ 차지.'),
    (11, '라이브 & 이벤트',                    '콘서트·페스티벌·팬미팅. COVID 이후 역대 최대 수요. Live Nation·K-Pop 투어 수혜.'),
    (11, '팬 플랫폼 & 굿즈 (IP 수익화)',        '위버스·팬카페·공식 MD·포토카드. K-Pop 팬덤 경제의 핵심 수익화 레이어.'),
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
# 4. companies 재삽입 (음악 산업 특화)
# ─────────────────────────────────────────────
companies = [
    # ── 음악 레이블 ──
    (11, '음악 레이블 (Major Labels & K-Pop)',
     'Universal Music Group', 'UMG.AS',
     '글로벌 음악 레이블 1위 (시장점유율 32%). Taylor Swift·Drake·BTS 등 보유. 스트리밍 로열티 최대 수혜 구조.',
     '스트리밍 단가 인상으로 로열티 상승. AI 생성 음악 저작권 수익화 선도. K-Pop·라틴·아프리카 신흥 장르 확장.',
     1),
    (11, '음악 레이블 (Major Labels & K-Pop)',
     'Warner Music Group', 'WMG',
     '글로벌 3위 레이블 (시장점유율 18%). Ed Sheeran·Bruno Mars·Coldplay 등 보유. 인디 배급 레이블 확장 중.',
     '퍼블리싱 부문(Warner Chappell) 성장. 신흥 시장(아프리카·동남아) 아티스트 발굴. 스트리밍 로열티 협상력 강화.',
     2),
    (11, '음악 레이블 (Major Labels & K-Pop)',
     'HYBE', '352820.KS',
     'BTS·세븐틴·뉴진스·르세라핌 등 멀티 레이블. 위버스 팬 플랫폼 글로벌 MAU 1,000만+. K-Pop IP 360도 수익화.',
     'BTS 완전체 복귀(2025) — 월드투어·앨범·위버스 동시 매출 폭발 기대. 미국·일본 현지 레이블 성장.',
     3),
    (11, '음악 레이블 (Major Labels & K-Pop)',
     'SM Entertainment', '041510.KS',
     'EXO·aespa·NCT·SHINEE 등 글로벌 K-Pop IP. SM 유니버스 세계관 기반 스토리텔링 전략.',
     'aespa 글로벌 팬덤 확대. SM 유니버스 웹툰·영상 확장. 카카오엔터와 IP 시너지 강화.',
     4),
    (11, '음악 레이블 (Major Labels & K-Pop)',
     'JYP Entertainment', '035900.KS',
     'TWICE·Stray Kids·ITZY·NiziU·NEXZ. 일본 현지화 성공 사례. 북미·동남아 레이블 확장 중.',
     '글로벌 오디션 기반 현지 아티스트 발굴. K-Pop 비즈니스 모델 현지화 표준 구축.',
     5),
    (11, '음악 레이블 (Major Labels & K-Pop)',
     'YG Entertainment', '122870.KS',
     'BLACKPINK·BIGBANG·WINNER·iKON 등. BLACKPINK 솔로 활동 및 재계약이 단기 촉매.',
     'BLACKPINK 완전체 컴백 여부가 주가 핵심 변수. 신인 그룹 론칭으로 포트폴리오 다각화.',
     6),

    # ── 스트리밍 & 디지털 배급 ──
    (11, '스트리밍 & 디지털 배급',
     'Spotify', 'SPOT',
     '글로벌 음악 스트리밍 1위 — MAU 6억 8천만+. 팟캐스트·오디오북 확장. 아티스트 직접 배급 플랫폼.',
     'AI DJ·AI 플레이리스트로 개인화 강화. 스트리밍 단가 인상으로 수익성 개선. 유료 구독자 3억 돌파 로드맵.',
     7),
    (11, '스트리밍 & 디지털 배급',
     'Apple', 'AAPL',
     'Apple Music — 스트리밍 2위, iOS 생태계 내 독점적 위치. 공간 음악(Spatial Audio) 표준 선도.',
     'Vision Pro 공간 음악 경험 확대. Apple One 번들 내 Music 구독 성장. 아티스트 직접 배급 강화.',
     8),

    # ── 라이브 & 이벤트 ──
    (11, '라이브 & 이벤트',
     'Live Nation Entertainment', 'LYV',
     'Ticketmaster 독점 + 전 세계 공연 기획. 라이브 이벤트 역대 최대 수요 수혜. 콘서트 경제 독점 플랫폼.',
     '콘서트 티켓 수요 사상 최대 지속. 동적 가격제(Dynamic Pricing)로 ARPU 상승. K-Pop 아시아 투어 유통 수혜.',
     9),

    # ── 팬 플랫폼 & 굿즈 ──
    (11, '팬 플랫폼 & 굿즈 (IP 수익화)',
     'Alphabet (YouTube)', 'GOOGL',
     'YouTube Music + YouTube 아티스트 채널 — K-Pop 글로벌 팬덤 형성의 핵심 플랫폼. 광고·프리미엄 수익.',
     'YouTube Shorts K-Pop 숏폼 바이럴 효과. YouTube Music 유료 구독 성장. 아티스트 채널 수익 분배 확대.',
     10),
    (11, '팬 플랫폼 & 굿즈 (IP 수익화)',
     'Kakao Entertainment', '035720.KS',
     '카카오엔터 — 멜론(국내 최대 음원 플랫폼) + SM엔터 지분 + 웹툰·웹소설 IP. K-Pop 국내 디지털 유통 독점.',
     '멜론 유료 구독 안정적 + SM 시너지로 K-Pop IP 콘텐츠 확장. 웹툰→드라마 IP 수익화.',
     11),
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
print("\n✅ 음악 산업 (id=11) 재구성 완료!")
