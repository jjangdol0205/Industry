import sqlite3
conn = sqlite3.connect('InvestmentPortal/backend/investment_portal.db')
cur = conn.cursor()

# 삼성전자 최근 데이터
cur.execute("SELECT date, eps_fwd, price, fwd_per FROM eps_timeseries WHERE code='A005930' ORDER BY date DESC LIMIT 5")
print('=== 삼성전자 DB 데이터 ===')
for r in cur.fetchall():
    print(f'  {r[0]} | EPS={r[1]:,.0f} | 주가={r[2]:,.0f} | PER={r[3]:.1f}x')

# 시장 평균 PER
cur.execute("""
SELECT date, COUNT(*) as cnt, ROUND(AVG(fwd_per),2) as avg_per
FROM eps_timeseries
WHERE index_type='KOSPI200' AND fwd_per>0 AND fwd_per<200
  AND date >= '2026-07-01'
GROUP BY date ORDER BY date DESC LIMIT 10
""")
print('\n=== KOSPI200 최근 평균 FWD PER ===')
for r in cur.fetchall():
    print(f'  {r[0]} | 종목수={r[1]} | AVG PER={r[2]}x')

# 극단치 낮은 PER 확인
cur.execute("""
SELECT code, name, eps_fwd, price, fwd_per FROM eps_timeseries
WHERE date='2026-08-07' AND fwd_per IS NOT NULL AND fwd_per>0 AND fwd_per<200
ORDER BY fwd_per ASC LIMIT 10
""")
print('\n=== FWD PER 낮은 종목 TOP 10 (2026-08-07) ===')
for r in cur.fetchall():
    print(f'  {r[1]} | EPS={r[2]:,.0f} | 주가={r[3]:,.0f} | PER={r[4]:.1f}x')

# 실제 PER 분포
cur.execute("""
SELECT
  CASE WHEN fwd_per < 5 THEN '0~5x'
       WHEN fwd_per < 10 THEN '5~10x'
       WHEN fwd_per < 15 THEN '10~15x'
       WHEN fwd_per < 20 THEN '15~20x'
       WHEN fwd_per < 30 THEN '20~30x'
       ELSE '30x+' END as per_band,
  COUNT(*) as cnt
FROM eps_timeseries
WHERE date='2026-08-07' AND fwd_per>0 AND fwd_per<200
GROUP BY per_band ORDER BY per_band
""")
print('\n=== PER 분포 (2026-08-07) ===')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}개')

conn.close()
