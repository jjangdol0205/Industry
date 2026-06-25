import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('investment_portal.db')
cur = conn.cursor()

# MAXR id=23 관련 데이터 전부 삭제
cur.execute('DELETE FROM financial_data WHERE company_id=23')
print(f'financial_data 삭제: {cur.rowcount}개')

cur.execute('DELETE FROM company_profiles WHERE company_id=23')
print(f'company_profiles 삭제: {cur.rowcount}개')

cur.execute('DELETE FROM agents WHERE type=? AND target_id=23', ('company',))
print(f'agents 삭제: {cur.rowcount}개')

cur.execute('DELETE FROM companies WHERE id=23')
print(f'companies 삭제: {cur.rowcount}개')

conn.commit()

# 검증
cur.execute('SELECT COUNT(*) FROM companies')
print(f'\n남은 기업 수: {cur.fetchone()[0]}개')
cur.execute('SELECT id, name, ticker, industry_id FROM companies ORDER BY industry_id, id')
for r in cur.fetchall():
    print(f'  [{r[0]:2}] {r[2]:6} {r[1]}')
conn.close()
print('\nMAXR 삭제 완료!')
