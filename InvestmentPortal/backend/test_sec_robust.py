import requests
from datetime import datetime, timedelta

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
    
    # Store all periods
    # We will key them by (start_date, end_date) to deduplicate and keep the one with the latest 'filed' date
    periods = {}
    for item in rev_units:
        if 'start' not in item or 'end' not in item:
            continue
        try:
            start = item['start']
            end = item['end']
            val = float(item['val'])
            filed = item['filed']
            
            key = (start, end)
            if key not in periods or filed > periods[key]['filed']:
                periods[key] = {
                    'val': val,
                    'filed': filed
                }
        except Exception as e:
            continue

    # Now group by duration
    annuals = [] # list of {start, end, val}
    quarterlies_3m = [] # list of {start, end, val}
    cum_6m = []
    cum_9m = []
    
    for (start, end), data in periods.items():
        s_dt = datetime.strptime(start, '%Y-%m-%d')
        e_dt = datetime.strptime(end, '%Y-%m-%d')
        duration = (e_dt - s_dt).days
        
        item = {'start': start, 'end': end, 'val': data['val'], 's_dt': s_dt, 'e_dt': e_dt}
        
        if 330 <= duration <= 380:
            annuals.append(item)
        elif 70 <= duration <= 110:
            quarterlies_3m.append(item)
        elif 150 <= duration <= 200:
            cum_6m.append(item)
        elif 240 <= duration <= 300:
            cum_9m.append(item)

    # Reconstruct missing 3m quarters using cumulative data
    # For each annual (FY) period:
    # We find Q1 (3m), Q2 (6m cumulative), Q3 (9m cumulative)
    # Then we compute:
    # Q1 = Q1_3m
    # Q2 = Q2_6m_cum - Q1_3m
    # Q3 = Q3_9m_cum - Q2_6m_cum
    # Q4 = FY_12m - Q3_9m_cum
    
    reconstructed_quarters = [] # list of (date, val)
    
    for ann in annuals:
        fy_end = ann['e_dt']
        fy_start = ann['s_dt']
        fy_val = ann['val']
        
        # Find Q1 ending ~9 months before fy_end
        q1_end_target = fy_start + timedelta(days=90)
        q1 = None
        for q in quarterlies_3m:
            if abs((q['e_dt'] - q1_end_target).days) <= 20:
                q1 = q
                break
                
        # Find Q2 ending ~6 months before fy_end
        q2_end_target = fy_start + timedelta(days=180)
        q2_3m = None
        for q in quarterlies_3m:
            if abs((q['e_dt'] - q2_end_target).days) <= 20:
                q2_3m = q
                break
        q2_cum = None
        for q in cum_6m:
            if abs((q['e_dt'] - q2_end_target).days) <= 20:
                q2_cum = q
                break
                
        # Find Q3 ending ~3 months before fy_end
        q3_end_target = fy_start + timedelta(days=270)
        q3_3m = None
        for q in quarterlies_3m:
            if abs((q['e_dt'] - q3_end_target).days) <= 20:
                q3_3m = q
                break
        q3_cum = None
        for q in cum_9m:
            if abs((q['e_dt'] - q3_end_target).days) <= 20:
                q3_cum = q
                break
                
        # Now compute quarterly values
        # Q1
        if q1:
            reconstructed_quarters.append((q1['end'], q1['val'], 'Q1'))
        
        # Q2
        if q2_3m:
            reconstructed_quarters.append((q2_3m['end'], q2_3m['val'], 'Q2'))
        elif q2_cum and q1:
            reconstructed_quarters.append((q2_cum['end'], q2_cum['val'] - q1['val'], 'Q2'))
            
        # Q3
        if q3_3m:
            reconstructed_quarters.append((q3_3m['end'], q3_3m['val'], 'Q3'))
        elif q3_cum and q2_cum:
            reconstructed_quarters.append((q3_cum['end'], q3_cum['val'] - q2_cum['val'], 'Q3'))
            
        # Q4
        if q3_cum:
            reconstructed_quarters.append((ann['end'], fy_val - q3_cum['val'], 'Q4'))
        elif q3_3m and q2_cum:
            reconstructed_quarters.append((ann['end'], fy_val - (q2_cum['val'] + q3_3m['val']), 'Q4'))

    # Deduplicate reconstructed quarters by date
    unique_quarters = {}
    for date, val, label in reconstructed_quarters:
        unique_quarters[date] = (val, label)
        
    sorted_q = sorted(unique_quarters.items())
    for date, (val, label) in sorted_q[-12:]:
        print(f"Date: {date}, Val: {val/1e9:.3f}B, Period: {label}")

test_calc('NVDA')
