import sqlite3
conn = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = conn.cursor()

# NVDA 중복 확인
cur.execute("""
    SELECT c.id, c.name, c.ticker, c.industry_id, c.portfolio_tier, ir.title
    FROM companies c
    LEFT JOIN industry_reports ir ON c.industry_id = ir.id
    WHERE c.ticker LIKE '%NVDA%' OR c.name LIKE '%Nvidia%' OR c.name LIKE '%NVIDIA%'
    ORDER BY c.id
""")
rows = cur.fetchall()
print(f"NVIDIA 관련 종목 {len(rows)}개:")
for r in rows:
    print(f"  id={r[0]}, name={r[1]}, ticker={r[2]}, tier={r[4]}, industry='{r[5]}'")

# ticker 기준으로 중복 전체 확인
cur.execute("""
    SELECT ticker, COUNT(*) as cnt, GROUP_CONCAT(name, ' | ') as names
    FROM companies
    WHERE ticker IS NOT NULL
    GROUP BY ticker
    HAVING cnt > 1
    ORDER BY cnt DESC
    LIMIT 20
""")
dups = cur.fetchall()
print(f"\n중복 ticker {len(dups)}개:")
for d in dups:
    print(f"  ticker={d[0]}, 개수={d[1]}, names={d[2]}")

conn.close()
