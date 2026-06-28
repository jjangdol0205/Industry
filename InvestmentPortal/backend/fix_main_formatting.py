import os
import re

main_file = r'D:\Industry\InvestmentPortal\backend\main.py'
with open(main_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace mktcap logic
def repl_mktcap(m):
    return """    is_krw = company.ticker.endswith('.KS') or company.ticker.endswith('.KQ')
    if p and p.market_cap:
        if is_krw:
            mktcap = f"₩{(p.market_cap/1e8):.0f}억"
        else:
            mktcap = f"${(p.market_cap/1e9):.1f}B"
    else:
        mktcap = "N/A\""""

text = re.sub(r'    mktcap = f"\$\{\(p\.market_cap/1e9\):\.1f\}B" if p and p\.market_cap else "N/A"', repl_mktcap, text)

with open(main_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated main.py")
