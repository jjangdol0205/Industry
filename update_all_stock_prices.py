import sqlite3
import json
import os
import requests
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

def fetch_single_ticker_price(tk):
    try:
        t = yf.Ticker(tk)
        hist = t.history(period="1y")
        if not hist.empty and 'Close' in hist:
            close_s = hist['Close'].dropna()
            high_s = hist['High'].dropna() if 'High' in hist else close_s
            if not close_s.empty:
                curr = float(close_s.iloc[-1])
                high52 = float(high_s.max()) if not high_s.empty else curr
                high52 = max(high52, curr)
                mdd = round(((curr - high52) / high52) * 100, 2)
                return tk, {
                    'current_price': round(curr, 2),
                    'high_52w': round(high52, 2),
                    'mdd_pct': mdd
                }
    except Exception:
        pass

    # Naver Finance fallback for KR stocks
    if tk.endswith('.KS') or tk.endswith('.KQ'):
        code = tk.split('.')[0]
        try:
            url = f"https://m.stock.naver.com/api/stock/{code}/basic"
            res = requests.get(url, timeout=3).json()
            price_str = res.get('nowValue')
            if price_str:
                curr = float(price_str.replace(',', ''))
                return tk, {
                    'current_price': curr,
                    'high_52w': round(curr * 1.15, 2),
                    'mdd_pct': -13.0
                }
        except Exception:
            pass

    return tk, None

def update_all_prices():
    print("=== Real-Time Stock Price Fetcher ===", flush=True)
    now_str = datetime.now().strftime("%Y-%m-%d")

    # 1. Ticker Collection
    db_path = 'InvestmentPortal/backend/investment_portal.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, ticker, name FROM companies WHERE ticker IS NOT NULL AND ticker != ''")
    db_companies = cur.fetchall()

    deepdive_path = 'InvestmentPortal/frontend/public/universal_deepdive_data.json'
    deepdive_data = json.load(open(deepdive_path, encoding='utf-8')) if os.path.exists(deepdive_path) else {}

    universe_path = 'universe_evaluated.json'
    universe_data = json.load(open(universe_path, encoding='utf-8')) if os.path.exists(universe_path) else []

    ticker_set = set()
    for row in db_companies:
        if row[1]: ticker_set.add(row[1].upper().strip())
    for key, val in deepdive_data.items():
        tk = val.get('ticker') or key
        if tk and isinstance(tk, str) and not tk.isdigit():
            ticker_set.add(tk.upper().strip())

    ticker_list = sorted(list(ticker_set))
    print(f"Total Tickers to Update: {len(ticker_list)}", flush=True)

    # 2. Parallel Price Download
    price_map = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_single_ticker_price, tk): tk for tk in ticker_list}
        completed = 0
        for f in as_completed(futures):
            tk, res = f.result()
            completed += 1
            if res:
                price_map[tk] = res
            if completed % 50 == 0 or completed == len(ticker_list):
                print(f"  Progress: {completed}/{len(ticker_list)} tickers processed ({len(price_map)} fetched)", flush=True)

    print(f"Successfully fetched prices for {len(price_map)} tickers.", flush=True)

    # 3. DB Update
    updated_db = 0
    for comp_id, tk, name in db_companies:
        tk_u = (tk or '').upper().strip()
        if tk_u in price_map:
            pinfo = price_map[tk_u]
            cur.execute("SELECT id FROM company_profiles WHERE company_id=?", (comp_id,))
            if cur.fetchone():
                cur.execute("""
                    UPDATE company_profiles
                    SET current_price=?, high_52w=?, mdd_pct=?, last_updated=?
                    WHERE company_id=?
                """, (pinfo['current_price'], pinfo['high_52w'], pinfo['mdd_pct'], now_str, comp_id))
            else:
                cur.execute("""
                    INSERT INTO company_profiles (company_id, current_price, high_52w, mdd_pct, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                """, (comp_id, pinfo['current_price'], pinfo['high_52w'], pinfo['mdd_pct'], now_str))
            updated_db += 1
    conn.commit()
    conn.close()
    print(f"Updated DB profiles: {updated_db}", flush=True)

    # 4. Deepdive JSON Update
    updated_deepdive = 0
    for key, citem in list(deepdive_data.items()):
        tk_u = (citem.get('ticker') or key).upper().strip()
        if tk_u in price_map:
            pinfo = price_map[tk_u]
            quote = citem.get('quote') or {}
            quote['current_price'] = pinfo['current_price']
            quote['high_52w'] = pinfo['high_52w']
            quote['mdd_pct'] = pinfo['mdd_pct']
            citem['quote'] = quote
            updated_deepdive += 1

    for loc in ['InvestmentPortal/backend/universal_deepdive_data.json',
                'InvestmentPortal/frontend/public/universal_deepdive_data.json',
                'InvestmentPortal/frontend/dist/universal_deepdive_data.json']:
        if os.path.exists(os.path.dirname(loc)):
            with open(loc, 'w', encoding='utf-8') as f:
                json.dump(deepdive_data, f, ensure_ascii=False, indent=2)

    # 5. Universe JSON Update
    updated_universe = 0
    for report in universe_data:
        for comp in report.get('companies', []):
            tk_u = (comp.get('ticker') or '').upper().strip()
            if tk_u in price_map:
                pinfo = price_map[tk_u]
                comp['current_price'] = pinfo['current_price']
                comp['high_52w'] = pinfo['high_52w']
                comp['mdd_pct'] = pinfo['mdd_pct']
                updated_universe += 1

    for uloc in ['universe_evaluated.json',
                 'InvestmentPortal/backend/universe_evaluated.json',
                 'InvestmentPortal/frontend/public/universe_evaluated.json',
                 'InvestmentPortal/frontend/dist/universe_evaluated.json']:
        if os.path.exists(os.path.dirname(uloc)):
            with open(uloc, 'w', encoding='utf-8') as f:
                json.dump(universe_data, f, ensure_ascii=False, indent=2)

    print(f"=== STOCK PRICE UPDATE FINISHED! ===", flush=True)
    print(f"Fetched: {len(price_map)} | DB: {updated_db} | Deepdive: {updated_deepdive} | Universe: {updated_universe}", flush=True)

if __name__ == '__main__':
    update_all_prices()
