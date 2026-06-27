import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

c = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
r = c.cursor().execute('SELECT id, name, ticker, display_order FROM companies WHERE industry_id=5 ORDER BY id').fetchall()
for x in r:
    print(x)
c.close()
