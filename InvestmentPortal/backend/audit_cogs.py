import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('investment_portal.db')
cur = conn.cursor()

cur.execute('''
    SELECT c.id, c.name, c.ticker,
        COUNT(*) as total_rows,
        SUM(CASE WHEN fd.cost_of_revenue IS NULL THEN 1 ELSE 0 END) as null_count,
        SUM(CASE WHEN fd.cost_of_revenue IS NOT NULL AND fd.cost_of_revenue != 0 THEN 1 ELSE 0 END) as has_data
    FROM companies c
    JOIN financial_data fd ON c.id = fd.company_id
    GROUP BY c.id
    ORDER BY has_data ASC, c.id
''')
rows = cur.fetchall()
print(f"{'ID':>4} {'Ticker':>6} {'기업명':<30} {'전체':>5} {'COGS있음':>8} {'NULL':>5} 상태")
print('-' * 70)
missing = []
for r in rows:
    status = 'MISSING' if r[5] == 0 else 'OK'
    if r[5] == 0:
        missing.append((r[0], r[1], r[2]))
    print(f"{r[0]:>4} {r[2]:>6} {r[1]:<30} {r[3]:>5} {r[5]:>8} {r[4]:>5}  {status}")

print(f"\n총 {len(rows)}개 기업 중 COGS 완전 누락: {len(missing)}개")
print("\n누락 기업:")
for cid, name, ticker in missing:
    print(f"  [{cid}] {name} ({ticker})")
conn.close()
