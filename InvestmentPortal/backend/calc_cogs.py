import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('investment_portal.db')
cur = conn.cursor()

# 매출총이익이 있는 경우: 매출원가 = 매출 - 매출총이익
cur.execute('''
    UPDATE financial_data
    SET cost_of_revenue = revenue - gross_profit
    WHERE cost_of_revenue IS NULL
    AND revenue IS NOT NULL AND revenue != 0
    AND gross_profit IS NOT NULL AND gross_profit != 0
    AND (revenue - gross_profit) > 0
''')
by_gp = cur.rowcount
print(f'매출총이익으로 매출원가 계산: {by_gp}개')

# 매출원가가 있는 경우: 매출총이익 = 매출 - 매출원가 (역방향)
cur.execute('''
    UPDATE financial_data
    SET gross_profit = revenue - cost_of_revenue
    WHERE gross_profit IS NULL
    AND revenue IS NOT NULL AND revenue != 0
    AND cost_of_revenue IS NOT NULL AND cost_of_revenue != 0
    AND (revenue - cost_of_revenue) > 0
''')
by_cogs = cur.rowcount
print(f'매출원가로 매출총이익 역산: {by_cogs}개')

conn.commit()

# 결과 검증
cur.execute('SELECT COUNT(*) FROM financial_data WHERE cost_of_revenue IS NULL AND revenue IS NOT NULL AND gross_profit IS NOT NULL')
still_null = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM financial_data WHERE cost_of_revenue IS NOT NULL')
has_data = cur.fetchone()[0]
print(f'\n최종: COGS 완비 {has_data}개 / 여전히 NULL {still_null}개')

# 샘플 확인
cur.execute('''
    SELECT c.ticker, fd.date, fd.period_type,
        fd.revenue/1e9, fd.cost_of_revenue/1e9, fd.gross_profit/1e9
    FROM financial_data fd JOIN companies c ON fd.company_id=c.id
    WHERE fd.cost_of_revenue IS NOT NULL AND fd.gross_profit IS NOT NULL
    ORDER BY c.ticker, fd.date DESC LIMIT 10
''')
print('\n샘플 확인:')
for r in cur.fetchall():
    check = 'OK' if abs(r[3] - r[4] - r[5]) < 0.01 else 'CHECK'
    print(f'  {r[0]:6} {r[1]} {r[2]:9}: {r[3]:.2f}B - {r[4]:.2f}B = {r[5]:.2f}B [{check}]')
conn.close()
