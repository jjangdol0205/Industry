import sqlite3, sys, yfinance as yf
sys.stdout.reconfigure(encoding='utf-8')

DB = 'investment_portal.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT id, name, ticker FROM companies ORDER BY id")
companies = cur.fetchall()
conn.close()

print(f"전체 {len(companies)}개 기업 상장 여부 확인 중...\n")
delisted = []
active = []

for cid, name, ticker in companies:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period='5d')
        info = t.info
        qt = info.get('quoteType', '')
        ln = info.get('longName', '') or info.get('shortName', '')
        
        if len(hist) == 0 or qt == 'NONE' or not qt:
            delisted.append((cid, name, ticker, '상장폐지/데이터없음'))
            print(f"  ❌ [{cid}] {name} ({ticker}) - 상장폐지 (quoteType={qt})")
        else:
            price = hist['Close'].iloc[-1] if len(hist) > 0 else 0
            active.append((cid, name, ticker, price))
            print(f"  ✅ [{cid}] {name} ({ticker}) - 활성 ${price:.2f}")
    except Exception as e:
        delisted.append((cid, name, ticker, f'오류: {e}'))
        print(f"  ⚠️ [{cid}] {name} ({ticker}) - 오류: {e}")

print(f"\n=== 결과 ===")
print(f"활성: {len(active)}개 / 상장폐지: {len(delisted)}개")
print(f"\n상장폐지 목록:")
for d in delisted:
    print(f"  [{d[0]}] {d[1]} ({d[2]}): {d[3]}")
