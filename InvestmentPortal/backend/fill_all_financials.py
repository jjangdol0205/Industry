# -*- coding: utf-8 -*-
"""
전체 기업 재무제표 전수 수집 스크립트 v4
- UPSERT 방식: 기존 데이터 보존 + 신규 데이터 추가/업데이트
- 더 넓은 날짜 범위 지원
"""
import sqlite3
import yfinance as yf
from datetime import datetime
import time
import math

DB_PATH = 'investment_portal.db'

def safe_float(val):
    try:
        if val is None: return None
        f = float(val)
        if math.isnan(f) or math.isinf(f): return None
        return f
    except:
        return None

def try_keys(df, keys, col):
    for k in keys:
        try:
            if df is None or df.empty: continue
            if k not in df.index: continue
            v = df.loc[k, col]
            r = safe_float(v)
            if r is not None: return r
        except:
            continue
    return None

def fetch_data(ticker_str):
    t = yf.Ticker(ticker_str)
    try:
        inc_a = t.financials
        inc_q = t.quarterly_financials
        bs_a  = t.balance_sheet
        bs_q  = t.quarterly_balance_sheet
        cf_a  = t.cashflow
        cf_q  = t.quarterly_cashflow
        info  = t.info
    except Exception as e:
        print(f"  [ERR] fetch failed: {e}")
        return [], {}

    periods = []

    def process(date_col, ptype, inc, bs, cf):
        d = str(date_col)[:10]
        rev   = try_keys(inc, ['Total Revenue', 'Revenue'], date_col)
        cogs  = try_keys(inc, ['Cost Of Revenue', 'Cost of Revenue'], date_col)
        gp    = try_keys(inc, ['Gross Profit'], date_col)
        if gp is None and rev and cogs: gp = rev - cogs
        op_inc = try_keys(inc, ['Operating Income', 'Operating Revenue'], date_col)
        ebitda = try_keys(inc, ['EBITDA', 'Normalized EBITDA'], date_col)
        net_inc = try_keys(inc, [
            'Net Income', 'Net Income Common Stockholders',
            'Net Income Including Noncontrolling Interests'
        ], date_col)
        eps = try_keys(inc, ['Diluted EPS', 'Basic EPS', 'Normalized Diluted EPS'], date_col)

        gpm = (gp / rev * 100) if gp is not None and rev else None
        opm = (op_inc / rev * 100) if op_inc is not None and rev else None
        npm = (net_inc / rev * 100) if net_inc is not None and rev else None
        ebitda_m = (ebitda / rev * 100) if ebitda is not None and rev else None

        total_assets = try_keys(bs, ['Total Assets'], date_col)
        cur_assets = try_keys(bs, ['Total Current Assets', 'Current Assets'], date_col)
        cash = try_keys(bs, [
            'Cash And Cash Equivalents',
            'Cash Cash Equivalents And Short Term Investments',
            'Cash And Cash Equivalents And Short Term Investments'
        ], date_col)
        total_debt = try_keys(bs, ['Total Debt', 'Long Term Debt And Capital Lease Obligation'], date_col)
        total_liab = try_keys(bs, ['Total Liabilities Net Minority Interest', 'Total Liabilities'], date_col)
        cur_liab = try_keys(bs, ['Total Current Liabilities', 'Current Liabilities'], date_col)
        equity = try_keys(bs, [
            'Stockholders Equity', 'Common Stock Equity',
            'Total Equity Gross Minority Interest'
        ], date_col)
        net_debt = (total_debt - cash) if total_debt is not None and cash is not None else None
        cur_ratio = (cur_assets / cur_liab) if cur_assets and cur_liab and cur_liab != 0 else None
        de_ratio  = (total_debt / equity * 100) if total_debt is not None and equity and equity != 0 else None
        roe = (net_inc / equity * 100) if net_inc is not None and equity and equity != 0 else None
        roa = (net_inc / total_assets * 100) if net_inc is not None and total_assets and total_assets != 0 else None

        ocf = try_keys(cf, ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities'], date_col)
        capex = try_keys(cf, [
            'Capital Expenditure', 'Capital Expenditures',
            'Purchase Of Property Plant And Equipment'
        ], date_col)
        fcf = try_keys(cf, ['Free Cash Flow'], date_col)
        if fcf is None and ocf is not None and capex is not None:
            fcf = ocf + capex
        fcf_margin = (fcf / rev * 100) if fcf is not None and rev else None

        periods.append({
            'date': d, 'period_type': ptype, 'fiscal_year': d[:4],
            'revenue': rev, 'cost_of_revenue': cogs, 'gross_profit': gp,
            'operating_income': op_inc, 'ebitda': ebitda,
            'net_income': net_inc, 'eps': eps,
            'gross_margin': gpm, 'op_margin': opm,
            'net_margin': npm, 'ebitda_margin': ebitda_m,
            'total_assets': total_assets, 'total_current_assets': cur_assets,
            'cash_and_equivalents': cash, 'total_debt': total_debt,
            'total_liabilities': total_liab, 'total_current_liabilities': cur_liab,
            'shareholders_equity': equity, 'net_debt': net_debt,
            'current_ratio': cur_ratio, 'debt_to_equity_ratio': de_ratio,
            'operating_cash_flow': ocf, 'capital_expenditure': capex,
            'free_cash_flow': fcf, 'roe': roe, 'roa': roa, 'fcf_margin': fcf_margin,
        })

    if inc_a is not None and not inc_a.empty:
        for col in inc_a.columns:
            process(col, 'annual', inc_a, bs_a, cf_a)
    if inc_q is not None and not inc_q.empty:
        for col in inc_q.columns:
            process(col, 'quarterly', inc_q, bs_q, cf_q)

    return periods, info

def update_profile(cur, company_id, info):
    if not info: return
    price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"))
    profile = {
        'sector': info.get('sector'),
        'industry_classification': info.get('industry'),
        'description': info.get('longBusinessSummary'),
        'employees': info.get('fullTimeEmployees'),
        'website': info.get('website'),
        'current_price': price,
        'market_cap': safe_float(info.get('marketCap')),
        'beta': safe_float(info.get('beta')),
        'pe_ratio': safe_float(info.get('trailingPE')),
        'pb_ratio': safe_float(info.get('priceToBook')),
        'ev_ebitda': safe_float(info.get('enterpriseToEbitda')),
        'ev_sales': safe_float(info.get('enterpriseToRevenue')),
        'roe': safe_float(info.get('returnOnEquity')),
        'roa': safe_float(info.get('returnOnAssets')),
        'gross_margin_ttm': safe_float(info.get('grossMargins')),
        'op_margin_ttm': safe_float(info.get('operatingMargins')),
        'net_margin_ttm': safe_float(info.get('profitMargins')),
        'revenue_growth': safe_float(info.get('revenueGrowth')),
        'eps_growth': safe_float(info.get('trailingEps')),
        'current_ratio': safe_float(info.get('currentRatio')),
        'debt_to_equity': safe_float(info.get('debtToEquity')),
        'dividend_yield': safe_float(info.get('dividendYield')),
        'payout_ratio': safe_float(info.get('payoutRatio')),
        'last_updated': datetime.now().strftime('%Y-%m-%d'),
    }
    # None 필드 제외
    profile = {k: v for k, v in profile.items() if v is not None or k in ('last_updated',)}
    
    cur.execute("SELECT id FROM company_profiles WHERE company_id=?", (company_id,))
    if cur.fetchone():
        fields = ', '.join([f"{k}=?" for k in profile.keys()])
        cur.execute(f"UPDATE company_profiles SET {fields} WHERE company_id=?",
                    list(profile.values()) + [company_id])
    else:
        cols = ', '.join(['company_id'] + list(profile.keys()))
        ph = ', '.join(['?'] * (len(profile) + 1))
        cur.execute(f"INSERT INTO company_profiles ({cols}) VALUES ({ph})",
                    [company_id] + list(profile.values()))

def upsert_financials(cur, company_id, periods):
    """UPSERT 방식: 기존 데이터 보존, 새 데이터 추가/업데이트"""
    new_count = 0
    update_count = 0
    
    for p in periods:
        # 기존 레코드 확인 (company_id + date + period_type로 식별)
        cur.execute(
            "SELECT id FROM financial_data WHERE company_id=? AND date=? AND period_type=?",
            (company_id, p['date'], p['period_type'])
        )
        existing = cur.fetchone()
        
        try:
            if existing:
                # UPDATE - 새 값으로 덮어쓰기 (revenue가 있는 경우만)
                if p['revenue'] is not None:
                    cur.execute("""
                        UPDATE financial_data SET
                            revenue=?, cost_of_revenue=?, gross_profit=?, operating_income=?,
                            ebitda=?, net_income=?, eps=?,
                            gross_margin=?, op_margin=?, net_margin=?, ebitda_margin=?,
                            total_assets=?, total_current_assets=?, cash_and_equivalents=?,
                            total_debt=?, total_liabilities=?, total_current_liabilities=?,
                            shareholders_equity=?, net_debt=?,
                            current_ratio=?, debt_to_equity_ratio=?,
                            operating_cash_flow=?, capital_expenditure=?, free_cash_flow=?,
                            roe=?, roa=?, fcf_margin=?
                        WHERE company_id=? AND date=? AND period_type=?
                    """, (
                        p['revenue'], p['cost_of_revenue'], p['gross_profit'],
                        p['operating_income'], p['ebitda'], p['net_income'], p['eps'],
                        p['gross_margin'], p['op_margin'], p['net_margin'], p['ebitda_margin'],
                        p['total_assets'], p['total_current_assets'], p['cash_and_equivalents'],
                        p['total_debt'], p['total_liabilities'], p['total_current_liabilities'],
                        p['shareholders_equity'], p['net_debt'],
                        p['current_ratio'], p['debt_to_equity_ratio'],
                        p['operating_cash_flow'], p['capital_expenditure'], p['free_cash_flow'],
                        p['roe'], p['roa'], p['fcf_margin'],
                        company_id, p['date'], p['period_type']
                    ))
                    update_count += 1
            else:
                # INSERT
                cur.execute("""
                    INSERT INTO financial_data (
                        company_id, date, period_type, fiscal_year,
                        revenue, cost_of_revenue, gross_profit, operating_income, ebitda, net_income, eps,
                        gross_margin, op_margin, net_margin, ebitda_margin,
                        total_assets, total_current_assets, cash_and_equivalents,
                        total_debt, total_liabilities, total_current_liabilities,
                        shareholders_equity, net_debt,
                        current_ratio, debt_to_equity_ratio,
                        operating_cash_flow, capital_expenditure, free_cash_flow,
                        roe, roa, fcf_margin
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    company_id, p['date'], p['period_type'], p['fiscal_year'],
                    p['revenue'], p['cost_of_revenue'], p['gross_profit'],
                    p['operating_income'], p['ebitda'], p['net_income'], p['eps'],
                    p['gross_margin'], p['op_margin'], p['net_margin'], p['ebitda_margin'],
                    p['total_assets'], p['total_current_assets'], p['cash_and_equivalents'],
                    p['total_debt'], p['total_liabilities'], p['total_current_liabilities'],
                    p['shareholders_equity'], p['net_debt'],
                    p['current_ratio'], p['debt_to_equity_ratio'],
                    p['operating_cash_flow'], p['capital_expenditure'], p['free_cash_flow'],
                    p['roe'], p['roa'], p['fcf_margin'],
                ))
                new_count += 1
        except Exception as e:
            print(f"  [WARN] {p['date']} {p['period_type']}: {e}")
    
    return new_count, update_count

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, name, ticker FROM companies ORDER BY id")
    companies = cur.fetchall()

    print(f"=== {len(companies)} companies - UPSERT financial data ===")
    print("="*70)

    results = []

    for cid, name, ticker in companies:
        print(f"\n[{cid}/{len(companies)}] {name} ({ticker})")

        # MAXR 상장폐지 - 히스토리 데이터 시도
        if ticker == 'MAXR':
            print("  [INFO] MAXR delisted in 2023. Trying historical data...")

        try:
            periods, info = fetch_data(ticker)
        except Exception as e:
            print(f"  [ERR] {e}")
            results.append((cid, name, ticker, 0, 0, 0))
            time.sleep(2)
            continue

        annual_c = len([p for p in periods if p['period_type'] == 'annual'])
        quarter_c = len([p for p in periods if p['period_type'] == 'quarterly'])

        try:
            update_profile(cur, cid, info)
        except Exception as e:
            print(f"  [WARN] profile error: {e}")

        new_c, upd_c = upsert_financials(cur, cid, periods)
        conn.commit()

        price_str = "N/A"
        if info:
            p = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            if p: price_str = f"${p:.2f}"

        print(f"  [OK] annual={annual_c}, quarterly={quarter_c} | new={new_c}, updated={upd_c} | price={price_str}")
        results.append((cid, name, ticker, annual_c, quarter_c, new_c + upd_c))

        time.sleep(2)

    conn.close()

    print("\n" + "="*70)
    print("=== FINAL RESULTS ===")
    print(f'{"ID":<4} {"Company":<32} {"Ticker":<8} {"Annual":<8} {"Qtr":<6} {"Added/Upd"}')
    print("-"*65)
    ok = 0
    fail = 0
    for r in results:
        status = "[OK]" if r[3] > 0 else "[FAIL]"
        print(f'{status} {r[0]:<4} {r[1]:<32} {r[2]:<8} {r[3]:<8} {r[4]:<6} {r[5]}')
        if r[3] > 0: ok += 1
        else: fail += 1
    print(f"\nSuccess={ok}, No annual data={fail}")

if __name__ == "__main__":
    main()
