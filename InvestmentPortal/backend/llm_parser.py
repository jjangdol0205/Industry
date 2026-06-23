import os
from pydantic import BaseModel
import google.generativeai as genai

# NOTE: Set your GOOGLE_API_KEY environment variable.
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", "YOUR_API_KEY_HERE"))

# We can use pdfplumber to extract text or just use genai File API.
# For simplicity, if we have text:
def parse_industry_report(text_content: str):
    prompt = """
    You are an expert financial analyst. Read the following industry report text.
    Please extract:
    1. A summary of the industry value chain nodes.
    2. A list of US listed companies mentioned or strongly implied in this value chain.
    Format your response cleanly.
    """
    
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content([prompt, text_content])
    return response.text
