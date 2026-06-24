import yfinance as yf

for t in ['XYZ', 'SQ', 'BLOCK', 'BRPHF', 'GLXY', 'GXDF']:
    try:
        info = yf.Ticker(t).info
        name = info.get('longName') or info.get('shortName') or '?'
        price = info.get('currentPrice') or info.get('regularMarketPrice') or 'N/A'
        mktcap = info.get('marketCap')
        mc_str = f"${mktcap/1e9:.1f}B" if mktcap else 'N/A'
        if name != '?':
            print(f"[OK] {t}: {name} | price={price} | mktcap={mc_str}")
        else:
            print(f"[?]  {t}: no data")
    except Exception as e:
        print(f"[ERR] {t}: {e}")
