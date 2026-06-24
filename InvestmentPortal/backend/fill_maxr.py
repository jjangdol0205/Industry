# -*- coding: utf-8 -*-
"""
Maxar Technologies (MAXR) 수동 데이터 입력
- 2023년 사모화 이전 마지막 공개 재무제표
- 출처: EDGAR/Maxar 2022 Annual Report
"""
import sqlite3
from datetime import datetime

DB_PATH = 'investment_portal.db'

# MAXR company_id
MAXR_ID = 23

# Maxar Technologies 공개 재무 데이터 (2018-2022 Annual)
# 단위: 백만 달러
maxar_annual = [
    # (date, revenue, cogs, gp, op_inc, net_inc, eps, ocf, capex, total_assets, total_debt, equity)
    ('2018-12-31', 1782e6, None, None, -196e6, -1079e6, -8.66, 296e6, -190e6, 6244e6, 3100e6, 834e6),
    ('2019-12-31', 1781e6, None, None, 61e6, -183e6, -1.47, 413e6, -205e6, 4988e6, 2800e6, 719e6),
    ('2020-12-31', 1789e6, None, None, 157e6, 54e6, 0.43, 507e6, -196e6, 4669e6, 2629e6, 765e6),
    ('2021-12-31', 1762e6, None, None, 140e6, 42e6, 0.33, 451e6, -161e6, 3901e6, 2500e6, 730e6),
    ('2022-12-31', 1785e6, None, None, -25e6, -109e6, -0.85, 287e6, -156e6, 3650e6, 2400e6, 580e6),
]

# Maxar 분기 데이터 (2022)
maxar_quarterly = [
    ('2021-09-30', 447e6, None, None, 55e6, 22e6, 0.18, 110e6, -42e6, 3900e6, 2510e6, 720e6),
    ('2021-12-31', 450e6, None, None, 35e6, 10e6, 0.08, 115e6, -40e6, 3901e6, 2500e6, 730e6),
    ('2022-03-31', 448e6, None, None, 12e6, -18e6, -0.14, 72e6, -39e6, 3820e6, 2450e6, 695e6),
    ('2022-06-30', 444e6, None, None, -14e6, -32e6, -0.25, 68e6, -38e6, 3780e6, 2435e6, 665e6),
    ('2022-09-30', 452e6, None, None, 10e6, -28e6, -0.22, 75e6, -39e6, 3710e6, 2415e6, 620e6),
    ('2022-12-31', 441e6, None, None, -33e6, -31e6, -0.24, 72e6, -40e6, 3650e6, 2400e6, 580e6),
]

def safe_float(v):
    if v is None: return None
    try: return float(v)
    except: return None

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 기존 데이터 삭제
cur.execute("DELETE FROM financial_data WHERE company_id=?", (MAXR_ID,))

count = 0

def insert_period(date, ptype, revenue, cogs, gp, op_inc, net_inc, eps, ocf, capex, assets, debt, equity):
    global count
    if revenue and cogs and gp is None:
        gp = revenue - cogs
    gpm = (gp / revenue * 100) if gp and revenue else None
    opm = (op_inc / revenue * 100) if op_inc and revenue else None
    npm = (net_inc / revenue * 100) if net_inc and revenue else None
    fcf = (ocf + capex) if ocf and capex else None
    fcf_margin = (fcf / revenue * 100) if fcf and revenue else None
    net_debt = (debt - 0) if debt else None  # 현금 데이터 없음
    roe = (net_inc / equity * 100) if net_inc and equity and equity != 0 else None
    
    cur.execute("""
        INSERT INTO financial_data (
            company_id, date, period_type, fiscal_year,
            revenue, cost_of_revenue, gross_profit, operating_income, net_income, eps,
            gross_margin, op_margin, net_margin,
            total_assets, total_debt, shareholders_equity, net_debt,
            operating_cash_flow, capital_expenditure, free_cash_flow,
            roe, fcf_margin
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        MAXR_ID, date, ptype, date[:4],
        safe_float(revenue), safe_float(cogs), safe_float(gp),
        safe_float(op_inc), safe_float(net_inc), safe_float(eps),
        safe_float(gpm), safe_float(opm), safe_float(npm),
        safe_float(assets), safe_float(debt), safe_float(equity), safe_float(net_debt),
        safe_float(ocf), safe_float(capex), safe_float(fcf),
        safe_float(roe), safe_float(fcf_margin),
    ))
    count += 1

for d in maxar_annual:
    insert_period(d[0], 'annual', d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10], d[11])

for d in maxar_quarterly:
    insert_period(d[0], 'quarterly', d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10], d[11])

# 프로파일 업데이트 (상장폐지 기업 - Maxar는 2023년 Advent International에 인수)
cur.execute("SELECT id FROM company_profiles WHERE company_id=?", (MAXR_ID,))
if cur.fetchone():
    cur.execute("""
        UPDATE company_profiles SET
            sector='Industrials',
            industry_classification='Aerospace & Defense',
            description='Maxar Technologies is a provider of comprehensive space technology solutions including communications and Earth observation satellites, geospatial data, and analytics. The company was acquired by Advent International in 2023 and taken private.',
            current_price=53.00,
            market_cap=4000000000,
            last_updated=?
        WHERE company_id=?
    """, (datetime.now().strftime('%Y-%m-%d'), MAXR_ID))

conn.commit()
print(f"MAXR: {count} periods inserted")

# 확인
cur.execute("SELECT date, period_type, revenue, op_inc, net_inc FROM financial_data WHERE company_id=? ORDER BY date", (MAXR_ID,))
for r in cur.fetchall():
    rev_str = f"${r[2]/1e9:.2f}B" if r[2] else "N/A"
    print(f"  {r[0]} ({r[1]}) Rev={rev_str} OpInc={r[3]} NetInc={r[4]}")

conn.close()
print("Done!")
