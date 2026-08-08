import sqlite3
conn = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = conn.cursor()
cur.execute("""
    SELECT c.name, c.ticker, cp.high_52w, cp.mdd_pct, cp.buy_signal 
    FROM companies c 
    JOIN company_profiles cp ON c.id=cp.company_id 
    WHERE cp.mdd_pct IS NULL OR cp.high_52w IS NULL
""")
rows = cur.fetchall()
print(f"NULL MDD/52w 종목 {len(rows)}개:")
for r in rows:
    print(r)
conn.close()
