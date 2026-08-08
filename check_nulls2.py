import sqlite3
conn = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = conn.cursor()

cur.execute('SELECT count(*) FROM company_profiles WHERE mdd_pct IS NULL')
print('mdd_pct NULL:', cur.fetchone()[0])

cur.execute('SELECT count(*) FROM company_profiles WHERE high_52w IS NULL')
print('high_52w NULL:', cur.fetchone()[0])

cur.execute('SELECT count(*) FROM company_profiles WHERE current_price IS NULL')
print('current_price NULL:', cur.fetchone()[0])

cur.execute("""
    SELECT c.name, c.ticker, cp.current_price, cp.high_52w, cp.mdd_pct 
    FROM companies c 
    JOIN company_profiles cp ON c.id=cp.company_id 
    WHERE cp.mdd_pct IS NULL 
    LIMIT 5
""")
print('mdd_pct NULL 종목:', cur.fetchall())
conn.close()
