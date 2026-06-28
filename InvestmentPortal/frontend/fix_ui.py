import os
import re

app_file = r'D:\Industry\InvestmentPortal\frontend\src\App.jsx'
with open(app_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix current_price
text = text.replace(
    "`$${p.current_price?.toFixed(2)}`", 
    "fDollar(p.current_price, company?.ticker)"
)
text = text.replace(
    "${p.current_price?.toFixed(2)}",
    "{fDollar(p.current_price, company?.ticker)}"
)

# Fix market cap
text = text.replace(
    "`$${(p.market_cap/1e9).toFixed(1)}B`",
    "fB(p.market_cap, company?.ticker)"
)

# Fix headers
text = text.replace(
    'title="손익 추이 (Income Statement History — $B)"',
    'title="손익 추이 (단위: 십억 달러 / 한국 억원)"'
)
text = text.replace(
    'title="현금흐름 (Cash Flow — $B)"',
    'title="현금흐름 (단위: 십억 달러 / 한국 억원)"'
)
text = text.replace(
    'title="재무상태표 (Balance Sheet — $B)"',
    'title="재무상태표 (단위: 십억 달러 / 한국 억원)"'
)
text = text.replace(
    '매출 $1에서 남는 이익',
    '매출 1단위에서 남는 이익'
)
text = text.replace(
    '📊 수익 폭포 차트 (Profit Waterfall) — $B',
    '📊 수익 폭포 차트 (Profit Waterfall)'
)
text = text.replace(
    'value={p.market_cap ? fB(p.market_cap, company?.ticker) : \'-\'}',
    'value={fB(p.market_cap, company?.ticker)}'
)
# Note: previous replace was '`$${(p.market_cap/1e9).toFixed(1)}B`'

with open(app_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed UI hardcoded strings.")
