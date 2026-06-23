import requests
import pandas as pd

url = "https://stockrow.com/api/companies/NVDA/financials.xlsx?dimension=Q&section=Income%20Statement&sort=desc"
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    with open('nvda.xlsx', 'wb') as f:
        f.write(response.content)
    df = pd.read_excel('nvda.xlsx')
    print("Columns:", df.columns[:5])
    print("Rows:", len(df))
else:
    print("Status:", response.status_code)
