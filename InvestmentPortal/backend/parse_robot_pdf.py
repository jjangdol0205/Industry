import pdfplumber
import os
import google.generativeai as genai

# Setup Gemini
api_key = os.environ.get("GOOGLE_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)

pdf_path = r"D:\Industry\산업자료\2. 로봇\로봇 산업.pdf"

print("Extracting text from PDF...")
text = ""
with pdfplumber.open(pdf_path) as pdf:
    # Just read the first 5 pages for summary to save tokens and time, or all if small.
    # Let's read first 10 pages.
    pages_to_read = min(len(pdf.pages), 10)
    for i in range(pages_to_read):
        page_text = pdf.pages[i].extract_text()
        if page_text:
            text += page_text + "\n"

print(f"Extracted {len(text)} characters from first {pages_to_read} pages.")

prompt = """
You are an expert investment analyst. Review the following text extracted from a Robot Industry Report.
Please generate a JSON object containing:
1. "summary": A detailed markdown overview of the robot industry in Korean (including standards, competitive dynamics, value chain shifts, and market size/outlook). Format with clear headers, bullet points, and strong tags (like the Autonomous Driving summary).
2. "tag": The tag for this industry (use "로봇").
3. "value_chains": A list of value chain nodes. Each node should have a "name" and a "desc" (in Korean).
4. "companies": A list of US listed companies active in this industry. For each company, provide:
   - "name": Company name (e.g. "Intuitive Surgical")
   - "ticker": Ticker symbol (e.g. "ISRG")
   - "role": Brief Korean description of their role/position in the robot industry.
   - "growth": Brief Korean description of their future growth potential in robotics.
   - "node": The name of the value chain node they belong to (must match one of the names in your "value_chains" list).

Ensure the response is ONLY valid JSON, no markdown formatting blocks.
"""

if api_key:
    print("Calling Gemini to analyze...")
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content([prompt, text])
    print(response.text)
    # Save results to a temporary JSON file
    with open("robot_extracted.json", "w", encoding="utf-8") as f:
        f.write(response.text)
else:
    print("No GOOGLE_API_KEY found. Generating fallback data.")
