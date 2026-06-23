from yahooquery import Ticker

t = Ticker('NVDA')
df = t.income_statement(frequency='q')
print(f"Number of quarters found: {len(df)}")
if len(df) > 0:
    if 'symbol' in df.index.names:
        df = df.reset_index()
    print("Dates:")
    for d in df['asOfDate']:
        print(d)
