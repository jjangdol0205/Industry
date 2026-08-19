import sqlite3
import json
import os
import yfinance as yf
from datetime import datetime

def update_all_prices():
    print("=== Fast Batch Stock Price Fetcher ===")
    now_str = datetime.now().strftime("%Y-%m-%d")

    # 1. Load database & JSON files
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
    if isinstance(universe_data, list):
        for comp in universe_data:
            if isinstance(comp, dict) and comp.get('ticker'):
                ticker_set.add(comp['ticker'].upper().strip())

    ticker_list = sorted(list(ticker_set))
    print(f"Downloading batch prices for {len(ticker_list)} tickers...")

    # Batch download 1y history for 52w High & current price
    download_df = yf.download(ticker_list, period="1y", group_by="ticker", progress=False)

    price_map = {}
    for tk in ticker_list:
        try:
            df = download_df[tk] if len(ticker_list) > 1 else download_df
            close_s = df['Close'].dropna()
            high_s = df['High'].dropna() if 'High' in df else close_s
            if not close_s.empty:
                curr = float(close_s.iloc[-1])
                high52 = float(high_s.max()) if not high_s.empty else curr
                high52 = max(high52, curr)
                mdd = round(((curr - high52) / high52) * 100, 2)
                price_map[tk] = {
                    'current_price': round(curr, 2) if not (tk.endswith('.KS') or tk.endswith('.KQ')) else int(curr),
                    'high_52w': round(high52, 2) if not (tk.endswith('.KS') or tk.endswith('.KQ')) else int(high52),
                    'mdd_pct': mdd
                }
        except Exception:
            pass

    print(f"Successfully processed {len(price_map)} tickers.")

    # Update DB
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

    # Update deepdive_data
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
            citem['current_price'] = pinfo['current_price']
            updated_deepdive += 1

    for loc in ['InvestmentPortal/backend/universal_deepdive_data.json',
                'InvestmentPortal/frontend/public/universal_deepdive_data.json',
                'InvestmentPortal/frontend/dist/universal_deepdive_data.json']:
        if os.path.exists(os.path.dirname(loc)):
            with open(loc, 'w', encoding='utf-8') as f:
                json.dump(deepdive_data, f, ensure_ascii=False, indent=2)

    # Update universe_data
    updated_universe = 0
    if isinstance(universe_data, list):
        for comp in universe_data:
            if isinstance(comp, dict):
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

    print(f"Finished! DB: {updated_db} | Deepdive: {updated_deepdive} | Universe: {updated_universe}")

if __name__ == '__main__':
    update_all_prices()
