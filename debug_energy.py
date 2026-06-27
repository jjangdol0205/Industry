import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

c = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = c.cursor()

# Check industry_reports id=5
row = cur.execute('SELECT id, title FROM industry_reports WHERE id=5').fetchone()
print(f"Industry report: {row}")

# Check value_chain_nodes for industry 5
nodes = cur.execute('SELECT id, node_name FROM value_chain_nodes WHERE industry_id=5').fetchall()
print(f"Value chain nodes ({len(nodes)} total):")
for n in nodes:
    print(f"  {n}")

# Check all companies
all_companies = cur.execute('SELECT id, name, ticker, industry_id FROM companies ORDER BY id DESC LIMIT 20').fetchall()
print(f"Recent companies:")
for co in all_companies:
    print(f"  {co}")

c.close()
