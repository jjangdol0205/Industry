import sqlite3, sys, yfinance as yf, pandas as pd, math
sys.stdout.reconfigure(encoding='utf-8')

def safe(v):
    try: f=float(v); return None if (math.isnan(f) or math.isinf(f)) else f
    except: return None

DB = 'investment_portal.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1) NVDA id=1 COGS 업데이트
t = yf.Ticker('NVDA')
inc_a = t.financials
inc_q = t.quarterly_financials
updated = 0
for df, ptype in [(inc_a, 'annual'), (inc_q, 'quarterly')]:
    if df is None or df.empty: continue
    for col in df.columns:
        d = pd.Timestamp(col).strftime('%Y-%m-%d')
        ym = d[:7]
        cogs = None
        for key in ['Cost Of Revenue', 'Cost Of Goods Sold']:
            if key in df.index:
                cogs = safe(df.loc[key, col])
                break
        if cogs is None: continue
        cur.execute(
            'SELECT id FROM financial_data WHERE company_id=1 AND period_type=? AND substr(date,1,7)=? AND cost_of_revenue IS NULL',
            (ptype, ym)
        )
        rows = cur.fetchall()
        for (rid,) in rows:
            cur.execute('UPDATE financial_data SET cost_of_revenue=? WHERE id=?', (cogs, rid))
            updated += 1

conn.commit()
print(f'NVDA(id=1) COGS 업데이트: {updated}개')

# 2) 나머지 NULL은 어느 기간인지 확인
cur.execute('SELECT company_id, MIN(date), MAX(date) FROM financial_data WHERE cost_of_revenue IS NULL AND period_type=? GROUP BY company_id LIMIT 10', ('quarterly',))
print('\n분기 NULL 기간 범위:')
for r in cur.fetchall():
    cur.execute('SELECT ticker FROM companies WHERE id=?', (r[0],))
    tk = cur.fetchone()
    print(f'  {tk[0] if tk else r[0]}: {r[1]} ~ {r[2]}')

# 3) 최종 전체 현황 요약
cur.execute('''
    SELECT 
        SUM(CASE WHEN fd.cost_of_revenue IS NULL THEN 1 ELSE 0 END) as total_null,
        SUM(CASE WHEN fd.cost_of_revenue IS NOT NULL THEN 1 ELSE 0 END) as total_data,
        COUNT(*) as grand_total
    FROM financial_data fd
    JOIN companies c ON fd.company_id = c.id
    WHERE c.ticker != 'MAXR'
''')
r = cur.fetchone()
print(f'\n=== 전체 COGS 현황 ===')
print(f'데이터 있음: {r[1]}개 ({r[1]/r[2]*100:.1f}%)')
print(f'NULL: {r[0]}개 ({r[0]/r[2]*100:.1f}%)')
print(f'전체: {r[2]}개')

conn.close()
