import sqlite3, yfinance as yf, math, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'investment_portal.db'

def safe_float(val):
    try:
        if val is None: return None
        f = float(val)
        if math.isnan(f) or math.isinf(f): return None
        return f
    except: return None

def try_keys(df, keys, col):
    for k in keys:
        try:
            if df is None or df.empty: continue
            if k not in df.index: continue
            v = df.loc[k, col]
            r = safe_float(v)
            if r is not None: return r
        except: continue
    return None

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for cid, name, ticker in [(34, 'Block (Square)', 'XYZ'), (42, 'Galaxy Digital', 'GLXY')]:
    print(f"\n[{cid}] {name} ({ticker})")
    t = yf.Ticker(ticker)
    try:
        inc_a = t.financials
        inc_q = t.quarterly_financials
        bs_a  = t.balance_sheet
        bs_q  = t.quarterly_balance_sheet
        cf_a  = t.cashflow
        cf_q  = t.quarterly_cashflow
        info  = t.info
    except Exception as e:
        print(f"  [ERR] {e}")
        continue

    # Profile
    price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"))
    profile = {
        'sector': info.get('sector'), 'industry_classification': info.get('industry'),
        'description': info.get('longBusinessSummary'), 'employees': info.get('fullTimeEmployees'),
        'website': info.get('website'), 'current_price': price,
        'market_cap': safe_float(info.get('marketCap')), 'beta': safe_float(info.get('beta')),
        'pe_ratio': safe_float(info.get('trailingPE')), 'pb_ratio': safe_float(info.get('priceToBook')),
        'ev_ebitda': safe_float(info.get('enterpriseToEbitda')), 'ev_sales': safe_float(info.get('enterpriseToRevenue')),
        'roe': safe_float(info.get('returnOnEquity')), 'roa': safe_float(info.get('returnOnAssets')),
        'gross_margin_ttm': safe_float(info.get('grossMargins')), 'op_margin_ttm': safe_float(info.get('operatingMargins')),
        'net_margin_ttm': safe_float(info.get('profitMargins')), 'revenue_growth': safe_float(info.get('revenueGrowth')),
        'eps_growth': safe_float(info.get('trailingEps')), 'current_ratio': safe_float(info.get('currentRatio')),
        'debt_to_equity': safe_float(info.get('debtToEquity')), 'dividend_yield': safe_float(info.get('dividendYield')),
        'payout_ratio': safe_float(info.get('payoutRatio')), 'last_updated': datetime.now().strftime('%Y-%m-%d'),
    }
    profile = {k: v for k, v in profile.items() if v is not None or k == 'last_updated'}
    
    cur.execute("SELECT id FROM company_profiles WHERE company_id=?", (cid,))
    if cur.fetchone():
        fields = ', '.join([f"{k}=?" for k in profile.keys()])
        cur.execute(f"UPDATE company_profiles SET {fields} WHERE company_id=?", list(profile.values()) + [cid])
    else:
        cols = ', '.join(['company_id'] + list(profile.keys()))
        ph = ', '.join(['?'] * (len(profile) + 1))
        cur.execute(f"INSERT INTO company_profiles ({cols}) VALUES ({ph})", [cid] + list(profile.values()))
    print(f"  [OK] profile: price=${price}, mktcap=${safe_float(info.get('marketCap'))/1e9:.1f}B" if price else "  [OK] profile saved")

    # Financials
    periods = []
    def process(date_col, ptype, inc, bs, cf):
        d = str(date_col)[:10]
        rev = try_keys(inc, ['Total Revenue', 'Revenue'], date_col)
        cogs = try_keys(inc, ['Cost Of Revenue'], date_col)
        gp = try_keys(inc, ['Gross Profit'], date_col)
        if gp is None and rev and cogs: gp = rev - cogs
        op_inc = try_keys(inc, ['Operating Income'], date_col)
        ebitda = try_keys(inc, ['EBITDA', 'Normalized EBITDA'], date_col)
        net_inc = try_keys(inc, ['Net Income', 'Net Income Common Stockholders'], date_col)
        eps = try_keys(inc, ['Diluted EPS', 'Basic EPS'], date_col)
        gpm = (gp/rev*100) if gp and rev else None
        opm = (op_inc/rev*100) if op_inc and rev else None
        npm = (net_inc/rev*100) if net_inc and rev else None
        ebitda_m = (ebitda/rev*100) if ebitda and rev else None
        total_assets = try_keys(bs, ['Total Assets'], date_col)
        cur_assets = try_keys(bs, ['Total Current Assets'], date_col)
        cash = try_keys(bs, ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments'], date_col)
        total_debt = try_keys(bs, ['Total Debt'], date_col)
        total_liab = try_keys(bs, ['Total Liabilities Net Minority Interest'], date_col)
        cur_liab = try_keys(bs, ['Total Current Liabilities'], date_col)
        equity = try_keys(bs, ['Stockholders Equity', 'Common Stock Equity'], date_col)
        net_debt = (total_debt - cash) if total_debt is not None and cash is not None else None
        cur_ratio = (cur_assets/cur_liab) if cur_assets and cur_liab and cur_liab != 0 else None
        de_ratio = (total_debt/equity*100) if total_debt is not None and equity and equity != 0 else None
        roe = (net_inc/equity*100) if net_inc is not None and equity and equity != 0 else None
        roa = (net_inc/total_assets*100) if net_inc is not None and total_assets and total_assets != 0 else None
        ocf = try_keys(cf, ['Operating Cash Flow'], date_col)
        capex = try_keys(cf, ['Capital Expenditure', 'Capital Expenditures'], date_col)
        fcf = try_keys(cf, ['Free Cash Flow'], date_col)
        if fcf is None and ocf is not None and capex is not None: fcf = ocf + capex
        fcf_margin = (fcf/rev*100) if fcf is not None and rev else None
        periods.append({'date':d,'period_type':ptype,'fiscal_year':d[:4],
            'revenue':rev,'cost_of_revenue':cogs,'gross_profit':gp,'operating_income':op_inc,
            'ebitda':ebitda,'net_income':net_inc,'eps':eps,'gross_margin':gpm,'op_margin':opm,
            'net_margin':npm,'ebitda_margin':ebitda_m,'total_assets':total_assets,
            'total_current_assets':cur_assets,'cash_and_equivalents':cash,'total_debt':total_debt,
            'total_liabilities':total_liab,'total_current_liabilities':cur_liab,
            'shareholders_equity':equity,'net_debt':net_debt,'current_ratio':cur_ratio,
            'debt_to_equity_ratio':de_ratio,'operating_cash_flow':ocf,'capital_expenditure':capex,
            'free_cash_flow':fcf,'roe':roe,'roa':roa,'fcf_margin':fcf_margin})

    if inc_a is not None and not inc_a.empty:
        for col in inc_a.columns: process(col, 'annual', inc_a, bs_a, cf_a)
    if inc_q is not None and not inc_q.empty:
        for col in inc_q.columns: process(col, 'quarterly', inc_q, bs_q, cf_q)

    saved = 0
    for p in periods:
        cur.execute("SELECT id FROM financial_data WHERE company_id=? AND date=? AND period_type=?",
                    (cid, p['date'], p['period_type']))
        if not cur.fetchone():
            try:
                cur.execute("""INSERT INTO financial_data (company_id,date,period_type,fiscal_year,
                    revenue,cost_of_revenue,gross_profit,operating_income,ebitda,net_income,eps,
                    gross_margin,op_margin,net_margin,ebitda_margin,total_assets,total_current_assets,
                    cash_and_equivalents,total_debt,total_liabilities,total_current_liabilities,
                    shareholders_equity,net_debt,current_ratio,debt_to_equity_ratio,
                    operating_cash_flow,capital_expenditure,free_cash_flow,roe,roa,fcf_margin)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (cid,p['date'],p['period_type'],p['fiscal_year'],p['revenue'],p['cost_of_revenue'],
                     p['gross_profit'],p['operating_income'],p['ebitda'],p['net_income'],p['eps'],
                     p['gross_margin'],p['op_margin'],p['net_margin'],p['ebitda_margin'],
                     p['total_assets'],p['total_current_assets'],p['cash_and_equivalents'],
                     p['total_debt'],p['total_liabilities'],p['total_current_liabilities'],
                     p['shareholders_equity'],p['net_debt'],p['current_ratio'],p['debt_to_equity_ratio'],
                     p['operating_cash_flow'],p['capital_expenditure'],p['free_cash_flow'],
                     p['roe'],p['roa'],p['fcf_margin']))
                saved += 1
            except Exception as e:
                print(f"    [WARN] {e}")
    print(f"  [OK] financials: {len(periods)} periods, {saved} saved")

conn.commit()
conn.close()
print("\nDone!")
