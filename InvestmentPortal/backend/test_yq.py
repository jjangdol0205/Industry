from yahooquery import Ticker

t = Ticker('NVDA')
df = t.income_statement(frequency='a')
print(df.columns.tolist() if df is not None else "No data")

df_q = t.income_statement(frequency='q')
print(df_q.columns.tolist() if df_q is not None else "No data")
