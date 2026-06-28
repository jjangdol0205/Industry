# -*- coding: utf-8 -*-
"""
문제 종목 제거 + 대체 종목 추가 + 재무 데이터 수집
LAZR(상장폐지), AGIX(비상장), LICY(파산), ABB(스위스/데이터없음) 처리
"""
import sqlite3
import yfinance as yf
from datetime import datetime
import time
import math
import sys
sys.stdout.reconfigure(encoding='utf-8')

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
        rev    = try_keys(inc, ['Total Revenue', 'Revenue'], date_col)
        cogs   = try_keys(inc, ['Cost Of Revenue', 'Cost of Revenue'], date_col)
        gp     = try_keys(inc, ['Gross Profit'], date_col)
        if gp is None and rev and cogs: gp = rev - cogs
        op_inc = try_keys(inc, ['Operating Income', 'Operating Revenue'], date_col)
        ebitda = try_keys(inc, ['EBITDA', 'Normalized EBITDA'], date_col)
        net_inc = try_keys(inc, ['Net Income', 'Net Income Common Stockholders', 'Net Income Including Noncontrolling Interests'], date_col)
        eps = try_keys(inc, ['Diluted EPS', 'Basic EPS', 'Normalized Diluted EPS'], date_col)
        gpm = (gp/rev*100) if gp and rev else None
        opm = (op_inc/rev*100) if op_inc and rev else None
        npm = (net_inc/rev*100) if net_inc and rev else None
        ebitda_m = (ebitda/rev*100) if ebitda and rev else None
        total_assets = try_keys(bs, ['Total Assets'], date_col)
        cur_assets = try_keys(bs, ['Total Current Assets', 'Current Assets'], date_col)
        cash = try_keys(bs, ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments'], date_col)
        total_debt = try_keys(bs, ['Total Debt', 'Long Term Debt And Capital Lease Obligation'], date_col)
        total_liab = try_keys(bs, ['Total Liabilities Net Minority Interest', 'Total Liabilities'], date_col)
        cur_liab = try_keys(bs, ['Total Current Liabilities', 'Current Liabilities'], date_col)
        equity = try_keys(bs, ['Stockholders Equity', 'Common Stock Equity', 'Total Equity Gross Minority Interest'], date_col)
        net_debt = (total_debt - cash) if total_debt and cash else None
        cur_ratio = (cur_assets / cur_liab) if cur_assets and cur_liab and cur_liab != 0 else None
        de_ratio = (total_debt / equity * 100) if total_debt and equity and equity != 0 else None
        roe = (net_inc / equity * 100) if net_inc and equity and equity != 0 else None
        roa = (net_inc / total_assets * 100) if net_inc and total_assets and total_assets != 0 else None
        ocf = try_keys(cf, ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities'], date_col)
        capex = try_keys(cf, ['Capital Expenditure', 'Capital Expenditures', 'Purchase Of Property Plant And Equipment'], date_col)
        fcf = try_keys(cf, ['Free Cash Flow'], date_col)
        if fcf is None and ocf is not None and capex is not None: fcf = ocf + capex
        fcf_margin = (fcf/rev*100) if fcf and rev else None
        periods.append({
            'date': d, 'period_type': ptype, 'fiscal_year': d[:4],
            'revenue': rev, 'cost_of_revenue': cogs, 'gross_profit': gp,
            'operating_income': op_inc, 'ebitda': ebitda, 'net_income': net_inc, 'eps': eps,
            'gross_margin': gpm, 'op_margin': opm, 'net_margin': npm, 'ebitda_margin': ebitda_m,
            'total_assets': total_assets, 'total_current_assets': cur_assets,
            'cash_and_equivalents': cash, 'total_debt': total_debt,
            'total_liabilities': total_liab, 'total_current_liabilities': cur_liab,
            'shareholders_equity': equity, 'net_debt': net_debt,
            'current_ratio': cur_ratio, 'debt_to_equity_ratio': de_ratio,
            'operating_cash_flow': ocf, 'capital_expenditure': capex,
            'free_cash_flow': fcf, 'roe': roe, 'roa': roa, 'fcf_margin': fcf_margin,
        })

    if inc_a is not None and not inc_a.empty:
        for col in inc_a.columns: process(col, 'annual', inc_a, bs_a, cf_a)
    if inc_q is not None and not inc_q.empty:
        for col in inc_q.columns: process(col, 'quarterly', inc_q, bs_q, cf_q)
    return periods, info

def update_profile(cur, company_id, info):
    if not info: return
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
    cur.execute("SELECT id FROM company_profiles WHERE company_id=?", (company_id,))
    if cur.fetchone():
        fields = ', '.join([f"{k}=?" for k in profile.keys()])
        cur.execute(f"UPDATE company_profiles SET {fields} WHERE company_id=?", list(profile.values()) + [company_id])
    else:
        cols = ', '.join(['company_id'] + list(profile.keys()))
        ph = ', '.join(['?'] * (len(profile) + 1))
        cur.execute(f"INSERT INTO company_profiles ({cols}) VALUES ({ph})", [company_id] + list(profile.values()))

def upsert_financials(cur, company_id, periods):
    new_c = upd_c = 0
    for p in periods:
        cur.execute("SELECT id FROM financial_data WHERE company_id=? AND date=? AND period_type=?",
                    (company_id, p['date'], p['period_type']))
        existing = cur.fetchone()
        try:
            if existing:
                if p['revenue'] is not None:
                    cur.execute("""
                        UPDATE financial_data SET revenue=?,cost_of_revenue=?,gross_profit=?,operating_income=?,
                        ebitda=?,net_income=?,eps=?,gross_margin=?,op_margin=?,net_margin=?,ebitda_margin=?,
                        total_assets=?,total_current_assets=?,cash_and_equivalents=?,total_debt=?,total_liabilities=?,
                        total_current_liabilities=?,shareholders_equity=?,net_debt=?,current_ratio=?,
                        debt_to_equity_ratio=?,operating_cash_flow=?,capital_expenditure=?,free_cash_flow=?,
                        roe=?,roa=?,fcf_margin=? WHERE company_id=? AND date=? AND period_type=?
                    """, (p['revenue'],p['cost_of_revenue'],p['gross_profit'],p['operating_income'],
                          p['ebitda'],p['net_income'],p['eps'],p['gross_margin'],p['op_margin'],
                          p['net_margin'],p['ebitda_margin'],p['total_assets'],p['total_current_assets'],
                          p['cash_and_equivalents'],p['total_debt'],p['total_liabilities'],
                          p['total_current_liabilities'],p['shareholders_equity'],p['net_debt'],
                          p['current_ratio'],p['debt_to_equity_ratio'],p['operating_cash_flow'],
                          p['capital_expenditure'],p['free_cash_flow'],p['roe'],p['roa'],p['fcf_margin'],
                          company_id,p['date'],p['period_type']))
                    upd_c += 1
            else:
                cur.execute("""
                    INSERT INTO financial_data (company_id,date,period_type,fiscal_year,
                    revenue,cost_of_revenue,gross_profit,operating_income,ebitda,net_income,eps,
                    gross_margin,op_margin,net_margin,ebitda_margin,total_assets,total_current_assets,
                    cash_and_equivalents,total_debt,total_liabilities,total_current_liabilities,
                    shareholders_equity,net_debt,current_ratio,debt_to_equity_ratio,
                    operating_cash_flow,capital_expenditure,free_cash_flow,roe,roa,fcf_margin
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (company_id,p['date'],p['period_type'],p['fiscal_year'],
                      p['revenue'],p['cost_of_revenue'],p['gross_profit'],p['operating_income'],
                      p['ebitda'],p['net_income'],p['eps'],p['gross_margin'],p['op_margin'],
                      p['net_margin'],p['ebitda_margin'],p['total_assets'],p['total_current_assets'],
                      p['cash_and_equivalents'],p['total_debt'],p['total_liabilities'],
                      p['total_current_liabilities'],p['shareholders_equity'],p['net_debt'],
                      p['current_ratio'],p['debt_to_equity_ratio'],p['operating_cash_flow'],
                      p['capital_expenditure'],p['free_cash_flow'],p['roe'],p['roa'],p['fcf_margin']))
                new_c += 1
        except Exception as e:
            print(f"  [WARN] {p['date']} {p['period_type']}: {e}")
    return new_c, upd_c

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ================================================================
    # Step 1: 문제 종목 제거
    # ================================================================
    bad_tickers = {
        'LAZR': '상장폐지 (May Mobility 인수)',
        'AGIX': '비상장(Private) 기업',
        'LICY': '파산/상장폐지',
        'ABB':  '스위스 기업, yfinance 재무데이터 없음',
    }
    print("=== Step 1: 문제 종목 제거 ===")
    for ticker, reason in bad_tickers.items():
        cur.execute("SELECT id FROM companies WHERE ticker=?", (ticker,))
        row = cur.fetchone()
        if row:
            cid = row[0]
            cur.execute("DELETE FROM financial_data WHERE company_id=?", (cid,))
            cur.execute("DELETE FROM company_profiles WHERE company_id=?", (cid,))
            cur.execute("DELETE FROM companies WHERE id=?", (cid,))
            print(f"  [DEL] {ticker} ({reason})")
        else:
            print(f"  [SKIP] {ticker} not found")
    conn.commit()

    # ================================================================
    # Step 2: 대체 종목 추가
    # ================================================================
    print("\n=== Step 2: 대체 종목 추가 ===")

    # 자율주행 노드
    cur.execute("SELECT id FROM value_chain_nodes WHERE industry_id=1 LIMIT 1")
    node_av = cur.fetchone()[0]
    # 로봇 노드
    cur.execute("SELECT id FROM value_chain_nodes WHERE industry_id=2 LIMIT 1")
    node_robot = cur.fetchone()[0]
    # 이차전지 업스트림 노드
    cur.execute("SELECT id FROM value_chain_nodes WHERE industry_id=7 ORDER BY id LIMIT 1")
    node_batt_up = cur.fetchone()[0]
    # 이차전지 다운스트림 노드
    cur.execute("SELECT id FROM value_chain_nodes WHERE industry_id=7 ORDER BY id LIMIT 1 OFFSET 2")
    row_batt_down = cur.fetchone()
    node_batt_down = row_batt_down[0] if row_batt_down else node_batt_up
    # 이차전지 리사이클링 노드
    cur.execute("SELECT id FROM value_chain_nodes WHERE industry_id=7 ORDER BY id LIMIT 1 OFFSET 3")
    row_batt_recycle = cur.fetchone()
    node_batt_recycle = row_batt_recycle[0] if row_batt_recycle else node_batt_up

    replacements = [
        # LAZR 대체 → OUST (Ouster) - 살아있는 라이다 기업
        ('Ouster', 'OUST', 1, node_av,
         'Ouster — 디지털 라이다(LiDAR) 기술 선도기업. 구 Velodyne과 합병하여 북미 라이다 시장 점유율 1위. 자율주행·산업용·스마트인프라 전방위 공급.',
         '자율주행 차량 양산 확대에 따른 라이다 수요 급증 직접 수혜. 디지털 라이다의 원가 절감 기술 우위로 대중 시장 침투 가속.', 50),
        # ABB 대체 → 야스카와전기 YASKY (OTC) - 실제 글로벌 1위급 로봇 팔 기업
        ('Yaskawa Electric', 'YASKY', 2, node_robot,
         'Yaskawa Electric — 세계 최대 서보 모터·인버터·산업용 로봇 팔 제조사. 제조업 자동화 핵심 부품·로봇 글로벌 1위 공급사.',
         '전 세계 제조업 자동화 수요 구조적 성장과 AI·모션 제어 기술 융합으로 고마진 솔루션 매출 확대. 리쇼어링·니어쇼어링 수혜.', 50),
        # AGIX 대체 → ISRG는 이미 있음. Symbotic(SYM)도 있음. → KION Group (KGX.DE OTC KIGRY) or 고영테크놀러지
        ('Kion Group', 'KIGRY', 2, node_robot,
         'KION Group — 산업용 지게차·자동화 물류 로봇 글로벌 2위. Dematic(창고 자동화) 보유. 아마존·이케아 등 대형 물류 자동화 수주.',
         '전자상거래 확대에 따른 물류 자동화 수요 급증. AI 창고 자동화 솔루션 Dematic의 AI 업그레이드로 고마진 전환.', 51),
        # LICY 대체 → Ascend Elements는 비상장. → Li Industries(비상장). → 대안: ECOVYST (ECVT) 촉매 리사이클
        # 혹은 MP Materials (MP) - 희토류 공급망
        ('MP Materials', 'MP', 7, node_batt_up,
         'MP Materials — 미국 유일 희토류(Rare Earth) 광산 및 제련 기업. 캘리포니아 마운틴패스 광산 보유. EV 모터·배터리 소재 핵심 비중국 공급원.',
         'IRA 비중국 광물 조달 강화로 구조적 수혜. GM 장기 공급 계약 기반 안정 매출. 미국 희토류 자급 달성 시 프리미엄 밸류에이션.', 17),
    ]

    cur.execute("SELECT ticker FROM companies")
    existing = {r[0] for r in cur.fetchall()}

    for name, ticker, ind_id, node_id, role, growth, disp in replacements:
        if ticker in existing:
            print(f"  [SKIP] {ticker} already exists")
            continue
        cur.execute("""
            INSERT INTO companies (name, ticker, industry_id, value_chain_node_id, role_description, future_growth, display_order)
            VALUES (?,?,?,?,?,?,?)
        """, (name, ticker, ind_id, node_id, role, growth, disp))
        print(f"  [INSERT] {ticker} ({name}) -> industry_id={ind_id}")
    conn.commit()

    # ================================================================
    # Step 3: 신규 추가 종목 재무 데이터 수집
    # ================================================================
    print("\n=== Step 3: 신규 대체 종목 재무 수집 ===")
    new_tickers = [r[0] for r in replacements]

    cur.execute("SELECT id, name, ticker FROM companies WHERE ticker IN ({})".format(
        ','.join('?' * len(new_tickers))), new_tickers)
    to_fetch = cur.fetchall()

    results = []
    for cid, name, ticker in to_fetch:
        print(f"\n[{cid}] {name} ({ticker})")
        try:
            periods, info = fetch_data(ticker)
        except Exception as e:
            print(f"  [ERR] {e}")
            results.append((name, ticker, 0, 0))
            time.sleep(1)
            continue

        annual_c = len([p for p in periods if p['period_type'] == 'annual'])
        qtr_c = len([p for p in periods if p['period_type'] == 'quarterly'])

        try:
            update_profile(cur, cid, info)
        except Exception as e:
            print(f"  [WARN] profile: {e}")

        new_c, upd_c = upsert_financials(cur, cid, periods)
        conn.commit()

        price_str = "N/A"
        if info:
            p = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            if p: price_str = f"{p:.2f}"

        mktcap_str = "N/A"
        if info and info.get('marketCap'):
            mc = info['marketCap']
            if mc >= 1e9: mktcap_str = f"${mc/1e9:.1f}B"
            else: mktcap_str = f"${mc/1e6:.0f}M"

        status = "OK" if annual_c > 0 or qtr_c > 0 else "WARN"
        print(f"  [{status}] annual={annual_c}, qtr={qtr_c} | price={price_str} | mktcap={mktcap_str}")
        results.append((name, ticker, annual_c, qtr_c))
        time.sleep(2)

    # ================================================================
    # Step 4: 최종 산업별 종목 수 요약
    # ================================================================
    print("\n=== 최종 산업별 종목 수 ===")
    cur.execute("""
        SELECT ir.id, ir.title, COUNT(c.id) as cnt
        FROM industry_reports ir
        LEFT JOIN companies c ON c.industry_id = ir.id
        GROUP BY ir.id
        ORDER BY ir.id
    """)
    for row in cur.fetchall():
        print(f"  id={row[0]}: {row[1][:30]} | {row[2]}개 기업")

    cur.execute("SELECT COUNT(*) FROM companies")
    total = cur.fetchone()[0]
    print(f"\n  총 기업 수: {total}개")

    conn.close()
    print("\n완료!")

if __name__ == "__main__":
    main()
