import pandas as pd
from bs4 import BeautifulSoup

filepath = r"C:\Users\infomax\.gemini\antigravity\brain\6531c14d-086c-46bb-88d5-04b1428d67ce\.system_generated\steps\244\content.md"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

try:
    tables = pd.read_html(content)
    print(f"Found {len(tables)} tables.")
    for i, t in enumerate(tables):
        print(f"Table {i}:")
        print(t.head())
except Exception as e:
    print("Error:", e)
