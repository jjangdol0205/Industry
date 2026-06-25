"""
Circle Internet Group (CRCL) - 코인 산업 추가
USDC 스테이블코인 발행사, 2025년 NYSE 상장
"""
import sqlite3, sys, yfinance as yf, math, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

DB = 'investment_portal.db'

def safe(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except: return None

def get_val(df, col, *keys):
    for key in keys:
        try:
            if df is not None and not df.empty and key in df.index:
                return safe(df.loc[key, col])
        except: pass
    return None

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 코인 산업 ID 확인
cur.execute("SELECT id, title FROM industry_reports WHERE tag='코인'")
coin = cur.fetchone()
print(f'코인 산업: {coin}')
coin_id = coin[0]

# 이미 있으면 스킵
cur.execute("SELECT id FROM companies WHERE ticker='CRCL'")
existing = cur.fetchone()
if existing:
    print(f'CRCL 이미 존재합니다 (id={existing[0]})')
    conn.close()
    exit()

# ── 기업 정보 추가 ──
cur.execute('''
    INSERT INTO companies (name, ticker, industry_id, role_description, future_growth)
    VALUES (?, ?, ?, ?, ?)
''', (
    'Circle Internet Group',
    'CRCL',
    coin_id,
    'USDC(USD Coin) 스테이블코인 발행 및 Circle Payments Network(CPN) 운영. 전 세계 최대 규모의 달러 연동 디지털 화폐 인프라를 구축하며, 기업·기관·정부의 디지털 결제 및 국경 간 송금 플랫폼을 제공.',
    '미국 스테이블코인 법제화(GENIUS Act) 통과 시 USDC의 법적 지위 확립으로 기관 채택 폭발적 성장 기대. 글로벌 B2B 결제·DeFi 생태계에서 USDC 순환 규모 확대가 핵심 성장 동력. 2025년 IPO로 브랜드 신뢰도 급상승.'
))
cid = cur.lastrowid
conn.commit()
print(f'기업 추가: id={cid}')

# ── yfinance 데이터 수집 ──
t = yf.Ticker('CRCL')
info = t.info
fin_a = t.financials
fin_q = t.quarterly_financials
bs_a  = t.balance_sheet
bs_q  = t.quarterly_balance_sheet
cf_a  = t.cashflow
cf_q  = t.quarterly_cashflow

inserted = 0
for df_inc, df_bs, df_cf, ptype in [
    (fin_a, bs_a, cf_a, 'annual'),
    (fin_q, bs_q, cf_q, 'quarterly')
]:
    if df_inc is None or df_inc.empty:
        print(f'{ptype}: 재무제표 없음')
        continue
    for col in df_inc.columns:
        d = pd.Timestamp(col).strftime('%Y-%m-%d')

        rev    = get_val(df_inc, col, 'Total Revenue', 'Revenue')
        cogs   = get_val(df_inc, col, 'Cost Of Revenue', 'Cost Of Goods Sold')
        gp     = get_val(df_inc, col, 'Gross Profit')
        opInc  = get_val(df_inc, col, 'Operating Income', 'Ebit')
        netInc = get_val(df_inc, col, 'Net Income')
        ebitda = get_val(df_inc, col, 'EBITDA', 'Normalized EBITDA')
        eps    = get_val(df_inc, col, 'Diluted EPS', 'Basic EPS')

        # 역산
        if gp is None and rev and cogs: gp = rev - cogs
        if cogs is None and rev and gp: cogs = rev - gp
        gm = (gp/rev*100) if (gp and rev and rev > 0) else None
        om = (opInc/rev*100) if (opInc and rev and rev > 0) else None
        nm = (netInc/rev*100) if (netInc and rev and rev > 0) else None

        # 대차대조표
        ta   = get_val(df_bs, col, 'Total Assets') if df_bs is not None and not df_bs.empty else None
        cash = get_val(df_bs, col, 'Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments')
        debt = get_val(df_bs, col, 'Total Debt', 'Long Term Debt')
        eq   = get_val(df_bs, col, "Stockholders' Equity", 'Total Equity Gross Minority Interest')
        tl   = get_val(df_bs, col, 'Total Liabilities Net Minority Interest')
        ca   = get_val(df_bs, col, 'Current Assets', 'Total Current Assets')
        cl   = get_val(df_bs, col, 'Current Liabilities', 'Total Current Liabilities')

        # 현금흐름
        ocf   = get_val(df_cf, col, 'Operating Cash Flow')
        capex = get_val(df_cf, col, 'Capital Expenditure')
        fcf   = None
        if ocf is not None and capex is not None:
            fcf = ocf + capex  # capex는 보통 음수로 기록됨
        elif ocf is not None:
            fcf = ocf

        # 파생 지표
        roe  = (netInc/eq*100) if (netInc and eq and eq != 0) else None
        roa  = (netInc/ta*100) if (netInc and ta and ta != 0) else None
        de   = (debt/eq*100) if (debt and eq and eq != 0) else None
        cr   = (ca/cl) if (ca and cl and cl != 0) else None
        nd   = (debt - cash) if (debt and cash) else None
        fcfm = (fcf/rev*100) if (fcf and rev and rev > 0) else None

        cur.execute('''
            INSERT OR REPLACE INTO financial_data
            (company_id, date, period_type,
             revenue, cost_of_revenue, gross_profit, gross_margin,
             operating_income, op_margin, ebitda, net_income, net_margin, eps,
             total_assets, cash_and_equivalents, total_debt, total_liabilities,
             shareholders_equity, net_debt, debt_to_equity_ratio, current_ratio,
             operating_cash_flow, capital_expenditure, free_cash_flow,
             roe, roa, fcf_margin)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (cid, d, ptype,
              rev, cogs, gp, gm,
              opInc, om, ebitda, netInc, nm, eps,
              ta, cash, debt, tl,
              eq, nd, de, cr,
              ocf, capex, fcf,
              roe, roa, fcfm))
        inserted += 1

conn.commit()
print(f'재무 데이터: {inserted}개 레코드 삽입')

# ── company_profiles 추가 ──
p = info
cur.execute('''
    INSERT OR REPLACE INTO company_profiles
    (company_id, current_price, market_cap, pe_ratio, pb_ratio, ev_ebitda, ev_sales,
     beta, revenue_growth, gross_margin_ttm, net_margin_ttm, op_margin_ttm,
     eps_growth, roe, roa, debt_to_equity, current_ratio, dividend_yield, description)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
''', (
    cid,
    safe(p.get('currentPrice')),
    safe(p.get('marketCap')),
    safe(p.get('trailingPE') or p.get('forwardPE')),
    safe(p.get('priceToBook')),
    safe(p.get('enterpriseToEbitda')),
    safe(p.get('enterpriseToRevenue')),
    safe(p.get('beta')),
    safe(p.get('revenueGrowth')),
    safe(p.get('grossMargins')),
    safe(p.get('profitMargins')),
    safe(p.get('operatingMargins')),
    safe(p.get('earningsGrowth')),
    safe(p.get('returnOnEquity')),
    safe(p.get('returnOnAssets')),
    safe(p.get('debtToEquity')),
    safe(p.get('currentRatio')),
    safe(p.get('dividendYield')),
    p.get('longBusinessSummary', '')[:2000]
))
conn.commit()
print('company_profiles 추가 완료')

# ── Agent 추가 ──
cur.execute('''
    INSERT OR IGNORE INTO agents (name, role, type, target_id)
    VALUES (?, ?, ?, ?)
''', (
    'Circle Internet Group Tracker',
    'Equity Research Specialist monitoring Circle Internet Group (CRCL) - USDC Stablecoin & Payments',
    'company',
    cid
))
conn.commit()
print('Agent 추가 완료')

# ── 최종 검증 ──
cur.execute('SELECT id, name, ticker FROM companies WHERE id=?', (cid,))
print(f'\n추가 완료: {cur.fetchone()}')
cur.execute('SELECT COUNT(*) FROM financial_data WHERE company_id=?', (cid,))
print(f'재무 레코드: {cur.fetchone()[0]}개')
cur.execute('SELECT current_price, market_cap FROM company_profiles WHERE company_id=?', (cid,))
prof = cur.fetchone()
if prof and prof[0]:
    print(f'현재가: ${prof[0]:.2f}, 시총: ${prof[1]/1e9:.1f}B')
print('\n써클(CRCL) 추가 완료!')
conn.close()
