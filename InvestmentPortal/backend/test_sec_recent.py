import requests
from datetime import datetime

def parse_sec_data(ticker):
    headers = {'User-Agent': 'InvestmentPortal admin@example.com'}
    # Get CIK
    resp = requests.get('https://www.sec.gov/files/company_tickers.json', headers=headers)
    tickers_dict = resp.json()
    cik = None
    for key, val in tickers_dict.items():
        if val['ticker'] == ticker:
            cik = str(val['cik_str']).zfill(10)
            break
            
    if not cik:
        return

    facts_url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    facts_resp = requests.get(facts_url, headers=headers)
    facts = facts_resp.json()
    us_gaap = facts['facts'].get('us-gaap', {})

    def find_concept(possible_keys):
        for k in possible_keys:
            if k in us_gaap:
                return us_gaap[k]['units']['USD']
        return None

    rev_units = find_concept(['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet'])
    
    for item in rev_units:
        if 'start' not in item or 'end' not in item:
            continue
        start = datetime.strptime(item['start'], '%Y-%m-%d')
        end = datetime.strptime(item['end'], '%Y-%m-%d')
        duration = (end - start).days
        
        if 70 <= duration <= 110 and '2024-' in item['end'] or '2025-' in item['end'] or '2026-' in item['end']:
            print(f"Quarterly: start={item['start']}, end={item['end']}, val={item['val']/1e9}B, form={item['form']}, fp={item['fp']}")
            
parse_sec_data('NVDA')
