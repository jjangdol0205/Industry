"""
EPS 시계열 데이터를 압축 CSV로 내보내기
Render 서버에서 로드용
"""
import sqlite3
import os
import gzip

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'InvestmentPortal', 'backend', 'investment_portal.db')
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'InvestmentPortal', 'backend', 'eps_data.csv.gz')

print(f"DB 경로: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM eps_timeseries")
total = cur.fetchone()[0]
print(f"총 {total:,}행 내보내기 시작...")

with gzip.open(OUT_PATH, 'wt', encoding='utf-8') as f:
    # 헤더
    f.write("date,code,name,index_type,eps_fwd,price,fwd_per\n")
    
    # 데이터 배치 조회
    BATCH = 50000
    offset = 0
    written = 0
    while True:
        cur.execute(f"""
            SELECT date, code, name, index_type, eps_fwd, price, fwd_per
            FROM eps_timeseries
            ORDER BY code, date
            LIMIT {BATCH} OFFSET {offset}
        """)
        rows = cur.fetchall()
        if not rows:
            break
        for r in rows:
            # CSV 안전하게 쓰기
            name_safe = str(r[2]).replace(',', '_')
            eps  = '' if r[4] is None else f'{r[4]:.2f}'
            prc  = '' if r[5] is None else f'{r[5]:.0f}'
            per  = '' if r[6] is None else f'{r[6]:.2f}'
            f.write(f"{r[0]},{r[1]},{name_safe},{r[3]},{eps},{prc},{per}\n")
        written += len(rows)
        offset += BATCH
        print(f"  진행: {written:,}/{total:,}행")

conn.close()
size_mb = os.path.getsize(OUT_PATH) / 1024 / 1024
print(f"\n완료! 출력: {OUT_PATH}")
print(f"압축 파일 크기: {size_mb:.1f} MB")
