import sqlite3
conn = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = conn.cursor()
cur.execute("""
    SELECT c.id, c.name, c.ticker, c.portfolio_tier, cp.mdd_pct, cp.buy_signal, cp.current_price, cp.high_52w
    FROM companies c
    LEFT JOIN company_profiles cp ON c.id = cp.company_id
    WHERE cp.buy_signal LIKE '%BUY_CANDIDATE%'
    ORDER BY cp.mdd_pct ASC
""")
rows = cur.fetchall()
print(f'총 BUY_CANDIDATE 종목: {len(rows)}개')
for r in rows:
    mdd = r[4] if r[4] else 0
    price = r[6] if r[6] else 0
    print(f'  [{r[3]}] {r[1]} ({r[2]}) | MDD={mdd:.1f}% | 현재가=${price:.2f}')
conn.close()
