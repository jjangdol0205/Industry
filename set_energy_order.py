import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

c = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = c.cursor()

rows = cur.execute('SELECT id, name, ticker, display_order, value_chain_node_id FROM companies WHERE industry_id=5 ORDER BY id').fetchall()
print(f"Energy companies ({len(rows)} total):")
for x in rows:
    print(f"  id={x[0]}, name='{x[1]}', ticker={x[2]}, display_order={x[3]}, vc_node={x[4]}")

# Set display_order for energy companies
# Ranking: 1=CEG, 2=BWXT, 3=LEU, 4=GEV, 5=MHVYF, 6=SMNEY, 7=SMR, 8=OKLO, 9=Doosan
rank_map = {
    'CEG': 1,      # Constellation Energy - operational revenue, MS PPA
    'BWXT': 2,     # BWX Tech - proven foundry, defense contracts  
    'LEU': 3,      # Centrus Energy - HALEU monopoly
    'GEV': 4,      # GE Vernova - gas turbine leader
    'MHVYF': 5,   # Mitsubishi - ultra-high efficiency turbine
    'SMNEY': 6,    # Siemens Energy - flexible grid
    '034020.KS': 7, # Doosan Enerbility - nuclear foundry
    'SMR': 8,      # NuScale - SMR fabless
    'OKLO': 9,     # Oklo - early stage SMR
}

for ticker, rank in rank_map.items():
    cur.execute('UPDATE companies SET display_order=? WHERE ticker=? AND industry_id=5', (rank, ticker))
    print(f"  Set {ticker} -> rank {rank}")

c.commit()

# Verify
rows = cur.execute('SELECT id, name, ticker, display_order FROM companies WHERE industry_id=5 ORDER BY display_order').fetchall()
print("\nUpdated order:")
for x in rows:
    print(f"  [{x[3]}] {x[1]} ({x[2]})")

c.close()
print("Done!")
