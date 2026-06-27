import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'InvestmentPortal/backend/investment_portal.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables:", [t[0] for t in tables])

# Check industry_reports
cur.execute("SELECT id, title FROM industry_reports ORDER BY id")
for r in cur.fetchall():
    print(f"  Report {r[0]}: {r[1]}")

conn.close()
