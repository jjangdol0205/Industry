import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

c = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = c.cursor()

# Energy company tickers to fix
energy_tickers = ['GEV', 'SMEGF', 'MHVYF', 'SMR', 'OKLO', 'CEG', 'LEU', 'BWXT', '034020.KS']

print("=== Fixing industry_id for energy companies ===")
for ticker in energy_tickers:
    row = cur.execute('SELECT id, name, ticker, industry_id FROM companies WHERE ticker=?', (ticker,)).fetchone()
    if row:
        print(f"  Found: id={row[0]}, {row[1]} ({row[2]}), industry_id={row[3]}")
        if row[3] != 5:
            cur.execute('UPDATE companies SET industry_id=5 WHERE id=?', (row[0],))
            print(f"    -> Fixed to industry_id=5")
    else:
        print(f"  NOT FOUND: {ticker}")

c.commit()

# Set display_order now
rank_map = {
    'CEG': 1,       # Constellation Energy - operational revenue, MS PPA
    'BWXT': 2,      # BWX Tech - proven foundry, defense
    'LEU': 3,       # Centrus Energy - HALEU monopoly
    'GEV': 4,       # GE Vernova - gas turbine leader
    'MHVYF': 5,    # Mitsubishi - ultra-high efficiency turbine
    'SMEGF': 6,     # Siemens Energy - flexible grid
    '034020.KS': 7, # Doosan Enerbility - nuclear foundry
    'SMR': 8,       # NuScale - SMR fabless
    'OKLO': 9,      # Oklo - early stage SMR
}

print("\n=== Setting display_order ===")
for ticker, rank in rank_map.items():
    result = cur.execute('UPDATE companies SET display_order=? WHERE ticker=? AND industry_id=5', (rank, ticker))
    print(f"  {ticker} -> rank {rank} (rows updated: {result.rowcount})")

c.commit()

# Also fix value_chain_node_id
# Nodes: 20=GasTurbine, 21=SMR Fabless, 22=Foundry&Mfg, 23=NuclearFuel, 24=NuclearOps
vc_map = {
    'GEV': 20,
    'SMEGF': 20,
    'MHVYF': 20,
    'SMR': 21,
    'OKLO': 21,
    'CEG': 24,
    'LEU': 23,
    'BWXT': 22,
    '034020.KS': 22,
}

print("\n=== Setting value_chain_node_id ===")
for ticker, vc_id in vc_map.items():
    result = cur.execute('UPDATE companies SET value_chain_node_id=? WHERE ticker=? AND industry_id=5', (vc_id, ticker))
    print(f"  {ticker} -> vc_node {vc_id} (rows updated: {result.rowcount})")

c.commit()

# Verify
print("\n=== Final verification ===")
rows = cur.execute('SELECT id, name, ticker, industry_id, display_order, value_chain_node_id FROM companies WHERE industry_id=5 ORDER BY display_order').fetchall()
print(f"Energy companies ({len(rows)} total):")
for x in rows:
    print(f"  [{x[4]}] id={x[0]}, {x[1]} ({x[2]}), vc={x[5]}")

c.close()
print("\nDone!")
