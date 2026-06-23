import pandas as pd
import requests
from datetime import datetime, timedelta
from yahooquery import Ticker

def safe_get(row, keys):
    for key in keys:
        val = row.get(key, 0)
        if pd.notna(val) and val != 0:
            return float(val)
    return 0.0

def process_sec_concept(concept_units):
    if not concept_units:
        return {}, {}
    
    periods = {}
    for item in concept_units:
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
        except Exception:
            continue

    annuals = []
    quarterlies_3m = []
    cum_6m = []
    cum_9m = []
    
    for (start, end), data in periods.items():
        try:
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
        except Exception:
            continue

    annual_data = {}
    quarterly_data = {}
    
    # 1. Annual directly
    for ann in annuals:
        annual_data[ann['end']] = ann['val']
        
    # 2. Reconstruct quarterly
    for ann in annuals:
        fy_end = ann['e_dt']
        fy_start = ann['s_dt']
        fy_val = ann['val']
        
        # Q1 (approx 90 days after fy_start)
        q1_end_target = fy_start + timedelta(days=90)
        q1 = None
        for q in quarterlies_3m:
            if abs((q['e_dt'] - q1_end_target).days) <= 20:
                q1 = q
                break
                
        # Q2 (approx 180 days after fy_start)
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
                
        # Q3 (approx 270 days after fy_start)
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
                
        if q1:
            quarterly_data[q1['end']] = q1['val']
        
        if q2_3m:
            quarterly_data[q2_3m['end']] = q2_3m['val']
        elif q2_cum and q1:
            quarterly_data[q2_cum['end']] = q2_cum['val'] - q1['val']
            
        if q3_3m:
            quarterly_data[q3_3m['end']] = q3_3m['val']
        elif q3_cum and q2_cum:
            quarterly_data[q3_cum['end']] = q3_cum['val'] - q2_cum['val']
            
        if q3_cum:
            quarterly_data[ann['end']] = fy_val - q3_cum['val']
        elif q3_3m and q2_cum:
            quarterly_data[ann['end']] = fy_val - (q2_cum['val'] + q3_3m['val'])

    # Fill any remaining 3m periods (e.g. current fiscal year's quarters)
    for q in quarterlies_3m:
        if q['end'] not in quarterly_data:
            quarterly_data[q['end']] = q['val']
            
    return annual_data, quarterly_data

