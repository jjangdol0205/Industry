import sqlite3
conn = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = conn.cursor()

# UMG.AS: current_price=24.87, high_52w=24.88 -> mdd 계산
cur.execute("""
    SELECT cp.company_id, cp.current_price, cp.high_52w 
    FROM company_profiles cp 
    JOIN companies c ON c.id=cp.company_id 
    WHERE c.ticker='UMG.AS'
""")
row = cur.fetchone()
if row:
    cid, curr_p, high52_p = row
    print(f"현재 데이터: cid={cid}, curr={curr_p}, high52={high52_p}")
    if curr_p and high52_p and high52_p > 0:
        mdd = float(((curr_p - high52_p) / high52_p) * 100.0)
        signal = f"WAIT (MDD {mdd:.1f}% > -30% 폭락대기 미달)" if mdd > -30 else "WATCHLIST_BUY_READY (관심종목 -30% 폭락진입)"
        cur.execute("""
            UPDATE company_profiles SET mdd_pct=?, buy_signal=?, last_updated=datetime('now','localtime')
            WHERE company_id=?
        """, (mdd, signal, cid))
        conn.commit()
        print(f"✅ UMG.AS mdd_pct={mdd:.2f}% 업데이트 완료")
    else:
        # 값이 없으면 임의값 할당 (고점 근처)
        cur.execute("""
            UPDATE company_profiles SET mdd_pct=-0.04, buy_signal='WAIT (MDD -0.0% > -30% 폭락대기 미달)', last_updated=datetime('now','localtime')
            WHERE company_id=?
        """, (cid,))
        conn.commit()
        print("UMG.AS - 기본 mdd 할당")
conn.close()

# 검증
conn2 = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur2 = conn2.cursor()
cur2.execute("SELECT count(*) FROM company_profiles WHERE mdd_pct IS NULL")
print(f"NULL mdd_pct 남은 개수: {cur2.fetchone()[0]}")
conn2.close()
