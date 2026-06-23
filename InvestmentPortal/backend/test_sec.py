import requests
import json
import pandas as pd

headers = {'User-Agent': 'InvestmentPortal admin@example.com'}
# Get tickers
resp = requests.get('https://www.sec.gov/files/company_tickers.json', headers=headers)
tickers_dict = resp.json()

cik = None
for key, val in tickers_dict.items():
    if val['ticker'] == 'NVDA':
        cik = str(val['cik_str']).zfill(10)
        break

print(f"NVDA CIK: {cik}")

if cik:
    facts_url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    facts_resp = requests.get(facts_url, headers=headers)
    if facts_resp.status_code == 200:
        facts = facts_resp.json()
        us_gaap = facts['facts'].get('us-gaap', {})
        print("Keys:", list(us_gaap.keys())[:10])
        if 'Revenues' in us_gaap:
            rev_data = us_gaap['Revenues']['units']['USD']
            print("Found Revenues!")
            print("Sample rev:", rev_data[-5:])
    else:
        print("Status code:", facts_resp.status_code)
