import urllib.request
import json
import time

time.sleep(25)

data = json.loads(urllib.request.urlopen('https://industry-l08j.onrender.com/api/portfolio/universe').read().decode('utf-8'))
items = data['universe']

none_mdd = [x['name'] for x in items if x['mdd_pct'] is None]
none_h52 = [x['name'] for x in items if x['high_52w'] is None]
core = [x for x in items if x['portfolio_tier'] == 'Core']
sat = [x for x in items if x['portfolio_tier'] == 'Satellite']
buy = [x for x in items if x['buy_signal'] and 'BUY_READY' in x['buy_signal']]

print(f"전체: {len(items)}개")
print(f"mdd_pct=None: {len(none_mdd)}개 {none_mdd[:3]}")
print(f"high_52w=None: {len(none_h52)}개 {none_h52[:3]}")
print(f"Core: {len(core)}개, Satellite: {len(sat)}개")
print(f"BUY_READY 매수가능: {len(buy)}개")
for x in buy[:7]:
    mdd_str = f"{round(x['mdd_pct'],1)}%" if x['mdd_pct'] else "None"
    print(f"  [{x['portfolio_tier']}] {x['name']} | {x['ticker']} | 52w:{x['high_52w']} | MDD:{mdd_str}")
