# -*- coding: utf-8 -*-
"""
financial_data → financial_data_history 동기화
연간(annual) 데이터를 fiscal_year 기준으로 집계하여 history 테이블에 upsert
"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'investment_portal.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 대상: industry_id=8 기업들 (또는 industry_id 전달 인자로 지정)
import sys
if len(sys.argv) > 1:
    industry_filter = f"AND c.industry_id={sys.argv[1]}"
    print(f"[Sync] industry_id={sys.argv[1]} 기업만 동기화")
else:
    industry_filter = ""
    print("[Sync] 전체 기업 동기화")

cur.execute(f"""
    SELECT c.id, c.ticker
    FROM companies c
    WHERE 1=1 {industry_filter}
""")
companies = cur.fetchall()
print(f"대상 기업 수: {len(companies)}")

new_c = upd_c = skip_c = 0

for cid, ticker in companies:
    # annual 데이터를 fiscal_year별로 집계
    cur.execute("""
        SELECT 
            fiscal_year,
            MAX(revenue) as revenue,
            MAX(gross_profit) as gross_profit,
            MAX(operating_income) as operating_income,
            MAX(net_income) as net_income,
            MAX(free_cash_flow) as free_cash_flow,
            MAX(total_assets) as total_assets,
            MAX(total_debt) as total_debt,
            MAX(shareholders_equity) as shareholders_equity,
            MAX(gross_margin) as gross_margin,
            MAX(op_margin) as op_margin,
            MAX(net_margin) as net_margin,
            MAX(fcf_margin) as fcf_margin,
            MAX(roe) as roe
        FROM financial_data
        WHERE company_id=? AND period_type='annual'
        GROUP BY fiscal_year
        ORDER BY fiscal_year
    """, (cid,))
    rows = cur.fetchall()
    
    if not rows:
        skip_c += 1
        continue
    
    for row in rows:
        fy = row[0]
        if not fy:
            continue
        try:
            fy_int = int(str(fy)[:4])
        except:
            continue
        
        rev, gp, op_inc, net_inc, fcf = row[1], row[2], row[3], row[4], row[5]
        tot_assets, tot_debt, equity = row[6], row[7], row[8]
        gpm, opm, npm, fcfm, roe = row[9], row[10], row[11], row[12], row[13]
        
        if rev is None:
            continue
        
        cur.execute("SELECT id FROM financial_data_history WHERE company_id=? AND fiscal_year=?",
                    (cid, fy_int))
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""
                UPDATE financial_data_history SET
                    ticker=?, revenue=?, gross_profit=?, operating_income=?, net_income=?,
                    free_cash_flow=?, total_assets=?, total_debt=?, shareholders_equity=?,
                    gross_margin=?, op_margin=?, net_margin=?, fcf_margin=?, roe=?,
                    source='financial_data_sync'
                WHERE company_id=? AND fiscal_year=?
            """, (ticker, rev, gp, op_inc, net_inc, fcf, tot_assets, tot_debt, equity,
                  gpm, opm, npm, fcfm, roe, cid, fy_int))
            upd_c += 1
        else:
            cur.execute("""
                INSERT INTO financial_data_history
                    (company_id, ticker, fiscal_year, revenue, gross_profit,
                     operating_income, net_income, free_cash_flow,
                     total_assets, total_debt, shareholders_equity,
                     gross_margin, op_margin, net_margin, fcf_margin, roe, source)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'financial_data_sync')
            """, (cid, ticker, fy_int, rev, gp, op_inc, net_inc, fcf,
                  tot_assets, tot_debt, equity, gpm, opm, npm, fcfm, roe))
            new_c += 1

conn.commit()

# 결과 확인
if len(sys.argv) > 1:
    cur.execute(f"""
        SELECT COUNT(*), MIN(fiscal_year), MAX(fiscal_year)
        FROM financial_data_history
        WHERE company_id IN (SELECT id FROM companies WHERE industry_id={sys.argv[1]})
    """)
    cnt, min_fy, max_fy = cur.fetchone()
    print(f"✅ 동기화 완료: new={new_c}, upd={upd_c}, skip={skip_c}")
    print(f"   industry_id={sys.argv[1]} 히스토리 레코드: {cnt}개 ({min_fy}~{max_fy})")
else:
    cur.execute("SELECT COUNT(*) FROM financial_data_history")
    total = cur.fetchone()[0]
    print(f"✅ 전체 동기화 완료: new={new_c}, upd={upd_c}, skip={skip_c}")
    print(f"   financial_data_history 전체: {total}개")

conn.close()
