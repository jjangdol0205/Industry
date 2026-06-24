import sqlite3

conn = sqlite3.connect('investment_portal.db')
cur = conn.cursor()

# 전체 기업 목록
cur.execute('SELECT id, name, ticker FROM companies ORDER BY id')
companies = cur.fetchall()
print(f'=== 전체 기업 수: {len(companies)} ===')
for c in companies:
    print(f'  [{c[0]}] {c[1]} ({c[2]})')

print()
# 재무제표 보유 현황
cur.execute("""
    SELECT c.id, c.name, c.ticker,
           COUNT(f.id) as fin_count,
           COUNT(CASE WHEN f.period_type='annual' THEN 1 END) as annual_cnt,
           COUNT(CASE WHEN f.period_type='quarterly' THEN 1 END) as quarter_cnt,
           MAX(f.date) as latest_date,
           SUM(CASE WHEN f.revenue IS NULL THEN 1 ELSE 0 END) as null_revenue
    FROM companies c
    LEFT JOIN financial_data f ON c.id = f.company_id
    GROUP BY c.id, c.name, c.ticker
    ORDER BY fin_count ASC
""")
rows = cur.fetchall()
print('=== 재무제표 현황 ===')
print(f'{"ID":<4} {"기업":<32} {"티커":<8} {"총":<5} {"연간":<5} {"분기":<5} {"최신날짜":<12} {"매출NULL":<8}')
print('-'*85)
for r in rows:
    flag = '  ★ 없음' if r[3] == 0 else ('  △ 부족' if r[3] < 4 else '')
    print(f'{r[0]:<4} {r[1]:<32} {r[2]:<8} {r[3]:<5} {r[4]:<5} {r[5]:<5} {str(r[6] or ""):<12} {str(r[7] or 0):<8}{flag}')

# 프로파일 현황
print()
cur.execute("""
    SELECT c.id, c.name, c.ticker,
           CASE WHEN p.id IS NULL THEN '없음' ELSE '있음' END as profile,
           p.current_price, p.market_cap, p.last_updated
    FROM companies c
    LEFT JOIN company_profiles p ON c.id = p.company_id
    ORDER BY c.id
""")
prof_rows = cur.fetchall()
print('=== 프로파일(주가 등) 현황 ===')
print(f'{"ID":<4} {"기업":<32} {"티커":<8} {"프로파일":<9} {"현재주가":<12} {"시총":<14} {"갱신일"}')
print('-'*90)
for r in prof_rows:
    price_str = f'${r[4]:.2f}' if r[4] else '없음'
    mktcap_str = f'${r[5]/1e9:.1f}B' if r[5] else '없음'
    flag = '  ★ 프로파일없음' if r[3] == '없음' else ''
    print(f'{r[0]:<4} {r[1]:<32} {r[2]:<8} {r[3]:<9} {price_str:<12} {mktcap_str:<14} {str(r[6] or "")}{flag}')

conn.close()
