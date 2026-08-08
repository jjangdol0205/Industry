# -*- coding: utf-8 -*-
import yfinance as yf
import requests

tickers = ['ASML', '207940.KS', 'NVDA', 'TSM', '192820.KS', '003230.KS', 'RKLB', '018290.KQ']

print("--- YFINANCE REAL TIME CHECK ---")
for sym in tickers:
    t = yf.Ticker(sym)
    hist = t.history(period="1y")
    if not hist.empty:
        curr = hist['Close'].iloc[-1]
        high52 = hist['High'].max()
        mdd = ((curr - high52) / high52) * 100
        print(f"{sym}: 현재가 {curr:,.2f} | 52주최고가 {high52:,.2f} | MDD: {mdd:.2f}%")

print("\n--- NAVER FINANCE CHECK FOR KOREAN STOCKS ---")
# 네이버 금융 실시간 주가 API (한국 주식용)
for sym in ['207940', '192820', '003230', '018290']:
    url = f"https://m.stock.naver.com/api/stock/{sym}/basic"
    res = requests.get(url).json()
    price = res.get('nowValue')
    print(f"네이버금융 {sym}: 현재가 {price} 원")
