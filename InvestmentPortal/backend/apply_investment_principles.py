# -*- coding: utf-8 -*-
"""
4단계 투자원칙 기반 유니버스 스크리닝 데이터베이스 적용 스크립트
companies 테이블에 portfolio_tier (Core / Satellite / Watchlist / Standard) 및
principle_reason (원칙 부합 이유) 필드 추가 및 데이터 업데이트
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investment_portal.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. 컬럼 존재 여부 확인 및 추가
cur.execute("PRAGMA table_info(companies)")
cols = [col[1] for col in cur.fetchall()]

if "portfolio_tier" not in cols:
    cur.execute("ALTER TABLE companies ADD COLUMN portfolio_tier TEXT DEFAULT 'Standard'")
    print("[OK] portfolio_tier 컬럼 추가")

if "principle_reason" not in cols:
    cur.execute("ALTER TABLE companies ADD COLUMN principle_reason TEXT")
    print("[OK] principle_reason 컬럼 추가")

# 2. 투자원칙 핵심 종목 매핑
TIER_MAPPING = [
    # Core (독점 병목 3종목 + 국내 대체 2종목)
    ("ASML", "Core", "EUV 노광장비 100% 독점, GPM 51%+, 전환비용 극상 (Core 1호)"),
    ("NVIDIA", "Core", "AI GPU 시장 80%+ 독점, OPM 55%+, CUDA 생태계 락인 (Core 2호)"),
    ("TSMC", "Core", "5nm 이하 파운드리 90%+ 독점, OPM 42%+, CoWoS 병목 소유 (Core 3호)"),
    ("삼성바이오로직스", "Core", "세계 1위 배양용량 CDMO 독점력, CAPEX 무거운 자본 장벽 (국내 Core 대체)"),
    ("코스맥스", "Core", "글로벌 1위 화장품 ODM, Fast Beauty 밸류체인 핵심 병목 (국내 Core 대체)"),

    # Satellite (고성장 알파 2종목 + 국내 대체 2종목)
    ("Rocket Lab USA", "Satellite", "소형 발사체 독보적 2위, 수주잔고 역대 최고치, 위성 SW/시스템 체질개선 (Satellite 1호)"),
    ("Vertiv Holdings", "Satellite", "AI 데이터센터 액체냉각/UPS 1위, 수주잔고 YoY +35%, 고마진 체질개선 (Satellite 2호)"),
    ("삼양식품", "Satellite", "불닭볶음면 글로벌 IP 독점, 수출 비중 70%+, 수주/수출 역대 최고치 (국내 Satellite 대체)"),
    ("HD현대일렉트릭", "Satellite", "글로벌 전력기기 리드타임 2년+ 병목, 수주잔고 최고치 경신 (국내 Satellite 대체)"),

    # Watchlist (대체 관심종목 5개 - MDD -30%~-40% 폭락 대기)
    ("Intuitive Surgical", "Watchlist", "다빈치 수술로봇 독점, OPM 30%+, 소모품 락인 (대체 관심 1호)"),
    ("HD한국조선해양", "Watchlist", "LNG/친환경선 글로벌 1위, 3년치 고가 수주잔고 (대체 관심 2호)"),
    ("브이티", "Watchlist", "마이크로니들(리들샷) 독점 IP, 글로벌 바이럴 고마진 (대체 관심 3호)"),
    ("Palantir Technologies", "Watchlist", "기업/정부 AI 운영체제(AIP) 시장 선도, ARR 구독 성장 (대체 관심 4호)"),
    ("실리콘투", "Watchlist", "K-뷰티 글로벌 풀필먼트 플랫폼 1위, 150개국 직매입 유통 (대체 관심 5호)"),
]

print("\n[투자원칙 티어 업데이트 시작]")
for company_name, tier, reason in TIER_MAPPING:
    cur.execute("""
        UPDATE companies 
        SET portfolio_tier=?, principle_reason=?
        WHERE name LIKE ? OR ticker LIKE ?
    """, (tier, reason, f"%{company_name}%", f"%{company_name}%"))
    print(f"[OK] {company_name} -> {tier} ({cur.rowcount}행 적용)")

conn.commit()

# 결과 확인
cur.execute("SELECT portfolio_tier, count(*) FROM companies GROUP BY portfolio_tier")
print("\n[티어별 기업 수 분포]")
for r in cur.fetchall():
    print(f"  - {r[0]}: {r[1]}개")

conn.close()
print("\n✅ DB 투자원칙 스크리닝 데이터 적용 완료!")
