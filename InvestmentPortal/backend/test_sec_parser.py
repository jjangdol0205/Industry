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
        print(f"CIK not found for {ticker}")
        return []

    facts_url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    facts_resp = requests.get(facts_url, headers=headers)
    if facts_resp.status_code != 200:
        print(f"Error fetching SEC facts: {facts_resp.status_code}")
        return []

    facts = facts_resp.json()
    us_gaap = facts['facts'].get('us-gaap', {})

    # Helper to find the best concept key
    def find_concept(possible_keys):
        for k in possible_keys:
            if k in us_gaap:
                return us_gaap[k]['units']['USD']
        return None

    rev_units = find_concept(['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet'])
    op_units = find_concept(['OperatingIncomeLoss', 'OperatingProfit'])
    net_units = find_concept(['NetIncomeLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic'])

    if not rev_units or not op_units or not net_units:
        print("Missing some required financial concepts")
        return []

    # Map from end date to metrics
    # We will separate by 'annual' and 'quarterly'
    data_points = {}

    def extract_periods(units, name):
        for item in units:
            # Check if start date exists (some items like balance sheets don't have start, but income statement items do)
            if 'start' not in item or 'end' not in item:
                continue
            try:
                start = datetime.strptime(item['start'], '%Y-%m-%d')
                end = datetime.strptime(item['end'], '%Y-%m-%d')
                duration = (end - start).days
                
                # Determine period type
                if 330 <= duration <= 380:
                    period_type = 'annual'
                elif 70 <= duration <= 110:
                    period_type = 'quarterly'
                else:
                    continue  # Ignore 6-month, 9-month, or other odd periods

                date_str = item['end']
                val = float(item['val'])
                
                key = (period_type, date_str)
                if key not in data_points:
                    data_points[key] = {}
                data_points[key][name] = val
            except Exception as e:
                continue

    extract_periods(rev_units, 'revenue')
    extract_periods(op_units, 'operating_income')
    extract_periods(net_units, 'net_income')

    # Now build list
    financials = []
    for (period_type, date), metrics in data_points.items():
        # Only keep if we have revenue (operating income and net income could be 0, but revenue is essential)
        if 'revenue' in metrics:
            rev = metrics['revenue']
            op_inc = metrics.get('operating_income', 0.0)
            net_inc = metrics.get('net_income', 0.0)
            gross_margin = (op_inc / rev * 100) if rev > 0 else 0.0
            
            financials.append({
                "period_type": period_type,
                "date": date,
                "revenue": rev,
                "operating_income": op_inc,
                "net_income": net_inc,
                "gross_margin": gross_margin
            })

    # Sort financials
    financials.sort(key=lambda x: x['date'])
    return financials

# Test NVDA
res = parse_sec_data('NVDA')
print(f"Parsed {len(res)} data points for NVDA")
print("Annual:")
for r in [x for x in res if x['period_type'] == 'annual'][-5:]:
    print(r)
print("\nQuarterly:")
for r in [x for x in res if x['period_type'] == 'quarterly'][-5:]:
    print(r)
