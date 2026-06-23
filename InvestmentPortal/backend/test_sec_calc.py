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
    if not rev_units:
        print("No revenue units")
        return

    # Let's organize by fiscal year and period
    # We want:
    # - 3-month (Q1, Q2, Q3)
    # - 6-month (Q2 cumulative)
    # - 9-month (Q3 cumulative)
    # - 12-month (FY cumulative)
    
    by_fy = {} # fy -> {fp -> {duration: val}}
    
    for item in rev_units:
        if 'start' not in item or 'end' not in item:
            continue
        try:
            start = datetime.strptime(item['start'], '%Y-%m-%d')
            end = datetime.strptime(item['end'], '%Y-%m-%d')
            duration = (end - start).days
            
            fy = item['fy']
            fp = item['fp']
            val = float(item['val'])
            date = item['end']
            
            if fy not in by_fy:
                by_fy[fy] = {}
            if fp not in by_fy[fy]:
                by_fy[fy][fp] = []
            
            by_fy[fy][fp].append({
                'duration': duration,
                'val': val,
                'date': date
            })
        except Exception as e:
            continue

    # Now calculate quarterly for each fiscal year
    quarters = [] # list of (date, val)
    for fy, fps in by_fy.items():
        # Get Q1 (approx 3 months)
        q1_items = fps.get('Q1', [])
        q1_val = None
        q1_date = None
        for item in q1_items:
            if 70 <= item['duration'] <= 110:
                q1_val = item['val']
                q1_date = item['date']
                break
        
        # Get Q2 (approx 3 months, or 6 months cumulative)
        q2_items = fps.get('Q2', [])
        q2_val = None
        q2_date = None
        # Try 3 months first
        for item in q2_items:
            if 70 <= item['duration'] <= 110:
                q2_val = item['val']
                q2_date = item['date']
                break
        # Fallback to 6 months cumulative minus Q1
        if q2_val is None:
            for item in q2_items:
                if 150 <= item['duration'] <= 200:
                    if q1_val is not None:
                        q2_val = item['val'] - q1_val
                        q2_date = item['date']
                        break

        # Get Q3 (approx 3 months, or 9 months cumulative)
        q3_items = fps.get('Q3', [])
        q3_val = None
        q3_date = None
        # Try 3 months first
        for item in q3_items:
            if 70 <= item['duration'] <= 110:
                q3_val = item['val']
                q3_date = item['date']
                break
        # Fallback to 9 months cumulative minus Q2 cumulative (6 months)
        if q3_val is None:
            q2_cum = None
            for item in q2_items:
                if 150 <= item['duration'] <= 200:
                    q2_cum = item['val']
                    break
            if q2_cum is not None:
                for item in q3_items:
                    if 240 <= item['duration'] <= 300:
                        q3_val = item['val'] - q2_cum
                        q3_date = item['date']
                        break

        # Get Q4 (12 months cumulative minus 9 months cumulative)
        fy_items = fps.get('FY', [])
        q4_val = None
        q4_date = None
        # Try to find FY 12-month value
        fy_val = None
        for item in fy_items:
            if 330 <= item['duration'] <= 380:
                fy_val = item['val']
                q4_date = item['date']
                break
        # Find Q3 cumulative (9 months)
        q3_cum = None
        for item in q3_items:
            if 240 <= item['duration'] <= 300:
                q3_cum = item['val']
                break
        if fy_val is not None and q3_cum is not None:
            q4_val = fy_val - q3_cum
            
        if q1_val is not None and q1_date:
            quarters.append((q1_date, q1_val, 'Q1'))
        if q2_val is not None and q2_date:
            quarters.append((q2_date, q2_val, 'Q2'))
        if q3_val is not None and q3_date:
            quarters.append((q3_date, q3_val, 'Q3'))
        if q4_val is not None and q4_date:
            quarters.append((q4_date, q4_val, 'Q4'))

    quarters.sort(key=lambda x: x[0])
    for q in quarters[-8:]:
        print(f"Date: {q[0]}, Val: {q[1]/1e9:.3f}B, Period: {q[2]}")

test_calc('NVDA')