def fetch_sec_financials(ticker_symbol: str):
    headers = {'User-Agent': 'InvestmentPortal admin@example.com'}
    # Get CIK
    resp = requests.get('https://www.sec.gov/files/company_tickers.json', headers=headers)
    if resp.status_code != 200:
        return []
    tickers_dict = resp.json()
    
    cik = None
    for key, val in tickers_dict.items():
        if val['ticker'] == ticker_symbol.upper():
            cik = str(val['cik_str']).zfill(10)
            break
            
    if not cik:
        return []

    facts_url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    facts_resp = requests.get(facts_url, headers=headers)
    if facts_resp.status_code != 200:
        return []
        
    facts = facts_resp.json()
    us_gaap = facts['facts'].get('us-gaap', {})

    def find_concept(possible_keys):
        for k in possible_keys:
            if k in us_gaap:
                return us_gaap[k]['units']['USD']
        return None

    rev_units = find_concept(['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'RevenueFromContractWithCustomerIncludingAssessedTax', 'SalesRevenueNet', 'SalesRevenueGoodsNet', 'SalesRevenueServicesNet'])
    op_units = find_concept(['OperatingIncomeLoss', 'OperatingProfit'])
    net_units = find_concept(['NetIncomeLoss', 'NetIncomeLossAvailableToCommonStockholdersBasic'])

    if not rev_units:
        return []

    rev_ann, rev_q = process_sec_concept(rev_units)
    op_ann, op_q = process_sec_concept(op_units)
    net_ann, net_q = process_sec_concept(net_units)

    financials = []
    
    # Annual
    for date, rev_val in rev_ann.items():
        op_val = op_ann.get(date, 0.0)
        net_val = net_ann.get(date, 0.0)
        gm = (op_val / rev_val * 100) if rev_val > 0 else 0.0
        financials.append({
            "period_type": "annual",
            "date": date,
            "revenue": rev_val,
            "operating_income": op_val,
            "net_income": net_val,
            "gross_margin": gm
        })
        
    # Quarterly
    for date, rev_val in rev_q.items():
        op_val = op_q.get(date, 0.0)
        net_val = net_q.get(date, 0.0)
        gm = (op_val / rev_val * 100) if rev_val > 0 else 0.0
        financials.append({
            "period_type": "quarterly",
            "date": date,
            "revenue": rev_val,
            "operating_income": op_val,
            "net_income": net_val,
            "gross_margin": gm
        })
        
    financials.sort(key=lambda x: x['date'])
    return financials

def fetch_financial_data(ticker_symbol: str):
    """
    Fetches up to 5 years of annual and quarterly financial data.
    First tries SEC EDGAR API, and falls back to yahooquery if failed.
    """
    try:
        sec_data = fetch_sec_financials(ticker_symbol)
        has_recent = any('2023' in x['date'] or '2024' in x['date'] or '2025' in x['date'] for x in sec_data) if sec_data else False
        if sec_data and len(sec_data) > 0 and has_recent:
            print(f"Successfully fetched financial data for {ticker_symbol} from SEC EDGAR API.")
            return sec_data
        else:
            print(f"SEC EDGAR data for {ticker_symbol} is missing or outdated. Trying yahooquery...")
    except Exception as e:
        print(f"Failed to fetch from SEC EDGAR API for {ticker_symbol}: {e}")

    # Fallback to yahooquery
    print(f"Falling back to yahooquery for {ticker_symbol}...")
    t = Ticker(ticker_symbol)
    financials = []
    
    try:
        annual_df = t.income_statement(frequency='a')
        if isinstance(annual_df, pd.DataFrame) and not annual_df.empty:
            if 'symbol' in annual_df.index.names:
                annual_df = annual_df.reset_index()
            
            for _, row in annual_df.iterrows():
                date = str(row['asOfDate'])[:10]
                rev = safe_get(row, ['TotalRevenue', 'OperatingRevenue'])
                op_inc = safe_get(row, ['OperatingIncome', 'TotalOperatingIncomeAsReported', 'EBIT'])
                net_inc = safe_get(row, ['NetIncome', 'NetIncomeCommonStockholders', 'NetIncomeContinuousOperations'])
                gross_margin = (op_inc / rev * 100) if rev and rev > 0 else 0.0
                
                financials.append({
                    "period_type": "annual",
                    "date": date,
                    "revenue": rev,
                    "operating_income": op_inc,
                    "net_income": net_inc,
                    "gross_margin": gross_margin
                })
    except Exception as e:
        print(f"Error fetching annual for {ticker_symbol} via yahooquery: {e}")

    try:
        quarterly_df = t.income_statement(frequency='q')
        if isinstance(quarterly_df, pd.DataFrame) and not quarterly_df.empty:
            if 'symbol' in quarterly_df.index.names:
                quarterly_df = quarterly_df.reset_index()
                
            for _, row in quarterly_df.iterrows():
                date = str(row['asOfDate'])[:10]
                rev = safe_get(row, ['TotalRevenue', 'OperatingRevenue'])
                op_inc = safe_get(row, ['OperatingIncome', 'TotalOperatingIncomeAsReported', 'EBIT'])
                net_inc = safe_get(row, ['NetIncome', 'NetIncomeCommonStockholders', 'NetIncomeContinuousOperations'])
                gross_margin = (op_inc / rev * 100) if rev and rev > 0 else 0.0
                
                financials.append({
                    "period_type": "quarterly",
                    "date": date,
                    "revenue": rev,
                    "operating_income": op_inc,
                    "net_income": net_inc,
                    "gross_margin": gross_margin
                })
    except Exception as e:
        print(f"Error fetching quarterly for {ticker_symbol} via yahooquery: {e}")

    return financials
