import os
import re

agent_file = r'D:\Industry\InvestmentPortal\backend\agent_harness.py'
with open(agent_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace fmt_b definition
old_fmt_b = """def fmt_b(v):
    v = safe_float(v)
    return f"${v/1e9:.2f}B" if v is not None else "N/A"
"""

new_fmt_b = """def fmt_b(v, ticker=''):
    v = safe_float(v)
    if v is None: return "N/A"
    if ticker.endswith('.KS') or ticker.endswith('.KQ'):
        return f"₩{v/1e8:,.0f}억"
    return f"${v/1e9:.2f}B"
"""

if old_fmt_b in text:
    text = text.replace(old_fmt_b, new_fmt_b)

# Replace target_str formatting
# original: target_str = f"${target_5y:.2f}" if target_5y else "N/A"
# new: target_str = f"₩{target_5y:,.0f}" if target_5y and (ticker ends with KS/KQ) else f"${target_5y:.2f}"

def repl_target_str(m):
    # m.group(0) is the entire line
    # We'll replace it manually
    return """        is_krw = company.ticker.endswith('.KS') or company.ticker.endswith('.KQ')
        target_str = (f"₩{target_5y:,.0f}" if is_krw else f"${target_5y:.2f}") if target_5y else "N/A\""""

text = re.sub(r'        target_str = f"\$\{target_5y:\.2f\}" if target_5y else "N/A"', repl_target_str, text)

# Also fix the fcf_str and rev_str calls to use ticker
text = text.replace('cap_str = fmt_b(cap)', 'cap_str = fmt_b(cap, company.ticker)')
text = text.replace('fcf_str = fmt_b(fcf_val)', 'fcf_str = fmt_b(fcf_val, company.ticker)')
text = text.replace('rev_str = fmt_b(rev_val)', 'rev_str = fmt_b(rev_val, company.ticker)')

with open(agent_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated agent_harness.py")
