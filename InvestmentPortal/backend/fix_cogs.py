"""
매출원가(COGS) 전체 기업 완전 재수집
- yfinance 날짜와 DB 날짜 형식을 정확히 맞춰서 매칭
- NULL인 레코드만 UPSERT
"""
import sqlite3, yfinance as yf, math, sys, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

DB = 'investment_portal.db'

def safe(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except: return None

def try_cogs(df, col):
    for key in ['Cost Of Revenue', 'Cost Of Goods Sold', 'Cost of Revenue']:
        try:
            if df is None or df.empty or key not in df.index: continue
            return safe(df.loc[key, col])
        except: continue
    return None

def normalize_date(col):
    """pandas Timestamp / str → 'YYYY-MM-DD'"""
    try:
        return pd.Timestamp(col).strftime('%Y-%m-%d')
    except:
        return str(col)[:10]

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 전체 기업 조회 (MAXR 제외)
cur.execute("SELECT id, name, ticker FROM companies WHERE ticker != 'MAXR' ORDER BY id")
all_companies = cur.fetchall()
print(f"전체 대상 기업: {len(all_companies)}개\n")

updated_total = 0
for cid, name, ticker in all_companies:
    try:
        t = yf.Ticker(ticker)
        inc_a = t.financials          # 연간
        inc_q = t.quarterly_financials # 분기

        company_updated = 0
        for df, ptype in [(inc_a, 'annual'), (inc_q, 'quarterly')]:
            if df is None or df.empty: continue
            for col in df.columns:
                d = normalize_date(col)
                cogs = try_cogs(df, col)
                if cogs is None: continue

                # NULL인 레코드에 COGS 업데이트 (날짜 다양한 형식 처리)
                cur.execute('''
                    UPDATE financial_data
                    SET cost_of_revenue = ?
                    WHERE company_id = ?
                    AND (date = ? OR date = substr(?,1,7) || '-01' OR substr(date,1,7) = substr(?,1,7))
                    AND period_type = ?
                    AND cost_of_revenue IS NULL
                ''', (cogs, cid, d, d, d, ptype))
                
                if cur.rowcount == 0:
                    # 정확한 날짜 매칭 시도 (월만 일치)
                    year_month = d[:7]
                    cur.execute('''
                        SELECT id, date FROM financial_data
                        WHERE company_id = ? AND period_type = ? AND cost_of_revenue IS NULL
                        AND substr(date,1,7) = ?
                    ''', (cid, ptype, year_month))
                    rows = cur.fetchall()
                    for row_id, row_date in rows:
                        cur.execute('UPDATE financial_data SET cost_of_revenue = ? WHERE id = ?', (cogs, row_id))
                        company_updated += 1

                company_updated += cur.rowcount

        conn.commit()
        if company_updated > 0:
            print(f"  [{cid}] {name} ({ticker}): {company_updated}개 업데이트")
        updated_total += company_updated
    except Exception as e:
        print(f"  [{cid}] {name} ({ticker}): 오류 - {e}")

print(f"\n=== 최종 결과 ===")
print(f"총 {updated_total}개 레코드 업데이트 완료")

# 검증
cur.execute('''
    SELECT c.ticker,
        SUM(CASE WHEN fd.cost_of_revenue IS NULL THEN 1 ELSE 0 END) as still_null,
        SUM(CASE WHEN fd.cost_of_revenue IS NOT NULL THEN 1 ELSE 0 END) as has_data,
        COUNT(*) as total
    FROM companies c
    JOIN financial_data fd ON c.id = fd.company_id
    WHERE c.ticker != 'MAXR'
    GROUP BY c.id
    HAVING still_null > 0
    ORDER BY still_null DESC
    LIMIT 15
''')
remaining = cur.fetchall()
print(f"\n여전히 NULL 있는 기업 (MAXR 제외):")
for r in remaining:
    pct = r[1] / r[3] * 100 if r[3] > 0 else 0
    print(f"  {r[0]}: NULL {r[1]}개 / 전체 {r[3]}개 ({pct:.0f}% null)")

conn.close()
