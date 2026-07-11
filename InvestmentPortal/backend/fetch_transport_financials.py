"""
운송 산업 기업 재무 데이터 수집 스크립트
"""
import sqlite3, sys, math, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), 'investment_portal.db')

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance -q")
    import yfinance as yf

def safe(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except:
        return None

TRANSPORT_TICKERS = [
    '011200.KS', '003490.KS', '086280.KS', '000120.KS', '028670.KS',
    'FDX', 'UPS', 'JBHT', 'ODFL', 'XPO', 'AMKBY',
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for ticker in TRANSPORT_TICKERS:
    cur.execute('SELECT id, name FROM companies WHERE ticker=?', (ticker,))
    row = cur.fetchone()
    if not row:
        print(f'[SKIP] {ticker} not in DB')
        continue
    comp_id, name = row
    print(f'\n=== {name} ({ticker}) ===')

    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}

        # ── Profile ────────────────────────────────────────────────
        cur.execute('SELECT id FROM company_profiles WHERE company_id=?', (comp_id,))
        existing = cur.fetchone()
        profile_data = (
            comp_id,
            info.get('sector'),
            safe(info.get('marketCap')),
            safe(info.get('currentPrice') or info.get('regularMarketPrice')),
            safe(info.get('trailingPE') or info.get('forwardPE')),
            safe(info.get('priceToBook')),
            safe(info.get('enterpriseToEbitda')),
            safe(info.get('returnOnEquity')),
            safe(info.get('returnOnAssets')),
            safe(info.get('grossMargins')),
            safe(info.get('operatingMargins')),
            safe(info.get('profitMargins')),
            safe(info.get('revenueGrowth')),
            safe(info.get('earningsGrowth')),
            safe(info.get('fcfToMarketCap') or info.get('freeCashflow') and info.get('marketCap') and
                 safe(info['freeCashflow']) / safe(info['marketCap'])),
            safe(info.get('debtToEquity')),
            safe(info.get('currentRatio')),
            safe(info.get('dividendYield')),
        )
        if not existing:
            cur.execute('''INSERT INTO company_profiles
              (company_id, sector, market_cap, current_price, pe_ratio, pb_ratio,
               ev_ebitda, roe, roa, gross_margin_ttm, op_margin_ttm, net_margin_ttm,
               revenue_growth, eps_growth, fcf_growth, debt_to_equity, current_ratio,
               dividend_yield, last_updated)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))''', profile_data)
            print(f'  [OK] profile inserted')
        else:
            cur.execute('''UPDATE company_profiles SET
              sector=?, market_cap=?, current_price=?, pe_ratio=?, pb_ratio=?,
              ev_ebitda=?, roe=?, roa=?, gross_margin_ttm=?, op_margin_ttm=?,
              net_margin_ttm=?, revenue_growth=?, eps_growth=?, fcf_growth=?,
              debt_to_equity=?, current_ratio=?, dividend_yield=?,
              last_updated=datetime('now')
              WHERE company_id=?''', profile_data[1:] + (comp_id,))
            print(f'  [OK] profile updated')

        # ── Annual Financials ───────────────────────────────────────
        try:
            fin = tk.financials   # columns: dates, rows: metrics
            cf  = tk.cashflow
            bs  = tk.balance_sheet

            if fin is not None and not fin.empty:
                for col in fin.columns:
                    yr = str(col)[:4]
                    date_str = yr + '-12-31'

                    def get_row(df, *names):
                        if df is None: return None
                        for n in names:
                            if n in df.index:
                                return safe(df.loc[n, col]) if col in df.columns else None
                        return None

                    rev   = get_row(fin, 'Total Revenue', 'Revenue')
                    gp    = get_row(fin, 'Gross Profit')
                    oi    = get_row(fin, 'Operating Income', 'EBIT')
                    ni    = get_row(fin, 'Net Income', 'Net Income Common Stockholders')
                    ocf   = get_row(cf,  'Operating Cash Flow', 'Total Cash From Operating Activities')
                    capex = get_row(cf,  'Capital Expenditure', 'Capital Expenditures')
                    fcf   = (ocf + capex) if ocf is not None and capex is not None else None
                    ta    = get_row(bs,  'Total Assets')
                    te    = get_row(bs,  'Stockholders Equity', 'Total Equity Gross Minority Interest')
                    td    = get_row(bs,  'Total Debt', 'Long Term Debt')
                    cash  = get_row(bs,  'Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments')

                    gm = (gp/rev) if gp and rev and rev>0 else None
                    om = (oi/rev) if oi and rev and rev>0 else None
                    nm = (ni/rev) if ni and rev and rev>0 else None
                    fm = (fcf/rev) if fcf and rev and rev>0 else None

                    cur.execute('SELECT id FROM financial_data WHERE company_id=? AND date=? AND period_type=?',
                                (comp_id, date_str, 'annual'))
                    if cur.fetchone():
                        cur.execute('''UPDATE financial_data SET
                          revenue=?, gross_profit=?, operating_income=?, net_income=?,
                          operating_cash_flow=?, capital_expenditure=?, free_cash_flow=?,
                          gross_margin=?, op_margin=?, net_margin=?, fcf_margin=?,
                          total_assets=?, shareholders_equity=?, total_debt=?, cash_and_equivalents=?
                          WHERE company_id=? AND date=? AND period_type=?''',
                          (rev,gp,oi,ni,ocf,capex,fcf,gm,om,nm,fm,ta,te,td,cash,
                           comp_id, date_str, 'annual'))
                    else:
                        cur.execute('''INSERT INTO financial_data
                          (company_id, date, period_type, revenue, gross_profit, operating_income, net_income,
                           operating_cash_flow, capital_expenditure, free_cash_flow,
                           gross_margin, op_margin, net_margin, fcf_margin,
                           total_assets, shareholders_equity, total_debt, cash_and_equivalents)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (comp_id, date_str, 'annual', rev,gp,oi,ni,ocf,capex,fcf,gm,om,nm,fm,ta,te,td,cash))
                print(f'  [OK] {len(fin.columns)} years of financials inserted/updated')
            else:
                print(f'  [WARN] No annual financials')
        except Exception as fe:
            print(f'  [WARN] financials error: {fe}')

        conn.commit()

    except Exception as e:
        print(f'  [ERR] {e}')

conn.close()
print('\n=== 운송 산업 재무 데이터 수집 완료 ===')
