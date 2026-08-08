import sqlite3
import os

# 정확한 경로로 확인
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                       'InvestmentPortal', 'backend', 'investment_portal.db')
print(f"DB 경로: {DB_PATH}")
print(f"DB 파일 크기: {os.path.getsize(DB_PATH)/1024/1024:.1f} MB")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM eps_timeseries")
print(f"총 행수: {cur.fetchone()[0]:,}")

cur.execute("SELECT COUNT(DISTINCT code) FROM eps_timeseries")
print(f"총 종목수: {cur.fetchone()[0]}")

# 삼성전자 확인
cur.execute("""SELECT date, eps_fwd, price, fwd_per FROM eps_timeseries 
              WHERE code='A005930' ORDER BY date DESC LIMIT 5""")
print('\n=== 삼성전자 (A005930) 최근 5일 ===')
for r in cur.fetchall():
    print(f'  {r[0]} | EPS={r[1]:,.0f}원 | 주가={r[2]:,.0f}원 | FWD PER={r[3]:.1f}x')

# SK하이닉스
cur.execute("""SELECT date, eps_fwd, price, fwd_per FROM eps_timeseries 
              WHERE code='A000660' ORDER BY date DESC LIMIT 3""")
print('\n=== SK하이닉스 (A000660) ===')
for r in cur.fetchall():
    print(f'  {r[0]} | EPS={r[1]:,.0f}원 | 주가={r[2]:,.0f}원 | FWD PER={r[3]:.1f}x')

# FWD PER 분포 (2026-08-07)
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

# KOSPI200 평균
cur.execute("""
SELECT date, COUNT(*) as cnt, ROUND(AVG(fwd_per),2) as avg_per
FROM eps_timeseries
WHERE index_type='KOSPI200' AND fwd_per>0 AND fwd_per<200
  AND date >= '2026-08-01'
GROUP BY date ORDER BY date DESC
""")
print('\n=== KOSPI200 최근 AVG FWD PER ===')
for r in cur.fetchall():
    print(f'  {r[0]} | 종목수={r[1]} | AVG={r[2]}x')

conn.close()
