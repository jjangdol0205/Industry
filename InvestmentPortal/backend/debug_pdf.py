import pdfplumber

pdf_path = r"D:\Industry\산업자료\2. 로봇\로봇 산업.pdf"
with pdfplumber.open(pdf_path) as pdf:
    print("Total pages:", len(pdf.pages))
    for i in range(min(5, len(pdf.pages))):
        text = pdf.pages[i].extract_text()
        print(f"Page {i} characters: {len(text) if text else 0}")
