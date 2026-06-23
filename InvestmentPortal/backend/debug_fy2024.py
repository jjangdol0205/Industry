import requests
from datetime import datetime

def test_calc(ticker):
    headers = {'User-Agent': 'InvestmentPortal admin@example.com'}
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
    
    # We want to print for fy = 2024
    for item in rev_units:
        if item['fy'] == 2024:
            print(f"FY2024: start={item.get('start')}, end={item.get('end')}, val={item['val']/1e9:.3f}B, form={item['form']}, fp={item['fp']}")
            
test_calc('NVDA')
