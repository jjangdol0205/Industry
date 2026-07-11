"""HMM, 팬오션 프로필 데이터 업데이트"""
import sqlite3, yfinance as yf, math, sys, os
sys.stdout.reconfigure(encoding='utf-8')
DB = os.path.join(os.path.dirname(__file__), 'investment_portal.db')

def safe(v):
    try: f = float(v); return None if math.isnan(f) or math.isinf(f) else f
    except: return None

conn = sqlite3.connect(DB)
cur = conn.cursor()

for ticker in ['011200.KS', '028670.KS']:
    cur.execute('SELECT id, name FROM companies WHERE ticker=?', (ticker,))
    r = cur.fetchone()
    if not r:
        print(f'{ticker} not in DB')
        continue
    comp_id, name = r
    print(f'\n{name} ({ticker})')
    tk = yf.Ticker(ticker)
    info = tk.info or {}
    
    rev_g = safe(info.get('revenueGrowth'))
    opm   = safe(info.get('operatingMargins'))
    roe   = safe(info.get('returnOnEquity'))
    print(f'  yfinance: rev_growth={rev_g}, opm={opm}, roe={roe}')

    cur.execute('SELECT id FROM company_profiles WHERE company_id=?', (comp_id,))
    existing = cur.fetchone()
    if existing:
        cur.execute('''UPDATE company_profiles SET
          current_price=?, revenue_growth=?, op_margin_ttm=?,
          net_margin_ttm=?, roe=?, roa=?,
          pe_ratio=?, pb_ratio=?, market_cap=?,
          gross_margin_ttm=?, debt_to_equity=?, last_updated=datetime('now')
          WHERE company_id=?''', (
            safe(info.get('currentPrice') or info.get('regularMarketPrice')),
            rev_g, opm,
            safe(info.get('profitMargins')),
            roe, safe(info.get('returnOnAssets')),
            safe(info.get('trailingPE') or info.get('forwardPE')),
            safe(info.get('priceToBook')),
            safe(info.get('marketCap')),
            safe(info.get('grossMargins')),
            safe(info.get('debtToEquity')),
            comp_id,
        ))
        print(f'  Updated existing profile')
    else:
        cur.execute('''INSERT INTO company_profiles
          (company_id, sector, market_cap, current_price, pe_ratio, pb_ratio,
           ev_ebitda, roe, roa, gross_margin_ttm, op_margin_ttm, net_margin_ttm,
           revenue_growth, eps_growth, debt_to_equity, current_ratio, dividend_yield,
           last_updated)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))''', (
            comp_id, info.get('sector'),
            safe(info.get('marketCap')),
            safe(info.get('currentPrice') or info.get('regularMarketPrice')),
            safe(info.get('trailingPE') or info.get('forwardPE')),
            safe(info.get('priceToBook')),
            safe(info.get('enterpriseToEbitda')),
            roe, safe(info.get('returnOnAssets')),
            safe(info.get('grossMargins')), opm,
            safe(info.get('profitMargins')), rev_g,
            safe(info.get('earningsGrowth')),
            safe(info.get('debtToEquity')),
            safe(info.get('currentRatio')),
            safe(info.get('dividendYield')),
        ))
        print(f'  Inserted new profile')

conn.commit()
conn.close()
print('\nDone')
