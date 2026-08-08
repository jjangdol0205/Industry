import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('investment_portal.db')
cur = conn.cursor()

# Check NULL future_growth
cur.execute("SELECT id,name,ticker,future_growth FROM companies WHERE future_growth IS NULL OR future_growth=''")
rows = cur.fetchall()
print(f"NULL/empty future_growth: {len(rows)}")
for r in rows[:20]:
    print(r)

# Check Render API reports error - simulate the query
cur.execute("SELECT COUNT(*) FROM industry_reports")
cnt = cur.fetchone()[0]
print(f"\nTotal industry reports: {cnt}")

cur.execute("SELECT id, title, tag FROM industry_reports ORDER BY id")
for r in cur.fetchall():
    print(r)

conn.close()
