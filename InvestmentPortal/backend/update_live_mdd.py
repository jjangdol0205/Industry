# -*- coding: utf-8 -*-
"""
최신 주가, 52주 최고가, MDD(고점 대비 하락률), 제1원칙 가격 필터 검증 스크립트
yfinance를 이용하여 DB의 모든 기업(또는 Core/Satellite/Watchlist)의 최신 주가를 조회하고 MDD를 구함
"""
import sqlite3, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investment_portal.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. company_profiles 테이블 컬럼 확인 및 추가 (current_price, high_52w, mdd_pct, buy_signal)
cur.execute("PRAGMA table_info(company_profiles)")
cols = [c[1] for c in cur.fetchall()]

new_cols = [
    ("current_price", "REAL"),
    ("high_52w", "REAL"),
    ("mdd_pct", "REAL"),
    ("buy_signal", "TEXT"),  # 'BUY_READY' (-20%~-30% 이상 할인), 'WAIT' (고점근처 미달), 'DEEP_DISCOUNT' (-40% 이상)
]

for col_name, col_type in new_cols:
    if col_name not in cols:
        cur.execute(f"ALTER TABLE company_profiles ADD COLUMN {col_name} {col_type}")
        print(f"[OK] company_profiles에 {col_name} 컬럼 추가")

# 2. 대상 기업 가져오기 (Core, Satellite, Watchlist 및 주요 기업)
cur.execute("""
    SELECT c.id, c.name, c.ticker, c.portfolio_tier
    FROM companies c
    WHERE c.portfolio_tier IN ('Core', 'Satellite', 'Watchlist') OR c.ticker IS NOT NULL
""")
companies = cur.fetchall()
print(f"총 수집 대상 기업 수: {len(companies)}개")

results = []

for cid, cname, ticker, tier in companies:
    if not ticker or len(ticker.strip()) == 0:
        continue
    
    clean_ticker = ticker.strip()
    # yfinance 포맷 변환 (필요시)
    yf_ticker = clean_ticker
    
    try:
        t = yf.Ticker(yf_ticker)
        hist = t.history(period="1y")
        
        if hist.empty and ".KS" not in yf_ticker and ".KQ" not in yf_ticker:
            # 혹시 모르니 재시도
            pass
        
        if not hist.empty:
            curr = float(hist['Close'].iloc[-1])
            high52 = float(hist['High'].max())
            mdd = float(((curr - high52) / high52) * 100.0)
            
            # 제1원칙 가격 필터 조건 판정
            # Core/Satellite: MDD <= -20.0% (즉 20% 이상 하락) 시 BUY_READY
            # Watchlist: MDD <= -30.0% (30% 이상 하락) 시 BUY_READY
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

            # company_profiles에 저장/업데이트
            cur.execute("SELECT id FROM company_profiles WHERE company_id=?", (cid,))
            if cur.fetchone():
                cur.execute("""
                    UPDATE company_profiles 
                    SET current_price=?, high_52w=?, mdd_pct=?, buy_signal=?, last_updated=datetime('now', 'localtime')
                    WHERE company_id=?
                """, (curr, high52, mdd, signal, cid))
            else:
                cur.execute("""
                    INSERT INTO company_profiles (company_id, current_price, high_52w, mdd_pct, buy_signal, last_updated)
                    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """, (cid, curr, high52, mdd, signal))

            results.append((cname, ticker, tier, curr, high52, mdd, signal))
            print(f"[{tier or 'Std'}] {cname} ({ticker}): 현재가 {curr:,.2f} | 52주 최고가 {high52:,.2f} | MDD: {mdd:.2f}% -> Signal: {signal}")
        else:
            print(f"[SKIP] {cname} ({ticker}) - 히스토리 데이터 없음")
    except Exception as e:
        print(f"[ERR] {cname} ({ticker}): {e}")
    
    time.sleep(0.1)

conn.commit()
conn.close()
print("\n✅ 최신 주가 & 52주 최고가 & MDD 제1원칙 가격 필터 수집 완료!")
