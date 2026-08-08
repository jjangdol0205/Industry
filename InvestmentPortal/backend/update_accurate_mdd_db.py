# -*- coding: utf-8 -*-
"""
정확한 최신 주가, 52주 최고가, MDD 및 제1원칙 가격 필터 신호 업데이트 스크립트
"""
import sqlite3, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "investment_portal.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
    SELECT c.id, c.name, c.ticker, c.portfolio_tier
    FROM companies c
    WHERE c.portfolio_tier IN ('Core', 'Satellite', 'Watchlist') OR c.ticker IS NOT NULL
""")
companies = cur.fetchall()

print("=== 4단계 투자원칙 제1원칙(MDD) 정밀 가격 검증 및 DB 업데이트 ===")

for cid, cname, ticker, tier in companies:
    if not ticker or len(ticker.strip()) == 0:
        continue
    
    clean_ticker = ticker.strip()
    
    try:
        t = yf.Ticker(clean_ticker)
        hist = t.history(period="1y")
        
        if not hist.empty:
            curr = float(hist['Close'].iloc[-1])
            high52 = float(hist['High'].max())
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

            print(f"[{tier or 'Std'}] {cname} ({ticker}): 현재가 {curr:,.2f} | 52주최고가 {high52:,.2f} | MDD: {mdd:.2f}% -> {signal}")
    except Exception as e:
        print(f"[ERR] {cname} ({ticker}): {e}")

conn.commit()
conn.close()
print("\n✅ 정밀 주가 DB 업데이트 완료!")
