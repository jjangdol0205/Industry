import requests
from bs4 import BeautifulSoup
import re
import json

def test_macrotrends(ticker):
    # Macrotrends URL format: https://www.macrotrends.net/stocks/charts/NVDA/nvidia/revenue
    url = f"https://www.macrotrends.net/stocks/charts/{ticker}/nvidia/revenue"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    
    # We look for the data array in the script tags
    soup = BeautifulSoup(response.text, 'html.parser')
    scripts = soup.find_all('script')
    for s in scripts:
        if s.string and 'var originalData' in s.string:
            print("Found originalData!")
            # Extract data using regex
            match = re.search(r'var originalData = (\[.*?\]);', s.string, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                print(f"Found {len(data)} rows.")
                print("Sample:", data[:3])
                return

    print("Data not found.")

test_macrotrends('NVDA')
