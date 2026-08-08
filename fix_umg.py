import sqlite3
import yfinance as yf

conn = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = conn.cursor()

# UMG.AS 데이터 yfinance로 직접 가져오기
ticker = "UMG.AS"
try:
    t = yf.Ticker(ticker)
    hist = t.history(period="1y")
    if not hist.empty:
        curr = float(hist['Close'].iloc[-1])
        high52 = float(hist['High'].max())
        mdd = float(((curr - high52) / high52) * 100.0)
        signal = f"WAIT (MDD {mdd:.1f}% > -30% 폭락대기 미달)" if mdd > -30 else "WATCHLIST_BUY_READY (관심종목 -30% 폭락진입)"
        
        cur.execute("""
            UPDATE company_profiles SET current_price=?, high_52w=?, mdd_pct=?, buy_signal=?, 
            last_updated=datetime('now','localtime')
            WHERE company_id=(SELECT id FROM companies WHERE ticker='UMG.AS')
        """, (curr, high52, mdd, signal))
        conn.commit()
        print(f"UMG.AS 업데이트: 현재가={curr:.2f}, 52w고={high52:.2f}, MDD={mdd:.1f}%")
    else:
        print("hist empty. Trying info...")
        info = t.fast_info
        curr = float(info.last_price or 0)
        high52 = float(info.year_high or 0)
        if curr and high52:
            mdd = float(((curr - high52) / high52) * 100.0)
            signal = f"WAIT (MDD {mdd:.1f}%)"
            cur.execute("""
                UPDATE company_profiles SET current_price=?, high_52w=?, mdd_pct=?, buy_signal=?,
                last_updated=datetime('now','localtime')
                WHERE company_id=(SELECT id FROM companies WHERE ticker='UMG.AS')
            """, (curr, high52, mdd, signal))
            conn.commit()
            print(f"UMG.AS (fast_info): 현재가={curr:.2f}, 52w고={high52:.2f}, MDD={mdd:.1f}%")
except Exception as e:
    print(f"Error: {e}")
    # 마지막 수단: high_52w 기준으로 mdd_pct만 계산
    cur.execute("SELECT cp.company_id, cp.current_price, cp.high_52w FROM company_profiles cp JOIN companies c ON c.id=cp.company_id WHERE c.ticker='UMG.AS'")
    row = cur.fetchone()
    if row and row[1] and row[2]:
        cid, curr_p, high52_p = row
        mdd = float(((curr_p - high52_p) / high52_p) * 100.0)
        signal = f"WAIT (MDD {mdd:.1f}% > -30% 폭락대기 미달)"
        cur.execute("UPDATE company_profiles SET mdd_pct=?, buy_signal=? WHERE company_id=?", (mdd, signal, cid))
        conn.commit()
        print(f"UMG.AS (기존 데이터 계산): mdd={mdd:.1f}%")

conn.close()
print("완료!")
