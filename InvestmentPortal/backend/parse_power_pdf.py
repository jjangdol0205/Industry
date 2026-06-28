import pdfplumber
import os

pdf_path = r'D:\Industry\산업자료\6. 전력 인프라\전력 인프르 산업.pdf'

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}\n")
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                print(f"=== Page {i+1} ===")
                print(text[:1000]) # Print first 1000 chars of each page
                print("-" * 40)
except Exception as e:
    print(f"Error reading PDF: {e}")
